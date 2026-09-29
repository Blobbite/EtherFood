"""Automatic documentation and optional package services through the real generic UI."""

from copy import deepcopy
import json

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QSettings, QUrl
from PySide6.QtGui import QImage, QTextDocument
from PySide6.QtWidgets import QDoubleSpinBox, QInputDialog, QMessageBox, QPushButton

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.document_service import DocumentService
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.plugin_service import PluginService
from etherfood_studio.application.tool_packages import ToolPackageService
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.pipeline_recipes import template
from etherfood_studio.ui.asset_workspace import AssetWorkspace
from etherfood_studio.ui.documents.project_links import ProjectMarkdownView
from etherfood_studio.ui.main_window import MainWindow
from etherfood_studio.ui.pipeline_editor import PipelineEditor
from test_script_platform import EXAMPLE, asset, import_scale, run


@pytest.fixture
def window(qt_app, tmp_path):
    window = MainWindow(QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat))
    root = tmp_path / "Projekt"
    root.mkdir()
    window.new_project(root, "Meine Welt")
    yield window
    window.documents.dirty = False
    window.close()
    qt_app.processEvents()


def test_start_page_and_canvas_change_link_to_editable_section(window, qt_app, monkeypatch):
    project = window.project
    act = project.create_card("act", "Akt 1", project.project().id)
    window.refresh()
    window.show_start_page()
    editor = window.documents
    assert editor.current.data["automation"] == "index" and editor.editor.isReadOnly()
    assert "Akt 1" in editor.current.data["body"]
    assert "STUDIO:AUTO" not in editor.preview.toPlainText()
    editor.follow_link(QUrl("Akt%201/Akt%201.md"))
    assert editor.current.owner_id == act.id and not editor.editor.isReadOnly()
    editor.editor.setPlainText(editor.current.data["body"] + "Eigene Planung.\n")
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Cancel)
    editor.follow_link(QUrl("../Projekt.md"))
    assert editor.current.owner_id == act.id and editor.dirty
    assert editor.save()
    project.rename(act.id, "Akt Neu", act.revision_no)
    window.refresh()
    window.show_start_page()
    assert "Akt Neu" in editor.current.data["body"]
    editor.follow_link(QUrl("Akt%20Neu/Akt%20Neu.md"))
    assert "Eigene Planung." in editor.editor.toPlainText()
    assert project.catalog.db.execute("SELECT count(*) FROM jobs").fetchone()[0] == 0


def test_color_resources_open_from_workflow_and_leave_asset_controls_removed(
        window, qt_app, monkeypatch):
    project = window.project
    owner = next(r for r in project.cards() if r.kind == "global")
    record = AssetService(project).create(
        "Textur", owner.id, default_definition("texture").to_data())
    pipelines = PipelineService(project)
    recipe = pipelines.create("Farbwerkzeug", "source_color")
    workspace = AssetWorkspace(AssetService(project), record.id)
    try:
        assert workspace.findChild(QPushButton, "asset_pipeline_action_references") is None
        pipelines.assign(recipe.id, asset_id=record.id)
        workspace.refresh()
        assert workspace.findChild(QPushButton, "asset_pipeline_action_references") is None
        editor = PipelineEditor(project, recipe.id)
        action = editor.findChild(QPushButton, "workflow_asset_resources")
        assert action is not None
        calls = []
        monkeypatch.setattr(QInputDialog, "getItem", lambda parent, title, label, items, *a:
                            (items[0], True))
        class References:
            def __init__(self, project, asset_id, parent):
                self.identifier = asset_id

            def exec(self):
                calls.append(self.identifier)
        monkeypatch.setattr("etherfood_studio.ui.reference_materials.ReferenceMaterialsDialog",
                            References)
        action.click()
        assert calls == [record.id]
        editor.deleteLater()
        recipe = pipelines.recipe(recipe.id)
        data = deepcopy(recipe.data["recipe"])
        data["steps"][1]["enabled"] = False
        pipelines.save(recipe.id, data, recipe.revision_no)
        workspace.refresh()
        qt_app.processEvents()
        assert workspace.package_actions.count() == 0
    finally:
        workspace.deleteLater()
        qt_app.processEvents()


