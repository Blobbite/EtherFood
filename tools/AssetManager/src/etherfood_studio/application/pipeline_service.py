"""Project-local recipe revisions and explicit assignment precedence."""

from copy import deepcopy
import json

from ..domain.assets import CAPABILITIES, require
from ..domain.models import StudioError
from ..domain.pipeline_recipes import BUILTINS, blockers, template, validate_recipe
from .asset_service import AssetService
from .profile_service import ProfileService


class PipelineService:
    def __init__(self, project):
        self.project, self.catalog = project, project.catalog
        self.project_id = project.project().id
        self.global_id = next(r.id for r in project.cards() if r.kind == "global")

    def manifests(self) -> dict:
        from .plugin_service import PluginService

        return {**BUILTINS, **PluginService(self.project).manifests()}

    def recipes(self) -> list:
        return [r for r in self.catalog.records() if r.kind == "pipeline"]

    def recipe(self, identifier):
        record = self.project.require_active_card(identifier)
        require(record.kind == "pipeline", "Pipeline-Karte auswählen.")
        require(record.data.get("project_id") == self.project_id,
                "Pipeline gehört nicht zum geöffneten Projekt.")
        validate_recipe(record.data["recipe"], self.manifests())
        return record

    def create(self, title, template_id="empty"):
        return self.project.create_card("pipeline", title, self.global_id,
            {"project_id": self.project_id, "recipe": template(template_id)})

    def save(self, identifier, data, expected_revision):
        validate_recipe(data, self.manifests())
        profiles = ProfileService(self.project).profiles()
        require(set(data["profiles"]) <= set(profiles), "Unbekanntes Projektprofil im Rezept.")
        with self.catalog.transaction():
            record = self.recipe(identifier)
            require(record.revision_no == expected_revision,
                    "Pipeline wurde inzwischen geändert; erneut öffnen.")
            values = {**record.data, "recipe": deepcopy(data)}
            return record if record.data == values else self.catalog.save(record, data=values)

    def assign(self, recipe_id, *, asset_id=None, type_id=None, capabilities=(), overrides=None):
        recipe = self.recipe(recipe_id)
        require(not (asset_id and type_id), "Asset oder Typregel wählen, nicht beides.")
        owner = asset_id or self.global_id
        if asset_id:
            AssetService(self.project).asset(asset_id)
        if type_id:
            require(type_id in self.asset_types(), "Asset-Typ ist im Projekt nicht bekannt.")
        values = {"project_id": self.project_id, "recipe_id": recipe.id,
                  "asset_id": asset_id, "type_id": type_id, "capabilities": list(capabilities),
                  "overrides": overrides or {}}
        self._overrides(recipe.data["recipe"], values["overrides"])
        require(set(capabilities) <= set(CAPABILITIES), "Unbekannte Fähigkeit.")
        return self.catalog.create("pipeline_assignment", recipe.title, owner, values)

    def asset_types(self):
        from ..domain.assets import TYPE_PRESETS

        result = {key: title for key, (title, _) in TYPE_PRESETS.items()}
        for record in self.catalog.records():
            if record.kind == "asset" and "asset_definition" in record.data:
                definition = AssetService(self.project).definition(record.id)
                result[definition.type_id] = definition.type_label
        return result

    def assignments(self):
        rows = [r for r in self.catalog.records() if r.kind == "pipeline_assignment"]
        for record in rows:
            self.validate_assignment(record)
        return rows

    def validate_assignment(self, record):
        data = record.data
        require(set(data) == {"project_id", "recipe_id", "asset_id", "type_id", "capabilities",
                             "overrides"} and data["project_id"] == self.project_id,
                "Ungültige/projektfremde Pipeline-Zuweisung.")
        require(isinstance(data["recipe_id"], str) and
                (data["asset_id"] is None or isinstance(data["asset_id"], str)) and
                (data["type_id"] is None or isinstance(data["type_id"], str)) and
                isinstance(data["capabilities"], list) and
                all(isinstance(v, str) and v in CAPABILITIES for v in data["capabilities"]) and
                isinstance(data["overrides"], dict) and not (data["asset_id"] and data["type_id"]),
                "Ungültige Zuweisungsparameter.")
        recipe = self.catalog.get(data["recipe_id"])
        require(recipe.kind == "pipeline" and recipe.data.get("project_id") == self.project_id,
                "Zuweisung benötigt ein Rezept desselben Projekts.")
        require(record.owner_id == (data["asset_id"] or self.global_id),
                "Besitzer und Pipeline-Zuweisung widersprechen sich.")
        if data["asset_id"]:
            require(self.catalog.get(data["asset_id"]).kind == "asset", "Asset-Ziel fehlt.")
        require(all(isinstance(key, str) for key in data["overrides"]),
                "Ungültige lokale Parameterbezeichnungen.")

    def resolve(self, asset_id):
        definition = AssetService(self.project).definition(asset_id)
        matches = []
        for record in self.assignments():
            data = record.data
            require(data["project_id"] == self.project_id,
                    "Projektfremde Pipeline-Zuweisung.")
            if data["asset_id"]:
                if data["asset_id"] != asset_id:
                    continue
                priority, origin = 3, "Explizite Asset-Zuweisung"
            elif data["type_id"] or data["capabilities"]:
                if (data["type_id"] and data["type_id"] != definition.type_id or
                        not set(data["capabilities"]) <= set(definition.capabilities)):
                    continue
                priority, origin = 2, "Asset-Typ-/Fähigkeitsregel"
            else:
                priority, origin = 1, "Projektstandard"
            matches.append((priority, record, origin))
        if not matches:
            return None
        highest = max(row[0] for row in matches)
        winners = [row for row in matches if row[0] == highest]
        require(len(winners) == 1, "Konflikt: mehrere Pipeline-Zuweisungen gleicher Priorität.")
        _, assignment, origin = winners[0]
        recipe = self.recipe(assignment.data["recipe_id"])
        data = self._overrides(recipe.data["recipe"], assignment.data["overrides"])
        require(set(data["capabilities"]) <= set(definition.capabilities),
                "Pipeline passt nicht zu den Fähigkeiten dieses Assets.")
        return {"recipe": recipe, "assignment": assignment, "origin": origin, "data": data}

    def _overrides(self, data, overrides):
        require(isinstance(overrides, dict) and set(overrides) <= set(data["overridable"]),
                "Lokale Abweichung ist nicht vom Rezept freigegeben.")
        result = deepcopy(data)
        for node in result["steps"]:
            for key in node["parameters"]:
                token = node["id"] + "." + key
                if token in overrides:
                    node["parameters"][key] = overrides[token]
        validate_recipe(result, self.manifests())
        return result

    def summary(self, identifier):
        record = self.recipe(identifier)
        reasons = blockers(record.data["recipe"], self.manifests())
        from .pipeline_exchange import PipelineExchange
        reasons += PipelineExchange(self.project).dependency_blockers(
            record.data["recipe"], verify_content=False)
        count = 0
        for asset in self.catalog.records():
            if asset.kind == "asset" and "asset_definition" in asset.data:
                try:
                    effective = self.resolve(asset.id)
                    count += bool(effective and effective["recipe"].id == identifier)
                except StudioError:
                    pass
        runs = []
        for build in self.catalog.records():
            if (build.kind == "build" and build.data.get("contract") == "studio-build-run-v1"
                    and json.loads(build.data["plan"].get("snapshot", "{}")).get(
                        "recipe_id") == identifier):
                runs.append(build)
        latest = max(runs, key=lambda r: (r.created_at, r.id)) if runs else None
        return {"category": record.data["recipe"]["category"], "assets": count,
                "enabled": record.data["recipe"]["enabled"], "blockers": reasons,
                "status": "blockiert" if reasons else "Struktur gültig",
                "last_build": latest.data["status"] if latest else "nicht ausgeführt"}
