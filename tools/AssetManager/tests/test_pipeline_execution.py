"""Actual isolated worker processes: phase barriers, cache, frozen inputs and cancellation."""

import json
from pathlib import Path

from PIL import Image
import pytest

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.pipeline_execution import PipelineExecution
from etherfood_studio.application.pipeline_workspace import PipelineWorkspace
from etherfood_studio.application.source_import import SourceImportService, SourceSpec
from etherfood_studio.application.workspace_files import WorkspaceFiles
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.sources import expected_sources
from test_pipeline_workspace import passthrough, project


def source_asset(project, tmp_path, title, pixel):
    assets = AssetService(project)
    owner = next(r.id for r in project.cards() if r.kind == "global")
    asset = assets.create(title, owner, default_definition("texture").to_data())
    path = tmp_path / (title + ".png")
    Image.new("RGBA", (8, 8), pixel).save(path)
    imports = SourceImportService(assets)
    key = expected_sources(assets.definition(asset.id))[0]
    source = imports.import_plan(
        imports.prepare(asset.id, asset.revision_no, [SourceSpec(path, key, 1, 1, 1)])
    )[0]
    return asset, source


def approved(project, title, targets):
    script, definition = passthrough(project, title)
    workspace = PipelineWorkspace(project)
    usage = workspace.use(definition.id, targets)
    check = workspace.check(definition.id)
    assert check["valid"], check
    workspace.approve(definition.id, check["hash"])
    return script, definition, usage


def test_two_assets_phase_barrier_results_cache_and_layout(project, tmp_path):
    first, one = source_asset(project, tmp_path, "Erstes", "red")
    second, two = source_asset(project, tmp_path, "Zweites", "blue")
    _, da, a = approved(project, "PA", [project.project().id])
    _, db, b = approved(project, "PB", [])
    workspace = PipelineWorkspace(project)
    workspace.update_usage(
        b.id,
        connections=[{"usage": a.id, "out": "output", "in": "input"}],
        expected_revision=b.revision_no,
    )
    executor = PipelineExecution(project)
    events = []
    result = executor.run(on_event=events.append)
    assert result["state"] == "succeeded", result
    steps = [e for e in events if e["state"] == "step_finished"]
    assert [e["usage_id"] for e in steps] == [a.id, a.id, b.id, b.id]
    assert {e["asset_id"] for e in steps[:2]} == {first.id, second.id}
    assert {e["asset_id"] for e in steps[2:]} == {first.id, second.id}
    assert result["executed"] == 4
    records = project.catalog.db.execute("SELECT * FROM pipeline_results").fetchall()
    assert len(records) == 4
    for row in records:
        outputs = json.loads(row["outputs"])
        for item in outputs["output"]:
            assert row["usage_id"] in item["path"]
            assert (project.catalog.path.parent / item["path"]).is_file()
    project.catalog.save_layout(a.id, {"x": 500, "y": -100})
    again = executor.run()
    assert again["executed"] == 0 and again["reused"] == 4


def test_corrupt_publication_is_not_cache_hit(project, tmp_path):
    source_asset(project, tmp_path, "Quelle", "green")
    _, _, usage = approved(project, "Prüfung", [project.project().id])
    engine = PipelineExecution(project)
    result = engine.run()
    assert result["executed"] == 1
    item = result["phases"][0]["rows"][0]["outputs"]["output"][0]
    (project.catalog.path.parent / item["path"]).unlink()
    again = engine.run()
    assert again["executed"] == 1 and again["reused"] == 0


def test_unconnected_usage_never_receives_predecessor_results(project, tmp_path):
    source_asset(project, tmp_path, "Quelle", "yellow")
    _, _, a = approved(project, "PA", [project.project().id])
    _, _, b = approved(project, "PB", [])
    result = PipelineExecution(project).run()
    assert result["executed"] == 1
    phase = next(p for p in result["phases"] if p["usage_id"] == b.id)
    assert phase["rows"] == [] and phase["reason"] == "Keine passenden Eingaben."


def test_failed_fingerprint_not_retried_and_downstream_blocked(project, tmp_path):
    source_asset(project, tmp_path, "Quelle", "purple")
    script, definition, a = approved(project, "Fehler", [project.project().id])
    files = WorkspaceFiles(project)
    _, digest = files.read(script.id)
    files.save(
        script.id,
        "def run(context, inputs, parameters):\n    raise ValueError('synthetic')\n",
        digest,
        script.revision_no,
    )
    workspace = PipelineWorkspace(project)
    check = workspace.check(definition.id)
    workspace.approve(definition.id, check["hash"])
    engine = PipelineExecution(project)
    first = engine.run()
    assert first["state"] == "failed"
    assert "synthetic" in first["phases"][0]["reason"]
    second = engine.run()
    assert second["executed"] == 0
    assert "Erneut versuchen" in second["phases"][0]["reason"]
    assert project.catalog.db.execute("SELECT COUNT(*) FROM pipeline_results").fetchone()[0] == 0


