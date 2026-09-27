"""Real Qt profile/assignment editing and image builds through the shared planner."""

from copy import deepcopy
import json
import time

from PIL import Image
import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QCoreApplication, QEvent, QTimer, Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.profile_service import ProfileService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.source_import import SourceImportService, SourceSpec
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.sources import expected_sources
from etherfood_studio.storage.blob_store import file_hash
from etherfood_studio.ui import pipeline_auxiliary as ui


def wait_for(predicate, timeout=30):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(0.005)
    assert predicate()


@pytest.fixture
def project(qt_app, tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    value = ProjectService.new(root, "Pipeline-Dialoge")
    yield value
    for widget in QApplication.topLevelWidgets():
        if not isinstance(widget, (ui.ProfileDialog, ui.AssignmentDialog, ui.PipelineRunDialog)):
            continue
        if isinstance(widget, ui.PipelineRunDialog):
            widget.cancel()
            if widget.preview_worker:
                widget.preview_worker.cancelled.set()
            wait_for(lambda: widget.worker is None and widget.preview_worker is None)
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qt_app.processEvents()
    value.catalog.close()


def select(combo, value):
    index = combo.findData(value)
    assert index >= 0
    combo.setCurrentIndex(index)


def make_asset(project, tmp_path, *, animated=False, source=True):
    assets = AssetService(project)
    data = default_definition("effect" if animated else "texture").to_data()
    if animated:
        data["poses"] = data["poses"][:1]
        data["poses"][0]["fps"] = 8.0
    global_id = next(r.id for r in project.cards() if r.kind == "global")
    asset = assets.create("Animation" if animated else "Textur", global_id, data)
    if not source:
        return asset, None
    count = 16 if animated else 1
    path = tmp_path / (asset.id + ".png")
    image = Image.new("RGBA", (count * 32, 16), (50, 180, 100, 255))
    for index in range(count):
        image.paste((index * 15, 180, 100, 255), (index * 32, 0, (index + 1) * 32, 16))
    image.save(path)
    imports = SourceImportService(assets)
    key = expected_sources(assets.definition(asset.id))[0]
    plan = imports.prepare(asset.id, asset.revision_no, [SourceSpec(path, key, count, 1, count)])
    imports.import_plan(plan)
    return asset, path


def confirm(monkeypatch, response=QMessageBox.StandardButton.Yes):
    monkeypatch.setattr(ui.QMessageBox, "question", lambda *_args, **_kwargs: response)


def test_profiles_show_proportions_and_preserve_keys(project):
    dialog = ui.ProfileDialog(project)
    assert dialog.table.rowCount() == 5
    assert dialog.table.item(1, 8).text() == "256 × 128 px"
    assert dialog.table.item(3, 8).text() == "128 × 64 px"
    assert dialog.table.item(4, 8).text() == "115 × 58 px"
    assert not dialog.table.item(0, 0).flags() & Qt.ItemFlag.ItemIsEditable
    assert dialog.table.cellWidget(4, 7).currentData() == "pixel_high"
    assert not dialog.table.cellWidget(4, 6).isEnabled()
    dialog.table.cellWidget(0, 5).setValue(0.5)
    assert dialog.table.item(0, 8).text() == "256 × 128 px"
    select(dialog.table.cellWidget(0, 4), "max_edge")
    dialog.table.cellWidget(0, 5).setValue(128)
    assert dialog.table.item(0, 8).text() == "128 × 64 px"
    for row in (1, 2):
        dialog.table.cellWidget(row, 2).setChecked(False)
    dialog.add_profile()
    dialog.table.item(5, 0).setText("menu_preview")
    dialog.table.item(5, 1).setText("Menüvorschau")
    dialog.save()
    assert dialog.result() == ui.QDialog.DialogCode.Accepted
    profiles = ProfileService(project).profiles()
    assert set(profiles) == {"comic_high", "comic_mid", "comic_low", "pixel_high",
                             "pixel_low", "menu_preview"}
    assert sum(p["enabled"] for p in profiles.values()) == 4
    assert profiles["menu_preview"]["name"] == "Menüvorschau"
    loaded = ProjectService.open(project.catalog.path.parent, read_only=True)
    assert ProfileService(loaded).profiles() == profiles
    loaded.catalog.close()


def test_profiles_invalid_edit_stale_save_and_unsaved_guard(project, monkeypatch):
    errors = []
    monkeypatch.setattr(ui, "show_error", lambda _parent, error: errors.append(str(error)))
    dialog = ui.ProfileDialog(project)
    dialog.show()
    revision = project.project().revision_no
    dialog.table.item(0, 1).setText("")
    dialog.save()
    assert errors and project.project().revision_no == revision
    assert dialog.isVisible()
    dialog.table.item(0, 1).setText("Anderer Anzeigename")
    project.catalog.save(project.project(), title="Parallel geändert")
    dialog.save()
    assert len(errors) == 2
    assert ProfileService(project).profiles()["comic_high"]["name"] == "Comic High"
    confirm(monkeypatch, QMessageBox.StandardButton.No)
    dialog.reject()
    assert dialog.isVisible()
    confirm(monkeypatch)
    dialog.reject()
    assert not dialog.isVisible()


def test_profile_draft_undo_redo_does_not_write_or_remove_existing_keys(project):
    dialog = ui.ProfileDialog(project)
    original = ProfileService(project).profiles()
    revision = project.project().revision_no
    dialog.table.cellWidget(0, 5).setValue(0.25)
    assert dialog.undo_button.isEnabled()
    dialog.history(False)
    assert dialog.table.cellWidget(0, 5).value() == 1
    dialog.history(True)
    assert dialog.table.cellWidget(0, 5).value() == 0.25
    dialog.add_profile()
    assert dialog.table.rowCount() == 6
    dialog.history(False)
    assert dialog.table.rowCount() == 5
    dialog.history(True)
    assert dialog.table.rowCount() == 6
    assert not dialog.table.item(0, 0).flags() & Qt.ItemFlag.ItemIsEditable
    assert project.project().revision_no == revision
    assert ProfileService(project).profiles() == original


def test_profile_parent_later_in_table_is_preserved(project):
    service = ProfileService(project)
    profiles = list(service.profiles().values())
    custom = {**profiles[3], "key": "custom_pixel", "name": "Andere Pixelbasis", "value": 64}
    profiles.append(custom)
    profiles[4]["parent"] = custom["key"]
    service.save(profiles, project.project().revision_no)
    dialog = ui.ProfileDialog(project)
    assert dialog.values() == profiles
    assert dialog.table.item(4, 8).text() == "58 × 29 px"
    assert not dialog.commands.done


def test_profile_precision_and_invalid_sizes_are_not_silently_changed(project, monkeypatch):
    errors = []
    monkeypatch.setattr(ui, "show_error", lambda _parent, error: errors.append(str(error)))
    profiles = list(ProfileService(project).profiles().values())
    profiles[0]["value"] = 0.123456789
    profiles[1]["value"] = 1e-12
    ProfileService(project).save(profiles, project.project().revision_no)
    dialog = ui.ProfileDialog(project)
    assert dialog.values() == profiles
    assert not dialog.commands.done
    for value in (0, -1, float("inf"), float("nan"), "invalid"):
        dialog.table.cellWidget(0, 5).setValue(value)
        dialog.save()
        assert errors
        errors.clear()
    dialog.table.cellWidget(0, 5).setValue(0.5)
    select(dialog.table.cellWidget(0, 4), "max_edge")
    dialog.table.cellWidget(0, 5).setValue(128.5)
    dialog.save()
    assert errors and ProfileService(project).profiles()["comic_high"]["value"] == 0.123456789


def test_assignments_actual_types_priority_conflicts_and_undo(project, tmp_path):
    pipelines = PipelineService(project)
    recipe = pipelines.create("Grafik", "graphics")
    asset, _ = make_asset(project, tmp_path)
    dialog = ui.AssignmentDialog(project, recipe.id)
    assert dialog.types.findData("npc") >= 0
    select(dialog.mode, "type")
    select(dialog.types, "texture")
    dialog.add()
    assert pipelines.resolve(asset.id)["origin"] == "Asset-Typ-/Fähigkeitsregel"
    future, _ = make_asset(project, tmp_path, source=False)
    assert pipelines.resolve(future.id)["recipe"].id == recipe.id
    assert project.catalog.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
    select(dialog.mode, "asset")
    select(dialog.assets, asset.id)
    dialog.add()
    assert pipelines.resolve(asset.id)["origin"] == "Explizite Asset-Zuweisung"
    dialog.add()
    with pytest.raises(StudioError, match="Konflikt"):
        pipelines.resolve(asset.id)
    assert "Konflikt" in dialog.notice.text()
    assert any("Konflikt" in dialog.table.item(row, 4).text()
               for row in range(dialog.table.rowCount()))
    dialog.history(False)
    assert pipelines.resolve(asset.id)["origin"] == "Explizite Asset-Zuweisung"
    dialog.history(True)
    with pytest.raises(StudioError, match="Konflikt"):
        pipelines.resolve(asset.id)
    row = next(row for row in range(dialog.table.rowCount())
               if dialog.table.item(row, 0).text() == "Asset")
    dialog.table.setCurrentCell(row, 0)
    removed = dialog.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
    dialog.remove()
    assert project.catalog.get(removed).archived
    assert pipelines.resolve(asset.id)["recipe"].id == recipe.id


def test_assignment_overrides_only_allow_declared_parameters(project, tmp_path, monkeypatch):
    errors = []
    monkeypatch.setattr(ui, "show_error", lambda _parent, error: errors.append(str(error)))
    pipelines = PipelineService(project)
    recipe = pipelines.create("Frames", "frames")
    data = deepcopy(recipe.data["recipe"])
    token = data["steps"][1]["id"] + ".fps"
    data["overridable"] = [token]
    pipelines.save(recipe.id, data, recipe.revision_no)
    asset, _ = make_asset(project, tmp_path, animated=True)
    dialog = ui.AssignmentDialog(project, recipe.id)
    assert dialog.overrides.isEnabled()
    select(dialog.assets, asset.id)
    dialog.overrides.setPlainText(json.dumps({token: 4}))
    dialog.add()
    assert pipelines.resolve(asset.id)["data"]["steps"][1]["parameters"]["fps"] == 4
    dialog.overrides.setPlainText('{"unapproved.fps": 20}')
    dialog.add()
    assert errors and len(pipelines.assignments()) == 1
    assert "freigegeben" in errors[-1]
    dialog.overrides.setPlainText("null")
    dialog.add()
    assert "JSON-Objekt" in errors[-1] and len(pipelines.assignments()) == 1


def test_assignment_empty_type_rule_not_misreported_as_default(project, monkeypatch):
    errors = []
    monkeypatch.setattr(ui, "show_error", lambda _parent, error: errors.append(str(error)))
    pipelines = PipelineService(project)
    recipe = pipelines.create("Grafik", "graphics")
    dialog = ui.AssignmentDialog(project, recipe.id)
    assert not dialog.add_button.isEnabled()
    select(dialog.mode, "type")
    dialog.add()
    assert errors and not pipelines.assignments()
    select(dialog.mode, "default")
    dialog.add()
    assert len(pipelines.assignments()) == 1
    assert dialog.table.item(0, 0).text() == "Projektstandard"


def test_real_graphics_dialog_dry_run_results_cache_and_static_preview(project, tmp_path,
                                                                      monkeypatch):
    pipelines = PipelineService(project)
    recipe = pipelines.create("Grafik", "graphics")
    asset, original = make_asset(project, tmp_path)
    original_hash = file_hash(original)
    pipelines.assign(recipe.id, asset_id=asset.id)
    missing, _ = make_asset(project, tmp_path, source=False)
    pipelines.assign(recipe.id, asset_id=missing.id)
    excluded, _ = make_asset(project, tmp_path, source=False)
    dialog = ui.PipelineRunDialog(project, recipe.id)
    dialog.show()
    ticks = []
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start(5)
    dialog.preview()
    wait_for(lambda: dialog.worker is None)
    assert "Betroffen: 1 · Ausgeschlossen: 1 · Blockiert: 1" in dialog.summary.text()
    assert len(dialog.plans) == 1
    assert len(dialog.rows) == 3
    assert dialog.run_button.isEnabled()
    assert project.catalog.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
    confirm(monkeypatch, QMessageBox.StandardButton.No)
    dialog.execute()
    assert dialog.worker is None
    confirm(monkeypatch)
    dialog.execute()
    assert not dialog.plan_button.isEnabled()
    dialog.reject()
    assert dialog.isVisible() and "abwarten" in dialog.notice.text()
    wait_for(lambda: dialog.worker is None)
    # Closing during a run requests cancellation; do a fresh, explicitly confirmed run.
    dialog.preview()
    wait_for(lambda: dialog.worker is None)
    dialog.execute()
    wait_for(lambda: dialog.worker is None)
    assert "Erfolgreich geprüft: 1/1" in dialog.summary.text(), dialog.logs.toPlainText()
    assert ticks and file_hash(original) == original_hash
    assert dialog.reports[0]["report"]["diagnostic"] is False
    assert all(r["actual"] in {"built", "reused"} for r in dialog.reports[0]["report"]["actual"])
    parent = dialog.tree.topLevelItem(0)
    item = next(parent.child(row) for row in range(parent.childCount())
                if parent.child(row).text(0).endswith("/comic_high"))
    dialog.tree.setCurrentItem(item)
    wait_for(lambda: dialog.preview_worker is None)
    assert not dialog.image.pixmap().isNull()
    assert not dialog.preview_fps.isEnabled()
    assert not dialog.play_button.isEnabled()
    assert "fps" not in dialog.preview_metadata
    assert dialog.preview_metadata["frame_size"] == [32, 16]
    build = project.catalog.get(dialog.selected_build)
    assert ui.ResultPreviewWorker(project, build.id).resampling(build) == Image.Resampling.LANCZOS
    assert '"logical_size"' in dialog.details.toPlainText()
    dialog.preview()
    wait_for(lambda: dialog.worker is None)
    assert all(n.state == "reused" for n in dialog.plans[0].nodes)
    parent = next(dialog.tree.topLevelItem(i) for i in range(dialog.tree.topLevelItemCount())
                  if dialog.tree.topLevelItem(i).text(1) == "Betroffen")
    dialog.tree.setCurrentItem(parent.child(0))
    wait_for(lambda: dialog.preview_worker is None)
    assert dialog.preview_frames
    assert excluded.id in [r["asset_id"] for r in dialog.rows if r["state"] == "excluded"]
    timer.stop()
    dialog.close()


def test_custom_pixel_preview_uses_frozen_method_not_name(project, tmp_path):
    from etherfood_studio.application.build_planner import BuildPlanner
    from etherfood_studio.application.recipe_builds import RecipeBuildService

    profiles = ProfileService(project)
    values = list(profiles.profiles().values())
    values.append({**values[3], "key": "tiny", "name": "Eigene Pixel"})
    profiles.save(values, project.project().revision_no)
    service = PipelineService(project)
    recipe = service.create("Pixel", "graphics")
    data = deepcopy(recipe.data["recipe"])
    data["profiles"] = ["tiny"]
    service.save(recipe.id, data, recipe.revision_no)
    asset, _ = make_asset(project, tmp_path)
    service.assign(recipe.id, asset_id=asset.id)
    plan = RecipeBuildService(project).plan(asset.id)
    report = BuildPlanner(project).execute(plan)
    build = project.catalog.get(report["actual"][-1]["build_id"])
    values[-1]["method"] = "comic"
    profiles.save(values, project.project().revision_no)
    worker = ui.ResultPreviewWorker(project, build.id)
    assert worker.resampling(build) == Image.Resampling.NEAREST


def test_single_asset_disabled_targets_are_excluded_not_empty_success(project, tmp_path):
    asset, _ = make_asset(project, tmp_path, source=False)
    profiles = ProfileService(project)
    values = list(profiles.profiles().values())
    for profile in values:
        profile["enabled"] = False
    profiles.save(values, project.project().revision_no)
    service = PipelineService(project)
    recipe = service.create("Ausgeschaltet", "graphics")
    service.assign(recipe.id, asset_id=asset.id)
    dialog = ui.PipelineRunDialog(project, asset_id=asset.id)
    dialog.preview()
    wait_for(lambda: dialog.worker is None)
    assert not dialog.plans and not dialog.run_button.isEnabled()
    assert "Ausgeschlossen: 1" in dialog.summary.text()
    assert not dialog.reports


def test_asset_result_check_is_readonly_and_does_not_invent_success(project, tmp_path):
    from etherfood_studio.ui.asset_workspace import AssetWorkspace

    asset, _ = make_asset(project, tmp_path)
    workspace = AssetWorkspace(AssetService(project), asset.id)
    workspace.show()
    workspace.check_results()
    workspace.reject()  # Do not destroy a running read-only worker.
    assert workspace.pending_close
    wait_for(lambda: workspace.status_worker is None)
    assert "Kein vollständiger Bildlauf" in workspace.result_status.text()
    assert not workspace.isVisible()
    assert project.catalog.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
    workspace.deleteLater()


def test_single_asset_frame_run_frozen_settings_and_transient_preview(project, tmp_path,
                                                                     monkeypatch):
    confirm(monkeypatch)
    asset, original = make_asset(project, tmp_path, animated=True)
    original_hash = file_hash(original)
    pipelines = PipelineService(project)
    recipe = pipelines.create("Frames", "frames")
    data = deepcopy(recipe.data["recipe"])
    data["steps"][1]["parameters"].update(frames=8, fps=8, timing="keep_duration")
    recipe = pipelines.save(recipe.id, data, recipe.revision_no)
    pipelines.assign(recipe.id, asset_id=asset.id)
    dialog = ui.PipelineRunDialog(project, asset_id=asset.id)
    dialog.preview()
    wait_for(lambda: dialog.worker is None)
    snapshot = dialog.plans[0].snapshot
    data["steps"][1]["parameters"].update(frames=10, fps=15)
    changed = pipelines.save(recipe.id, data, recipe.revision_no)
    dialog.execute()
    wait_for(lambda: dialog.worker is None)
    assert "1/1" in dialog.summary.text(), dialog.logs.toPlainText()
    assert dialog.reports[0]["report"]["plan"]["snapshot"] == snapshot
    dialog.tree.setCurrentItem(dialog.tree.topLevelItem(0).child(0))
    wait_for(lambda: dialog.preview_worker is None)
    assert len(dialog.preview_frames) == 8
    assert dialog.preview_metadata["fps"] == 4
    assert dialog.preview_metadata["duration"] == 2
    assert dialog.preview_metadata["source_indices"] == list(range(0, 16, 2))
    assert dialog.preview_fps.isEnabled() and dialog.play_button.isEnabled()
    dialog.preview_fps.setValue(12)
    dialog.toggle_play()
    assert dialog.timer.isActive()
    assert dialog.timer.interval() == 83
    dialog.next_frame()
    assert dialog.frame_index == 1
    dialog.toggle_play()
    assert not dialog.timer.isActive()
    assert pipelines.recipe(recipe.id).revision_no == changed.revision_no
    assert pipelines.recipe(recipe.id).data["recipe"] == data
    assert file_hash(original) == original_hash


def test_single_asset_wrong_recipe_excluded_and_no_automatic_run(project, tmp_path):
    pipelines = PipelineService(project)
    first = pipelines.create("Wirksam", "graphics")
    second = pipelines.create("Andere", "graphics")
    asset, _ = make_asset(project, tmp_path)
    pipelines.assign(first.id, asset_id=asset.id)
    dialog = ui.PipelineRunDialog(project, second.id, asset_id=asset.id)
    dialog.preview()
    wait_for(lambda: dialog.worker is None)
    assert not dialog.plans and not dialog.run_button.isEnabled()
    assert "Ausgeschlossen: 1" in dialog.summary.text()
    assert project.catalog.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0


def test_worker_failure_is_visible_without_publishing_results(project, tmp_path, monkeypatch):
    confirm(monkeypatch)
    pipelines = PipelineService(project)
    recipe = pipelines.create("Grafik", "graphics")
    asset, _ = make_asset(project, tmp_path)
    pipelines.assign(recipe.id, asset_id=asset.id)
    dialog = ui.PipelineRunDialog(project, recipe.id)
    dialog.preview()
    wait_for(lambda: dialog.worker is None)

    def fail(*_args, **_kwargs):
        raise StudioError("integrity", "Werkzeuge seit dem Dry-run verändert")

    monkeypatch.setattr(ui.BuildPlanner, "execute", fail)
    dialog.execute()
    wait_for(lambda: dialog.worker is None)
    assert "Erfolgreich geprüft: 0/1" in dialog.summary.text()
    assert dialog.tree.topLevelItem(0).text(1) == "Fehlgeschlagen"
    assert "Werkzeuge" in dialog.logs.toPlainText()
    assert not dialog.reports and not dialog.preview_frames
    assert not any(record.kind == "build" for record in project.catalog.records())
