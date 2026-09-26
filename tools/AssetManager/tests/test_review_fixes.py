"""Regression coverage for the first human review of the Studio dashboard."""

import pytest

from etherfood_studio.application.issue_service import Finding, IssueService
from etherfood_studio.application.commands import Commands
from etherfood_studio.application.document_service import DocumentService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.status_service import StatusService
from etherfood_studio.domain.models import StudioError


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    service = ProjectService.new(root, "Review")
    yield service
    service.catalog.close()


def test_task_update_preserves_identity_finding_and_invalidates_approval(project):
    ids = project.demo()
    service = IssueService(project)
    item = service.create(ids["hero"], "Prüfen", "Alt", issue=True, approval_needed=True,
                          finding=Finding(direction="SW", frame_index=0))
    approved = service.set_status(item.id, "done", item.revision_no, approval_confirmed=True)
    updated = service.update(item.id, "Neue Prüfung", "Neuer Inhalt", approved.revision_no,
                             priority="high", assignee="Anna")
    assert updated.id == item.id and updated.owner_id == item.owner_id
    assert updated.data["finding"] == item.data["finding"]
    assert updated.data["status"] == "open" and not updated.data["approval_confirmed"]
    assert service.search("Neuer Inhalt")[0].id == item.id
    unchanged = service.update(item.id, updated.title, updated.data["body"], updated.revision_no,
                               priority="high", assignee="Anna")
    assert unchanged.revision_no == updated.revision_no
    before = project.catalog.export_snapshot()
    with pytest.raises(StudioError, match="Neuere"):
        service.update(item.id, "Veraltet", "Nichts überschreiben", item.revision_no)
    with pytest.raises(StudioError):
        service.update(item.id, "", "Ungültig", updated.revision_no)
    assert project.catalog.export_snapshot() == before
    assert StatusService(project).status(ids["hero"])["source"].state == "waiting_external"
    reopened = ProjectService.open(project.catalog.path.parent)
    assert reopened.catalog.get(item.id).data["body"] == "Neuer Inhalt"
    reopened.catalog.close()


def test_task_body_limit_and_non_task_rejected(project):
    service = IssueService(project)
    owner = project.project()
    with pytest.raises(StudioError, match="1 MiB"):
        service.create(owner.id, "Zu groß", "a" * (1024 * 1024 + 1))
    with pytest.raises(StudioError):
        service.update(owner.id, "Kein Task", "Text", owner.revision_no)


def test_retarget_atomic_identity_undo_and_cycle_rejection(project):
    ids = project.demo()
    commands = Commands(project)
    edge_id = commands.link(ids["hero"], ids["one"], "depends_on")
    commands.relink(edge_id, ids["hero"], ids["two"])
    edge = lambda: next(row for row in project.catalog.relations() if row["id"] == edge_id)
    assert edge()["target_id"] == ids["two"]
    commands.undo()
    assert edge()["target_id"] == ids["one"]
    commands.redo()
    assert edge()["target_id"] == ids["two"]
    commands.link(ids["one"], ids["hero"], "depends_on")
    before = project.catalog.export_snapshot()
    stack = list(commands.done)
    with pytest.raises(StudioError, match="Zyklus"):
        commands.relink(edge_id, ids["hero"], ids["one"])
    with pytest.raises(StudioError):
        commands.relink(edge_id, ids["hero"], ids["hero"])
    assert project.catalog.export_snapshot() == before and commands.done == stack
    owner_edge = next(row for row in project.catalog.relations()
                      if row["source_id"] == ids["temple"] and row["kind"] == "belongs_to")
    commands.relink(owner_edge["id"], ids["temple"], ids["two"])
    assert project.catalog.get(ids["temple"]).owner_id == ids["two"]
    commands.undo()
    assert owner_edge in project.catalog.relations()


def test_duplicate_retarget_is_rejected_without_losing_edge(project):
    ids = project.demo()
    edges = [row for row in project.catalog.relations()
             if row["kind"] == "uses" and row["source_id"] == ids["one"]]
    before = project.catalog.export_snapshot()
    with pytest.raises(StudioError, match="existiert"):
        project.relink(edges[0]["id"], ids["one"], edges[1]["target_id"])
    assert project.catalog.export_snapshot() == before


def test_document_rename_keeps_body_and_rejects_duplicate_conflict_and_report(project):
    service = DocumentService(project)
    owner = project.project().id
    first = service.create(owner, "Notiz 1", "Nicht verlieren")
    second = service.create(owner, "Notiz 2")
    report = service.create(owner, "Bericht", generated=True)
    updated = service.rename(first.id, "Umbenannt", first.revision_no)
    assert updated.id == first.id and updated.data == first.data
    before = project.catalog.export_snapshot()
    with pytest.raises(StudioError, match="existiert"):
        service.rename(first.id, second.title, updated.revision_no)
    with pytest.raises(StudioError, match="Neuere"):
        service.rename(first.id, "Veraltet", first.revision_no)
    with pytest.raises(StudioError, match="schreibgeschützt"):
        service.rename(report.id, "Manipuliert", report.revision_no)
    assert project.catalog.export_snapshot() == before
