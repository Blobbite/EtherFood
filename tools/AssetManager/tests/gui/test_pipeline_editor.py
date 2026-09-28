"""Pipeline cards reuse Canvas gestures while recipe edits and layouts stay independent."""

from copy import deepcopy
import json

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QPointF, QSettings, Qt
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QInputDialog, QLineEdit, QMessageBox,
    QPushButton, QSpinBox, QWidget,
)

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.commands import Commands
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.pipeline_exchange import PipelineExchange
from etherfood_studio.application.plugin_service import PluginService
from etherfood_studio.application.profile_service import ProfileService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.pipeline_recipes import template
from etherfood_studio.ui.asset_workspace import AssetWorkspace
from etherfood_studio.ui.main_window import MainWindow
from etherfood_studio.ui.pipeline_auxiliary import PipelineRunDialog, ProfileDialog
from etherfood_studio.ui.pipeline_editor import PipelineEditor


@pytest.fixture
def editor(tmp_path, qt_app):
    root = tmp_path / "studio"
    root.mkdir()
    project = ProjectService.new(root, "Pipelines")
    pipeline = PipelineService(project).create("Frame-Rezept", "frames")
    dialog = PipelineEditor(project, pipeline.id)
    dialog.show()
    qt_app.processEvents()
    yield dialog
    dialog.baseline = deepcopy(dialog.state)
    dialog.reject()
    dialog.deleteLater()
    qt_app.processEvents()
    project.catalog.close()


def test_recipe_parameters_layout_save_reload_and_undo(editor, qt_app):
    record = editor.record
    node = editor.state["recipe"]["steps"][1]
    editor.select_step(node["id"])
    editor.parameter_changed(node["id"], "frames", 12)
    assert editor.state["recipe"]["steps"][1]["parameters"]["frames"] == 12
    editor.undo()
    assert editor.state["recipe"]["steps"][1]["parameters"]["frames"] == 8
    editor.redo()
    editor.move_nodes({node["id"]: {"x": 421, "y": -72}})
    assert editor.save()
    assert editor.project.catalog.get(record.id).revision_no == record.revision_no + 1
    layout = editor.project.catalog.layout(record.id)
    assert layout["pipeline_nodes"][node["id"]] == {"x": 421, "y": -72}
    before = editor.project.catalog.get(record.id)
    editor.move_nodes({node["id"]: {"x": 812, "y": 140}})
    assert editor.save()
    assert editor.project.catalog.get(record.id).revision_no == before.revision_no
    assert not any(r.kind == "build" for r in editor.project.catalog.records())
    editor.commands.undo()
    assert editor.project.catalog.layout(record.id) == layout
    loaded = ProjectService.open(editor.project.catalog.path.parent, read_only=True)
    assert loaded.catalog.get(record.id).data["recipe"]["steps"][1]["parameters"]["frames"] == 12
    loaded.catalog.close()


def test_canvas_real_port_connections_and_blocked_cycles(editor, qt_app, monkeypatch):
    errors = []
    monkeypatch.setattr("etherfood_studio.ui.pipeline_editor.show_error",
                        lambda parent, e: errors.append(str(e)))
    recipe = deepcopy(editor.state["recipe"])
    recipe["connections"] = []
    editor.state["recipe"] = recipe
    editor.render()
    source, target = recipe["steps"]
    editor.connect_steps(source["id"], target["id"])
    assert len(editor.state["recipe"]["connections"]) == 1
    editor.connect_steps(source["id"], target["id"])
    assert errors and len(editor.state["recipe"]["connections"]) == 1
    editor.undo()
    assert editor.state["recipe"]["connections"] == []
    editor.redo()
    canvas = editor.canvas
    item = canvas.items_by_id[target["id"]]
    canvas.centerOn(item)
    qt_app.processEvents()
    spy = QSignalSpy(canvas.open_requested)
    QTest.mouseDClick(canvas.viewport(), Qt.LeftButton,
                     pos=canvas.mapFromScene(item.pos() + QPointF(110, 48)))
    assert spy.count() == 1


