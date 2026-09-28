"""Read-only planning, verified reuse and reproducible execution of frozen DAGs."""

from collections import Counter
from dataclasses import asdict, dataclass
import json

from ..domain.builds import BuildGraph, BuildNode, VariantTarget
from ..domain.models import StudioError, new_id
from ..pipelines.adapters import REGISTRY
from ..pipelines.base import InputFile
from ..pipelines.fingerprints import digest, input_fingerprint
from ..storage.build_cache import BuildCache
from .job_service import JobService

STATES = ("new", "reused", "stale", "blocked", "not_required")


@dataclass(frozen=True)
class PlannedNode:
    node: BuildNode
    fingerprint: str
    state: str
    reason: str
    build_id: str | None = None
    result_digest: str | None = None


@dataclass(frozen=True)
class BuildPlan:
    id: str
    owner_id: str
    nodes: tuple[PlannedNode, ...]
    variants: tuple[VariantTarget, ...]
    snapshot: str = "{}"

    @property
    def counts(self) -> dict[str, int]:
        rows = {row.node.key: row for row in self.nodes}
        count = Counter(rows[v.node].state if v.required else "not_required" for v in self.variants)
        return {state: count[state] for state in STATES}

    def to_data(self) -> dict:
        return {"contract": "studio-build-plan-v1", **asdict(self), "counts": self.counts}


