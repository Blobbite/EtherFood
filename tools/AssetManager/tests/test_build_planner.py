"""Content invalidation, immutable history and verified cache with actual subprocess outputs."""

from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.build_graphs import asset_graph, diagnostic_graph
from etherfood_studio.application.build_planner import BuildPlanner
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.source_import import SourceImportService, SourceSpec
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.builds import (
    BuildGraph, BuildNode, ContentInput, Dependency, OutputSpec, VariantTarget,
)
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.sources import SourceKey
from etherfood_studio.pipelines.fingerprints import digest
from etherfood_studio.storage.blob_store import file_hash
from etherfood_studio.storage.job_store import JobStore
from etherfood_studio.storage.sqlite_repository import Catalog


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "Buildprojekt"
    root.mkdir()
    value = ProjectService.new(root, "Builds")
    yield value
    value.catalog.close()


def branches(master="master1", walk_mask="mask1", *, failure=False):
    template = diagnostic_graph().nodes[0]

    def node(key, stage, inputs=(), parents=(), mode="success"):
        return replace(template, key=key, stage=stage, inputs=tuple(inputs),
                       dependencies=tuple(Dependency(p, "result.json", "diagnostic")
                                          for p in parents), parameters=json.dumps({"mode": mode}))

    return BuildGraph((
        node("palette", "profile", [ContentInput("master_mask", "mask", digest(master)),
                                    ContentInput("master_source", "image", digest("source"))]),
        node("walk_mask", "maskcheck", [ContentInput("target_mask", "mask", digest(walk_mask))]),
        node("walk", "color", parents=["palette", "walk_mask"],
             mode="missing" if failure else "success"),
        node("walk_package", "package", parents=["walk"]),
        node("stand", "color", parents=["palette"]),
        node("temple", "package", [ContentInput("source", "image", digest("temple"))]),
    ), (VariantTarget("walk", "walk_package"), VariantTarget("stand", "stand"),
        VariantTarget("temple", "temple")))


def rows(plan):
    return {r.node.key: r for r in plan.nodes}


def execute(project, graph):
    planner = BuildPlanner(project)
    plan = planner.plan(project.project().id, graph)
    result = planner.execute(plan)
    assert result["status"] == "succeeded", result
    return planner, result


def test_nine_stages_plan_actual_reuse_restart_and_history(project):
    planner, report = execute(project, diagnostic_graph())
    assert len(report["actual"]) == 9 and {r["actual"] for r in report["actual"]} == {"built"}
    stored = project.catalog.get(report["run_id"])
    graph = diagnostic_graph()
    plan = planner.plan(project.project().id, graph)
    assert plan.counts == {"new": 0, "reused": 1, "stale": 0, "blocked": 0, "not_required": 0}
    before_jobs = len(JobStore(project.catalog).rows())
    assert all(r["actual"] == "reused" for r in planner.execute(plan)["actual"])
    assert len(JobStore(project.catalog).rows()) == before_jobs
    reopened = ProjectService.open(project.catalog.path.parent)
    try:
        assert BuildPlanner(reopened).plan(project.project().id, graph).counts["reused"] == 1
        assert reopened.catalog.get(stored.id) == stored
        with pytest.raises(StudioError, match="unveränderlich"):
            reopened.catalog.save(stored, title="Alter Build verändert")
    finally:
        reopened.catalog.close()


def test_walk_mask_invalidates_only_its_branch_and_master_all_dependents(project):
    planner, _ = execute(project, branches())
    owner = project.project().id
    initial = rows(planner.plan(owner, branches()))
    assert {r.state for r in initial.values()} == {"reused"}
    changed = rows(planner.plan(owner, branches(walk_mask="mask2")))
    assert {key for key, value in changed.items() if value.state == "stale"} == {
        "walk_mask", "walk", "walk_package"}
    assert changed["temple"].state == changed["stand"].state == "reused"
    master = rows(planner.plan(owner, branches(master="master2")))
    assert {key for key, value in master.items() if value.state == "stale"} == {
        "palette", "walk", "walk_package", "stand"}
    assert master["walk_mask"].state == master["temple"].state == "reused"


def test_names_canvas_timestamps_do_not_change_pixel_inputs(project):
    ids = project.demo()
    planner, _ = execute(project, branches())
    before = rows(planner.plan(project.project().id, branches()))
    card = project.catalog.get(ids["one"])
    project.rename(card.id, "Anderes Kapitel", card.revision_no)
    project.catalog.save_layout(card.id, {"x": 500, "y": 800, "width": 250, "height": 120})
    after = rows(planner.plan(project.project().id, branches()))
    assert {k: r.fingerprint for k, r in before.items()} == \
        {k: r.fingerprint for k, r in after.items()}
    assert {r.state for r in after.values()} == {"reused"}


