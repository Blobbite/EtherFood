"""Transfer result files/provenance, then retire the old execution data transactionally."""

from copy import deepcopy
import json
from pathlib import Path

from ..domain.assets import require
from ..domain.models import StudioError, utc_now
from ..storage.blob_store import file_hash
from ..storage.paths import safe_target
from ..storage.sqlite_repository import canonical
from .legacy_artifacts import read_results
from .workspace_files import content_hash

MIGRATION = "retire-legacy-jobs-v1"


class RetireJobs:
    def __init__(self, project):
        self.project, self.catalog = project, project.catalog
        self.root = self.catalog.path.parent

    def run(self, *, backup=None, checkpoint=lambda step: None):
        previous = self.catalog.db.execute(
            "SELECT detail FROM workspace_migrations WHERE name=?", (MIGRATION,)
        ).fetchone()
        if previous:
            return json.loads(previous[0])
        tables = {r[0] for r in self.catalog.db.execute("SELECT name FROM sqlite_master")}
        jobs = list(self.catalog.db.execute("SELECT * FROM jobs")) if "jobs" in tables else []
        records = self.catalog.records(include_archived=True)
        builds = [r for r in records if r.kind == "build"]
        require(
            not (jobs or builds) or backup, "Alte Ausführung benötigt vor Ablösung eine Sicherung."
        )
        result = {"results": [], "notices": [], "backup": backup}
        with self.catalog.transaction():
            changes = self.catalog.file_changes()
            for build in builds:
                requests = [
                    json.loads(job["request"])
                    for job in jobs
                    if job["id"] == build.data.get("job_id")
                ]
                provenance = {
                    "contract": "migrated-result-evidence-v1",
                    "asset_id": build.owner_id,
                    "created_at": build.created_at,
                    "title": build.title,
                    "legacy_snapshot": build.data,
                    "requests": requests,
                    "state": "historical",
                    "verified_on_transfer": False,
                }
                if build.data.get("contract") != "studio-build-v1" or build.data.get(
                    "diagnostic", True
                ):
                    self.catalog.db.execute(
                        "INSERT INTO pipeline_result_evidence VALUES (?,?)",
                        (build.id, canonical(provenance)),
                    )
                    continue
                directory = safe_target(
                    self.root, ".asset-studio/jobs/" + build.data["job_id"] + "/output"
                )
                valid, outputs, content = True, {}, {}
                try:
                    for item in build.data["outputs"]:
                        path = safe_target(directory, item["path"])
                        require(
                            path.is_file()
                            and path.stat().st_size == item["length"]
                            and file_hash(path) == item["sha256"],
                            "Alter Ergebnisnachweis ist beschädigt.",
                        )
                    if (directory / "artifacts.zip").is_file():
                        description, content = read_results(directory)
                        outputs = description["ports"]
                    else:
                        metadata = (
                            json.loads((directory / "metadata.json").read_bytes())
                            if (directory / "metadata.json").is_file()
                            else {}
                        )
                        for item in build.data["outputs"]:
                            path = safe_target(directory, item["path"])
                            kind = (
                                "gif"
                                if path.suffix == ".gif"
                                else (
                                    "spritesheet"
                                    if path.suffix == ".png"
                                    and metadata.get("kind") == "spritesheet"
                                    else (
                                        "image"
                                        if path.suffix == ".png"
                                        else "json" if path.suffix == ".json" else "file"
                                    )
                                )
                            )
                            content[item["path"]] = path.read_bytes()
                            outputs.setdefault(path.stem, []).append(
                                item | {"type": kind, "metadata": metadata}
                            )
                except (StudioError, OSError, ValueError, KeyError, TypeError) as error:
                    valid = False
                    result["notices"].append(build.title + ": " + str(error))
                    # Retain bytes as unverified evidence, never as a cache hit.
                    for item in build.data.get("outputs", []):
                        path = safe_target(directory, item["path"])
                        if path.is_file():
                            raw = path.read_bytes()
                            content[item["path"]] = raw
                            outputs.setdefault("unverified", []).append(
                                {
                                    "path": item["path"],
                                    "sha256": content_hash(raw),
                                    "length": len(raw),
                                    "type": "file",
                                    "metadata": {},
                                }
                            )
                transferred = {}
                for port, items in outputs.items():
                    transferred[port] = []
                    for item in items:
                        name = ".asset-studio/migrated-results/" + build.id + "/" + item["path"]
                        target = safe_target(self.root, name)
                        changes.write(target, content=content[item["path"]])
                        copied = item | {"path": name}
                        require(
                            file_hash(target) == copied["sha256"],
                            "Ergebnisübernahme konnte nicht geprüft werden.",
                        )
                        transferred[port].append(copied)
                        self.catalog.db.execute(
                            "INSERT OR IGNORE INTO current_files VALUES (?,?,?)",
                            (build.owner_id, name, copied["sha256"]),
                        )
                provenance.update(
                    {
                        "verified_on_transfer": valid,
                        "fingerprint": build.data.get("input_fingerprint"),
                        "tools": build.data.get("tools", []),
                        "dependencies": build.data.get("dependencies", {}),
                        "state": "historical" if valid else "invalid",
                    }
                )
                self.catalog.db.execute(
                    "INSERT INTO pipeline_result_evidence VALUES (?,?)",
                    (build.id, canonical(provenance)),
                )
                self.catalog.db.execute(
                    "INSERT INTO pipeline_results VALUES (?,?,?,?,?,?,?,?,0)",
                    (
                        build.id,
                        "historical:" + build.id,
                        build.owner_id,
                        build.data.get("node_key", build.id),
                        build.data.get("input_fingerprint", "legacy"),
                        "unapproved-legacy",
                        canonical(transferred),
                        build.created_at,
                    ),
                )
                result["results"].append(build.id)
            checkpoint("results")
            # Files are deleted only when recorded in the verified pre-migration backup manifest.
            manifest = (
                json.loads((self.root / backup / "manifest.json").read_bytes())
                if backup
                else {"files": []}
            )
            owned = set()
            for job in jobs:
                prefix = ".asset-studio/jobs/" + job["id"] + "/"
                request = json.loads(job["request"])
                names = {
                    "request.json",
                    "result.json",
                    "process.json",
                    "logs/events.jsonl",
                    "logs/stdout.log",
                    "logs/stderr.log",
                    "logs/host-stderr.log",
                }
                names.update("input/" + item["name"] for item in request.get("inputs", []))
                names.update("output/" + name for name in request.get("outputs", []))
                for build in builds:
                    if build.data.get("job_id") == job["id"]:
                        names.update(
                            "output/" + item["path"] for item in build.data.get("outputs", [])
                        )
                owned.update(prefix + name for name in names)
            for file in manifest["files"]:
                if file["path"] in owned:
                    changes.delete(safe_target(self.root, file["path"]), file["sha256"])
            for table in (
                "build_cache",
                "job_events",
                "jobs",
                "workflow_publications",
                "asset_publications",
            ):
                if table in tables:
                    self.catalog.db.execute("DROP TABLE " + table)
            old_ids = {r.id for r in builds}
            for record in records:
                if record.id in old_ids:
                    continue
                data = deepcopy(record.data)
                if data.get("current_build_id") in old_ids:
                    data.pop("current_build_id")
                evidence = data.get("evidence", {})
                for key in list(evidence):
                    if evidence[key].get("build_id") in old_ids:
                        evidence[key] = evidence[key] | {"state": "stale"}
                if data != record.data:
                    # Evidence is no longer current; never fabricate renewed approval.
                    self.catalog.save(record, data=data)
            for identifier in old_ids:
                self.catalog.db.execute(
                    "DELETE FROM relations WHERE source_id=? OR target_id=?",
                    (identifier, identifier),
                )
                self.catalog.db.execute("DELETE FROM revisions WHERE object_id=?", (identifier,))
                self.catalog.db.execute("DELETE FROM layouts WHERE object_id=?", (identifier,))
                self.catalog.db.execute("DELETE FROM objects WHERE id=?", (identifier,))
            self.catalog.db.execute(
                "INSERT INTO workspace_migrations VALUES (?,?,?)",
                (MIGRATION, "complete", canonical(result)),
            )
            checkpoint("retired")
        return result
