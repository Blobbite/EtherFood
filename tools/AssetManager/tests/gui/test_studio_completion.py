"""Exercise the complete two-act workflow with real images and a reopened desktop."""

import json
from pathlib import Path
from urllib.parse import quote

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QSettings, QUrl
from PySide6.QtGui import QImage, QTextDocument
from PySide6.QtWidgets import QFileDialog, QInputDialog

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.canvas_service import CanvasService
from etherfood_studio.application.document_service import DocumentService
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.plugin_service import PluginService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.recipe_results import RecipeResultService
from etherfood_studio.application.tool_environments import ToolEnvironments
from etherfood_studio.application.tool_packages import ToolPackageService
from etherfood_studio.storage.blob_store import file_hash
from etherfood_studio.ui.documents.project_links import ProjectMarkdownView
from etherfood_studio.ui.main_window import MainWindow
from etherfood_studio.ui.pipeline_auxiliary import PipelineRunWorker
from etherfood_studio.ui.pipeline_exchange_dialogs import PluginPackageImportDialog
from test_project_documents import assert_links, section
from test_script_platform import EXAMPLE, asset
from test_tool_packages import offline_pillow


@pytest.fixture
def window(qt_app, tmp_path):
    settings = QSettings(str(tmp_path / "desktop.ini"), QSettings.IniFormat)
    value = MainWindow(settings)
    root = tmp_path / "Zwei Akte"
    root.mkdir()
    assert value.new_project(root, "Abnahmeprojekt")
    yield value
    value.documents.dirty = False
    value.close()
    value.deleteLater()
    qt_app.processEvents()


def _import_from_canvas(window: MainWindow, monkeypatch: pytest.MonkeyPatch) -> str:
    opened = []
    monkeypatch.setattr(
        window.processing, "open", lambda kind, identifier: opened.append(identifier)
    )
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(EXAMPLE), "JSON"))

    def accept(dialog):
        dialog.import_copy()
        return dialog.result()

    monkeypatch.setattr(PluginPackageImportDialog, "exec", accept)
    window.import_pipeline()
    assert len(opened) == 1
    assert opened[0] in window.canvas.items_by_id
    service = ToolPackageService(window.project)
    recipe = PipelineService(window.project).recipe(opened[0]).data["recipe"]
    node = next(step for step in recipe["steps"] if step["operation"] != "source")
    package = service.details(node["operation"].split(":")[1])
    service.approve(package["digest"])
    ToolEnvironments(window.project).prepare(package["manifest"])
    return opened[0]


def _worker_result(worker: PipelineRunWorker) -> dict:
    results, errors = [], []
    worker.result.connect(results.append)
    worker.failed.connect(errors.append)
    try:
        worker.run()
        assert not errors, errors
        assert len(results) == 1
        return results[0]
    finally:
        worker.deleteLater()


def _documents_and_links(project: ProjectService) -> dict[str, str]:
    documents = DocumentService(project)
    identifiers = {}
    for card in project.cards():
        base = [d for d in documents.documents(card.id) if d.data.get("automation") == "section"]
        assert len(base) == 1, card.title
        assert documents.path(base[0].id).is_file()
        identifiers[card.id] = base[0].id
    assert_links(project.files.root)
    return identifiers


def _publications(project: ProjectService, assets: list[str], recipe: str) -> dict[str, dict]:
    publications = {}
    for identifier in assets:
        result = RecipeResultService(project).latest(identifier)
        assert result["state"] == "ready", result
        assert result["recipe_id"] == recipe
        assert len(result["artifacts"]) == 1
        artifact = result["artifacts"][0]
        image = project.files.root / artifact["image_path"]
        assert image.parent == project.files.path(identifier) / "Ergebnisse/Einzelbild/scaled"
        assert file_hash(image) == artifact["sha256"]
        current = json.loads(
            (project.files.path(identifier) / "Ergebnisse/aktuell.json").read_text()
        )
        assert current["asset_id"] == identifier and current["recipe_id"] == recipe
        gallery = image.parent / "index.md"
        assert "| Datei | Vorschau |" in gallery.read_text() and "![" in gallery.read_text()
        view = ProjectMarkdownView(DocumentService(project), gallery)
        try:
            preview = view.view.loadResource(QTextDocument.ImageResource, QUrl(image.name))
            assert isinstance(preview, QImage) and not preview.isNull()
            assert (preview.width(), preview.height()) == (256, 128)
        finally:
            view.deleteLater()
        publications[identifier] = {
            "run_id": result["run_id"],
            "build_id": artifact["build_id"],
            "metadata": artifact["metadata"],
            "sha256": file_hash(image),
        }
    assert {r.id for r in project.cards() if r.kind == "asset"} == set(assets)
    assert not list(project.files.path(recipe).rglob("*.png"))
    return publications


