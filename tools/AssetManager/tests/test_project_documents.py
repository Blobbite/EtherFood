"""Automatic Markdown follows ownership without losing prose, IDs or checked images."""

import re
from urllib.parse import unquote

import pytest

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.canvas_service import CanvasService
from etherfood_studio.application.commands import Commands
from etherfood_studio.application.document_service import DocumentService
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.models import StudioError
from etherfood_studio.storage.blob_store import file_hash
from legacy_fixtures import asset, import_scale, offline_pillow
from test_pipeline_processing import run
from test_pipeline_workspace import passthrough
from etherfood_studio.application.pipeline_workspace import PipelineWorkspace

@pytest.fixture
def project(tmp_path):
    root = tmp_path / "Welt"
    root.mkdir()
    value = ProjectService.new(root, "Meine Welt")
    yield value
    value.catalog.close()


def section(project, owner):
    return next(r for r in DocumentService(project).documents(owner)
                if r.data.get("automation") == "section")


def docpath(project, doc):
    row = project.catalog.db.execute(
        "SELECT * FROM document_files WHERE id=?", (doc.id,)).fetchone()
    return project.files.path(row["owner_id"]) / row["path"]


def assert_links(root):
    for path in root.rglob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            assert (path.parent / unquote(target)).exists(), (path, target)


def test_sections_are_idempotent_and_reopening_does_not_create_revisions(project):
    act = project.create_card("act", "Akt 1", project.project().id)
    chapter = project.create_card("chapter", "Kapitel 1", act.id)
    _, pipeline = passthrough(project, "Skalierung")
    PipelineWorkspace(project).use(pipeline.id)
    for card in project.cards():
        doc = section(project, card.id)
        assert docpath(project, doc).is_file()
    rows = project.catalog.records()
    reopened = ProjectService.open(project.files.root)
    try:
        assert reopened.catalog.records() == rows
        assert section(reopened, chapter.id).id == section(project, chapter.id).id
    finally:
        reopened.catalog.close()
    assert_links(project.files.root)


def test_canvas_create_undo_redo_keeps_one_base_document_and_updates_index(project):
    commands = Commands(project)
    root = project.project()
    card = CanvasService(commands).create(root.id, root.revision_no, "act", "Akt Neu", 20, 50)
    doc = section(project, card.id)
    index = project.files.root / "Index.md"
    assert "Akt Neu" in index.read_text()
    commands.undo()
    assert "Akt Neu" not in index.read_text()
    assert docpath(project, doc).exists()
    commands.redo()
    assert section(project, card.id).id == doc.id
    assert "Akt Neu" in index.read_text()
    edited = project.catalog.get(doc.id)
    DocumentService(project).save(edited.id, edited.data["body"] + "Eigene Arbeit\n",
                                 edited.revision_no)
    with pytest.raises(StudioError, match="Neue Inhalte"):
        commands.undo()


def test_manual_prose_extra_documents_renames_moves_and_type_change(project):
    act = project.create_card("act", "Akt 1", project.project().id)
    chapter = project.create_card("chapter", "Kapitel 1", act.id)
    other = project.create_card("chapter", "Kapitel 2", act.id)
    service = AssetService(project)
    card = service.create("NPC [Nord]", chapter.id, default_definition("npc").to_data())
    assert project.files.path(card.id).parts[-3:] == ("Assets", "NPC", "NPC [Nord]")
    doc = section(project, card.id)
    documents = DocumentService(project)
    documents.save(doc.id, doc.data["body"] + "Eigener Text **bleibt**.\n", doc.revision_no)
    extra = documents.create(card.id, "Weitere Doku", "# Handbuch\n", template="Dokumentation")
    commands = Commands(project)
    commands.move(card.id, other.id)
    project.rename(act.id, "Akt & Neu", act.revision_no)
    assert "Kapitel 2" in str(docpath(project, extra))
    assert "Eigener Text **bleibt**." in docpath(project, doc).read_text()
    assert "Weitere Doku" in docpath(project, doc).read_text()
    assert_links(project.files.root)
    commands.undo()
    assert "Kapitel 1" in str(docpath(project, extra))
    updated = project.catalog.get(card.id)
    service.configure(card.id, default_definition("character").to_data(), updated.revision_no)
    assert project.files.path(card.id).parent.name == "Figur"
    assert "NPC [Nord]" not in (project.files.path(chapter.id) / "Assets/NPC/index.md").read_text()
    assert_links(project.files.root)


