"""Pose preparation overview backed by source, mask and checked preview revisions."""

import json

from ..domain.models import StudioError
from .asset_service import AssetService
from .mask_service import MaskService
from .recipe_builds import RecipeBuildService
from .recipe_results import RecipeResultService
from .source_import import SourceImportService


class AssetDeliveries:
    def __init__(self, project):
        self.project = project
        self.assets = AssetService(project)
        self.sources = SourceImportService(self.assets)

    def poses(self, asset_id):
        asset = self.assets.asset(asset_id)
        definition = self.assets.definition(asset_id)
        rows = self.sources.delivery_matrix(asset_id)
        masks = MaskService(self.project)
        for row in rows:
            row["mask"] = "missing"
            identifier = asset.data.get("active_masks", {}).get(row["key"].token)
            if "supports_materials" not in definition.capabilities:
                row["mask"] = "not_required"
            elif identifier:
                try:
                    record = self.project.catalog.get(identifier)
                    source = row["revision"]
                    if source is None or record.data["source_revision"] != source.id:
                        row["mask"] = "stale"
                    else:
                        status = masks.status(identifier)
                        row["mask"] = "ready" if status["technical"] == "passed" and \
                            status["visual"] == "confirmed" else "review"
                except (StudioError, OSError, ValueError, KeyError):
                    row["mask"] = "invalid"
        previews = self.previews(asset_id)
        names = {p.id: p.display_name for p in definition.poses} or {None: "Einzelbild"}
        return [{"id": identifier, "name": name,
                 "rows": [row for row in rows if row["key"].pose_id == identifier],
                 "gifs": sum(row["revision"] is not None and row["revision"].id in previews
                             for row in rows if row["key"].pose_id == identifier and
                             row["key"].kind == "spritesheet")}
                for identifier, name in names.items()]

    def previews(self, asset_id):
        """Count checked publications whose inputs still match the current pipeline."""
        result = set()
        current = {}
        catalog = self.project.catalog
        for run in catalog.records():
            if run.kind != "build" or run.owner_id != asset_id or \
                    run.data.get("contract") != "studio-build-run-v1" or \
                    not run.data.get("published") or run.data.get("status") != "succeeded":
                continue
            snapshot = json.loads(run.data["plan"]["snapshot"])
            if not snapshot.get("recipe_id"):
                continue
            recipe_id = snapshot["recipe_id"]
            if recipe_id not in current:
                try:
                    plan = RecipeBuildService(self.project).plan(asset_id, recipe_id)
                    targets = {v.node for v in plan.variants if v.required}
                    current[recipe_id] = {row.node.key: row.fingerprint for row in plan.nodes
                                          if row.node.key in targets}
                except (StudioError, OSError, ValueError, KeyError, TypeError):
                    current[recipe_id] = {}
            stored = {row["node"]["key"]: row["fingerprint"]
                      for row in run.data["plan"]["nodes"]}
            nodes = {v["node"] for v in run.data["plan"]["variants"] if v["required"]}
            for item in run.data["actual"]:
                if item["node"] not in nodes or not item.get("build_id"):
                    continue
                if current[recipe_id].get(item["node"]) != stored.get(item["node"]):
                    continue
                build = catalog.get(item["build_id"])
                if any(o["path"] == "artifacts.zip" for o in build.data["outputs"]):
                    try:
                        from .tool_results import ToolResultService
                        for artifact in ToolResultService(self.project).artifacts(build):
                            if artifact["type"] == "gif" and artifact["metadata"].get("source_revision"):
                                result.add(artifact["metadata"]["source_revision"])
                    except (StudioError, OSError, ValueError, KeyError):
                        pass
                    continue
                if not any(o["path"] == "preview.gif" for o in build.data["outputs"]):
                    continue
                try:
                    artifact = RecipeResultService(self.project).metadata(build)
                    result.add(artifact["preview"]["source_revision"])
                except (StudioError, OSError, ValueError, KeyError):
                    continue
        return result
