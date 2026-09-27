"""Shared assets, document provenance and workflow truthfulness."""

from dataclasses import asdict
import json

import pytest

from etherfood_studio.application.document_service import DocumentService, TEMPLATES
from etherfood_studio.application.issue_service import Finding, IssueService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.status_service import StatusService
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.workflows import (
    Evidence, input_fingerprint, invalidated_steps, progress, resolve, template,
)
from etherfood_studio.storage.blob_store import file_hash
from etherfood_studio.storage.sqlite_repository import Catalog


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "Projekt Grün #1 100%"
    root.mkdir()
    service = ProjectService.new(root, "Synthetisches Testprojekt")
    yield service
    service.catalog.close()


def test_shared_asset_move_archive_and_reopen(project):
    ids = project.demo()
    hero = project.catalog.get(ids["hero"])
    uses = [edge for edge in project.catalog.relations()
            if edge["kind"] == "uses" and edge["target_id"] == hero.id]
    assert len(uses) == 2
    moved = project.move(hero.id, ids["two"], hero.revision_no)
    assert moved.id == hero.id
    assert project.catalog.relations().count(uses[0]) == 1
    project.archive(ids["one"], True, project.catalog.get(ids["one"]).revision_no)
    assert project.catalog.get(hero.id).archived is False
    other = project.create_card("act", "Demo: Akt 2", project.project().id)
    assert project.create_card("chapter", "Weiter arbeiten", other.id).owner_id == other.id
    reopened = ProjectService.open(project.catalog.path.parent)
    assert reopened.catalog.get(hero.id).owner_id == ids["two"]
    reopened.catalog.close()


def test_cycles_and_invalid_hierarchy_rollback(project):
    ids = project.demo()
    before = project.catalog.export_snapshot()
    with pytest.raises(StudioError):
        project.move(ids["act"], ids["one"], project.catalog.get(ids["act"]).revision_no)
    assert project.catalog.export_snapshot() == before
    child = project.create_card("package", "Innen", ids["temple"])
    with pytest.raises(StudioError, match="Zyklus"):
        project.move(ids["temple"], child.id, project.catalog.get(ids["temple"]).revision_no)
    project.relate(ids["one"], ids["two"], "depends_on")
    before = project.catalog.export_snapshot()
    with pytest.raises(StudioError, match="Zyklus"):
        project.relate(ids["two"], ids["one"], "depends_on")
    assert project.catalog.export_snapshot() == before
    assert "Kapitel 2" in StatusService(project).status(ids["one"])["dependencies"].reason


def test_documents_conflicts_reports_attachments_and_move(project, tiny_sheet, tmp_path):
    ids = project.demo()
    docs = DocumentService(project)
    manual = docs.create(ids["hero"], "Notiz", "Eigener Absatz <script>alert(1)</script>")
    report = docs.create(ids["hero"], "Bericht", "Nicht geprüft", generated=True)
    with pytest.raises(StudioError, match="schreibgeschützt"):
        docs.save(report.id, "fake", report.revision_no)
    before = file_hash(tiny_sheet)
    attached = docs.attach(manual.id, tiny_sheet, manual.revision_no)
    assert file_hash(docs.attachment_path(manual.id, 0)) == before
    moved = project.move(ids["hero"], ids["two"], project.catalog.get(ids["hero"]).revision_no)
    assert len(project.catalog.history(manual.id)) == 2
    assert docs.documents(moved.id)[0].owner_id == moved.id
    assert project.catalog.get(manual.id).data["body"] == manual.data["body"]
    with pytest.raises(StudioError, match="Neuere"):
        docs.save(manual.id, "overwrite", manual.revision_no)
    docs.save(attached.id, "Neue Notiz", attached.revision_no)
    assert file_hash(tiny_sheet) == before
    source = tmp_path / "README.md"
    source.write_text("# Echte Quelle\n", encoding="utf-8")
    imported = docs.import_markdown(ids["hero"], source)
    assert source.read_text() == "# Echte Quelle\n"
    assert imported.data["provenance"]["sha256"] == file_hash(source)
    with pytest.raises(StudioError, match="existiert"):
        docs.import_markdown(ids["hero"], source)
    assert docs.search("echte", scope_id=ids["two"])[0].id == imported.id
    assert len(TEMPLATES) == 7


