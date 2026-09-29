"""Pose preparation overview backed by source, mask and checked preview revisions."""

import json

from ..domain.models import StudioError
from .asset_service import AssetService
from .mask_service import MaskService
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
        """Only verified, current usage results count as prepared animations."""

        from .pipeline_results import PipelineResults

        active = self.project.catalog.get(asset_id).data.get("active_sources", {})
        result = PipelineResults(self.project).latest(asset_id)
        return {
            active[item["source_key"]]
            for item in result["artifacts"]
            if item["state"] == "ready" and item["type"] == "gif" and item["source_key"] in active
        }