class BuildPlanner:
    def __init__(self, project):
        self.project = project
        self.cache = BuildCache(project.catalog)

    def plan(self, owner_id: str, graph: BuildGraph, *, cancelled=lambda: False,
             snapshot="{}") -> BuildPlan:
        self.project.require_active_card(owner_id)
        rows, fingerprints = {}, {}
        for node in graph.ordered():
            if cancelled():
                raise StudioError("cancelled", "Dry-run abgebrochen; keine Änderungen geschrieben.")
            fingerprint = input_fingerprint(node, fingerprints)
            fingerprints[node.key] = fingerprint
            parents = [rows[d.node] for d in node.dependencies]
            dependencies = {d.node: rows[d.node].result_digest for d in node.dependencies}
            blockers = list(node.blockers)
            if node.adapter not in REGISTRY:
                blockers.append("Produktiver Adapter folgt in späterem Issue")
            if any(p.state == "blocked" for p in parents):
                blockers.append("Voraussetzung blockiert")
            if not node.required:
                state, reason = "not_required", "Vom Anforderungsprofil nicht benötigt"
                cached = None
            elif blockers:
                state, reason, cached = "blocked", "; ".join(blockers), None
            else:
                cached = self.cache.lookup(owner_id, node, fingerprint, dependencies) \
                    if all(p.state == "reused" for p in parents) else None
                if cached:
                    state, reason = "reused", "Vollständige Ergebnisliste und alle Hashes geprüft"
                elif self.cache.entries(owner_id, node.key):
                    state, reason = "stale", "Eingaben geändert oder Ergebnis/Abhängigkeit ungültig"
                else:
                    state, reason = "new", "Kein vollständiger lokaler Nachweis"
            rows[node.key] = PlannedNode(node, fingerprint, state, reason,
                                         cached.id if cached else None,
                                         cached.data["result_digest"] if cached else None)
        return BuildPlan(new_id(), owner_id, tuple(rows.values()), graph.variants, snapshot)

    def execute(self, plan: BuildPlan, *, cancelled=lambda: False, on_event=lambda event: None
                ) -> dict:
        # Revalidate the frozen graph. A changed tool or cache requires a new dry-run.
        BuildGraph(tuple(r.node for r in plan.nodes), plan.variants).ordered()
        if any(row.state == "blocked" for row in plan.nodes if row.node.required):
            raise StudioError("blocked", "Plan enthält blockierte Schritte; keine Ausführung.")
        self.project.require_active_card(plan.owner_id)
        service = JobService(self.project)
        results, actual = {}, []
        for row in plan.nodes:
            node = row.node
            dependencies = {d.node: results[d.node]["result_digest"] for d in node.dependencies
                            if d.node in results}
            item = {"node": node.key, "planned": row.state, "fingerprint": row.fingerprint}
            try:
                if not node.required:
                    item["actual"] = "not_required"
                elif cancelled():
                    item["actual"] = "cancelled"
                elif any(d.node not in results for d in node.dependencies):
                    item["actual"] = "blocked"
                elif row.state == "reused":
                    record = self.project.catalog.get(row.build_id)
                    data = self.cache.verify(record, tuple(o.path for o in node.outputs),
                                              dependencies)
                    results[node.key] = {**data, "build_id": record.id}
                    item.update(actual="reused", build_id=record.id)
                else:
                    parameters = json.loads(node.parameters)
                    if node.adapter == "diagnostic":
                        parameters["value"] = digest({"input": row.fingerprint,
                                                      "dependencies": dependencies})
                    request = service.prepare(plan.owner_id, node.adapter, parameters,
                                               source_ids=node.source_ids,
                                               resource_key=f"build:{plan.owner_id}:{node.key}",
                                               bindings=self.bindings(node, results), timeout=300)
                    if request.tool_hashes != node.tools or request.outputs != \
                            tuple(o.path for o in node.outputs):
                        service.start_failed(request.job_id, "Plan/Tool geändert; neu planen")
                        raise StudioError("stale", "Werkzeuge/Erwartungen seit Dry-run verändert.")
                    result = service.run(request, cancelled=cancelled, on_event=on_event)
                    item.update(actual=result["status"], job_id=request.job_id,
                                reason=result.get("reason", ""))
                    if result["status"] == "succeeded":
                        record = self.cache.register(plan.owner_id, node, row.fingerprint,
                                                     dependencies, request.job_id)
                        results[node.key] = {**record.data, "build_id": record.id}
                        item.update(actual="built", build_id=record.id)
            except (StudioError, OSError, ValueError) as error:
                item.update(actual="failed", reason=str(error))
            actual.append(item)
            on_event({"kind": "node_finished", **item})
        success = all(r["actual"] in {"built", "reused", "not_required"} for r in actual)
        diagnostic = all(row.node.adapter != "studio-image" for row in plan.nodes)
        report = {"contract": "studio-build-run-v1", "plan": plan.to_data(), "actual": actual,
                  "status": "succeeded" if success else "incomplete",
                  "diagnostic": diagnostic, "published": success and not diagnostic}
        try:
            record = self.project.catalog.create(
                "build", "Plan-/Ausführungsvergleich", plan.owner_id, report)
        except (StudioError, OSError) as error:
            if not report["published"]:
                raise
            report.update(status="incomplete", published=False, publication_error=str(error))
            on_event({"kind": "publication_failed", "reason": str(error)})
            record = self.project.catalog.create("build", "Ablage fehlgeschlagen", plan.owner_id,
                                                  report)
        return {**report, "run_id": record.id}

    def bindings(self, node, results):
        if node.adapter != "studio-image":
            return ()
        from ..storage.blob_store import BlobStore

        store = BlobStore(self.project.catalog, self.project.catalog.path.parent)
        bindings = []
        for item in node.inputs:
            if item.role == "source":
                continue
            path = store.path_for(item.sha256)
            bindings.append(InputFile(item.revision_id or item.sha256,
                str(path.relative_to(store.root)), item.role, item.sha256, path.stat().st_size))
        for dependency in node.dependencies:
            data = results[dependency.node]
            item = next(v for v in data["outputs"] if v["path"] == dependency.output)
            bindings.append(InputFile(data["build_id"],
                f".asset-studio/jobs/{data['job_id']}/output/{dependency.output}",
                "upstream.png" if dependency.kind == "image" else "upstream.json",
                item["sha256"], item["length"]))
        return tuple(bindings)
