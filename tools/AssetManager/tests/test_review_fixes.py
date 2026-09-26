"""Regression coverage for the first human review of the Studio dashboard."""

import pytest

from etherfood_studio.application.issue_service import Finding, IssueService
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