def _file_state(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): file_hash(path)
        for path in root.rglob("*")
        if path.is_file() and path.suffix in {".md", ".png", ".json", ".py"}
    }


def test_two_acts_build_move_undo_conflict_and_desktop_reopen(
    window, qt_app, tmp_path, monkeypatch, offline_pillow
):
    project = window.project
    root = project.files.root
    recipe = _import_from_canvas(window, monkeypatch)
    chapters, assets, originals = [], [], {}
    for number in (1, 2):
        act = project.create_card("act", f"Akt {number}", project.project().id)
        chapter = project.create_card("chapter", "Kapitel 1", act.id)
        chapters.append(chapter.id)
        owner = chapter
        if number == 1:
            owner = project.create_card("package", "Tempelpaket", chapter.id)
        record, source = asset(project, tmp_path, owner.id, title=f"Bild {number}")
        if number == 2:
            service = AssetService(project)
            definition = service.definition(record.id).to_data()
            definition["type"].update(id="surface", label="Oberfläche")
            service.configure(record.id, definition, project.catalog.get(record.id).revision_no)
        assets.append(record.id)
        originals[source] = file_hash(source)
        PipelineService(project).assign(recipe, asset_id=record.id)
    assert project.files.path(recipe) == root / ".pipelines/Proportionale Skalierung"
    assert project.files.path(assets[0]) == (
        root / "Akt 1/Kapitel 1/Assets/Pakete/Tempelpaket/Textur/Bild 1"
    )
    assert project.files.path(assets[1]) == root / "Akt 2/Kapitel 1/Assets/Oberfläche/Bild 2"
    assert project.catalog.db.execute("SELECT count(*) FROM jobs").fetchone()[0] == 0

    planned = _worker_result(PipelineRunWorker(project, recipe, None))
    assert {row["asset_id"] for row in planned["rows"]} == set(assets)
    completed = _worker_result(
        PipelineRunWorker(project, recipe, None, plans=[row["plan"] for row in planned["rows"]])
    )
    assert len(completed["reports"]) == 2
    assert all(row["report"]["published"] for row in completed["reports"])
    published = _publications(project, assets, recipe)
    job_rows = list(project.catalog.db.execute("SELECT * FROM jobs"))
    base_ids = _documents_and_links(project)

    window.refresh()
    window.open_document(base_ids[assets[0]])
    editor = window.documents
    editor.editor.setPlainText(editor.current.data["body"] + "Eigener Markdowntext.\n")
    assert editor.save()
    extra = editor.create_document("Zusätzliche Anleitung")
    editor.editor.setPlainText("# Handbuch\n\nZusätzlicher eigener Inhalt.\n")
    assert editor.save()
    foreign = project.files.path(assets[0]) / "Externe Notiz.txt"
    foreign.write_text("Unverwaltete Datei bleibt erhalten.\n", encoding="utf-8")
    gallery = project.files.path(assets[0]) / "Ergebnisse/Einzelbild/scaled/index.md"
    gallery.write_text(gallery.read_text() + "\nEigene Bildbewertung.\n", encoding="utf-8")

    # A new act refreshes an already open start page without creating another base document.
    window.show_start_page()
    current = project.project()
    third = CanvasService(window.commands).create(
        current.id, current.revision_no, "act", "Akt 3", 900, 100
    )
    window.refresh()
    assert "Akt 3" in window.documents.current.data["body"]
    assert "Akt 3" in window.documents.editor.toPlainText()
    assert "STUDIO:AUTO" not in window.documents.preview.toPlainText()
    assert set(_documents_and_links(project)) == set(base_ids) | {third.id}
    base_ids[third.id] = section(project, third.id).id

    # Moving the package across acts carries its asset, documents, outputs and foreign files.
    package = project.catalog.get(assets[0]).owner_id
    window.move_canvas_content(package, chapters[1])
    assert project.catalog.get(package).owner_id == chapters[1]
    moved = project.files.path(assets[0])
    assert moved.is_relative_to(root / "Akt 2/Kapitel 1/Assets/Pakete")
    assert (moved / foreign.name).read_text() == "Unverwaltete Datei bleibt erhalten.\n"
    assert "Eigene Bildbewertung." in (moved / "Ergebnisse/Einzelbild/scaled/index.md").read_text()
    assert _publications(project, assets, recipe) == published
    assert _documents_and_links(project) == base_ids
    window.tabs.setCurrentIndex(0)
    window.canvas.setFocus()
    window.undo(False)
    assert project.catalog.get(package).owner_id == chapters[0]
    assert project.files.path(assets[0]) / foreign.name == foreign
    window.undo(True)
    assert project.catalog.get(package).owner_id == chapters[1]

    window.select_card(chapters[1])
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Kapitel Neu", True))
    window.rename_dialog()
    assert project.catalog.get(chapters[1]).title == "Kapitel Neu"
    assert _documents_and_links(project) == base_ids
    assert _publications(project, assets, recipe) == published

    # Both sides of a simultaneous file/editor edit survive the rejected save.
    window.open_document(base_ids[assets[0]])
    editor = window.documents
    document_path = DocumentService(project).path(editor.current.id)
    saved = editor.current
    external = saved.data["body"] + "Extern ergänzt.\n"
    document_path.write_text(external, encoding="utf-8")
    draft = saved.data["body"] + "Ungespeicherter Entwurf.\n"
    editor.editor.setPlainText(draft)
    errors = []
    monkeypatch.setattr(
        "etherfood_studio.ui.documents.editor.show_error",
        lambda parent, error: errors.append(str(error)),
    )
    assert not editor.save()
    assert errors and "gleichzeitig extern" in errors[0]
    assert editor.dirty and editor.editor.toPlainText() == draft
    assert document_path.read_text() == external and project.catalog.get(saved.id) == saved
    # Explicitly merge the two texts after the external revision has been loaded.
    editor.dirty = False
    assert window.open_project(root)
    project = window.project
    window.open_document(saved.id)
    editor = window.documents
    assert "Extern ergänzt." in editor.editor.toPlainText()
    editor.editor.setPlainText(editor.current.data["body"] + "Ungespeicherter Entwurf.\n")
    assert editor.save()
    assert _documents_and_links(project) == base_ids
    assert _publications(project, assets, recipe) == published
    assert list(project.catalog.db.execute("SELECT * FROM jobs")) == job_rows

    # Close the window/catalog completely and reopen through a fresh desktop instance.
    snapshot = project.catalog.records()
    files = _file_state(root)
    window.close()
    reopened = MainWindow(QSettings(str(tmp_path / "reopened.ini"), QSettings.IniFormat))
    try:
        assert reopened.open_project(root)
        project = reopened.project
        reopened.show_start_page()
        qt_app.processEvents()
        assert project.catalog.records() == snapshot
        assert _file_state(root) == files
        assert _documents_and_links(project) == base_ids
        assert _publications(project, assets, recipe) == published
        assert list(project.catalog.db.execute("SELECT * FROM jobs")) == job_rows
        assert all(file_hash(path) == digest for path, digest in originals.items())
        path = DocumentService(project).path(saved.id).relative_to(root).as_posix()
        reopened.documents.follow_link(QUrl(quote(path)))
        assert reopened.documents.current.id == saved.id
        body = reopened.documents.editor.toPlainText()
        for text in ("Eigener Markdowntext.", "Extern ergänzt.", "Ungespeicherter Entwurf."):
            assert text in body
        assert project.catalog.get(extra.id).data["body"] == (
            "# Handbuch\n\nZusätzlicher eigener Inhalt.\n"
        )
    finally:
        reopened.documents.dirty = False
        reopened.close()
        reopened.deleteLater()
        qt_app.processEvents()
