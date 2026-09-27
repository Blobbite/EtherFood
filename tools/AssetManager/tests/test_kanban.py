"""Kanban is a scoped, grouped view of the existing revisioned task records."""

import pytest

from etherfood_studio.application.issue_service import IssueService
from etherfood_studio.application.kanban_service import KanbanService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.domain.models import new_id


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "board"
    root.mkdir()
    value = ProjectService.new(root, "Kanban-Test")
    yield value
    value.catalog.close()


def seed(project):
    ids = project.demo()
    ids["project"] = project.project().id
    ids["global"] = next(card.id for card in project.cards() if card.kind == "global")
    service = IssueService(project)
    tasks = {key: service.create(ids[key], "Aufgabe " + key, "Inhalt " + key,
                                 issue=key == "hero")
             for key in ("project", "global", "act", "one", "two", "hero", "temple")}
    return ids, tasks


def test_root_grouping_is_read_only_and_has_no_shared_duplicates(project):
    ids, tasks = seed(project)
    before = project.catalog.export_snapshot()
    entries = KanbanService(project).entries(ids["project"])
    assert {entry.record.id for entry in entries} == {task.id for task in tasks.values()}
    assert len(entries) == len(tasks) and not any(entry.shared for entry in entries)
    by_id = {entry.record.id: entry for entry in entries}
    assert by_id[tasks["project"].id].groups == by_id[tasks["global"].id].groups
    assert by_id[tasks["project"].id].groups[0].title == "Projektweite Aufgaben"
    assert [group.id for group in by_id[tasks["temple"].id].groups] == [
        ids["act"], ids["one"], ids["temple"]]
    assert by_id[tasks["hero"].id].groups[-1].id == ids["hero"]
    assert project.catalog.export_snapshot() == before


@pytest.mark.parametrize("scope,expected", [
    ("act", {"act", "one", "two", "hero", "temple"}),
    ("one", {"one", "hero", "temple"}), ("two", {"two", "hero"}),
    ("hero", {"hero"}), ("global", {"global", "hero"}),
])
def test_scope_includes_owned_and_used_tasks_once(project, scope, expected):
    ids, tasks = seed(project)
    entries = KanbanService(project).entries(ids[scope])
    assert {entry.record.id for entry in entries} == {tasks[key].id for key in expected}
    assert len(entries) == len(expected)
    if scope in {"act", "one", "two"}:
        shared = next(entry for entry in entries if entry.record.id == tasks["hero"].id)
        assert shared.shared and shared.groups[0].id == "shared"
        assert shared.record.owner_id == ids["hero"]
        assert "Projektweite Inhalte" in shared.location


def test_used_packages_include_children_handle_cycles_and_ignore_dependencies(project):
    ids, tasks = seed(project)
    child = project.create_card("asset", "Baustein", ids["temple"])
    nested = project.create_card("package", "Weiteres Paket", ids["global"])
    task = IssueService(project).create(child.id, "Paketinhalt prüfen")
    project.relate(ids["two"], ids["temple"], "uses")
    project.relate(ids["temple"], nested.id, "uses")
    project.relate(nested.id, ids["temple"], "uses")
    project.relate(ids["two"], ids["one"], "depends_on")
    rows = IssueService(project).search(scope_id=ids["two"])
    assert {row.id for row in rows} == {tasks[key].id for key in ("two", "hero", "temple")} \
        | {task.id}


def test_archived_tasks_owners_and_ancestors_are_excluded(project):
    ids, tasks = seed(project)
    project.archive(ids["act"], True, project.catalog.get(ids["act"]).revision_no)
    assert not KanbanService(project).entries(ids["one"])
    assert {row.id for row in IssueService(project).search()} == {
        tasks[key].id for key in ("project", "global", "hero")}
    project.archive(tasks["project"].id, True, tasks["project"].revision_no)
    project.archive(ids["hero"], True, project.catalog.get(ids["hero"]).revision_no)
    assert [row.id for row in IssueService(project).search()] == [tasks["global"].id]


def test_type_text_checklist_and_asset_filters_work_on_legacy_and_current_tasks(project):
    ids, tasks = seed(project)
    legacy = tasks["one"]
    project.catalog.save(legacy, data={key: value for key, value in legacy.data.items()
                                       if key != "checklist"})
    service = IssueService(project)
    task = service.create(ids["hero"], "Zusatz", checklist=[
        {"id": new_id(), "text": "SW kontrollieren", "done": False}])
    board = KanbanService(project)
    assert [e.record.id for e in board.entries(ids["project"], kind="issue")] == [tasks["hero"].id]
    assert [e.record.id for e in board.entries(ids["one"], "sW KONTROLLIEREN")] == [task.id]
    assert {e.record.id for e in board.entries(ids["act"], asset_type="animated")} == {
        task.id, tasks["hero"].id}
    assert not board.entries(ids["two"], "Inhalt one")


def test_rename_move_priority_and_restart_keep_ids_and_ownership(project):
    ids, tasks = seed(project)
    service = IssueService(project)
    urgent = service.create(ids["one"], "Zuerst prüfen", priority="critical")
    entries = KanbanService(project).entries(ids["one"])
    assert entries[0].record.id == urgent.id
    project.rename(ids["one"], "Neuer Kapitelname", project.catalog.get(ids["one"]).revision_no)
    moved = project.move(ids["temple"], ids["two"], project.catalog.get(ids["temple"]).revision_no)
    with_reopened = ProjectService.open(project.catalog.path.parent)
    try:
        entries = KanbanService(with_reopened).entries(ids["project"])
        renamed = next(e for e in entries if e.record.id == tasks["one"].id)
        assert renamed.groups[-1].title == "Neuer Kapitelname"
        assert renamed.record.owner_id == ids["one"]
        moved_task = next(e for e in entries if e.record.id == tasks["temple"].id)
        assert [g.id for g in moved_task.groups] == [ids["act"], ids["two"], moved.id]
        assert moved_task.record == tasks["temple"]
    finally:
        with_reopened.catalog.close()