def test_project_context_and_card_creation_undo(tmp_path, qt_app, monkeypatch):
    window = MainWindow(QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat))
    root = tmp_path / "project"
    root.mkdir()
    window.new_project(root, "Projektgrenze")
    project = window.project
    owner = project.project().id
    menu = window.navigation.menu(owner)
    names = {a.objectName() for a in menu.actions()}
    assert {"context_pipeline_new", "context_pipeline_template", "context_pipeline_import"} <= names
    menu.deleteLater()
    opened = []
    monkeypatch.setattr(window, "open_pipeline", opened.append)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Neue Grafikpipeline", True))
    monkeypatch.setattr(QInputDialog, "getItem", lambda *a, **k: ("Grafik-Assets", True))
    window.create_pipeline(choose_template=True)
    assert opened
    record = project.catalog.get(opened[0])
    assert record.owner_id == owner and record.kind == "pipeline"
    assert record.id in window.canvas.items_by_id
    window.commands.undo()
    assert project.catalog.get(record.id).archived
    window.commands.redo()
    assert not project.catalog.get(record.id).archived
    window.close()


def test_color_properties_only_show_effective_mode(editor):
    recipe = template("color")
    editor.state["recipe"] = recipe
    node = recipe["steps"][1]
    editor.render()
    editor.select_step(node["id"])
    assert editor.findChild(QComboBox, "pipeline_parameter_reference")
    editor.parameter_changed(node["id"], "mode", "fixed")
    assert editor.findChild(QComboBox, "pipeline_parameter_palette")
    assert editor.findChild(QComboBox, "pipeline_parameter_reference") is None


def test_automatic_duration_fps_is_not_an_ineffective_editor_control(editor):
    node = editor.state["recipe"]["steps"][1]
    editor.select_step(node["id"])
    editor.parameter_changed(node["id"], "timing", "keep_duration")
    fps = editor.findChild(QDoubleSpinBox, "pipeline_parameter_fps")
    assert fps and not fps.isEnabled()
    assert "Quelldauer" in fps.toolTip()
    before = node["parameters"]["fps"]
    editor.parameter_changed(node["id"], "timing", "keep_fps")
    fps = editor.findChild(QDoubleSpinBox, "pipeline_parameter_fps")
    assert fps.isEnabled() and fps.value() == before


def test_legacy_canvas_keeps_visual_context_without_executable_edges(editor, tmp_path):
    exchange = PipelineExchange(editor.project)
    plan = exchange.legacy({"nodes": [
        {"id": "a", "type": "text", "text": "Farben prüfen", "x": 300, "y": 210},
        {"id": "b", "type": "text", "text": "Schatten", "x": 100, "y": 400}],
        "edges": [{"id": "line", "fromNode": "a", "toNode": "b"}]})
    record = exchange.accept(plan, "Alte Planung")
    dialog = PipelineEditor(editor.project, record.id)
    assert not dialog.canvas.edges_by_id  # No executable dataflow inferred from visual arrows.
    assert len(dialog.canvas.legacy_edges) == 1
    nodes = dialog.state["recipe"]["steps"][1:]
    first = dialog.canvas.items_by_id[nodes[0]["id"]]
    assert "Farben prüfen" in first.toolTip()
    first.setSelected(True)
    dialog.remove_selected()
    assert not dialog.canvas.legacy_edges
    assert dialog.save()
    exchange.export(record.id, tmp_path / "edited.json", package=False)
    dialog.undo()
    assert len(dialog.canvas.legacy_edges) == 1
    dialog.baseline = deepcopy(dialog.state)
    dialog.reject()


def test_imported_card_undo_archives_copy_without_touching_original(editor, monkeypatch):
    project = editor.project
    window = MainWindow(QSettings())
    window.project, window.commands = project, Commands(project)
    copied = PipelineService(project).create("Importierte Kopie", "graphics")
    monkeypatch.setattr("etherfood_studio.ui.pipeline_exchange_dialogs.import_pipeline",
                        lambda *_args: copied)
    monkeypatch.setattr(window, "prepare_content_change", lambda: True)
    monkeypatch.setattr(window, "refresh", lambda: None)
    monkeypatch.setattr(window, "select_card", lambda _id: None)
    monkeypatch.setattr(window, "open_pipeline", lambda _id: None)
    window.import_pipeline()
    window.commands.undo()
    assert project.catalog.get(copied.id).archived
    assert not project.catalog.get(editor.record.id).archived
    window.commands.redo()
    assert not project.catalog.get(copied.id).archived
    window.project = None
    window.close()