def test_external_markdown_prose_survives_structure_changes(project):
    doc = section(project, project.project().id)
    path = docpath(project, doc)
    with path.open("a", encoding="utf-8") as stream:
        stream.write("Extern geschriebener Absatz.\n")
    project.create_card("act", "Extern erhalten", project.project().id)
    assert "Extern geschriebener Absatz." in project.catalog.get(doc.id).data["body"]
    assert "Extern erhalten" in path.read_text()
    assert "Extern geschriebener Absatz." in path.read_text()


def test_concurrent_markdown_conflict_rolls_back_without_losing_either_side(project):
    doc = section(project, project.project().id)
    path = docpath(project, doc)
    external = doc.data["body"] + "Externe Fassung\n"
    path.write_text(external)
    with pytest.raises(StudioError, match="gleichzeitig extern"):
        DocumentService(project).save(doc.id, doc.data["body"] + "App-Fassung\n", doc.revision_no)
    assert project.catalog.get(doc.id) == doc
    assert path.read_text() == external


def test_unknown_files_are_preserved_and_managed_marker_loss_is_visible(project):
    root = project.files.root
    (root / "Akt X").mkdir()
    foreign = root / "Akt X/Akt X.md"
    foreign.write_text("Fremdes Dokument\n")
    card = project.create_card("act", "Akt X", project.project().id)
    assert project.files.path(card.id) != foreign.parent
    assert foreign.read_text() == "Fremdes Dokument\n"
    doc = section(project, card.id)
    docpath(project, doc).write_text("Markierungen entfernt\n")
    with pytest.raises(StudioError, match="STUDIO:AUTO"):
        project.rename(card.id, "Nicht übernommen", card.revision_no)
    assert project.catalog.get(card.id).title == "Akt X"
    assert docpath(project, doc).read_text() == "Markierungen entfernt\n"


def test_invalid_external_markdown_is_a_validation_error_without_overwrite(project):
    doc = section(project, project.project().id)
    path = docpath(project, doc)
    path.write_bytes(b"\xff\xfe")
    with pytest.raises(StudioError, match="UTF-8"):
        project.create_card("act", "Nicht übernommen", project.project().id)
    assert path.read_bytes() == b"\xff\xfe"
    assert not any(r.title == "Nicht übernommen" for r in project.cards())


def test_layout_does_not_change_document_revisions_or_files(project):
    act = project.create_card("act", "Akt 1", project.project().id)
    documents = [r for r in project.catalog.records() if r.kind == "document"]
    before = {doc.id: (file_hash(docpath(project, doc)), docpath(project, doc).stat().st_mtime_ns)
              for doc in documents}
    Commands(project).layout(act.id, {"x": 500, "y": 900})
    assert documents == [r for r in project.catalog.records() if r.kind == "document"]
    assert before == {doc.id: (file_hash(docpath(project, doc)),
                              docpath(project, doc).stat().st_mtime_ns) for doc in documents}


def test_result_galleries_belong_to_assets_and_survive_moves(project, tmp_path):
    from etherfood_studio.application.pipeline_execution import PipelineExecution
    from test_pipeline_execution import source_asset, approved

    record, source = source_asset(project, tmp_path, "Galerie", "blue")
    _, definition, usage = approved(project, "Galerie", [record.id])
    report = PipelineExecution(project).run()
    assert report["state"] == "succeeded", report
    gallery = project.files.path(record.id) / "Ergebnisse" / usage.id / "index.md"
    body = gallery.read_text()
    assert "| Datei | Vorschau |" in body and "![" in body
    original = project.files.path(record.id)
    gallery.write_text(body + "\nEigene Bewertung.\n")
    current = project.catalog.get(record.id)
    project.rename(record.id, "Galerie umbenannt", current.revision_no)
    assert not original.exists()
    assert (
        "Eigene Bewertung."
        in (project.files.path(record.id) / "Ergebnisse" / usage.id / "index.md").read_text()
    )
    assert not list((project.files.root / ".tools/piplins").rglob("*.png"))
    assert_links(project.files.root)


