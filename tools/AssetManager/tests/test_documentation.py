"""Documentation templates and imports remain distinct from existing sticky notes."""

import pytest

from etherfood_studio.application.document_service import DocumentService
from etherfood_studio.application.note_service import NoteService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.domain.notes import is_note
from etherfood_studio.storage.blob_store import file_hash


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    value = ProjectService.new(root, "Dokumentationsprüfung")
    yield value
    value.catalog.close()


def test_documentation_template_does_not_reclassify_legacy_notes(project):
    service = DocumentService(project)
    owner = project.project().id
    note = service.create(owner, "Vorhandene Notiz", "Alte Notiz")
    doc = service.create(owner, "Neue Dokumentation", template="Dokumentation")
    assert is_note(note) and not is_note(doc)
    assert doc.data["body"] == "# Dokumentation\n\n"
    assert [row.id for row in NoteService(project).notes(owner)] == [note.id]
    assert project.catalog.get(note.id) == note
    reopened = ProjectService.open(project.catalog.path.parent)
    assert is_note(reopened.catalog.get(note.id))
    assert not is_note(reopened.catalog.get(doc.id))
    reopened.catalog.close()


@pytest.mark.parametrize("body", ["# Quelle\n\nUnveränderter Inhalt.\n", ""])
def test_markdown_import_is_documentation_and_preserves_exact_source(project, tmp_path, body):
    source = tmp_path / "Anleitung.markdown"
    source.write_text(body, encoding="utf-8")
    digest = file_hash(source)
    doc = DocumentService(project).import_markdown(project.project().id, source)
    assert not is_note(doc) and doc.data["template"] == "Dokumentation"
    assert doc.data["body"] == body and file_hash(source) == digest
    assert doc.data["provenance"] == {"original_name": source.name, "sha256": digest}
    assert NoteService(project).notes(project.project().id) == []


@pytest.mark.parametrize("template", ["Freie Notiz", "Dokumentation"])
def test_revision_import_preserves_classification_and_attachments(project, tmp_path, template):
    service = DocumentService(project)
    owner = project.project().id
    original = service.create(owner, "Behalten", "Vorher", template=template)
    source = tmp_path / "Andere Quelle.md"
    source.write_text("# Neue Revision\n", encoding="utf-8")
    original = service.attach(original.id, source, original.revision_no)
    updated = service.import_markdown(owner, source, identifier=original.id,
                                      expected_revision=original.revision_no)
    assert updated.id == original.id and updated.title == original.title
    assert updated.data["template"] == template
    assert is_note(updated) == is_note(original)
    assert updated.data["attachments"] == original.data["attachments"]
    assert service.attachment_text(updated.id, 0) == "# Neue Revision\n"
    assert updated.data["body"] == "# Neue Revision\n"
