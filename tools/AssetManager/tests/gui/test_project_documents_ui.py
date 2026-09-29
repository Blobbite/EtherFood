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
    open_start(window)
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
    open_start(window)
    assert "Akt Neu" in editor.current.data["body"]
    editor.follow_link(QUrl("Akt%20Neu/Akt%20Neu.md"))
    assert "Eigene Planung." in editor.editor.toPlainText()
    assert not project.catalog.db.execute(
        "SELECT 1 FROM sqlite_master WHERE name='jobs'"
    ).fetchone()


def test_gallery_renders_verified_images_and_refuses_arbitrary_local_files(window, tmp_path):
    project = window.project
    from test_pipeline_execution import source_asset, approved
    from etherfood_studio.application.pipeline_execution import PipelineExecution

    record, _ = source_asset(project, tmp_path, "Vorschau", "green")
    _, definition, usage = approved(project, "Bilder", [record.id])
    report = PipelineExecution(project).run()
    assert report["state"] == "succeeded", report
    artifact = report["phases"][0]["rows"][0]["outputs"]["output"][0]
    gallery = project.files.path(record.id) / "Ergebnisse" / usage.id / "index.md"
    view = ProjectMarkdownView(DocumentService(project), gallery)
    try:
        name = __import__("os").path.relpath(project.files.root / artifact["path"], gallery.parent)
        image = view.view.loadResource(QTextDocument.ImageResource, QUrl(name))
        assert isinstance(image, QImage) and not image.isNull()
        assert image.width() == 8 and image.height() == 8
        for url in ("file:///etc/passwd", "https://example.org/image.png",
                    "../../../../../etc/passwd"):
            assert not view.view.loadResource(QTextDocument.ImageResource, QUrl(url))
        original = project.files.root / artifact["path"]
        original.write_bytes(b"extern veraendert")
        assert not view.view.loadResource(QTextDocument.ImageResource, QUrl(name))
    finally:
        view.deleteLater()


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


def open_start(window):
    window.set_main_editor(0)
    window.set_section(3)
    window.documents.show_card(window.project.project().id)
    index = next(
        r
        for r in window.documents.service.documents(window.project.project().id)
        if r.data.get("automation") == "index"
    )
    window.documents.open_document(index.id)
