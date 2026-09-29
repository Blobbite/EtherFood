"""The real unified editor composes, opens and repairs immutable Python packages."""

import json

import pytest

pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QInputDialog, QLineEdit, QPushButton

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.tool_contract import operation
from etherfood_studio.ui.pipeline_editor import PipelineEditor
from etherfood_studio.ui.processing import ProcessingWorkspace
from etherfood_studio.ui.tool_editor import ToolEditor


@pytest.fixture
def workspace(qt_app, tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    project = ProjectService.new(root, "Verarbeitung")
    scope = next(card.id for card in project.cards() if card.kind == "global")
    AssetService(project).create("Textur", scope, default_definition("texture").to_data())
    widget = ProcessingWorkspace(project)
    widget.resize(1500, 950)
    widget.show()
    qt_app.processEvents()
    yield widget
    widget.leave()
    widget.deleteLater()
    qt_app.processEvents()
    project.catalog.close()


def test_compose_real_ports_folders_open_code_and_return(workspace, monkeypatch, qt_app):
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Comic-Ausgabe", True))
    workspace.new_workflow()
    editor = workspace.current
    assert isinstance(editor, PipelineEditor)
    package = workspace.service.packages()[0]
    op = operation(package["digest"], "comic_low")
    editor.operations.setCurrentIndex(editor.operations.findData(op))
    editor.add_step()
    node = editor.state["recipe"]["steps"][-1]
    editor.add_asset()
    asset = editor.asset_choices.currentData()
    editor.connect_steps("asset_" + asset, node["id"])
    editor.select_step(node["id"])
    assert editor.findChild(QLineEdit, "workflow_output_directory_image") is not None
    key = next(iter(editor.state["recipe"]["outputs"]))
    editor.output_changed(key, "directory", "Ergebnisse/ComicLow")
    assert editor.save()
    assert (workspace.project.files.path(asset) / "Ergebnisse/ComicLow").is_dir()
    identifier = editor.identifier
    editor.entry_open_requested.emit(op)
    qt_app.processEvents()
    assert isinstance(workspace.current, ToolEditor)
    assert workspace.current.current_file == "comic_low.py"
    assert workspace.current.entries.currentData() == "comic_low"
    assert "Verarbeitung /" in workspace.breadcrumb.text()
    workspace.back()
    assert isinstance(workspace.current, PipelineEditor)
    assert workspace.current.identifier == identifier
    assert workspace.current.state["recipe"]["outputs"][key]["directory"] == "Ergebnisse/ComicLow"
    assert workspace.project.catalog.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0


def test_python_draft_diagnostics_diff_version_and_pinned_references(
    workspace, monkeypatch, qt_app
):
    package = workspace.service.packages()[0]
    recipe = workspace.service.create_recipe(package["digest"], "comic_low")
    original = PipelineService(workspace.project).recipe(recipe.id).data["recipe"]
    workspace.open("tool", package["digest"], "comic_low")
    editor = workspace.current
    source = editor.code.toPlainText()
    editor.code.setPlainText("def run(:\n")
    preview = editor.check()
    assert preview.issues[0]["kind"] == "syntax"
    assert editor.save()
    editor.refresh_diff()
    assert "-def run" in editor.diff.toPlainText()
    editor.code.setPlainText("# Neue Paketversion\n" + source)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("1.0.1", True))
    editor.publish()
    assert editor.digest != package["digest"]
    assert workspace.service.details(editor.digest)["manifest"]["version"] == "1.0.1"
    assert not workspace.service.details(editor.digest)["approved"]
    assert PipelineService(workspace.project).recipe(recipe.id).data["recipe"] == original
    editor.copy_context()
    from PySide6.QtWidgets import QApplication

    assert "SDK: run(context, inputs, parameters)" in QApplication.clipboard().text()


def test_add_package_subflow_opens_editable_canvas(workspace, monkeypatch):
    package = workspace.service.packages()[0]
    workspace.open("package", package["digest"])
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("new_flow", True))
    workspace.current.add_entry(True)
    editor = workspace.current
    assert isinstance(editor, PipelineEditor) and editor.draft_save is not None
    op = operation(package["digest"], "comic_mid")
    editor.operations.setCurrentIndex(editor.operations.findData(op))
    editor.add_step()
    editor.connect_steps(
        editor.state["recipe"]["steps"][0]["id"], editor.state["recipe"]["steps"][1]["id"]
    )
    assert editor.save()
    workspace.back()
    assert isinstance(workspace.current, ToolEditor)
    manifest, _ = workspace.current.values()
    flow = next(flow for flow in manifest["flows"] if flow["id"] == "new_flow")
    assert flow["recipe"]["steps"][1]["operation"] == "local:comic_mid"
    assert flow["recipe"]["outputs"]