def test_code_change_during_phase_keeps_snapshot_but_does_not_publish(project, tmp_path):
    source_asset(project, tmp_path, "Quelle", "orange")
    script, definition, usage = approved(project, "Änderung", [project.project().id])
    files = WorkspaceFiles(project)

    def mutate(event):
        if event["state"] == "step_finished":
            path = files.path(script)
            path.write_text(path.read_text() + "\n# Änderung während Durchgang\n")

    result = PipelineExecution(project).run(on_event=mutate)
    assert result["phases"][0]["state"] == "stale"
    assert result["state"] != "succeeded"
    assert project.catalog.db.execute("SELECT COUNT(*) FROM pipeline_results").fetchone()[0] == 0
    assert PipelineWorkspace(project).status(definition.id)[0] == "yellow"


def test_scope_deduplicates_used_assets_and_excludes_archived_ancestors(project, tmp_path):
    asset, source = source_asset(project, tmp_path, "Gemeinsam", "white")
    act = project.create_card("act", "Akt", project.project().id)
    chapter = project.create_card("chapter", "Kapitel", act.id)
    project.relate(act.id, asset.id, "uses")
    project.relate(chapter.id, asset.id, "uses")
    _, _, usage = approved(project, "Bereich", [act.id, chapter.id])
    assert [r.id for r in PipelineWorkspace(project).scope(usage)] == [asset.id]
    project.archive(asset.id, True, project.catalog.get(asset.id).revision_no)
    assert PipelineWorkspace(project).scope(usage) == []


def test_asset_folder_move_keeps_current_results_without_processing(project, tmp_path):
    from etherfood_studio.application.pipeline_results import PipelineResults

    asset, _ = source_asset(project, tmp_path, "Vorher", "teal")
    approved(project, "Verschieben", [asset.id])
    engine = PipelineExecution(project)
    first = engine.run()
    old = first["phases"][0]["rows"][0]["outputs"]["output"][0]["path"]
    current = project.catalog.get(asset.id)
    project.rename(asset.id, "Nachher", current.revision_no)
    result = PipelineResults(project).latest(asset.id)
    assert result["state"] == "ready"
    assert "Nachher" in result["artifacts"][0]["file_path"]
    assert not (project.catalog.path.parent / old).exists()
    again = engine.run()
    assert again["executed"] == 0 and again["reused"] == 1


def test_map_collect_map_preserves_all_sources_per_asset_and_cache(project, tmp_path):
    from etherfood_studio.application.pipeline_results import PipelineResults
    from etherfood_studio.domain.pipeline_contract import INPUT, empty_definition

    assets = AssetService(project)
    owner = next(r.id for r in project.cards() if r.kind == "global")
    asset = assets.create("Richtungen", owner, default_definition("character").to_data())
    imports = SourceImportService(assets)
    specs = []
    for index, key in enumerate(expected_sources(assets.definition(asset.id))[:2]):
        path = tmp_path / f"richtung-{index}.png"
        Image.new("RGBA", (64, 8), "red" if index else "blue").save(path)
        specs.append(SourceSpec(path, key, 8, 1, 8))
    imported = imports.import_plan(imports.prepare(asset.id, asset.revision_no, specs))
    files = WorkspaceFiles(project)
    mapper, _ = passthrough(project, "Map")
    collector = files.create_script(
        "Sammeln",
        description={
            "execution": "collect",
            "inputs": {"input": {"type": "file", "multiple": True}},
            "outputs": {"output": {"type": "json"}},
        },
        code=(
            "import json\n"
            "def run(context, inputs, parameters):\n"
            "    values = inputs['input']\n"
            "    result = context.artifact('collection.json', 'json', {})\n"
            "    result.path.write_text(json.dumps("
            "[v.metadata['source_revision'] for v in values]))\n"
            "    return {'output': result}\n"
        ),
    )
    value = empty_definition("pending")
    value["inputs"] = {"input": {"type": "file"}}
    value["nodes"] = [
        {"id": name, "script_id": record.id, "parameters": {}}
        for name, record in (("map", mapper), ("collect", collector), ("after", mapper))
    ]
    value["connections"] = [
        {"from": source, "out": out, "to": target, "in": "input"}
        for source, out, target in (
            (INPUT, "input", "map"),
            ("map", "output", "collect"),
            ("collect", "output", "after"),
        )
    ]
    value["folders"] = [
        {"id": "output", "node": "after", "port": "output", "directory": "Sammlung"}
    ]
    definition = files.create_definition("Map Collect Map", definition=value)
    workspace = PipelineWorkspace(project)
    usage = workspace.use(definition.id, [asset.id])
    checked = workspace.check(definition.id)
    assert checked["valid"], checked
    workspace.approve(definition.id, checked["hash"])
    engine = PipelineExecution(project)
    events = []
    result = engine.run(on_event=events.append)
    assert result["state"] == "succeeded", result
    assert [e["node_id"] for e in events if e["state"] == "step_finished"] == [
        "map",
        "map",
        "collect",
        "after",
    ]
    phase = next(p for p in result["phases"] if p["usage_id"] == usage.id)
    item = phase["rows"][0]["outputs"]["output"][0]
    assert set(json.loads((engine.root / item["path"]).read_bytes())) == {r.id for r in imported}
    assert {p["source_id"] for p in item["provenance"]} == {r.id for r in imported}
    assert PipelineResults(project).latest(asset.id)["state"] == "ready"
    assert engine.run()["executed"] == 0