def asset_workspace(editor, *, preset="texture"):
    assets = AssetService(editor.project)
    owner = next(r.id for r in editor.project.cards() if r.kind == "global")
    asset = assets.create("Dialog-Asset", owner, default_definition(preset).to_data())
    return AssetWorkspace(assets, asset.id, editor)


def register_plugin(project, tmp_path, *, large_integer=False, precise_number=False):
    """An intentionally non-importable file proves declarative UI discovery stays inert."""
    identifier = "python:ui-generic"
    manifest = {
        "contract": "studio-python-step-v1", "id": identifier, "name": "Generische Parameter",
        "version": "1.0.0", "description": "Deklaratives Testmanifest, nicht freigegeben.",
        "parameters": {
            "passes": {"type": "integer", "default": 5_000_000_000 if large_integer else 2,
                       "minimum": 0, "maximum": 10 ** 12 if large_integer else 32},
            "amount": {"type": "number", "default": 0.123456789 if precise_number else 0.5,
                       "minimum": 0, "maximum": 1},
            "preserve_alpha": {"type": "boolean", "default": True},
            "style": {"type": "choice", "default": "soft", "choices": ["soft", "hard"]},
            "caption": {"type": "string", "default": "Deklarativ"},
        },
        "inputs": {"image": "image"}, "outputs": {"image": "image"},
        "capabilities": [], "entry_point": "process", "dependencies": [],
    }
    manifest_path = tmp_path / "generic-step.json"
    code_path = tmp_path / "generic-step.py"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    code_path.write_text('raise RuntimeError("Foreign code must not be imported by the UI")\n',
                         encoding="utf-8")
    PluginService(project).register(manifest_path, code_path)
    return identifier


def test_asset_workspace_all_build_buttons_open_real_pipeline_dialog(editor, monkeypatch):
    workspace = asset_workspace(editor)
    seen = []

    def inspect(dialog):
        assert isinstance(dialog, PipelineRunDialog)
        seen.append((dialog.project, dialog.asset_id, dialog.recipe_id, dialog.parent()))
        assert dialog.worker is None and not dialog.plans
        return 0

    monkeypatch.setattr(PipelineRunDialog, "exec", inspect)
    workspace.show()
    for name in ("workspace_build", "workspace_build_plan", "asset_pipeline_results"):
        if name == "asset_pipeline_results":
            workspace.tabs.setCurrentIndex(4)
        action = workspace.findChild(QPushButton, name)
        assert action is not None and action.isEnabled()
        QTest.mouseClick(action, Qt.LeftButton)
    assert seen == [(editor.project, workspace.identifier, None, workspace)] * 3
    assert editor.project.catalog.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
    workspace.reject()
    workspace.deleteLater()


def test_asset_workspace_valid_unsaved_requirements_block_build(editor, monkeypatch):
    workspace = asset_workspace(editor)
    shown, opened = [], []
    monkeypatch.setattr(QMessageBox, "information", lambda *args: shown.append(args))
    monkeypatch.setattr(PipelineRunDialog, "exec", lambda self: opened.append(self) or 0)
    workspace.editor.type_label.setText("Ungespeicherter Typname")
    workspace.run_pipeline()
    assert shown and not opened
    assert "bewusst speichern" in shown[0][2]
    assert workspace.assets.definition(workspace.identifier).type_label == "Textur"
    assert editor.project.catalog.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
    workspace.deleteLater()


