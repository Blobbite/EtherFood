"""Read verified results per usage and asset without replacing other pipeline outcomes."""

import json

from ..domain.models import StudioError
from .pipeline_execution import PipelineExecution


class PipelineResults:
    def __init__(self, project):
        self.project, self.catalog = project, project.catalog
        self.engine = PipelineExecution(project)

    def rows(self, asset_id):
        return [
            dict(row) | {"outputs": json.loads(row["outputs"])}
            for row in self.catalog.db.execute(
                "SELECT * FROM pipeline_results WHERE asset_id=? ORDER BY created_at DESC,id",
                (asset_id,),
            )
        ]

    def current(self, row, plan, seen=None):
        seen = set(seen or ())
        if row["id"] in seen or not row["current"] or not self.engine.outputs_valid(row["outputs"]):
            return False
        seen.add(row["id"])
        entry = plan["entries"].get(row["usage_id"])
        if (
            not entry
            or entry["issues"]
            or not entry["snapshot"]
            or entry["snapshot"]["hash"] != row["definition_hash"]
        ):
            return False
        if entry["usage"].data["connections"]:
            phases = {}
            for edge in entry["usage"].data["connections"]:
                previous = [
                    r
                    for r in self.rows(row["asset_id"])
                    if r["usage_id"] == edge["usage"] and r["current"]
                ]
                if not previous or not all(self.current(r, plan, seen) for r in previous):
                    return False
                phases[edge["usage"]] = {"rows": previous}
            candidates = self.engine.predecessor_rows(entry, phases)
        else:
            candidates = [r for r in entry["rows"] if r["state"] == "matching"]
        incoming = next(
            (
                r
                for r in self.engine.prepare_rows(entry, candidates)
                if r["asset_id"] == row["asset_id"] and r.get("source_key") == row["source_key"]
            ),
            None,
        )
        if incoming is None:
            return False
        return self.engine.row_key(entry, incoming) == row["fingerprint"]

    def latest(self, asset_id):
        rows = self.rows(asset_id)
        plan = self.engine.plan()
        artifacts, current, invalid = [], 0, 0
        for row in rows:
            valid = self.engine.outputs_valid(row["outputs"])
            actual = self.current(row, plan) if valid else False
            current += actual
            invalid += not valid
            try:
                title = self.catalog.get(row["usage_id"]).title
            except StudioError:
                title = "Übernommenes historisches Ergebnis"
            for port, items in row["outputs"].items():
                artifacts.extend(
                    item
                    | {
                        "usage_id": row["usage_id"],
                        "usage": title,
                        "port": port,
                        "source_key": row["source_key"],
                        "state": "ready" if actual else "stale" if valid else "invalid",
                        "file_path": item["path"],
                    }
                    for item in items
                )
        state = "invalid" if invalid else "ready" if current else "stale" if rows else "not_started"
        return {
            "state": state,
            "reason": f"{current} aktuelle Ergebnisstände in {len(rows)} Nachweisen.",
            "artifacts": artifacts,
        }