def test_changed_source_only_recomputes_affected_asset_and_independent_failure_does_not_stop(
    project, tmp_path
):
    from etherfood_studio.application.source_reconciliation import SourceReconciliation

    first, _ = source_asset(project, tmp_path, "Einzeln1", "red")
    second, _ = source_asset(project, tmp_path, "Einzeln2", "blue")
    _, definition, usage = approved(project, "Normal", [project.project().id])
    engine = PipelineExecution(project)
    assert engine.run()["executed"] == 2
    source, path = next(
        (s, p) for s, p in SourceReconciliation(project).known() if s.owner_id == first.id
    )
    Image.new("RGBA", (8, 8), "green").save(path)
    SourceReconciliation(project).reconcile()
    again = engine.run()
    assert again["executed"] == again["reused"] == 1
    assert PipelineWorkspace(project).status(definition.id)[0] == "green"
    bad, bd, bu = approved(project, "Kaputt", [first.id])
    files = WorkspaceFiles(project)
    _, digest = files.read(bad.id)
    files.save(
        bad.id,
        "def run(context, inputs, parameters):\n    raise ValueError('independent')\n",
        digest,
        bad.revision_no,
    )
    workspace = PipelineWorkspace(project)
    checked = workspace.check(bd.id)
    workspace.approve(bd.id, checked["hash"])
    _, _, downstream = approved(project, "Abhängig", [])
    workspace.update_usage(
        downstream.id,
        connections=[{"usage": bu.id, "out": "output", "in": "input"}],
        expected_revision=downstream.revision_no,
    )
    _, _, independent = approved(project, "Unabhängig", [second.id])
    result = engine.run()
    states = {p["usage_id"]: p["state"] for p in result["phases"]}
    assert states[bu.id] == "failed" and states[downstream.id] == "blocked"
    assert states[independent.id] == "succeeded"
    assert engine.run()["executed"] == 0


def test_project_folder_targets_are_collision_free_and_symlinks_blocked(project, tmp_path):
    from etherfood_studio.storage.sqlite_repository import canonical

    a, _ = source_asset(project, tmp_path, "Ablage1", "red")
    b, _ = source_asset(project, tmp_path, "Ablage2", "blue")
    _, definition = passthrough(project)
    workspace = PipelineWorkspace(project)
    data, digest = workspace.files.definition(definition.id)
    data["folders"][0]["scope"] = "project"
    workspace.files.save(definition.id, canonical(data), digest, definition.revision_no)
    first = workspace.use(definition.id, [a.id, b.id])
    second = workspace.use(definition.id, [a.id])
    check = workspace.check(definition.id)
    assert check["valid"]
    workspace.approve(definition.id, check["hash"])
    result = PipelineExecution(project).run()
    outputs = [r["outputs"]["output"][0]["path"] for p in result["phases"] for r in p["rows"]]
    assert len(outputs) == len(set(outputs)) == 3
    assert all(name.startswith("Ergebnisse/Projekt/") for name in outputs)
    target = project.catalog.path.parent / "Ergebnisse/Projekt" / second.id / a.id / "Kopien"
    # A new explicit folder cannot escape through a symbolic link.
    data, digest = workspace.files.definition(definition.id)
    data["folders"][0]["directory"] = "Ausweg"
    workspace.files.save(
        definition.id, canonical(data), digest, project.catalog.get(definition.id).revision_no
    )
    target.with_name("Ausweg").symlink_to(tmp_path, target_is_directory=True)
    check = workspace.check(definition.id)
    assert not check["valid"] and any("Symlink" in e for e in check["issues"])
