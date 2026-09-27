"""Portable, validated post-it positions are separate from content and Canvas layout."""

import json

import pytest

from etherfood_studio.application.note_service import NoteService
from etherfood_studio.application.commands import Commands
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.domain.models import StudioError
from etherfood_studio.storage.sqlite_repository import Catalog


@pytest.fixture
def service(tmp_path):
    project = ProjectService.new(tmp_path, "Pinnwand")
    yield NoteService(project)
    project.catalog.close()


def test_position_persists_without_changing_content_revision_or_canvas(service, tmp_path):
    owner = service.project.project().id
    note = service.write(owner, "Idee", "Alt")
    canvas = {"x": -52, "y": 87, "manual": {"x": 10, "y": 20}}
    service.catalog.save_layout(note.id, canvas)
    service.place(note.id, {"x": 710, "y": 421})
    assert service.catalog.get(note.id) == note
    assert service.catalog.layout(note.id) == canvas | {"note_board": {"x": 710, "y": 421}}
    before = service.catalog.export_snapshot()
    service.place(note.id, {"x": 710, "y": 421})
    assert service.catalog.export_snapshot() == before
    # Moving the post-it does not make an existing content editor's revision stale.
    changed = service.write(owner, "Idee", "Neu", identifier=note.id,
                            expected_revision=note.revision_no)
    assert service.position(note.id) == {"x": 710, "y": 421}
    reopened = ProjectService.open(service.catalog.path.parent)
    try:
        assert NoteService(reopened).position(note.id) == {"x": 710, "y": 421}
        assert reopened.catalog.get(note.id) == changed
    finally:
        reopened.catalog.close()
    target = Catalog(tmp_path / "imported.sqlite", create=True)
    try:
        imported = ProjectService(target)
        imported.import_snapshot(before)
        assert NoteService(imported).position(note.id) == {"x": 710, "y": 421}
    finally:
        target.close()


@pytest.mark.parametrize("position", [
    {}, {"x": 10}, [], {"x": 0, "y": "5"}, {"x": True, "y": 2},
    {"x": -1, "y": 0}, {"x": 0, "y": float("inf")}, {"x": float("nan"), "y": 0},
    {"x": 100001, "y": 0}, {"x": 10 ** 500, "y": 0}, {"x": 1, "y": 2, "z": 3},
])
def test_invalid_positions_and_creations_are_atomic(service, position):
    owner = service.project.project().id
    note = service.write(owner, "Idee", "Inhalt")
    before = service.catalog.export_snapshot()
    with pytest.raises(StudioError, match="Pinnwand"):
        service.place(note.id, position)
    with pytest.raises(StudioError, match="Pinnwand"):
        service.write(owner, "Neue Notiz", "Entwurf", position=position)
    assert service.catalog.export_snapshot() == before


def test_position_does_not_move_reports_or_archived_notes(service):
    owner = service.project.project().id
    report = service.create(owner, "Bericht", generated=True)
    note = service.write(owner, "Notiz", "Text")
    service.catalog.save(note, archived=True)
    before = service.catalog.export_snapshot()
    for identifier in (report.id, note.id, owner):
        with pytest.raises(StudioError):
            service.place(identifier, {"x": 10, "y": 20})
    assert service.catalog.export_snapshot() == before


def test_reopen_rejects_invalid_stored_note_layout(service):
    note = service.write(service.project.project().id, "Idee", "Text", position={"x": 10, "y": 20})
    service.catalog.db.execute("UPDATE layouts SET data=? WHERE object_id=?",
        (json.dumps({"note_board": {"x": "invalid", "y": 5}}), note.id))
    with pytest.raises(StudioError, match="Pinnwand"):
        ProjectService.open(service.catalog.path.parent)


def test_failed_initial_position_write_rolls_back_new_note(service, monkeypatch):
    before = service.catalog.export_snapshot()

    def fail(*args):
        raise OSError("Nicht schreibbar")

    monkeypatch.setattr(service.catalog, "save_layout", fail)
    with pytest.raises(OSError):
        service.write(service.project.project().id, "Neu", "Text", position={"x": 10, "y": 20})
    assert service.catalog.export_snapshot() == before


@pytest.mark.parametrize("grouped", [False, True])
def test_canvas_undo_redo_does_not_revert_later_board_moves(service, grouped):
    note = service.write(service.project.project().id, "Idee", "Text")
    commands = Commands(service.project)
    canvas_position = {"x": -30, "y": 44}
    if grouped:
        commands.layouts({note.id: canvas_position})
    else:
        commands.layout(note.id, canvas_position)
    service.place(note.id, {"x": 670, "y": 254})
    commands.undo()
    assert service.catalog.layout(note.id) == {"note_board": {"x": 670, "y": 254}}
    service.place(note.id, {"x": 730, "y": 290})
    commands.redo()
    assert service.catalog.layout(note.id) == canvas_position | {
        "note_board": {"x": 730, "y": 290}}
    assert service.catalog.get(note.id) == note
