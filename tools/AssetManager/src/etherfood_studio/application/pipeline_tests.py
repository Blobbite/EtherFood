"""Explicit nonpublishing script tests; no pipeline registration or production cache writes."""

from dataclasses import replace

from ..domain.assets import require
from ..domain.models import new_id
from ..storage.paths import make_directory
from .pipeline_inputs import PipelineInputs
from .pipeline_workspace import PipelineWorkspace


def script_test_plan(project, identifier):
    workspace = PipelineWorkspace(project)
    script = workspace.script_snapshot(identifier)
    require(not script["issues"], "\n".join(script["issues"]))
    usage = replace(
        project.project(),
        kind="pipeline_usage",
        data={"targets": [project.project().id], "connections": [], "unresolved": []},
    )
    rows = PipelineInputs(workspace).select(usage, {"inputs": script["description"]["inputs"]})
    matching = [row for row in rows if row["state"] == "matching"]
    if not script["description"]["inputs"]:
        matching = [{"inputs": {}, "asset_id": None, "source_key": "ohne Eingaben"}]
    require(
        bool(matching),
        "Keine passende registrierte Testeingabe. "
        + "\n".join(row["reason"] for row in rows if row["state"] == "invalid"),
    )
    return {"script": script, "rows": matching}


def test_script(project, identifier, engine, emit=lambda event: None, *, plan=None):
    plan = plan or script_test_plan(project, identifier)
    require(engine.lock.acquire(blocking=False), "Eine Verarbeitung läuft bereits.")
    engine.cancelled.clear()
    engine.active = True
    project.pipeline_executor = engine
    try:
        require(
            engine.workspace.script_snapshot(identifier)["hash"] == plan["script"]["hash"],
            "Skript seit Testbestätigung geändert.",
        )
        root = make_directory(engine.root, ".asset-studio/pipeline-tests/" + new_id())
        for row in plan["rows"]:
            for values in row["inputs"].values():
                for item in values:
                    engine.freeze_input(item, root / "inputs" / (row["asset_id"] or "standalone"))
                    engine.track_file(engine.root / item["path"], identifier, row["asset_id"])
        rows = engine.prepare_rows(
            {"snapshot": {"scripts": {identifier: plan["script"]}}}, plan["rows"]
        )
        results = []
        for row in rows:
            engine._check_cancel()
            path = make_directory(root, "steps/" + new_id())
            parameters = {
                name: value["default"]
                for name, value in plan["script"]["description"]["parameters"].items()
                if "default" in value
            }
            try:
                outputs = engine.invoke(plan["script"], parameters, row["inputs"], {}, path)
            finally:
                engine.track_run(path, identifier, row["asset_id"])
            results.append(
                {"asset_id": row["asset_id"], "source_key": row["source_key"], "outputs": outputs}
            )
            emit({"state": "script_test", "completed": len(results), "total": len(rows)})
        return {"state": "succeeded", "published": False, "results": results}
    finally:
        engine.active = False
        engine.lock.release()


test_script.__test__ = False
