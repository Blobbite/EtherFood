"""Endpoint creation is one local, revision-aware transaction, not a duplicate store."""

import pytest

from etherfood_studio.application.canvas_service import CanvasService
from etherfood_studio.application.commands import Commands
from etherfood_studio.application.document_service import DocumentService
from etherfood_studio.application.note_service import NoteService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.notes import note_word_count


@pytest.fixture
def project(tmp_path):
    project = ProjectService.new(tmp_path, "Inhaltsprüfung")
    project.ids = project.demo()
    yield project
    project.catalog.close()


@pytest.mark.parametrize(
    "kind,source",
    [(kind, "one") for kind in ("asset", "package", "note", "document", "task", "issue")]
    + [("chapter", "act"), ("act", "root")],
)
def test_create_link_layout_undo_redo_and_reopen(project, kind, source):
    commands = Commands(project)
    source = project.catalog.get(project.ids[source]) if source != "root" else project.project()
    created = CanvasService(commands).create(source.id, source.revision_no, kind, "Neu", 83, -71)
    assert created.owner_id == source.id and len(commands.done) == 1
    assert project.catalog.layout(created.id) == {"x": 83, "y": -71}
    edges = project.affected_relations(created.id)
    if created.kind in {"asset", "package", "chapter", "act", "pipeline"}:
        assert len(edges) == 1 and edges[0]["target_id"] == source.id
    commands.undo()
    assert project.catalog.get(created.id).archived
    commands.redo()
    assert not project.catalog.get(created.id).archived
    assert project.affected_relations(created.id) == edges
    loaded = ProjectService.open(project.catalog.path.parent)
    assert loaded.catalog.get(created.id).data == created.data
    assert loaded.catalog.layout(created.id) == {"x": 83, "y": -71}
    loaded.catalog.close()


@pytest.mark.parametrize("failure", ["name", "layout", "kind", "stale", "storage"])
def test_failed_creation_has_no_orphans_or_undo_entry(project, monkeypatch, failure):
    commands = Commands(project)
    source = project.catalog.get(project.ids["one"])
    before = project.catalog.export_snapshot()
    if failure == "storage":
        def fail(*args):
            raise StudioError("unavailable", "Simulierter Schreibfehler")
        monkeypatch.setattr(project.catalog, "save_layout", fail)
    with pytest.raises(StudioError):
        CanvasService(commands).create(source.id, source.revision_no - (failure == "stale"),
            "act" if failure == "kind" else "note", "" if failure == "name" else "Neu",
            float("nan") if failure == "layout" else 80, 40)
    assert not commands.done
    assert project.catalog.export_snapshot() == before


def test_content_source_uses_its_owner_and_undo_protects_later_edits(project):
    source = NoteService(project).write(project.ids["one"], "Quelle", "Idee")
    commands = Commands(project)
    created = CanvasService(commands).create(source.id, source.revision_no, "note", "Neu", 0, 0)
    assert created.owner_id == source.owner_id
    NoteService(project).write(created.owner_id, created.title, "Nicht verlieren",
                              identifier=created.id, expected_revision=created.revision_no)
    with pytest.raises(StudioError, match="Neuere Änderung"):
        commands.undo()
    assert len(commands.done) == 1 and not project.catalog.get(created.id).archived


def test_postit_word_cap_preserves_long_legacy_text_and_attachments(project, tmp_path):
    service = NoteService(project)
    owner = project.ids["one"]
    assert note_word_count("- [ ] Testen\n- [x] Prüfen") == 2
    record = service.write(owner, "Grenze", "Wort " * 100)
    before = project.catalog.export_snapshot()
    with pytest.raises(StudioError, match="100 Wörter"):
        service.write(owner, "Zu lang", "Wort " * 101)
    with pytest.raises(StudioError, match="100 Wörter"):
        service.write(owner, record.title, "Neu " * 101,
                      identifier=record.id, expected_revision=record.revision_no)
    assert project.catalog.export_snapshot() == before
    legacy = DocumentService(project).create(owner, "Alt", "Lang " * 250)
    path = tmp_path / "Beleg.txt"
    path.write_text("Alter Anhang", encoding="utf-8")
    legacy = service.attach(legacy.id, path, legacy.revision_no)
    updated = service.write(owner, "Alt umbenannt", legacy.data["body"], identifier=legacy.id,
                            expected_revision=legacy.revision_no, color="blue")
    assert updated.data["body"] == legacy.data["body"]
    assert updated.data["attachments"] == legacy.data["attachments"]
    assert service.attachment_text(legacy.id, 0) == "Alter Anhang"


def test_project_canvas_creation_does_not_offer_definition_creation(project):
    assert "pipeline" not in CanvasService(Commands(project)).kinds(project.project().id)
