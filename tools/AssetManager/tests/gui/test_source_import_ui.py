"""Actual file selection, worker completion, partial delivery and safe closing."""

from time import monotonic, sleep

from PIL import Image
import pytest

pytest.importorskip("PySide6.QtWidgets", reason="Qt/GUI-Systembibliotheken fehlen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QFileDialog, QMessageBox, QPushButton

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.source_import import SourceImportService
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.sources import expected_sources
from etherfood_studio.ui.source_import_dialog import SourceImportDialog


@pytest.fixture
def delivery(tmp_path, qt_app):
    root = tmp_path / "project"
    root.mkdir()
    project = ProjectService.new(root, "Quellen")
    assets = AssetService(project)
    asset = project.create_card("asset", "Testfigur", next(c.id for c in project.cards()
                                                           if c.kind == "global"))
    data = default_definition().to_data()
    data["directions"] = ["SW", "SO"]
    assets.configure(asset.id, data, asset.revision_no)
    dialog = SourceImportDialog(assets, asset.id)
    dialog.show()
    qt_app.processEvents()
    yield project, dialog
    dialog.close()
    wait_finished(dialog, qt_app)
    dialog.deleteLater()
    qt_app.processEvents()
    project.catalog.close()


def wait_finished(dialog, qt_app):
    deadline = monotonic() + 30
    while dialog.worker is not None and monotonic() < deadline:
        QTest.qWait(10)
        sleep(0.001)  # Let Python workers progress while the test drives Qt events.
        qt_app.processEvents()
    assert dialog.worker is None


def test_choose_horizontal_sheet_import_partial_and_reopen(delivery, tmp_path, qt_app, monkeypatch):
    project, dialog = delivery
    source = tmp_path / "hero_walk_SW_16x1.png"
    Image.new("RGBA", (64, 4), (30, 170, 60, 255)).save(source)
    monkeypatch.setattr(QFileDialog, "getOpenFileNames", lambda *args: ([str(source)], ""))
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    QTest.mouseClick(dialog.choose, Qt.MouseButton.LeftButton)
    assert dialog.table.cellWidget(0, 4).currentText() == "16x1"
    assert dialog.table.cellWidget(0, 2).currentData() == "SW"
    QTest.mouseClick(dialog.check_button, Qt.MouseButton.LeftButton)
    wait_finished(dialog, qt_app)
    assert dialog.plan and dialog.import_button.isEnabled()
    QTest.mouseClick(dialog.import_button, Qt.MouseButton.LeftButton)
    wait_finished(dialog, qt_app)
    assert dialog.changed and "1/2" in dialog.deliveries.summary.text()
    service = SourceImportService(AssetService(project))
    revision, = service.revisions(dialog.identifier)
    assert revision.data["grid"] == [16, 1]
    assert "nicht erzeugt" not in dialog.status.text()
    reopened = SourceImportDialog(AssetService(project), dialog.identifier)
    assert "1/2" in reopened.deliveries.summary.text()
    assert reopened.bundles.topLevelItemCount() == 1
    assert "1/2" in reopened.bundles.topLevelItem(0).text(1)
    assert reopened.table.rowCount() == 0
    group = reopened.deliveries.matrix.topLevelItem(0)
    assert not group.isExpanded()
    assert group.child(0).text(3) == "16×1"
    assert group.child(0).childCount() == 1
    reopened.close()
    reopened.deleteLater()


def test_grid_change_invalidates_preview_and_conflict_requires_consent(
        delivery, tmp_path, qt_app, monkeypatch):
    project, dialog = delivery
    source = tmp_path / "hero_SW.png"
    Image.new("RGBA", (64, 16), (30, 170, 60, 255)).save(source)
    dialog.add_files([source])
    dialog.table.cellWidget(0, 4).setCurrentText("16x1")
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    errors = []
    monkeypatch.setattr("etherfood_studio.ui.source_import_dialog.show_error",
                        lambda parent, error: errors.append(error))
    dialog.prepare()
    wait_finished(dialog, qt_app)
    dialog.table.cellWidget(0, 4).setCurrentText("1x16")
    assert dialog.plan is None and not dialog.import_button.isEnabled()
    dialog.prepare()
    wait_finished(dialog, qt_app)
    dialog.import_plan()
    wait_finished(dialog, qt_app)
    service = SourceImportService(AssetService(project))
    original, = service.revisions(dialog.identifier)
    assert original.data["grid"] == [1, 16]
    dialog.add_files([source])
    dialog.table.cellWidget(0, 4).setCurrentText("1x16")
    dialog.prepare()
    wait_finished(dialog, qt_app)
    dialog.import_plan()
    wait_finished(dialog, qt_app)
    assert errors[-1].code == "conflict"
    assert len(service.revisions(dialog.identifier)) == 1
    dialog.replace_active.setChecked(True)
    dialog.prepare()
    wait_finished(dialog, qt_app)
    dialog.import_plan()
    wait_finished(dialog, qt_app)
    assert len(service.revisions(dialog.identifier)) == 2
    panel = dialog.deliveries
    panel.show_pose(original.data["slot"]["pose_id"])
    panel.matrix.topLevelItem(0).child(0).setExpanded(True)
    QTest.mouseClick(panel.findChild(QPushButton, "activate_" + original.id),
                     Qt.MouseButton.LeftButton)
    assert next(iter(service.active(dialog.identifier).values())).id == original.id


def test_closing_running_import_waits_for_safe_cancel(delivery, tmp_path, qt_app, monkeypatch):
    project, dialog = delivery
    before = project.catalog.export_snapshot()
    source = tmp_path / "hero_SW.png"
    Image.new("RGBA", (64, 4)).save(source)
    dialog.add_files([source])

    def slow_prepare(self, *args, cancelled, **kwargs):
        deadline = monotonic() + 5
        while not cancelled() and monotonic() < deadline:
            QTest.qSleep(5)
        raise StudioError("cancelled", "Testabbruch")

    monkeypatch.setattr(SourceImportService, "prepare", slow_prepare)
    dialog.prepare()
    dialog.close()
    wait_finished(dialog, qt_app)
    assert not dialog.isVisible()
    assert not dialog.changed
    assert project.catalog.export_snapshot() == before


def test_pose_and_single_replacement_buttons_keep_other_directions(
        delivery, tmp_path, qt_app, monkeypatch):
    project, dialog = delivery
    errors = []
    monkeypatch.setattr("etherfood_studio.ui.source_import_dialog.show_error",
                        lambda parent, error: errors.append(str(error)))
    paths = []
    for direction in ("SW", "SO"):
        path = tmp_path / f"master_{direction}_4x4.png"
        Image.new("RGBA", (16, 16), (30, 170, 60, 255)).save(path)
        paths.append(str(path))
    monkeypatch.setattr(QFileDialog, "getOpenFileNames", lambda *args: (paths, ""))
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    dialog.choose_files()
    assert all(dialog.table.cellWidget(row, 4).currentText() == "4x4" for row in range(2))
    dialog.prepare()
    wait_finished(dialog, qt_app)
    assert dialog.plan is not None, errors
    dialog.import_plan()
    wait_finished(dialog, qt_app)
    service = SourceImportService(AssetService(project))
    required = expected_sources(dialog.definition)
    original = {key: value.id for key, value in service.active(dialog.identifier).items()}
    pose = required[0].pose_id
    group = dialog.deliveries.matrix.topLevelItem(0)
    assert not group.isExpanded() and "2/2" in group.text(2)
    assert group.child(0).text(3) == "4×4" and group.child(0).text(4) == "16"
    QTest.mouseClick(dialog.deliveries.findChild(QPushButton, "replace_pose_" + pose),
                     Qt.MouseButton.LeftButton)
    assert dialog.keys == required and dialog.table.rowCount() == 2
    dialog.replace_active.setChecked(True)
    dialog.prepare()
    wait_finished(dialog, qt_app)
    assert dialog.plan is not None, errors
    assert dialog.plan.required_keys == required
    dialog.import_plan()
    wait_finished(dialog, qt_app)
    assert len(service.revisions(dialog.identifier)) == 4
    previous = {key: value.id for key, value in service.active(dialog.identifier).items()}
    assert all(previous[key] != original[key] for key in required)
    paths[:] = paths[:1]
    dialog.deliveries.show_pose(pose)
    QTest.mouseClick(dialog.deliveries.findChild(QPushButton,
                                               "replace_source_" + required[0].token),
                     Qt.MouseButton.LeftButton)
    assert dialog.keys == (required[0],)
    dialog.replace_active.setChecked(True)
    dialog.prepare()
    wait_finished(dialog, qt_app)
    assert dialog.plan is not None, errors
    dialog.import_plan()
    wait_finished(dialog, qt_app)
    active = service.active(dialog.identifier)
    assert active[required[0]].id != previous[required[0]]
    assert active[required[1]].id == previous[required[1]]


def test_many_revisions_stay_in_one_collapsed_pose_bundle(delivery, tmp_path, qt_app, monkeypatch):
    project, dialog = delivery
    path = tmp_path / "hero_SW_4x4.png"
    Image.new("RGBA", (16, 16)).save(path)
    dialog.add_files([path])
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    dialog.prepare()
    wait_finished(dialog, qt_app)
    dialog.import_plan()
    wait_finished(dialog, qt_app)
    service = SourceImportService(AssetService(project))
    original, = service.revisions(dialog.identifier)
    with project.catalog.transaction():
        for index in range(200):
            project.catalog.create("source_revision", f"synthetic-{index}.png", dialog.identifier,
                                   original.data)
    dialog.deliveries.refresh()
    dialog.refresh_bundles()
    assert dialog.bundles.topLevelItemCount() == 1
    assert dialog.bundles.topLevelItem(0).childCount() == 0
    assert "201 Revisionen" in dialog.bundles.topLevelItem(0).text(2)
    group = dialog.deliveries.matrix.topLevelItem(0)
    assert dialog.deliveries.matrix.topLevelItemCount() == 1 and not group.isExpanded()
    assert group.child(0).childCount() == 201
    dialog.deliveries.show_pose(dialog.definition.poses[0].id)
    group.child(0).setExpanded(True)
    dialog.deliveries.refresh()
    assert dialog.deliveries.matrix.topLevelItem(0).isExpanded()
    assert dialog.deliveries.matrix.topLevelItem(0).child(0).isExpanded()
    record = service.assets.asset(dialog.identifier)
    definition = service.assets.definition(record.id).to_data()
    definition["directions"] = ["SO"]
    service.assets.configure(record.id, definition, record.revision_no)
    dialog.deliveries.refresh()
    group = dialog.deliveries.matrix.topLevelItem(0)
    unused = next(group.child(i) for i in range(group.childCount())
                  if group.child(i).text(0) == "SW")
    assert "Nicht erforderlich" in unused.text(2) and "Importiert" in unused.text(2)
