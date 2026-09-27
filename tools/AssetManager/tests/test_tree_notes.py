"""Ownership drops, usage references and post-it metadata preserve existing records."""

import pytest

from etherfood_studio.application.commands import Commands
from etherfood_studio.application.document_service import DocumentService
from etherfood_studio.application.issue_service import IssueService
from etherfood_studio.application.kanban_service import KanbanService
from etherfood_studio.application.note_service import NoteService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.tree_service import TreeService
from etherfood_studio.domain.models import StudioError, new_id
from etherfood_studio.domain.notes import is_note


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "tree-notes"
    root.mkdir()
    value = ProjectService.new(root, "Zuordnungen")
    yield value
    value.catalog.close()


@pytest.mark.parametrize("kind", ["asset", "note", "task", "issue", "document"])
def test_move_identity_contents_relations_undo_redo_and_restart(project, tiny_sheet, kind):
    ids = project.demo()
    if kind in {"asset", "note"}:
        record = project.create_card(kind, "Inhalt", ids["one"])
    elif kind in {"task", "issue"}:
        record = IssueService(project).create(ids["one"], "Inhalt", "Nicht verlieren",
            issue=kind == "issue", checklist=[{"id": new_id(), "text": "Prüfen", "done": True}])
    else:
        docs = NoteService(project)
        record = docs.write(ids["one"], "Inhalt", "Notiz", color="pink", pinned=True)
        record = docs.attach(record.id, tiny_sheet, record.revision_no)
    commands = Commands(project)
    tree = TreeService(commands)
    relations = project.catalog.relations()
    tree.apply(tree.capture(record.id), ids["two"])
    saved = project.catalog.get(record.id)
    assert saved.owner_id == ids["two"] and saved.data == record.data and saved.id == record.id
    if kind in {"task", "issue", "document"}:
        assert project.catalog.relations() == relations
    if kind in {"task", "issue"}:
        assert not KanbanService(project).entries(ids["one"])
        assert KanbanService(project).entries(ids["two"])[0].record.id == record.id
    if kind == "document":
        assert docs.attachment_path(record.id, 0).read_bytes() == tiny_sheet.read_bytes()
    commands.undo()
    assert project.catalog.get(record.id).owner_id == ids["one"]
    commands.redo()
    assert project.catalog.get(record.id).owner_id == ids["two"]
    reopened = ProjectService.open(project.catalog.path.parent)
    try:
        assert reopened.catalog.get(record.id).data == record.data
        assert reopened.catalog.get(record.id).owner_id == ids["two"]
    finally:
        reopened.catalog.close()


def test_references_move_only_usage_and_control_drag_adds_reference(project):
    ids = project.demo()
    commands = Commands(project)
    tree = TreeService(commands)
    asset = project.catalog.get(ids["hero"])
    third = project.create_card("chapter", "Drei", ids["act"])
    edge = next(row for row in project.catalog.relations()
                if row["kind"] == "uses" and row["source_id"] == ids["one"]
                and row["target_id"] == asset.id)
    tree.apply(tree.capture(asset.id, edge["id"]), third.id)
    assert project.catalog.get(asset.id) == asset
    assert next(row for row in project.catalog.relations() if row["id"] == edge["id"])[
        "source_id"] == third.id
    commands.undo()
    assert edge in project.catalog.relations()
    tree.apply(tree.capture(asset.id), third.id, copy=True)
    assert project.catalog.get(asset.id) == asset
    assert len([row for row in project.catalog.relations()
                if row["kind"] == "uses" and row["target_id"] == asset.id]) == 3
    commands.undo()
    assert len([row for row in project.catalog.relations()
                if row["kind"] == "uses" and row["target_id"] == asset.id]) == 2


def test_bad_drops_duplicate_names_cycles_archives_and_stale_revisions_are_atomic(project):
    ids = project.demo()
    tree = TreeService(Commands(project))
    docs = DocumentService(project)
    first = docs.create(ids["one"], "Doppelt")
    docs.create(ids["two"], "Doppelt")
    report = docs.create(ids["one"], "Bericht", generated=True)
    nested = project.create_card("package", "Kind", ids["temple"])
    archived = project.create_card("chapter", "Archiv", ids["act"])
    hidden = project.create_card("asset", "Archivkind", archived.id)
    project.archive(archived.id, True, archived.revision_no)
    stale = tree.capture(ids["hero"])
    project.rename(ids["hero"], "Neu", stale.record.revision_no)
    candidates = [(tree.capture(first.id), ids["two"], False),
                  (tree.capture(report.id), ids["two"], False),
                  (tree.capture(ids["act"]), ids["one"], False),
                  (tree.capture(ids["temple"]), nested.id, False),
                  (tree.capture(ids["hero"]), ids["one"], True),
                  (tree.capture(first.id), hidden.id, False),
                  (tree.capture(first.id), first.id, False),
                  (tree.capture(project.project().id), ids["one"], False),
                  (stale, ids["one"], False)]
    before = project.catalog.export_snapshot()
    for drag, target, copy in candidates:
        with pytest.raises(StudioError):
            tree.apply(drag, target, copy)
        assert project.catalog.export_snapshot() == before
        assert not tree.commands.done