@pytest.mark.parametrize("damage", ["bytes", "report", "symlink", "manifest", "extra"])
def test_cache_damage_and_missing_reports_prevent_reuse(project, tmp_path, damage):
    graph = BuildGraph((diagnostic_graph().nodes[0],), (VariantTarget("one", "profile"),))
    planner, report = execute(project, graph)
    build = project.catalog.get(report["actual"][0]["build_id"])
    directory = (project.catalog.path.parent / ".asset-studio/jobs" /
                 build.data["job_id"] / "output")
    if damage == "bytes":
        (directory / "result.json").write_bytes(b"corrupted")
    elif damage == "report":
        (directory / "report.json").unlink()
    elif damage == "symlink":
        original = tmp_path / "fake.json"
        original.write_bytes((directory / "result.json").read_bytes())
        (directory / "result.json").unlink()
        (directory / "result.json").symlink_to(original)
    elif damage == "extra":
        (directory / "unlisted.json").write_text("Not part of the verified result list")
    else:
        data = {**build.data, "outputs": build.data["outputs"][:1]}
        project.catalog.db.execute("UPDATE objects SET data=? WHERE id=?",
                                    (json.dumps(data), build.id))
    plan = planner.plan(project.project().id, graph)
    assert plan.counts["stale"] == 1 and plan.counts["reused"] == 0


def test_cache_changed_after_plan_fails_without_claiming_reuse(project):
    planner, _ = execute(project, branches())
    plan = planner.plan(project.project().id, branches())
    build = project.catalog.get(rows(plan)["palette"].build_id)
    directory = (project.catalog.path.parent / ".asset-studio/jobs" /
                 build.data["job_id"] / "output")
    (directory / "report.json").unlink()
    result = planner.execute(plan)
    actual = {r["node"]: r["actual"] for r in result["actual"]}
    assert actual["palette"] == "failed" and actual["walk"] == "blocked"
    assert actual["temple"] == "reused" and result["status"] == "incomplete"


def test_incomplete_builds_resume_only_verified_intermediates(project):
    planner = BuildPlanner(project)
    bad = planner.plan(project.project().id, branches(failure=True))
    result = planner.execute(bad)
    assert result["status"] == "incomplete"
    good = rows(planner.plan(project.project().id, branches()))
    assert good["palette"].state == good["stand"].state == good["temple"].state == "reused"
    assert good["walk"].state == good["walk_package"].state == "new"
    # Old pipeline folders have no verified registry entry and cannot become cache.
    partial = project.catalog.path.parent / "spritesheet-fram8"
    partial.mkdir()
    (partial / "Fertig.txt").write_text("Fertig")
    assert rows(planner.plan(project.project().id, branches()))["walk"].state == "new"


def test_output_digest_distinct_and_dependency_output_binding_checked(project):
    planner, report = execute(project, branches())
    builds = [project.catalog.get(r["build_id"]) for r in report["actual"]]
    for record in builds:
        assert record.data["result_digest"] != record.data["input_fingerprint"]
    walk = next(r for r in builds if r.data["node_key"] == "walk")
    with pytest.raises(StudioError, match="Bindung|bindung"):
        planner.cache.verify(walk, ("result.json", "report.json"), {"palette": "other-output"})


@pytest.mark.parametrize("case", ["cycle", "missing", "type", "path", "duplicate"])
def test_invalid_graphs_rejected_before_writes(project, case):
    graph = diagnostic_graph()
    first, second = graph.nodes[:2]
    if case == "cycle":
        first = replace(first, dependencies=(Dependency(second.key, "result.json", "diagnostic"),))
    elif case == "missing":
        second = replace(second, dependencies=(Dependency("absent", "result.json", "diagnostic"),))
    elif case == "type":
        second = replace(second, dependencies=(Dependency(first.key, "result.json", "image"),))
    elif case == "path":
        first = replace(first, outputs=(OutputSpec("../outside", "image"),))
    else:
        second = first
    with pytest.raises(StudioError):
        BuildGraph((first, second), ()).ordered()
    assert JobStore(project.catalog).rows() == []


def filesystem(root):
    return {str(p.relative_to(root)): file_hash(p) for p in root.rglob("*") if p.is_file()}


