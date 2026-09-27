"""Append-only local cache provenance, with full file verification on every lookup."""

from ..domain.models import StudioError
from ..pipelines.base import verify_files
from ..pipelines.fingerprints import digest
from .job_store import JobStore
from .paths import safe_target


class BuildCache:
    def __init__(self, catalog):
        self.catalog = catalog
        self.root = catalog.path.parent

    def entries(self, owner: str, node_key: str, fingerprint: str | None = None) -> list:
        rows = self.catalog.db.execute(
            "SELECT c.build_id FROM build_cache c JOIN objects o ON o.id=c.build_id "
            "WHERE o.owner_id=? AND c.node_key=? "
            "AND (? IS NULL OR c.input_fingerprint=?) ORDER BY o.created_at DESC,o.id",
            (owner, node_key, fingerprint, fingerprint),
        )
        return [self.catalog.get(r[0]) for r in rows]

    def verify(self, record, expected: tuple[str, ...], dependencies: dict[str, str]) -> dict:
        data = record.data
        local = self.catalog.db.execute("SELECT * FROM build_cache WHERE build_id=?",
                                         (record.id,)).fetchone()
        if not local or data.get("contract") != "studio-build-v1":
            raise StudioError("integrity", "Kein lokal verifiziertes Build.")
        job = JobStore(self.catalog).get(local["job_id"])
        if (job["status"] != "succeeded" or data["dependencies"] != dependencies or
                data["outputs"] != job["result"]["files"] or
                set(job["request"]["outputs"]) != set(expected) or
                data["input_fingerprint"] != local["input_fingerprint"]):
            raise StudioError("integrity", "Cachebindung/Ergebnisvertrag passt nicht.")
        directory = safe_target(self.root, f".asset-studio/jobs/{job['id']}/output")
        files = verify_files(directory, expected, data["outputs"])
        if digest(files) != data["result_digest"]:
            raise StudioError("integrity", "Ergebnisdigest des Builds ist beschädigt.")
        return data

    def lookup(self, owner: str, node, fingerprint: str, dependencies: dict[str, str]):
        for record in self.entries(owner, node.key, fingerprint):
            try:
                self.verify(record, tuple(o.path for o in node.outputs), dependencies)
                return record
            except (StudioError, OSError, ValueError, KeyError, TypeError):
                continue
        return None

    def register(self, owner: str, node, fingerprint: str, dependencies: dict[str, str],
                 job_id: str):
        job = JobStore(self.catalog).get(job_id)
        if job["status"] != "succeeded":
            raise StudioError("integrity", "Unvollständige Aufträge sind kein Cache.")
        if (job["request"]["adapter"] != node.adapter or
                tuple(tuple(v) for v in job["request"]["tool_hashes"]) != node.tools):
            raise StudioError("integrity", "Auftrag passt nicht zum geplanten Adapter/Werkzeug.")
        expected = tuple(o.path for o in node.outputs)
        directory = safe_target(self.root, f".asset-studio/jobs/{job_id}/output")
        files = verify_files(directory, expected, job["result"]["files"])
        data = {"contract": "studio-build-v1", "node_key": node.key, "stage": node.stage,
                "input_fingerprint": fingerprint, "result_digest": digest(files),
                "outputs": files, "dependencies": dependencies, "job_id": job_id,
                "diagnostic": True, "tools": list(node.tools)}
        with self.catalog.transaction():
            record = self.catalog.create("build", "Diagnosebuild · " + node.stage, owner, data)
            self.catalog.db.execute("INSERT INTO build_cache VALUES (?,?,?,?)",
                                    (record.id, node.key, fingerprint, job_id))
        return record
