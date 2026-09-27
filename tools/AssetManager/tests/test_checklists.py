"""Task checklists share the existing identity, revisions and explicit approval guards."""

import json

import pytest

from etherfood_studio.application.issue_service import IssueService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.status_service import StatusService
from etherfood_studio.domain.checklists import validate_checklist
from etherfood_studio.domain.models import StudioError, new_id
from etherfood_studio.storage.sqlite_repository import Catalog


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    project = ProjectService.new(root, "To-dos")
    yield project
    project.catalog.close()


def item(text="Walk prüfen", done=False):
    return {"id": new_id(), "text": text, "done": done}


def test_checklist_round_trip_search_completion_and_approval(project):
    identifiers = project.demo()
    service = IssueService(project)
    record = service.create(identifiers["hero"], "Quellen prüfen", "Beschreibung",
                            checklist=[item()], approval_needed=True)
    with pytest.raises(StudioError, match="To-do"):
        service.set_status(record.id, "done", record.revision_no, approval_confirmed=True)
    assert service.search("Walk prüfen", scope_id=identifiers["one"])[0].id == record.id
    completed = [dict(record.data["checklist"][0], done=True)]
    updated = service.update(record.id, record.title, record.data["body"], record.revision_no,
                             checklist=completed)
    assert updated.data["status"] == "open" and not updated.data["approval_confirmed"]
    with pytest.raises(StudioError, match="Abnahme"):
        service.set_status(updated.id, "done", updated.revision_no)
    approved = service.set_status(updated.id, "done", updated.revision_no, approval_confirmed=True)
    reopened = service.update(record.id, record.title, record.data["body"], approved.revision_no,
                              checklist=record.data["checklist"])
    assert reopened.data["status"] == "open" and not reopened.data["approval_confirmed"]
    assert reopened.data["checklist"][0]["id"] == record.data["checklist"][0]["id"]
    assert StatusService(project).status(identifiers["hero"])["source"].state == "waiting_external"
    loaded = ProjectService.open(project.catalog.path.parent)
    try:
        assert loaded.catalog.get(record.id) == reopened
    finally:
        loaded.catalog.close()


def test_legacy_tasks_preserve_checklists_and_conflicts_do_not_overwrite(project):
    service = IssueService(project)
    record = service.create(project.project().id, "Alt", checklist=[item()])
    updated = service.update(record.id, record.title, "Neuer Text", record.revision_no)
    assert updated.data["checklist"] == record.data["checklist"]
    before = project.catalog.export_snapshot()
    with pytest.raises(StudioError, match="Neuere"):
        service.update(record.id, record.title, "Veraltet", record.revision_no,
                       checklist=[item(done=True)])
    assert project.catalog.export_snapshot() == before
    legacy = dict(updated.data)
    del legacy["checklist"]
    record = project.catalog.save(updated, data=legacy)
    project.validate_structure()
    assert service.set_status(record.id, "done", record.revision_no).data["status"] == "done"


@pytest.mark.parametrize("value", [None, {}, [True], [{"text": "ohne ID"}],
    [{"id": "bad", "text": "Text", "done": False}],
    [{"id": new_id(), "text": " ", "done": False}],
    [{"id": new_id(), "text": "Text", "done": "yes"}], [item()] * 2,
    [item("x" * 501)], [item() for _ in range(201)]])
def test_invalid_checklists_are_rejected(value):
    with pytest.raises(StudioError):
        validate_checklist(value)


def test_invalid_snapshot_checklist_rolls_back_atomically(project, tmp_path):
    service = IssueService(project)
    record = service.create(project.project().id, "Nicht beschädigen", checklist=[item()])
    before = project.catalog.export_snapshot()
    snapshot = json.loads(before)
    # The shared catalog exports records without an alternate task store.
    row = next(r for r in snapshot["objects"] if r["id"] == record.id)
    row["data"]["checklist"][0]["done"] = "false"
    catalog = Catalog(tmp_path / "invalid-snapshot.sqlite", create=True)
    try:
        with pytest.raises(StudioError, match="Zustand"):
            ProjectService(catalog).import_snapshot(json.dumps(snapshot))
        assert not catalog.records()
    finally:
        catalog.close()
    assert project.catalog.export_snapshot() == before