def test_version_eight_project_migrates_folders_and_documents_with_backup(tmp_path):
    from pathlib import Path
    from etherfood_studio.domain.graphics import default_profiles
    from etherfood_studio.storage.sqlite_repository import Catalog, canonical

    root = tmp_path / "Bestand"
    root.mkdir()
    catalog = Catalog(root / "project.studio.sqlite", create=True, target_version=8)
    legacy = ProjectService(catalog)
    legacy.files.folder_parent = lambda card, targets, by_id: Path(targets[card.owner_id])
    with catalog.transaction():
        project = catalog.create("project", "Bestand", data={
            "graphics_profiles": default_profiles()})
        owner = legacy.create_card("global", "Projektweit", project.id)
        pipeline = PipelineService(legacy).create("Altes Rezept", "frames")
        card = AssetService(legacy).create("NPC", owner.id, default_definition("npc").to_data())
        catalog.create("document", "Bestehende Dokumentation", project.id, {
            "body": "Historischer eigener Text\n", "document_type": "manual",
            "attachments": [], "template": "Dokumentation"},
            identifier="ffffffff-ffff-ffff-ffff-ffffffffffff")
    original = catalog.get(card.id)
    (root / "project.studio-local.json").write_text(canonical({
        "schema_version": 1, "roots": {"WORKSPACE_ROOT": str(root)}}))
    assert (root / "Projektweit/NPC").is_dir() and (root / "Altes Rezept").is_dir()
    assert not (root / "Index.md").exists()
    catalog.close()
    migrated = ProjectService.open(root)
    try:
        assert migrated.catalog.last_backup.is_file()
        assert migrated.catalog.get(card.id).id == original.id
        assert (
            migrated.catalog.get(card.id).data["asset_definition"]["poses"]
            == original.data["asset_definition"]["poses"]
        )
        assert migrated.catalog.history(card.id)[0]["data"] == original.data
        assert migrated.files.path(card.id) == root / "Projektweit/Assets/NPC/NPC"
        assert migrated.files.path(pipeline.id) == root / ".pipelines/Altes Rezept"
        assert not (root / "Altes Rezept").exists()
        assert (root / "Index.md").is_file()
        assert_links(root)
        assert not migrated.catalog.db.execute(
            "SELECT 1 FROM sqlite_master WHERE name='jobs'"
        ).fetchone()
        rows = migrated.catalog.records()
        reopened = ProjectService.open(root)
        try:
            assert reopened.catalog.records() == rows
        finally:
            reopened.catalog.close()
    finally:
        migrated.catalog.close()


def test_document_projection_failure_rolls_back_catalog_and_files(project, monkeypatch):
    from etherfood_studio.application.project_documents import ProjectDocuments

    before = project.catalog.export_snapshot()
    files = {str(p.relative_to(project.files.root)): p.read_bytes()
             for p in project.files.root.rglob("*.md")}
    original = ProjectDocuments.sync

    def fail(self, change, cards):
        original(self, change, cards)
        raise OSError("Dokumentschreiben unterbrochen")
    monkeypatch.setattr(ProjectDocuments, "sync", fail)
    with pytest.raises(OSError, match="unterbrochen"):
        project.create_card("act", "Nicht übernommen", project.project().id)
    assert project.catalog.export_snapshot() == before
    assert not (project.files.root / "Nicht übernommen").exists()
    assert files == {str(p.relative_to(project.files.root)): p.read_bytes()
                     for p in project.files.root.rglob("*.md")}


def test_second_example_package_executes_duration_preserving_frame_selection(
    project, tmp_path, offline_pillow
):
    from copy import deepcopy
    from legacy_fixtures import EXAMPLE

    owner = next(r for r in project.cards() if r.kind == "global")
    record, _ = asset(project, tmp_path, owner.id, animated=True)
    recipe = import_scale(project, EXAMPLE.parent.parent / "pipeline_frames/manifest.json")
    data = deepcopy(recipe.data["recipe"])
    data["steps"][1]["parameters"]["timing"] = "keep_duration"
    pipelines = PipelineService(project)
    pipelines.save(recipe.id, data, recipe.revision_no)
    pipelines.assign(recipe.id, asset_id=record.id)
    _, results = run(project, record)
    result = results[0]
    assert result["metadata"]["source_indices"] == list(range(0, 16, 2))
    assert result["metadata"]["fps"] == 4.0 and result["metadata"]["duration"] == 2.0