def test_stale_reference_and_undo_after_external_move_do_not_overwrite(project):
    ids = project.demo()
    commands = Commands(project)
    tree = TreeService(commands)
    edge = next(row for row in project.catalog.relations() if row["kind"] == "uses")
    drag = tree.capture(edge["target_id"], edge["id"])
    project.unlink(edge["id"])
    with pytest.raises(StudioError, match="zwischenzeitlich"):
        tree.apply(drag, ids["act"])
    task = IssueService(project).create(ids["one"], "Aufgabe")
    tree.apply(tree.capture(task.id), ids["two"])
    changed = project.catalog.get(task.id)
    project.move(task.id, ids["act"], changed.revision_no)
    before = project.catalog.export_snapshot()
    with pytest.raises(StudioError, match="zwischenzeitlich"):
        commands.undo()
    assert project.catalog.export_snapshot() == before and len(commands.done) == 1


def test_undo_moves_only_owner_and_preserves_later_task_edits(project):
    ids = project.demo()
    service = IssueService(project)
    task = service.create(ids["one"], "Aufgabe", "Alt")
    commands = Commands(project)
    commands.move(task.id, ids["two"])
    moved = project.catalog.get(task.id)
    service.update(task.id, "Neu", "Aktueller Inhalt", moved.revision_no)
    commands.undo()
    saved = project.catalog.get(task.id)
    assert saved.owner_id == ids["one"] and saved.data["body"] == "Aktueller Inhalt"
    assert saved.title == "Neu"
    before = project.catalog.export_snapshot()
    commands.move(task.id, ids["one"])
    assert project.catalog.export_snapshot() == before


@pytest.mark.parametrize("operation", ["link", "relink"])
def test_undo_reference_change_cannot_remove_an_external_retarget(project, operation):
    ids = project.demo()
    commands = Commands(project)
    if operation == "link":
        identifier = commands.link(ids["act"], ids["hero"], "uses")
    else:
        edge = next(row for row in project.catalog.relations()
                    if row["kind"] == "uses" and row["source_id"] == ids["one"]
                    and row["target_id"] == ids["hero"])
        identifier = edge["id"]
        commands.relink(identifier, ids["act"], ids["hero"])
    third = project.create_card("chapter", "Anderer Ort", ids["act"])
    project.relink(identifier, third.id, ids["hero"])
    before = project.catalog.export_snapshot()
    with pytest.raises(StudioError, match="zwischenzeitlich"):
        commands.undo()
    assert project.catalog.export_snapshot() == before and commands.done


def test_invalid_persisted_note_style_is_rejected_on_reopen(project):
    note = NoteService(project).write(project.project().id, "Notiz", "Text")
    project.catalog.save(note, data=note.data | {"note_pinned": "invalid"})
    with pytest.raises(StudioError, match="Wahrheitswert"):
        ProjectService.open(project.catalog.path.parent)


def test_notes_classification_shared_scope_colors_pin_and_search(project):
    ids = project.demo()
    service = NoteService(project)
    legacy = service.create(ids["one"], "Alt", "Bisherige Notiz")
    shared = service.write(ids["hero"], "SW prüfen", "Raster testen", color="blue", pinned=True)
    service.create(ids["one"], "Anforderung", template="Kapitelanforderung")
    service.create(ids["one"], "Bericht", generated=True)
    assert is_note(legacy)
    assert [row.id for row in service.notes(ids["one"])] == [shared.id, legacy.id]
    assert [row.id for row in service.notes(ids["two"], "RASTER", "blue")] == [shared.id]
    assert not service.notes(ids["two"], color="pink")
    assert service.notes(project.project().id).count(shared) == 1


@pytest.mark.parametrize("color,pinned", [("red", False), ([], False), ("blue", "yes")])
def test_invalid_note_options_are_atomic(project, color, pinned):
    service = NoteService(project)
    before = project.catalog.export_snapshot()
    with pytest.raises(StudioError):
        service.write(project.project().id, "Nicht speichern", "Text", color=color, pinned=pinned)
    assert project.catalog.export_snapshot() == before


def test_note_edit_preserves_attachments_provenance_and_conflicting_draft(project, tiny_sheet):
    ids = project.demo()
    service = NoteService(project)
    record = service.create(ids["one"], "Alt", "Inhalt")
    record = service.attach(record.id, tiny_sheet, record.revision_no)
    updated = service.write(record.owner_id, "Neu", "Text", identifier=record.id,
        expected_revision=record.revision_no, color="purple", pinned=True)
    assert updated.data["attachments"] == record.data["attachments"]
    before = project.catalog.export_snapshot()
    with pytest.raises(StudioError, match="Neuere"):
        service.write(record.owner_id, "Veraltet", "Nicht überschreiben", identifier=record.id,
                      expected_revision=record.revision_no)
    assert project.catalog.export_snapshot() == before
    assert service.write(updated.owner_id, updated.title, updated.data["body"],
                         identifier=updated.id, expected_revision=updated.revision_no,
                         color="purple", pinned=True) == updated
    reopened = ProjectService.open(project.catalog.path.parent)
    try:
        assert NoteService(reopened).notes(ids["one"])[0] == updated
    finally:
        reopened.catalog.close()
