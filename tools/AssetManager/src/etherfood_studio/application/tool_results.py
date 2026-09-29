"""Verified file artifacts and transactional publication into declared asset folders."""

import hashlib
import json
from pathlib import Path

from ..domain.assets import require
from ..domain.models import StudioError
from ..domain.tool_contract import output_directory
from ..pipelines.tool_adapter import OUTPUTS, read_results
from ..storage.blob_store import file_hash
from ..storage.build_cache import BuildCache
from ..storage.paths import safe_target


class ToolResultService:
    def __init__(self, project):
        self.project = project
        self.root = project.catalog.path.parent

    def read(self, build):
        require(
            build.kind == "build" and not build.data.get("diagnostic", True),
            "Kein produktives Dateiergebnis.",
        )
        BuildCache(self.project.catalog).verify(build, OUTPUTS, build.data["dependencies"])
        directory = safe_target(self.root, f".asset-studio/jobs/{build.data['job_id']}/output")
        return read_results(directory)

    def artifacts(self, build, *, port=None):
        result, _ = self.read(build)
        artifacts = []
        for name, items in result["ports"].items():
            if port is not None and name != port:
                continue
            for item in items:
                row = self.project.catalog.db.execute(
                    "SELECT path FROM workflow_publications WHERE build_id=? AND artifact=?",
                    (build.id, item["path"]),
                ).fetchone()
                if row is None:
                    continue
                path = self.project.files.path(build.owner_id) / row["path"]
                path = safe_target(self.root, str(path.relative_to(self.root)))
                require(
                    path.is_file() and file_hash(path) == item["sha256"],
                    "Veröffentlichte Ergebnisdatei fehlt oder wurde verändert.",
                )
                value = {
                    **item,
                    "port": name,
                    "build_id": build.id,
                    "file_path": str(path.relative_to(self.root)),
                }
                if item["type"] in {"image", "spritesheet"}:
                    value["image_path"] = value["file_path"]
                artifacts.append(value)
        return artifacts

    def publish(self, projection, change, run):
        from .project_files import component

        report = run.data
        snapshot = json.loads(report["plan"]["snapshot"])
        actual = {row["node"]: row for row in report["actual"]}
        prepared = []
        try:
            for variant in report["plan"]["variants"]:
                if not variant["required"]:
                    continue
                output = snapshot["publications"][variant["key"]]
                if not output.get("publish", True):
                    continue
                item = actual[variant["node"]]
                require(item["actual"] in {"built", "reused"}, "Unvollständiger Ablauf.")
                build = self.project.catalog.get(item["build_id"])
                require(build.owner_id == run.owner_id, "Ergebnis gehört zu einem anderen Asset.")
                result, files = self.read(build)
                for artifact in result["ports"][output["port"]]:
                    meta = artifact["metadata"]
                    pose = (
                        projection.pose_folder(
                            self.project.catalog.get(run.owner_id), meta.get("slot", {})
                        )
                        or "Einzelbild"
                    )
                    directory = output.get("directory", "Ergebnisse/" + output["name"])
                    directory = directory.replace("{pose}", component(pose)).replace(
                        "{variante}", component(meta.get("profile", output["name"]))
                    )
                    output_directory(directory)
                    name = (
                        component(Path(artifact["path"]).stem)
                        + "--"
                        + build.data["input_fingerprint"][:16]
                        + Path(artifact["path"]).suffix
                    )
                    relative = str(Path(directory) / Path(artifact["path"]).parent / name)
                    prepared.append((build, artifact, relative, files[artifact["path"]]))
        except (StudioError, OSError, ValueError, KeyError, TypeError):
            if run.id in self.project.catalog.projection_builds:
                raise
            return
        index = []
        for build, artifact, relative, raw in prepared:
            require(
                projection.files.get((run.owner_id, relative)) in {None, artifact["sha256"]},
                "Ausgabepfad kollidiert mit einer vorhandenen Datei.",
            )
            projection.file(change, run.owner_id, relative, artifact["sha256"], content=raw)
            self.project.catalog.db.execute(
                "INSERT INTO workflow_publications VALUES (?,?,?,?,?) "
                "ON CONFLICT(build_id,artifact) DO UPDATE SET path=excluded.path",
                (build.id, run.owner_id, artifact["path"], relative, artifact["sha256"]),
            )
            index.append({**artifact, "path": relative, "build_id": build.id})
        projection.json(
            change,
            run.owner_id,
            "Ergebnisse/aktuell.json",
            {
                "contract": "studio-workflow-publication-v1",
                "run_id": run.id,
                "asset_id": run.owner_id,
                "recipe_id": snapshot["recipe_id"],
                "artifacts": index,
            },
        )
