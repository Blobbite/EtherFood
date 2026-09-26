"""Undo preserves identity and never replays an external deployment."""

import pytest

from etherfood_studio.application.commands import Commands
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.domain.models import StudioError


@pytest.fixture
def project(tmp_path):
    service = ProjectService.new(tmp_path, "Synthetische Undo-Prüfung")
    yield service
    service.catalog.close()


def test_create_layout_and_reload_undo(project):
    commands = Commands(project)
    identifier = commands.create_card("act", "Akt", project.project().id)
    original = project.catalog.get(identifier)
    commands.layout(identifier, {"x": 20, "y": 40})
    assert project.catalog.get(identifier) == original
    commands.undo()
    assert project.catalog.layout(identifier) == {}
    commands.undo()
    assert project.catalog.get(identifier).archived
    commands.redo()
    commands.redo()
    reopened = ProjectService.open(project.catalog.path.parent)
    assert reopened.catalog.get(identifier).archived is False
    assert reopened.catalog.layout(identifier) == {"x": 20, "y": 40}
    reopened.catalog.close()


def test_link_undo_redo_same_asset_and_relation_ids(project):
    ids = project.demo()
    commands = Commands(project)
    edge = commands.link(ids["temple"], ids["hero"], "uses")
    commands.unlink(edge)
    commands.undo()
    assert any(row["id"] == edge for row in project.catalog.relations())
    commands.undo()
    assert not any(row["id"] == edge for row in project.catalog.relations())
    commands.redo()
    assert any(row["id"] == edge for row in project.catalog.relations())
    assert len([row for row in project.cards() if row.id == ids["hero"]]) == 1


def test_move_identity_and_failed_command_does_not_enter_stack(project):
    ids = project.demo()
    commands = Commands(project)
    before = project.catalog.relations()
    commands.move(ids["hero"], ids["one"])
    commands.undo()
    assert project.catalog.relations() == before
    commands.link(ids["one"], ids["two"], "depends_on")
    count = len(commands.done)
    with pytest.raises(StudioError):
        commands.link(ids["two"], ids["one"], "depends_on")
    assert len(commands.done) == count
