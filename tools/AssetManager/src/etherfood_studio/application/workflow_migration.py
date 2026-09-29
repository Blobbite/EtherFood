"""Move legacy processing requirements into explicit, versioned workflow nodes."""

from copy import deepcopy
import hashlib
import sys

from ..domain.assets import require
from ..domain.pipeline_recipes import validate_recipe
from ..domain.tool_contract import empty_workflow, is_workflow, operation
from ..storage.sqlite_repository import canonical
from .asset_service import AssetService
from .builtin_tools import ensure
from .pipeline_service import PipelineService
from .profile_service import ProfileService
from .tool_packages import ToolPackageService


class WorkflowMigration:
    def __init__(self, project):
        self.project = project
        self.service = PipelineService(project)
        self.tools = ToolPackageService(project)

    def plugin(self, identifier):
        from .plugin_service import PluginService

        old = PluginService(self.project).details(identifier)
        spec = old["manifest"]
        source = self.tools.store.path_for(old["code_hash"]).read_bytes()
        version2 = spec["contract"] == "studio-python-step-v2"
        wrapper = (
            "from copy import deepcopy\nfrom PIL import Image\nimport legacy\n"
            "from etherfood_studio.pipelines.python_contract import result_metadata\n"
            "def run(context, inputs, parameters):\n"
            "    incoming = inputs['image']\n"
            "    image = Image.open(incoming.path).convert('RGBA')\n"
            "    meta = deepcopy(incoming.metadata)\n"
            "    result = legacy."
            + spec["entry_point"]
            + "(image.copy(), "
            + ("deepcopy(meta), " if version2 else "")
            + "parameters)\n"
            + (
                "    image, changes = result\n"
                "    meta = result_metadata(meta, changes, image.size)\n"
                if version2
                else "    if result.size != image.size: raise ValueError('Bildgröße geändert')\n"
                "    image = result\n"
            )
            + "    output = context.artifact('image.png', incoming.type, meta)\n"
            "    image.save(output.path)\n    return {'image': output}\n"
        ).encode()
        dependencies = list(spec["dependencies"])
        if not any(value.lower().startswith("pillow==") for value in dependencies):
            dependencies.append("Pillow==12.1.1")
        manifest = {
            "contract": "studio-tool-package-v1",
            "id": "legacy-" + old["code_hash"][:16],
            "name": spec["name"],
            "description": spec["description"],
            "version": "1.0.0",
            "python": f"{sys.version_info.major}.{sys.version_info.minor}",
            "dependencies": dependencies,
            "files": ["step.py", "legacy.py"],
            "flows": [],
            "steps": [
                {
                    "id": "process",
                    "name": spec["name"],
                    "description": spec["description"],
                    "source": "step.py",
                    "entry_point": "run",
                    "execution": "map",
                    "parameters": spec["parameters"],
                    "capabilities": spec["capabilities"],
                    "inputs": {"image": {"type": "image"}},
                    "outputs": {
                        "image": {"type": "image", "directory": "Ergebnisse/{pose}/{variante}"}
                    },
                }
            ],
        }
        package = self.tools.register(
            self.tools.inspect_content(manifest, {"step.py": wrapper, "legacy.py": source})
        )
        if old.get("approved_hash") == old["code_hash"]:
            self.tools.approve(package["digest"])
        return operation(package["digest"], "process")

    def convert(self, recipe, requested, profiles, package):
        if is_workflow(recipe):
            return deepcopy(recipe)
        result = empty_workflow()
        result.update(
            category=recipe["category"],
            enabled=recipe["enabled"],
            steps=[],
            resources=deepcopy(recipe["resources"]),
            capabilities=recipe["capabilities"],
            legacy_unresolved=list(recipe["legacy_unresolved"]),
        )
        streams = {}
        nonleaves = {edge["from"] for edge in recipe["connections"]}
        manifests = self.service.manifests()
        for node in validate_recipe(recipe, manifests):
            old = node["operation"]
            incoming = [
                value
                for edge in recipe["connections"]
                if edge["to"] == node["id"]
                for value in streams[edge["from"]]
            ]
            if old == "source":
                result["steps"].append(deepcopy(node))
                streams[node["id"]] = [(node["id"], "source")]
                continue
            if not node["enabled"]:
                streams[node["id"]] = incoming
                continue
            streams[node["id"]] = []
            targets = [key for key in (recipe["profiles"] or requested) if profiles[key]["enabled"]]
            selected_targets = set(targets)
            if old == "graphics":
                targets = list(
                    dict.fromkeys(
                        [profiles[key]["parent"] for key in targets if profiles[key]["parent"]]
                        + targets
                    )
                )
            for parent, inherited in incoming:
                made = {}
                for profile in targets if old == "graphics" else [inherited]:
                    params = deepcopy(node["parameters"])
                    entry = {
                        "prepare8": "grid",
                        "prepare16": "grid",
                        "source_color": "colors",
                        "color": "colors",
                    }.get(old, old)
                    if old == "graphics":
                        spec = profiles[profile]
                        entry = (
                            "pixel_low"
                            if spec["method"] == "pixel_low"
                            else "pixel_high" if spec["method"] == "pixel" else "comic_low"
                        )
                        params = {
                            "mode": spec["mode"],
                            "value": spec["value"],
                            "profile": profile,
                            "parent": spec["parent"] or "",
                        }
                        if entry == "pixel_high":
                            params["colors"] = spec["colors"]
                            params["palette"] = node["parameters"]["palette"]
                    elif old.startswith("prepare"):
                        params = {"columns": 4, "crop": True}
                    elif old == "gif":
                        params = {"source_timing": params["timing"] == "pose", "fps": params["fps"]}
                    identifier = (
                        "m_"
                        + hashlib.sha256((node["id"] + parent + profile).encode()).hexdigest()[:24]
                    )
                    name = operation(package["digest"], entry)
                    if old.startswith("python:"):
                        from ..domain.models import StudioError

                        try:
                            name = self.plugin(old)
                        except (StudioError, OSError, ValueError) as error:
                            name = old
                            result["legacy_unresolved"].append(
                                "Python-Paket reparieren: " + str(error)
                            )
                    if name not in self.service.manifests():
                        name = old
                        result["legacy_unresolved"].append("Fehlenden Baustein zuordnen: " + old)
                    result["steps"].append(
                        {"id": identifier, "operation": name, "enabled": True, "parameters": params}
                    )
                    upstream = (
                        made.get(profiles[profile]["parent"], parent)
                        if old == "graphics"
                        else parent
                    )
                    result["connections"].append(
                        {"from": upstream, "out": "image", "to": identifier, "in": "image"}
                    )
                    made[profile] = identifier
                    if old != "graphics" or profile in selected_targets:
                        streams[node["id"]].append((identifier, profile))
                    if (node["id"] not in nonleaves or old in {"graphics", "gif"}) and (
                        old != "graphics" or profile in selected_targets
                    ):
                        spec = self.service.manifests().get(name, {})
                        for port, output in spec.get("ports", {}).get("outputs", {}).items():
                            value = {"node": identifier, "port": port, **output}
                            if old == "graphics":
                                value["directory"] = "Ergebnisse/{pose}/" + profile
                            if old == "gif" and port == "gif":
                                value["directory"] = node["parameters"]["directory"]
                            result["outputs"][identifier + "_" + port] = value
        validate_recipe(result, self.service.manifests())
        return result

    def ensure(self):
        package = ensure(self.project)
        if (
            self.project.project().data.get("workflow_editor_version") == 1
            and all(is_workflow(recipe.data["recipe"]) for recipe in self.service.recipes())
            and all(
                card.data["asset_definition"]["schema_version"] == 2
                for card in self.project.cards()
                if card.kind == "asset" and "asset_definition" in card.data
            )
        ):
            return
        catalog = self.project.catalog
        profiles = ProfileService(self.project).profiles()
        recipes = self.service.recipes()
        assets = [
            card
            for card in self.project.cards()
            if card.kind == "asset" and "asset_definition" in card.data
        ]
        assignments = self.service.assignments()
        legacy = {recipe.id: recipe for recipe in recipes if not is_workflow(recipe.data["recipe"])}
        bindings = {}
        for asset in assets:
            matches = self.service.matching_assignments(asset.id)
            highest = max((priority for priority, _, _ in matches), default=0)
            definition = AssetService(self.project).definition(asset.id)
            bindings[asset.id] = []
            for priority, assignment, _ in matches:
                if priority != highest:
                    continue
                recipe = catalog.get(assignment.data["recipe_id"])
                effective = self.service._overrides(
                    recipe.data["recipe"], assignment.data["overrides"]
                )
                requested = (
                    list(definition.graphics) if definition.schema_version == 1 else list(profiles)
                )
                bindings[asset.id].append(
                    (assignment, self.convert(effective, requested, profiles, package))
                )
        with catalog.transaction():
            for recipe in legacy.values():
                value = self.convert(recipe.data["recipe"], list(profiles), profiles, package)
                catalog.save(catalog.get(recipe.id), data={**recipe.data, "recipe": value})
            # Bake old overrides into rule-specific recipes, including rules for future assets.
            for assignment in assignments:
                previous = legacy.get(assignment.data["recipe_id"])
                if previous and assignment.data["overrides"]:
                    effective = self.service._overrides(
                        previous.data["recipe"], assignment.data["overrides"]
                    )
                    value = self.convert(effective, list(profiles), profiles, package)
                    record = self.copy_recipe(previous.title + " · Regel", value)
                    catalog.save(
                        assignment,
                        data={**assignment.data, "recipe_id": record.id, "overrides": {}},
                    )
            for asset in assets:
                selections, specialized = [], False
                for original, value in bindings[asset.id]:
                    assignment = catalog.get(original.id)
                    current = catalog.get(assignment.data["recipe_id"])
                    effective = self.service._overrides(
                        current.data["recipe"], assignment.data["overrides"]
                    )
                    if value != effective:
                        current = self.copy_recipe(current.title + " · " + asset.title, value)
                        overrides = {}
                        specialized = True
                    else:
                        overrides = assignment.data["overrides"]
                    selections.append((assignment, current, overrides))
                # One explicit specialization must not hide other inherited workflows.
                if specialized:
                    for assignment, recipe, overrides in selections:
                        if assignment.data["asset_id"]:
                            catalog.save(
                                assignment,
                                data={
                                    **assignment.data,
                                    "recipe_id": recipe.id,
                                    "overrides": overrides,
                                },
                            )
                        else:
                            self.service.assign(
                                recipe.id,
                                asset_id=asset.id,
                                capabilities=assignment.data["capabilities"],
                                overrides=overrides,
                            )
            for asset in assets:
                data = deepcopy(asset.data)
                data["asset_definition"].update(schema_version=2, graphics=[], frames=[])
                catalog.save(catalog.get(asset.id), data=data)
            record = self.project.project()
            data = {key: value for key, value in record.data.items() if key != "graphics_profiles"}
            data["workflow_editor_version"] = 1
            catalog.save(record, data=data)

    def copy_recipe(self, title, value):
        return self.project.create_card(
            "pipeline",
            title,
            self.service.project_id,
            {"project_id": self.service.project_id, "recipe": value},
        )
