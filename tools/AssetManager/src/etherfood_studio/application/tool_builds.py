"""Expand reusable flows and compile named file ports into reproducible job graphs."""

from copy import deepcopy

from ..domain.assets import require
from ..domain.builds import (
    BuildGraph,
    BuildNode,
    ContentInput,
    Dependency,
    OutputSpec,
    VariantTarget,
)
from ..domain.pipeline_recipes import blockers, validate_recipe
from ..domain.sources import expected_sources
from ..domain.tool_contract import expand_workflow
from ..pipelines.fingerprints import digest
from ..pipelines.tool_adapter import ToolAdapter
from ..storage.blob_store import BlobStore, file_hash
from ..storage.sqlite_repository import canonical
from .asset_service import AssetService
from .build_planner import BuildPlanner
from .pipeline_service import PipelineService
from .source_import import SourceImportService
from .tool_environments import ToolEnvironments
from .tool_packages import ToolPackageService


class ToolBuildService:
    def __init__(self, project):
        self.project = project
        self.packages = ToolPackageService(project)
        self.environments = ToolEnvironments(project)
        self.store = BlobStore(project.catalog, project.catalog.path.parent)

    def plan(self, asset_id, binding):
        from .recipe_builds import RecipeBuildService

        manifests = PipelineService(self.project).manifests()
        recipe = expand_workflow(binding["data"], manifests)
        reasons = blockers(recipe, manifests)
        require(not reasons, "; ".join(reasons))
        ordered = validate_recipe(recipe, manifests)
        require(
            sum(step["operation"] == "source" for step in ordered) == 1,
            "Ablauf benötigt genau einen Asset-Eingang.",
        )
        assets = AssetService(self.project)
        definition = assets.definition(asset_id)
        imports = SourceImportService(assets)
        active = imports.active(asset_id)
        required = expected_sources(definition)
        require(
            required and all(key in active for key in required),
            "Benötigte Originalquellen fehlen; zuerst Quellen importieren/aktivieren.",
        )
        sources = [active[key] for key in required]
        nodes, streams, variants, publications = [], {}, [], {}
        prefix = binding["recipe"].id
        for source in sources:
            require(
                imports.availability(source) == "imported"
                and file_hash(self.store.path_for(source.data["sha256"])) == source.data["sha256"],
                "Originalquelle fehlt oder wurde verändert.",
            )
        for step in ordered:
            operation = step["operation"]
            manifest = manifests[operation]
            if operation == "source":
                streams[step["id"]] = {"image": []}
                for source in sources:
                    key = f"{prefix}/{step['id']}/{source.id}"
                    parameters = self.parameters()
                    parameters.update(
                        entry="source",
                        source=source.id + ".png",
                        metadata=RecipeBuildService.source_metadata(source, definition),
                    )
                    nodes.append(
                        self.node(
                            key,
                            parameters,
                            inputs=(
                                ContentInput("source", "image", source.data["sha256"], source.id),
                            ),
                            source_ids=(source.id,),
                        )
                    )
                    streams[step["id"]]["image"].append((key, "image", source.id))
                continue
            require(
                operation.startswith("tool:"),
                "Diesen älteren Schritt zuerst in einen Skriptbaustein umwandeln: " + operation,
            )
            require(
                set(manifest["capabilities"]) <= set(definition.capabilities),
                "Baustein passt nicht zu den Asset-Fähigkeiten: " + manifest["name"],
            )
            incoming = {port: [] for port in manifest["inputs"]}
            for edge in recipe["connections"]:
                if edge["to"] == step["id"]:
                    incoming[edge["in"]].extend(streams[edge["from"]][edge["out"]])
            if not step["enabled"]:
                require(
                    set(incoming) == set(manifest["outputs"]),
                    "Deaktivierter Baustein kann seine Anschlüsse nicht durchreichen.",
                )
                streams[step["id"]] = incoming
                continue
            package = self.packages.trusted(manifest["package_hash"])
            receipt = self.environments.verify(package["manifest"])
            groups = {value[2] for values in incoming.values() for value in values}
            if manifest["execution"] == "collect" or not groups:
                groups = {None}
            elif len(groups) > 1:
                groups.discard(None)
            streams[step["id"]] = {port: [] for port in manifest["outputs"]}
            for group in sorted(groups, key=lambda value: value or ""):
                key = f"{prefix}/{step['id']}/{group or 'collection'}"
                parameters = self.parameters()
                parameters.update(
                    package_hash=package["digest"],
                    manifest=package["manifest"],
                    entry=manifest["id"],
                    python=str(self.environments.executable(package["manifest"])),
                    environment=digest(receipt),
                    settings=deepcopy(step["parameters"]),
                )
                dependencies = []
                for port, values in incoming.items():
                    for parent, output, source_id in values:
                        if group is not None and source_id not in {group, None}:
                            continue
                        index = len(parameters["inputs"])
                        archive, result = f"input-{index}.zip", f"input-{index}.json"
                        parameters["inputs"].append(
                            {"in": port, "out": output, "archive": archive, "result": result}
                        )
                        dependencies += [
                            Dependency(parent, "artifacts.zip", "package", archive),
                            Dependency(parent, "result.json", "report", result),
                        ]
                inputs = [ContentInput("package.zip", "package", package["archive_hash"])]
                resource_recipe = recipe
                if package["manifest"]["id"] == "etherfood-images" and manifest["id"] in {
                    "colors",
                    "pixel_high",
                }:
                    source = next((source for source in sources if source.id == group), None)
                    require(
                        source is not None,
                        "Farbressourcen benötigen eine eindeutig gebundene Originalquelle.",
                    )
                    legacy = RecipeBuildService(self.project)
                    settings = parameters["settings"]
                    if manifest["id"] == "colors":
                        mode = settings["mode"]
                        names = {
                            "soft": ["reference"],
                            "fixed": ["palette"],
                            "material": ["materials", "mask"],
                        }[mode]
                        if mode == "material" and settings["mask"] == "@source":
                            settings["mask"] = legacy.mask_for_source(recipe, source)
                        resource_recipe = legacy.managed_resources(
                            settings, names, recipe, source, mode
                        )
                        for name in names:
                            require(
                                settings[name] in resource_recipe["resources"],
                                "Farbressource fehlt: " + name,
                            )
                        legacy.validate_colors(mode, settings, resource_recipe, source)
                        if mode == "material":
                            inputs.append(
                                ContentInput("original.png", "image", source.data["sha256"])
                            )
                            parameters["resources"]["original"] = "original.png"
                    elif settings["palette"]:
                        resource_recipe = legacy.managed_resources(
                            settings, ["palette"], recipe, source, "fixed"
                        )
                        require(
                            settings["palette"] in resource_recipe["resources"],
                            "Pixelpalette fehlt.",
                        )
                for name, resource in resource_recipe["resources"].items():
                    path = self.store.path_for(resource["sha256"])
                    require(
                        path.is_file() and file_hash(path) == resource["sha256"],
                        "Ressource fehlt/ist verändert: " + name,
                    )
                    alias = "resource-" + name + ".dat"
                    parameters["resources"][name] = alias
                    inputs.append(ContentInput(alias, "package", resource["sha256"]))
                nodes.append(
                    self.node(
                        key, parameters, inputs=tuple(inputs), dependencies=tuple(dependencies)
                    )
                )
                for port in manifest["outputs"]:
                    streams[step["id"]][port].append((key, port, group))
        require(recipe["outputs"], "Mindestens einen Ablaufausgang veröffentlichen.")
        for name, output in recipe["outputs"].items():
            for index, (key, port, _) in enumerate(streams[output["node"]][output["port"]]):
                target = f"{prefix}/{name}/{index}"
                variants.append(VariantTarget(target, key))
                publications[target] = {**output, "port": port, "name": name}
        snapshot = {
            "recipe_id": prefix,
            "recipe_revision": binding["recipe"].revision_no,
            "recipe": binding["data"],
            "expanded": recipe,
            "publications": publications,
            "asset_revision": assets.asset(asset_id).revision_no,
            "assignment_id": binding["assignment"].id,
            "origin": binding["origin"],
            "sources": [{"id": s.id, "data": s.data} for s in sources],
        }
        needed = {target.node for target in variants}
        for node in reversed(nodes):
            if node.key in needed:
                needed.update(dep.node for dep in node.dependencies)
        return BuildPlanner(self.project).plan(
            asset_id,
            BuildGraph(tuple(node for node in nodes if node.key in needed), tuple(variants)),
            snapshot=canonical(snapshot),
        )

    @staticmethod
    def parameters():
        return {
            "package_hash": None,
            "manifest": None,
            "entry": None,
            "python": None,
            "environment": "source",
            "settings": {},
            "inputs": [],
            "source": None,
            "metadata": None,
            "resources": {},
        }

    def node(self, key, parameters, **kwargs):
        plan = ToolAdapter().plan(self.project.catalog.path.parent, parameters)
        return BuildNode(
            key,
            "package",
            parameters=canonical(parameters),
            tools=plan.tool_hashes,
            outputs=(OutputSpec("artifacts.zip", "package"), OutputSpec("result.json", "report")),
            adapter="studio-tool",
            **kwargs,
        )