def test_asset_workspace_invalid_requirements_show_error_without_raising(editor, monkeypatch):
    workspace = asset_workspace(editor, preset="effect")
    errors, opened = [], []
    monkeypatch.setattr("etherfood_studio.ui.asset_workspace.show_error",
                        lambda parent, error: errors.append(str(error)))
    monkeypatch.setattr(PipelineRunDialog, "exec", lambda self: opened.append(self) or 0)
    workspace.editor.frames.setText("0")
    try:
        workspace.run_pipeline()
        assert errors and not opened
    finally:
        workspace.deleteLater()


def test_profile_dialog_custom_profile_reaches_recipe_and_asset_forms(editor, monkeypatch):
    editor.mutate("Grafikvorlage", lambda state: state.update(recipe=template("graphics")))
    before = deepcopy(editor.state)

    def add_custom(dialog):
        dialog.add_profile()
        row = dialog.table.rowCount() - 1
        dialog.table.item(row, 0).setText("map_thumbnail")
        dialog.table.item(row, 1).setText("Kartenvorschau")
        dialog.table.cellWidget(row, 5).setValue(0.125)
        dialog.table.cellWidget(1, 2).setChecked(False)
        dialog.save()
        return dialog.result()

    monkeypatch.setattr(ProfileDialog, "exec", add_custom)
    action = editor.findChild(QPushButton, "pipeline_profiles")
    assert action is not None
    QTest.mouseClick(action, Qt.LeftButton)
    assert editor.state == before
    targets = {editor.targets.item(i).data(Qt.UserRole): editor.targets.item(i)
               for i in range(editor.targets.count())}
    assert targets["map_thumbnail"].text() == "Kartenvorschau"
    assert "deaktiviert" in targets["comic_mid"].text()
    targets["map_thumbnail"].setCheckState(Qt.Checked)
    assert editor.state["recipe"]["profiles"] == ["map_thumbnail"]
    assert editor.save()
    assert editor.service.recipe(editor.identifier).data["recipe"]["profiles"] == ["map_thumbnail"]
    workspace = asset_workspace(editor)
    assert "map_thumbnail" in workspace.editor.graphics
    assert workspace.editor.graphics["map_thumbnail"].text() == "Kartenvorschau"
    assert "nicht als Pflichtausgabe" in workspace.editor.graphics["comic_mid"].toolTip()
    workspace.deleteLater()
    profile = ProfileService(editor.project).profiles()["map_thumbnail"]
    assert profile["value"] == 0.125 and profile["mode"] == "factor"


def test_editor_unsaved_cancel_discard_and_save_guard(editor, monkeypatch):
    identifier = editor.state["recipe"]["steps"][1]["id"]
    original = deepcopy(editor.record.data["recipe"])
    editor.parameter_changed(identifier, "fps", 12)
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Cancel)
    editor.reject()
    assert editor.isVisible()
    assert editor.service.recipe(editor.identifier).data["recipe"] == original
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.No)
    editor.reject()
    assert not editor.isVisible()
    assert editor.service.recipe(editor.identifier).data["recipe"] == original
    editor.show()
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Yes)
    editor.reject()
    assert not editor.isVisible()
    saved = editor.service.recipe(editor.identifier).data["recipe"]
    assert saved["steps"][1]["parameters"]["fps"] == 12


def test_invalid_header_does_not_dismiss_unsaved_editor(editor, monkeypatch):
    errors = []
    monkeypatch.setattr("etherfood_studio.ui.pipeline_editor.show_error",
                        lambda parent, error: errors.append(str(error)))
    original = deepcopy(editor.baseline)
    editor.category.setText("")
    try:
        editor.reject()
        assert errors
        assert editor.isVisible(), "Invalid header must not silently dismiss the editor"
        assert editor.service.recipe(editor.identifier).data["recipe"] == original["recipe"]
    finally:
        editor.category.setText(original["recipe"]["category"])