def test_imported_asset_service_and_conditional_parameters_need_explicit_trust(
        window, tmp_path, qt_app):
    project = window.project
    manifest = json.loads(EXAMPLE.read_text())
    manifest.update(id="python:context-tool", source="tool.py", actions=[{
        "id": "note", "name": "Werkzeugnotiz anlegen", "scope": "asset", "entry_point": "note"}])
    manifest["parameters"]["factor"]["visible_if"] = {"size_mode": ["factor"]}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    (tmp_path / "tool.py").write_text(
        'def apply(image, metadata, parameters):\n    return image, {}\n'
        'def note(context, parameters, parent):\n'
        '    from etherfood_studio.application.document_service import DocumentService\n'
        '    DocumentService(context["project"]).create(context["asset_id"], "Vom Paket", '
        '"Dienst ausgeführt.", template="Dokumentation")\n'
        '    return parameters\n')
    plugins = PluginService(project)
    package = plugins.package(path)
    recipe = plugins.import_package(path, manifest, package["code_hash"], "Eigener Dienst")
    owner = next(r for r in project.cards() if r.kind == "global")
    record = AssetService(project).create(
        "Asset", owner.id, default_definition("texture").to_data())
    PipelineService(project).assign(recipe.id, asset_id=record.id)
    workspace = AssetWorkspace(AssetService(project), record.id)
    editor = PipelineEditor(project, recipe.id)
    try:
        assert workspace.package_actions.count() == 0
        plugins.approve(manifest["id"], package["code_hash"])
        workspace.refresh()
        assert workspace.findChild(QPushButton, "asset_pipeline_action_note") is None
        documents = DocumentService(project).documents(record.id)
        assert not any(r.title == "Vom Paket" for r in documents)
        node = editor.state["recipe"]["steps"][1]
        tools = ToolPackageService(project)
        digest = node["operation"].split(":")[1]
        assert not tools.details(digest)["approved"]
        tools.approve(digest)
        assert tools.details(digest)["approved"]
        editor.select_step(node["id"])
        assert editor.findChild(QDoubleSpinBox, "pipeline_parameter_factor") is not None
        editor.parameter_changed(node["id"], "size_mode", "max_edge")
        assert editor.findChild(QDoubleSpinBox, "pipeline_parameter_factor") is None
        tools.revoke(digest)
        workspace.refresh()
        assert workspace.package_actions.count() == 0
    finally:
        editor.baseline = deepcopy(editor.state)
        editor.deleteLater()
        workspace.deleteLater()
        qt_app.processEvents()


def test_gallery_renders_verified_images_and_refuses_arbitrary_local_files(window, tmp_path):
    project = window.project
    owner = next(r for r in project.cards() if r.kind == "global")
    record, _ = asset(project, tmp_path, owner.id)
    recipe = import_scale(project)
    PipelineService(project).assign(recipe.id, asset_id=record.id)
    _, artifact = run(project, record)
    gallery = project.files.path(record.id) / "Ergebnisse/scaled/index.md"
    view = ProjectMarkdownView(DocumentService(project), gallery)
    try:
        name = artifact["image_path"].split("/")[-1]
        image = view.view.loadResource(QTextDocument.ImageResource, QUrl(name))
        assert isinstance(image, QImage) and not image.isNull()
        assert image.width() == 256 and image.height() == 128
        for url in ("file:///etc/passwd", "https://example.org/image.png",
                    "../../../../../etc/passwd"):
            assert not view.view.loadResource(QTextDocument.ImageResource, QUrl(url))
        original = project.files.root / artifact["image_path"]
        original.write_bytes(b"extern veraendert")
        assert not view.view.loadResource(QTextDocument.ImageResource, QUrl(name))
    finally:
        view.deleteLater()


def test_normal_run_action_opens_real_pipeline_dialog(window, monkeypatch):
    from etherfood_studio.ui.pipeline_auxiliary import PipelineRunDialog

    opened = []
    monkeypatch.setattr(PipelineRunDialog, "exec", lambda dialog: opened.append(dialog) or 0)
    window.show_build_plan()
    assert len(opened) == 1 and opened[0].recipe_id is None
    assert opened[0].run_button.objectName() == "pipeline_run_execute"


def test_base_documents_can_be_shown_in_canvas_with_undo(window):
    project = window.project
    section = next(d for d in DocumentService(project).documents(project.project().id)
                   if d.data.get("automation") == "section")
    assert section.id not in window.canvas.items_by_id
    window.navigation.document_canvas(section.id, True)
    assert section.id in window.canvas.items_by_id
    window.undo(False)
    assert section.id not in window.canvas.items_by_id
    window.undo(True)
    assert section.id in window.canvas.items_by_id