def test_dry_run_has_no_writes_including_cli_and_orphan_recovery(project):
    from etherfood_studio.application.job_service import JobService

    service = JobService(project)
    request = service.prepare(project.project().id)
    project.catalog.db.execute("UPDATE jobs SET owner_stamp='dead' WHERE id=?", (request.job_id,))
    root = project.catalog.path.parent
    before = filesystem(root)
    planner = BuildPlanner(project)
    plan = planner.plan(project.project().id, diagnostic_graph())
    assert plan.counts["new"] == 1 and filesystem(root) == before
    source = Path(__file__).resolve().parents[1] / "src"
    code = (f"import sys; sys.path.insert(0, {str(source)!r}); "
            "from etherfood_studio.cli import main; raise SystemExit(main(sys.argv[1:]))")
    process = subprocess.run([sys.executable, "-I", "-c", code, "build-plan", "--project",
                              str(root), "--diagnostic"], capture_output=True, check=True)
    assert json.loads(process.stdout)["counts"]["new"] == 1
    assert filesystem(root) == before
    readonly = ProjectService.open(root, read_only=True)
    try:
        with pytest.raises(sqlite3.OperationalError):
            readonly.catalog.db.execute("DELETE FROM jobs")
    finally:
        readonly.catalog.close()


def test_asset_variants_missing_sources_single_frames_and_rename(project, tiny_sheet):
    assets = AssetService(project)
    definition = default_definition("texture")
    owner = next(r.id for r in project.cards() if r.kind == "global")
    asset = assets.create("Textur", owner, definition.to_data())
    planner = BuildPlanner(project)
    missing = planner.plan(asset.id, asset_graph(project, asset.id))
    assert missing.counts["blocked"] == 5
    assert any("Quelle fehlt" in row.reason for row in missing.nodes)
    sources = SourceImportService(assets)
    spec = SourceSpec(tiny_sheet, SourceKey(None, None, "single_image"), 1, 1, 1, "Fixture")
    sources.import_plan(sources.prepare(asset.id, assets.asset(asset.id).revision_no, [spec]))
    current = asset_graph(project, asset.id)
    assert len(current.variants) == 5
    assert all(not row.required for row in current.nodes if row.stage == "frames")
    before = rows(planner.plan(asset.id, current))
    project.rename(asset.id, "Neu benannt", assets.asset(asset.id).revision_no)
    after = rows(planner.plan(asset.id, asset_graph(project, asset.id)))
    assert {k: r.fingerprint for k, r in before.items()} == \
        {k: r.fingerprint for k, r in after.items()}
    assert all("Quelle fehlt" not in row.reason for row in after.values())
    with pytest.raises(StudioError, match="blockierte"):
        planner.execute(planner.plan(asset.id, current))


def test_optional_variant_and_snapshot_never_imports_trusted_cache(project, tmp_path):
    base = diagnostic_graph()
    graph = replace(base, variants=base.variants + (VariantTarget("Nicht benötigt", None, False),))
    planner, _ = execute(project, graph)
    assert planner.plan(project.project().id, graph).counts["not_required"] == 1
    copy = Catalog(tmp_path / "copy.sqlite", create=True)
    try:
        imported = ProjectService(copy)
        imported.import_snapshot(project.catalog.export_snapshot())
        assert BuildPlanner(imported).plan(imported.project().id, graph).counts["reused"] == 0
    finally:
        copy.close()


@pytest.mark.parametrize("change", ["timing", "tool", "algorithm", "source"])
def test_relevant_input_changes_create_new_drafts_without_changing_history(project, change):
    graph = branches()
    planner, report = execute(project, graph)
    saved = project.catalog.get(report["run_id"])
    node = next(n for n in graph.nodes if n.key == "walk")
    if change == "timing":
        updated = replace(node, parameters='{"fps":12}')
    elif change == "tool":
        updated = replace(node, tools=(("tool.py", digest("version2")),))
    elif change == "algorithm":
        updated = replace(node, algorithm="2")
    else:
        updated = replace(node, inputs=(ContentInput("source", "image", digest("new-source")),))
    changed = replace(graph, nodes=tuple(updated if n.key == node.key else n for n in graph.nodes))
    plan = planner.plan(project.project().id, changed)
    assert {k for k, r in rows(plan).items() if r.state == "stale"} == {"walk", "walk_package"}
    assert project.catalog.get(saved.id) == saved


def test_changed_tool_after_dry_run_and_cancel_never_publish_partial_cache(project):
    graph = diagnostic_graph()
    planner = BuildPlanner(project)
    plan = planner.plan(project.project().id, graph)
    first = plan.nodes[0]
    forged = replace(first, node=replace(first.node, tools=(("missing", digest("version")),)))
    altered = replace(plan, nodes=(forged, *plan.nodes[1:]))
    result = planner.execute(altered)
    assert result["status"] == "incomplete" and result["actual"][0]["actual"] == "failed"
    cancelled = planner.execute(plan, cancelled=lambda: True)
    assert {r["actual"] for r in cancelled["actual"]} == {"cancelled"}
    assert planner.plan(project.project().id, graph).counts["new"] == 1