def test_saved_recipe_redo_restores_parameters_and_layout_without_builds(editor):
    node = editor.state["recipe"]["steps"][1]["id"]
    original = deepcopy(editor.record.data["recipe"])
    original_layout = editor.project.catalog.layout(editor.identifier)
    editor.parameter_changed(node, "frames", 14)
    editor.move_nodes({node: {"x": 81, "y": -120}})
    assert editor.save()
    saved = deepcopy(editor.service.recipe(editor.identifier).data["recipe"])
    saved_layout = editor.project.catalog.layout(editor.identifier)
    editor.commands.undo()
    assert editor.service.recipe(editor.identifier).data["recipe"] == original
    restored = editor.project.catalog.layout(editor.identifier)
    assert restored.get("pipeline_nodes", {}) == original_layout.get("pipeline_nodes", {})
    assert {k: v for k, v in restored.items() if k != "pipeline_nodes"} == original_layout
    editor.commands.redo()
    assert editor.service.recipe(editor.identifier).data["recipe"] == saved
    assert editor.project.catalog.layout(editor.identifier) == saved_layout
    assert not any(record.kind == "build" for record in editor.project.catalog.records())


def test_context_actions_project_only_and_archive_restore_preserve_recipe(tmp_path, qt_app,
                                                                        monkeypatch):
    window = MainWindow(QSettings(str(tmp_path / "contexts.ini"), QSettings.IniFormat))
    root = tmp_path / "contexts"
    root.mkdir()
    assert window.new_project(root, "Kontexte")
    project = window.project
    service = PipelineService(project)
    recipe = service.create("Archivierte Grafik", "graphics")
    act = project.create_card("act", "Akt", project.project().id)
    asset = AssetService(project).create("Textur", service.global_id,
                                         default_definition("texture").to_data())
    service.assign(recipe.id, asset_id=asset.id)
    project.catalog.save_layout(recipe.id, {"x": 71, "y": 82, "w": 270, "h": 150})
    original, layout = deepcopy(recipe.data), project.catalog.layout(recipe.id)
    window.refresh()
    create_actions = {"context_pipeline_new", "context_pipeline_template",
                      "context_pipeline_import"}
    for record in (project.catalog.get(service.global_id), act, asset, recipe):
        menu = window.navigation.menu(record.id)
        assert not create_actions.intersection(a.objectName() for a in menu.actions())
        menu.deleteLater()
    menu = window.navigation.menu(service.project_id)
    assert create_actions <= {a.objectName() for a in menu.actions()}
    menu.deleteLater()
    opened = []
    monkeypatch.setattr(window, "open_pipeline", opened.append)
    menu = window.navigation.menu(recipe.id)
    next(a for a in menu.actions() if a.objectName() == "context_pipeline_open").trigger()
    assert opened == [recipe.id]
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Yes)
    next(a for a in menu.actions() if a.objectName() == "context_archive").trigger()
    assert project.catalog.get(recipe.id).archived
    menu.deleteLater()
    with pytest.raises(StudioError):
        service.resolve(asset.id)
    menu = window.navigation.menu(recipe.id)
    assert "context_pipeline_open" not in {a.objectName() for a in menu.actions()}
    restore = next(a for a in menu.actions() if a.objectName() == "context_archive")
    assert restore.text() == "Wiederherstellen"
    restore.trigger()
    assert not project.catalog.get(recipe.id).archived
    assert service.recipe(recipe.id).data == original
    assert project.catalog.layout(recipe.id) == layout
    assert service.resolve(asset.id)["recipe"].id == recipe.id
    menu.deleteLater()
    window.close()


def test_archived_recipe_cannot_be_saved_by_an_already_open_editor(editor, monkeypatch):
    errors = []
    monkeypatch.setattr("etherfood_studio.ui.pipeline_editor.show_error",
                        lambda parent, error: errors.append(str(error)))
    node = editor.state["recipe"]["steps"][1]["id"]
    editor.parameter_changed(node, "frames", 10)
    original = deepcopy(editor.record.data["recipe"])
    editor.project.archive(editor.identifier, True, editor.record.revision_no)
    assert not editor.save()
    assert errors and editor.state != editor.baseline
    assert editor.project.catalog.get(editor.identifier).data["recipe"] == original