def test_tasks_finding_filter_rename_and_required_approval(project, tiny_sheet):
    ids = project.demo()
    issues = IssueService(project)
    finding = Finding(asset_id=ids["hero"], pose="walk", direction="SW", frame_count=16,
                      frame_index=4, graphics_profile="comic_high")
    item = issues.create(ids["hero"], "SW prüfen", "Noch offen", issue=True,
                         finding=finding, approval_needed=True)
    assert Finding(**json.loads(json.dumps(asdict(finding)))) == finding
    assert issues.search("SW", scope_id=ids["one"], asset_type="animated")[0].id == item.id
    project.rename(ids["one"], "Neuer Name", project.catalog.get(ids["one"]).revision_no)
    assert issues.search(scope_id=ids["one"])[0].owner_id == ids["hero"]
    with pytest.raises(StudioError, match="Abnahme"):
        issues.set_status(item.id, "done", item.revision_no)
    changed = issues.set_status(item.id, "done", item.revision_no, approval_confirmed=True)
    assert issues.search(status="done")[0].id == changed.id
    assert StatusService(project).status(ids["hero"])["source"].state == "waiting_external"


def test_missing_external_drive_is_not_an_empty_project(project, tmp_path):
    settings = project.catalog.path.parent / "project.studio-local.json"
    data = json.loads(settings.read_text())
    data["roots"]["VERSIONS_ROOT"] = str(tmp_path / "missing-drive")
    settings.write_text(json.dumps(data))
    opened = ProjectService.open(project.catalog.path.parent)
    assert opened.unavailable_roots() == ["VERSIONS_ROOT"]
    assert opened.project().id == project.project().id
    assert json.loads(settings.read_text()) == data
    opened.catalog.close()


def test_snapshot_import_validates_real_hierarchy(project, tmp_path):
    ids = project.demo()
    target = Catalog(tmp_path / "snapshot.studio.sqlite", create=True)
    other = ProjectService(target)
    other.import_snapshot(project.catalog.export_snapshot())
    assert other.catalog.get(ids["hero"]).id == ids["hero"]
    target.close()
    invalid = json.loads(project.catalog.export_snapshot())
    for row in invalid["objects"]:
        if row["id"] == ids["hero"]:
            row["owner_id"] = ids["hero"]
    target = Catalog(tmp_path / "invalid.studio.sqlite", create=True)
    with pytest.raises(StudioError):
        ProjectService(target).import_snapshot(json.dumps(invalid))
    assert target.records() == []
    target.close()


def test_layout_and_names_do_not_invalidate_workflows(project):
    ids = project.demo()
    before = StatusService(project).status(ids["hero"])
    project.catalog.save_layout(ids["hero"], {"x": 33, "y": 50})
    project.rename(ids["one"], "Neu", project.catalog.get(ids["one"]).revision_no)
    assert StatusService(project).status(ids["hero"]) == before
    assert invalidated_steps({"title", "layout", "zoom"}) == frozenset()
    assert "color" in invalidated_steps({"mask"})


def test_workflow_external_static_and_unknown_progress():
    assert resolve("animated", {})["source"].state == "waiting_external"
    static = resolve("static", {})
    assert static["frames"].state == "not_required" and static["frames"].reason
    assert progress(static, ("checks", "missing")) == (0, 2)
    assert {step.id for step in template("document")} == {"document", "review"}


@pytest.mark.parametrize("state", ["skipped", "failed", "cancelled", "running", "passed"])
def test_workflow_evidence_and_exact_build_binding(state):
    inputs = {"source": "source-1", "mask": "mask-1", "mask_source": "source-1"}
    proof = Evidence(state, input_fingerprint("color", inputs), "build-1")
    resolved = resolve("animated", inputs, {"color": proof}, current_build_id="build-1")
    assert resolved["color"].state == ("blocked" if state == "skipped" else state)
    if state == "passed":
        assert resolve("animated", inputs, {"color": proof})["color"].state == "blocked"
    revised = inputs | {"source": "source-2"}
    assert resolve("animated", revised, {"color": proof})["color"].state == "stale"
    assert proof.state == state  # Historical proof remains immutable.


def test_required_checks_cannot_be_overruled_by_done_flag():
    inputs = {"source": "source", "mask": "mask", "mask_source": "source"}
    evidence = {step: Evidence("passed", input_fingerprint(step, inputs), "build")
                for step in ("color", "frames", "scale")}
    evidence["checks"] = Evidence("failed", input_fingerprint("checks", inputs), "build")
    evidence["review"] = Evidence("passed", input_fingerprint("review", inputs), "build")
    result = resolve("animated", inputs | {"done": "yes"}, evidence, current_build_id="build")
    assert result["checks"].state == "failed"
    assert result["review"].state == "blocked"
    assert result["runtime"].state == "blocked"


def test_illegal_evidence_and_unbound_mask_are_not_success():
    inputs = {"source": "new-source", "mask": "old-mask", "mask_source": "old-source"}
    assert resolve("animated", inputs)["mask"].state == "stale"
    with pytest.raises(StudioError, match="Nachweisstatus"):
        resolve("animated", inputs, {"source": Evidence("done", "invalid")})
