"""One asset's applicable recipes, explicit rules and planned output directories."""

from ..domain.models import StudioError
from .asset_service import AssetService
from .pipeline_outputs import recipe_outputs
from .pipeline_service import PipelineService
from .profile_service import ProfileService


class AssetPipelines:
    def __init__(self, project):
        self.project = project
        self.service = PipelineService(project)

    def rows(self, asset_id):
        definition = AssetService(self.project).definition(asset_id)
        matches = self.service.matching_assignments(asset_id)
        if not matches:
            return []
        manifests = self.service.manifests()
        profiles = ProfileService(self.project).profiles()
        result = []
        for recipe_id in dict.fromkeys(row[1].data["recipe_id"] for row in matches):
            recipe = self.project.catalog.get(recipe_id)
            rules = [{"id": row.id, "origin": origin, "priority": priority, **row.data}
                     for priority, row, origin in matches if row.data["recipe_id"] == recipe_id]
            binding, data = None, recipe.data["recipe"]
            state, reason = "superseded", "Durch eine höher priorisierte Zuweisung übersteuert"
            try:
                binding = self.service.resolve(asset_id, recipe_id)
                if binding:
                    data = binding["data"]
                    state = "active" if data["enabled"] else "disabled"
                    reason = binding["origin"] if data["enabled"] else "Pipeline deaktiviert"
            except StudioError as error:
                state, reason = "blocked", str(error)
            if recipe.archived:
                state, reason, binding = "archived", "Pipeline archiviert", None
            outputs = recipe_outputs(data, manifests, profiles, [definition])
            result.append({"recipe": recipe, "data": data, "binding": binding,
                           "rules": rules, "state": state, "reason": reason, "outputs": outputs})
        rank = {"active": 0, "blocked": 1, "disabled": 2, "superseded": 3, "archived": 4}
        return sorted(result, key=lambda row: (rank[row["state"]], row["recipe"].title.casefold()))

    def directories(self, asset_id):
        return sorted({path for row in self.rows(asset_id) if row["state"] == "active"
                       for output in row["outputs"] if output["state"] == "active"
                       for path in output["paths"] if "{" not in path and "}" not in path})
