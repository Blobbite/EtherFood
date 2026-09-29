"""Read verified asset derivations; partial runs never replace a complete publication."""

import json

from PIL import Image

from ..domain.assets import require
from ..domain.models import StudioError
from ..pipelines.image_processing import validate_metadata
from ..storage.blob_store import file_hash
from ..storage.build_cache import BuildCache
from ..storage.paths import safe_target
from .asset_service import AssetService
from .recipe_builds import RecipeBuildService


class RecipeResultService:
    def __init__(self, project):
        self.project = project
        self.root = project.catalog.path.parent
        self.cache = BuildCache(project.catalog)

    def latest(self, asset_id):
        """Return state, provenance and checked artifacts without changing any active pointers.

        States: not_started, ready, stale, invalid. Artifact paths are project-relative.
        A failed newer attempt remains visible as last_run_status, while the previous
        complete publication stays historical. Layout/inactive parameters do not stale pixels.
        """
        AssetService(self.project).asset(asset_id)
        runs = sorted((r for r in self.project.catalog.records() if r.kind == "build" and
                       r.owner_id == asset_id and r.data.get("contract") == "studio-build-run-v1"
                       and not r.data.get("diagnostic", True)),
                      key=lambda r: (r.created_at, r.id), reverse=True)
        result = {"state": "not_started", "reason": "Noch kein vollständiger Bildlauf",
                  "run_id": None, "recipe_id": None, "recipe_revision": None, "artifacts": [],
                  "last_run_status": runs[0].data["status"] if runs else None}
        completed = next((r for r in runs if r.data.get("published") and
                          r.data["status"] == "succeeded"), None)
        if completed is None:
            return result
        try:
            plan = completed.data["plan"]
            snapshot = json.loads(plan["snapshot"])
            result.update(run_id=completed.id, recipe_id=snapshot["recipe_id"],
                          recipe_revision=snapshot["recipe_revision"])
            actual = {row["node"]: row for row in completed.data["actual"]}
            stored = {row["node"]["key"]: row for row in plan["nodes"]}
            require(len(actual) == len(stored) and set(actual) == set(stored),
                    "Veröffentlichter Bildlauf hat keine vollständige Schrittliste.")
            verified = {}
            for key, row in stored.items():
                if not row["node"]["required"]:
                    continue
                require(actual[key]["actual"] in {"built", "reused"},
                        "Unvollständiger Schritt ist kein veröffentlichtes Ergebnis.")
                record = self.project.catalog.get(actual[key]["build_id"])
                require(record.owner_id == asset_id and
                        record.data["input_fingerprint"] == row["fingerprint"] and
                        record.data["node_key"] == key,
                        "Build gehört nicht zum eingefrorenen Plan.")
                dependencies = {}
                for dep in row["node"]["dependencies"]:
                    predecessor = self.project.catalog.get(actual[dep["node"]]["build_id"])
                    dependencies[dep["node"]] = predecessor.data["result_digest"]
                self.cache.verify(record, tuple(o["path"] for o in row["node"]["outputs"]),
                                  dependencies)
                verified[key] = record
            artifacts = []
            for variant in plan["variants"]:
                if variant["required"]:
                    record = verified[variant["node"]]
                    if "publications" in snapshot:
                        from .tool_results import ToolResultService

                        artifacts.extend(
                            {"variant": variant["key"], **item}
                            for item in ToolResultService(self.project).artifacts(
                                record, port=snapshot["publications"][variant["key"]]["port"]
                            )
                        )
                        continue
                    artifacts.append({"variant": variant["key"], "build_id": record.id,
                                      **self.metadata(record)})
            result.update(artifacts=artifacts, state="ready",
                          reason="Bildableitungen vollständig geprüft")
        except (StudioError, OSError, ValueError, KeyError, TypeError) as error:
            return {**result, "state": "invalid", "reason": str(error), "artifacts": []}
        try:
            current = RecipeBuildService(self.project).plan(asset_id, snapshot["recipe_id"])
            old_targets = {(v["key"], v["node"]) for v in plan["variants"] if v["required"]}
            new_targets = {(v.key, v.node) for v in current.variants if v.required}
            identical = old_targets == new_targets and all(
                row.node.key in stored and stored[row.node.key]["fingerprint"] == row.fingerprint
                for row in current.nodes if row.node.required)
            if not identical:
                result.update(state="stale",
                              reason="Quellen, Rezept, Profile oder Werkzeuge geändert")
        except (StudioError, OSError, ValueError, KeyError, TypeError) as error:
            result.update(state="stale",
                          reason="Aktuelle Verarbeitung ist blockiert: " + str(error))
        return result

    def metadata(self, record, *, published=True):
        require(record.kind == "build" and record.data.get("contract") == "studio-build-v1"
                and not record.data.get("diagnostic", True), "Kein geprüftes Bildbuild.")
        self.cache.verify(record, tuple(item["path"] for item in record.data["outputs"]),
                          record.data["dependencies"])
        relative = f".asset-studio/jobs/{record.data['job_id']}/output"
        image_path = safe_target(self.root, relative + "/image.png")
        meta_path = safe_target(self.root, relative + "/metadata.json")
        if published:
            row = self.project.catalog.db.execute(
                "SELECT path FROM asset_publications WHERE build_id=? AND asset_id=?",
                (record.id, record.owner_id)).fetchone()
            if row:
                image_path = self.project.files.path(record.owner_id) / row["path"]
                image_path = safe_target(self.root, str(image_path.relative_to(self.root)))
                meta_path = safe_target(self.root,
                    str(image_path.with_suffix(".json").relative_to(self.root)))
                expected = {item["path"]: item["sha256"] for item in record.data["outputs"]}
                require(file_hash(image_path) == expected["image.png"] and
                        file_hash(meta_path) == expected["metadata.json"],
                        "Veröffentlichte Asset-Dateien fehlen oder wurden extern verändert.")
        require(meta_path.stat().st_size <= 65536, "Zu große Ergebnis-Metadaten.")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        require(isinstance(meta, dict) and meta.get("contract") == "studio-image-result-v1" and
                meta.get("image_sha256") == file_hash(image_path), "Bildbindung wurde verändert.")
        with Image.open(image_path) as image:
            require(image.format == "PNG" and image.mode == "RGBA" and
                    getattr(image, "n_frames", 1) == 1, "Kein statisches RGBA-PNG-Ergebnis.")
            validate_metadata(meta, image.size)
        result = {"image_path": str(image_path.relative_to(self.root)), "metadata": meta}
        if any(item["path"] == "preview.gif" for item in record.data["outputs"]):
            preview = self.preview(record)
            if published:
                path = self.project.files.path(record.owner_id) / preview["directory"] / \
                    image_path.with_suffix(".gif").name
                if row:
                    require(file_hash(path) == preview["sha256"],
                            "Veröffentlichte GIF-Vorschau fehlt oder wurde verändert.")
                    preview["path"] = str(path.relative_to(self.root))
            result["preview"] = preview
        return result

    def preview(self, record):
        self.cache.verify(record, tuple(item["path"] for item in record.data["outputs"]),
                          record.data["dependencies"])
        directory = safe_target(self.root, f".asset-studio/jobs/{record.data['job_id']}/output")
        require((directory / "preview.json").stat().st_size <= 65536, "Zu große GIF-Metadaten.")
        preview = json.loads((directory / "preview.json").read_text(encoding="utf-8"))
        from ..packages.previews.process import validate_directory
        validate_directory(preview["directory"])
        require(preview["sha256"] == file_hash(directory / "preview.gif"),
                "GIF-Vorschau stimmt nicht mit ihren Metadaten überein.")
        return {**preview, "path": str((directory / "preview.gif").relative_to(self.root))}