def test_plugin_context_refresh_and_generic_parameter_widgets_do_not_import_code(editor, tmp_path,
                                                                                monkeypatch):
    plugin_id = "python:ui-generic"
    assert editor.operations.findData(plugin_id) < 0
    monkeypatch.setattr("etherfood_studio.ui.pipeline_exchange_dialogs.manage_plugins",
                        lambda project, parent: register_plugin(project, tmp_path))
    QTest.mouseClick(editor.findChild(QPushButton, "pipeline_plugins"), Qt.LeftButton)
    index = editor.operations.findData(plugin_id)
    assert index >= 0
    editor.operations.setCurrentIndex(index)
    editor.add_step(editor.state["recipe"]["steps"][1]["id"], 650, 90)
    node = editor.state["recipe"]["steps"][-1]
    assert node["operation"] == plugin_id
    assert editor.findChild(QSpinBox, "pipeline_parameter_passes")
    assert editor.findChild(QDoubleSpinBox, "pipeline_parameter_amount")
    assert editor.findChild(QCheckBox, "pipeline_parameter_preserve_alpha")
    assert editor.findChild(QComboBox, "pipeline_parameter_style")
    assert editor.findChild(QLineEdit, "pipeline_parameter_caption")
    integer = editor.findChild(QSpinBox, "pipeline_parameter_passes")
    integer.setValue(4)
    integer.editingFinished.emit()
    number = editor.findChild(QDoubleSpinBox, "pipeline_parameter_amount")
    number.setValue(0.75)
    number.editingFinished.emit()
    editor.findChild(QCheckBox, "pipeline_parameter_preserve_alpha").click()
    choices = editor.findChild(QComboBox, "pipeline_parameter_style")
    choices.setCurrentIndex(choices.findData("hard"))
    choices.activated.emit(choices.currentIndex())
    text = editor.findChild(QLineEdit, "pipeline_parameter_caption")
    text.setText("Geändert")
    text.editingFinished.emit()
    parameters = editor.state["recipe"]["steps"][-1]["parameters"]
    assert parameters == {"passes": 4, "amount": 0.75, "preserve_alpha": False,
                          "style": "hard", "caption": "Geändert"}
    assert PluginService(editor.project).details(plugin_id)["approved_hash"] is None
    assert editor.save()
    assert not any(record.kind == "build" for record in editor.project.catalog.records())


def test_valid_large_integer_plugin_parameter_opens_without_qt_overflow(editor, tmp_path,
                                                                      monkeypatch):
    identifier = register_plugin(editor.project, tmp_path, large_integer=True)
    editor.manifests = editor.service.manifests()
    editor.fill_operations()
    editor.operations.setCurrentIndex(editor.operations.findData(identifier))
    errors = []
    monkeypatch.setattr("etherfood_studio.ui.pipeline_editor.show_error",
                        lambda parent, error: errors.append(str(error)))
    try:
        editor.add_step(editor.state["recipe"]["steps"][1]["id"])
    except (OverflowError, RuntimeError) as error:
        errors.append(str(error))
    assert not errors, "A valid manifest integer range must not overflow QSpinBox"
    node = editor.state["recipe"]["steps"][-1]
    assert node["operation"] == identifier
    assert node["parameters"]["passes"] == 5_000_000_000
    widget = editor.findChild(QWidget, "pipeline_parameter_passes")
    if isinstance(widget, QLineEdit):
        widget.setText("5000000001")
    else:
        widget.setValue(5_000_000_001)
    widget.editingFinished.emit()
    assert not errors
    assert editor.state["recipe"]["steps"][-1]["parameters"]["passes"] == 5_000_000_001


def test_generic_plugin_numeric_focus_does_not_round_recipe_parameters(editor, tmp_path):
    identifier = register_plugin(editor.project, tmp_path, precise_number=True)
    editor.manifests = editor.service.manifests()
    editor.fill_operations()
    editor.operations.setCurrentIndex(editor.operations.findData(identifier))
    editor.add_step(editor.state["recipe"]["steps"][1]["id"])
    before = deepcopy(editor.state)
    widget = editor.findChild(QWidget, "pipeline_parameter_amount")
    assert widget is not None
    widget.editingFinished.emit()
    assert editor.state == before, (
        "Merely leaving a numeric field must not rewrite recipe precision")
