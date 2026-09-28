"""Compile frozen project recipes into the existing technical BuildGraph and planner."""

from copy import deepcopy
import json

from PIL import Image

from ..domain.assets import require
from ..domain.builds import (
    BuildGraph, BuildNode, ContentInput, Dependency, OutputSpec, VariantTarget,
)
from ..domain.models import StudioError
from ..domain.pipeline_recipes import blockers, validate_recipe
from ..domain.sources import expected_sources
from ..pipelines.image_adapter import ImageAdapter
from ..pipelines.image_processing import finish_metadata, legacy_modules
from ..pipelines.fingerprints import digest
from ..storage.blob_store import BlobStore, file_hash
from ..storage.sqlite_repository import canonical
from .asset_service import AssetService
from .build_planner import BuildPlanner
from .pipeline_service import PipelineService
from .plugin_service import PluginService
from .profile_service import ProfileService
from .source_import import SourceImportService


class RecipeBuildService:
    def __init__(self, project):
        self.project = project
        self.pipelines = PipelineService(project)
        self.assets = AssetService(project)
        self.store = BlobStore(project.catalog, project.catalog.path.parent)
        self.color_bindings = {}

    def dry_run(self, recipe_id=None):
        """No job admission or automatic builds: include exclusions and conflicts explicitly."""
        rows = []
        for asset in self.project.catalog.records():
            if asset.kind != "asset":
                continue
            row = {"asset_id": asset.id, "title": asset.title}
            try:
                binding = self.pipelines.resolve(asset.id)
                if not binding or recipe_id and binding["recipe"].id != recipe_id:
                    row.update(state="excluded", reason="Keine passende wirksame Zuweisung")
                else:
                    plan = self.plan(asset.id)
                    if any(v.required for v in plan.variants):
                        row.update(state="affected", reason="Geprüfter Ausführungsplan", plan=plan)
                    else:
                        row.update(state="excluded", reason="Alle Zielprofile sind deaktiviert",
                                   plan=plan)
            except (StudioError, OSError, ValueError) as error:
                row.update(state="blocked", reason=str(error))
            rows.append(row)
        return rows

    def plan(self, asset_id):
        self.color_bindings = {}
        binding = self.pipelines.resolve(asset_id)
        require(binding is not None, "Dem Asset ist keine Pipeline zugewiesen.")
        record, recipe = binding["recipe"], binding["data"]
        manifests = self.pipelines.manifests()
        reasons = blockers(recipe, manifests)
        require(not reasons, "; ".join(reasons))
        definition = self.assets.definition(asset_id)
        profiles = ProfileService(self.project).profiles()
        require(set(recipe["profiles"]) <= set(profiles), "Rezept enthält unbekannte Profile.")
        requested = recipe["profiles"] or list(definition.graphics)
        ordered = validate_recipe(recipe, manifests)
        require(sum(n["operation"] == "source" for n in ordered) == 1,
                "Ein Rezept benötigt genau einen expliziten Quelle-Schritt.")
        if not self.has_requested_output(recipe, ordered, profiles, requested):
            variants = tuple(VariantTarget(f"{record.id}/{key.token}/{profile}", None, False)
                             for key in expected_sources(definition) for profile in requested)
            return BuildPlanner(self.project).plan(asset_id, BuildGraph((), variants),
                snapshot=self.snapshot(asset_id, binding, profiles, ()))
        imports = SourceImportService(self.assets)
        active = imports.active(asset_id)
        required = expected_sources(definition)
        names = {pose.id: pose.display_name for pose in definition.poses}
        missing = [f"{names.get(key.pose_id, 'Einzelbild')} · {key.direction or 'ohne Richtung'}"
                   for key in required if key not in active]
        require(required and not missing, "Benötigte Originalquellen fehlen: " +
                ", ".join(missing) + "; zuerst Quellen importieren/aktivieren.")
        sources = [active[key] for key in required]
        counts = {}
        for source in sources:
            path = self.store.path_for(source.data["sha256"])
            require(imports.availability(source) == "imported" and
                    file_hash(path) == source.data["sha256"],
                    "Originalquelle fehlt, ist ungeprüft oder wurde verändert.")
            if source.data["slot"]["kind"] == "spritesheet":
                pose_id = source.data["slot"]["pose_id"]
                require(counts.get(pose_id, source.data["frames"]) == source.data["frames"],
                        "Alle Richtungen einer Animation benötigen dieselbe Quellframezahl.")
                counts[pose_id] = source.data["frames"]
        for step in ordered:
            if step["enabled"]:
                require(set(manifests[step["operation"]]["capabilities"]) <=
                        set(definition.capabilities),
                        "Schritt passt nicht zu den Asset-Fähigkeiten.")
        nodes, variants = [], []
        for source in sources:
            self.compile_source(record.id, recipe, ordered, source, definition, profiles,
                                requested, nodes, variants)
        require(nodes and any(v.required for v in variants),
                "Keine aktiven Zielausgaben angefordert.")
        needed = {variant.node for variant in variants if variant.required}
        for node in reversed(nodes):
            if node.key in needed:
                needed.update(edge.node for edge in node.dependencies)
        nodes = [node for node in nodes if node.key in needed]
        graph = BuildGraph(tuple(nodes), tuple(variants))
        self.validate_color_order(graph)
        return BuildPlanner(self.project).plan(asset_id, graph,
            snapshot=self.snapshot(asset_id, binding, profiles, sources))

    def snapshot(self, asset_id, binding, profiles, sources):
        record, recipe = binding["recipe"], binding["data"]
        return canonical({"recipe_id": record.id, "recipe_revision": record.revision_no,
                    "recipe": deepcopy(recipe), "profiles": deepcopy(profiles),
                    "asset_revision": self.assets.asset(asset_id).revision_no,
                    "assignment_id": binding["assignment"].id, "origin": binding["origin"],
                    "sources": [{"id": s.id, "data": s.data} for s in sources],
                    "color_bindings": deepcopy(self.color_bindings)})

    @staticmethod
    def has_requested_output(recipe, ordered, profiles, requested):
        flows = {}
        parents = {edge["from"] for edge in recipe["connections"]}
        for step in ordered:
            incoming = [flows[e["from"]] for e in recipe["connections"] if e["to"] == step["id"]]
            flows[step["id"]] = step["operation"] == "source" or any(incoming)
            if step["enabled"] and step["operation"] == "graphics":
                flows[step["id"]] &= any(profiles[key]["enabled"] for key in requested)
        return any(flows[node["id"]] for node in ordered if node["id"] not in parents)

    @staticmethod
    def validate_color_order(graph):
        """Keep explicit graph order; require renewed exact mapping after mixing operations."""
        states = {}
        for node in graph.ordered():
            parents = [states[edge.node] for edge in node.dependencies]
            exact = any(value[0] for value in parents)
            mixed = any(value[1] for value in parents)
            params = json.loads(node.parameters)
            operation = params["operation"]
            if operation in {"color", "source_color"}:
                if params["settings"]["mode"] in {"fixed", "material"}:
                    exact, mixed = True, False
                elif exact:
                    mixed = True
            elif operation == "scale" and exact:
                profile = params["profile"]
                unchanged = profile["method"] == "comic" and profile["mode"] == "factor" \
                    and profile["value"] == 1.0
                if not unchanged and profile["method"] != "pixel_low":
                    mixed = True
            elif operation == "plugin" and exact:
                mixed = True
            states[node.key] = exact, mixed
        for variant in graph.variants:
            require(not variant.required or not states[variant.node][1],
                    "Festfarben nach Skalierung/Farbänderung erneut zuordnen: " + variant.key)

    def compile_source(self, recipe_id, recipe, ordered, source, definition, profiles,
                       requested, nodes, variants):
        metadata = self.source_metadata(source, definition)
        streams = {}
        nonleaves = {edge["from"] for edge in recipe["connections"]}
        prefix = f"{recipe_id}/{source.data['slot']['pose_id'] or 'static'}/" + \
            (source.data["slot"]["direction"] or "all")
        for step in ordered:
            operation = step["operation"]
            if operation == "source":
                streams[step["id"]] = [(None, "source", source.data["frames"])]
                continue
            parents = [e["from"] for e in recipe["connections"] if e["to"] == step["id"]]
            require(len(parents) == 1, "Schritt benötigt genau einen typisierten Bildeingang.")
            incoming = streams[parents[0]]
            if not step["enabled"]:
                streams[step["id"]] = incoming
                if step["id"] not in nonleaves:
                    require(all(node for node, _, _ in incoming),
                            "Deaktivierter Endschritt hat kein verarbeitetes Eingangsergebnis.")
                    variants.extend(VariantTarget(f"{prefix}/{step['id']}/{key}/{count}", node)
                                    for node, key, count in incoming)
                continue
            outgoing = []
            for upstream, profile_key, count in incoming:
                if operation == "graphics":
                    require(profile_key == "source", "Grafikprofile nicht mehrfach kaskadieren.")
                    targets = [key for key in requested if profiles[key]["enabled"]]
                    needed = set(targets)
                    needed.update(profiles[key]["parent"] for key in targets
                                  if profiles[key]["parent"])
                    built = {}
                    for key in sorted(needed, key=lambda k: profiles[k]["method"] == "pixel_low"):
                        profile = {k: v for k, v in profiles[key].items()
                                   if k not in {"name", "enabled"}}
                        parent = built[profile["parent"]] if profile["parent"] else upstream
                        node_key = f"{prefix}/{step['id']}/{key}"
                        nodes.append(self.node(node_key, step, recipe, source, metadata, parent,
                                               profile=profile))
                        built[key] = node_key
                    outgoing = [(built[key], key, count) for key in targets]
                    variants.extend(VariantTarget(
                        f"{prefix}/{step['id']}/{key}/{count}", None, False)
                                    for key in requested if key not in targets)
                else:
                    if operation in {"prepare8", "prepare16", "frames"}:
                        require(metadata["kind"] == "spritesheet",
                                "Einzelbilder haben keine Frame-Aufbereitung oder FPS.")
                    if operation.startswith("prepare"):
                        require(count is None or count == int(operation.removeprefix("prepare")),
                                "Fram8/Fram16 benötigt die passende Quellframezahl.")
                    if operation == "frames":
                        require(count is None or step["parameters"]["frames"] <= count,
                                "Frameauswahl darf keine zusätzlichen Frames erfinden.")
                        count = step["parameters"]["frames"]
                    require(operation != "source_color" or metadata["kind"] == "single_image",
                            "Source-Farbverarbeitung benötigt Einzelbilder.")
                    node_key = f"{prefix}/{step['id']}/{profile_key}"
                    nodes.append(self.node(node_key, step, recipe, source, metadata, upstream))
                    if operation.startswith("python:") and self.pipelines.manifests()[
                            operation]["contract"] == "studio-python-step-v2":
                        count = None  # A script's actual frame selection is verified in the worker.
                    outgoing.append((node_key, profile_key, count))
            streams[step["id"]] = outgoing
            if step["id"] not in nonleaves:
                for node, key, count in outgoing:
                    frame_key = count if count is not None else "dynamic"
                    variants.append(VariantTarget(f"{prefix}/{step['id']}/{key}/{frame_key}", node))

    def node(self, key, step, recipe, source, metadata, upstream, *, profile=None):
        operation, settings = step["operation"], deepcopy(step["parameters"])
        if operation == "frames" and settings["timing"] == "keep_duration":
            settings.pop("fps")  # Duration comes from the actual incoming animation, not a default.
        resources, inputs, plugin = {}, [], None
        if operation in {"color", "source_color"}:
            mode = settings["mode"]
            if mode == "material" and settings["mask"] == "@source":
                settings["mask"] = self.mask_for_source(recipe, source)
            names = {"soft": ["reference"], "fixed": ["palette"],
                     "material": ["materials", "mask"]}[mode]
            recipe = self.managed_resources(settings, names, recipe, source, mode)
            for name in names:
                self.resource(name, settings[name], recipe, resources, inputs)
            self.validate_colors(mode, settings, recipe, source)
            if mode == "material":
                resources["original"] = "original.png"
                inputs.append(ContentInput("original.png", "image", source.data["sha256"]))
            settings = {k: settings[k] for k in (["mode", "strength", "max_distance"]
                                                if mode == "soft" else ["mode"])}
        if operation == "graphics":
            operation = "scale"
            if profile["method"] == "pixel" and settings["palette"]:
                recipe = self.managed_resources(settings, ["palette"], recipe, source, "fixed")
                self.resource("palette", settings["palette"], recipe, resources, inputs)
                legacy_modules()[5].load_palette(self.store.path_for(inputs[-1].sha256))
            settings = {}
        if operation.startswith("python:"):
            registered = PluginService(self.project).trusted(operation)
            manifest = registered["manifest"]
            require(set(manifest["capabilities"]) <= set(
                self.assets.definition(source.owner_id).capabilities),
                "Python-Schritt passt nicht zum Asset.")
            plugin = {"id": operation, "version": manifest["version"],
                      "entry_point": manifest["entry_point"], "code_hash": registered["code_hash"],
                      "manifest_sha256": digest(manifest), "dependencies": manifest["dependencies"]}
            if manifest["contract"] == "studio-python-step-v2":
                plugin["manifest"] = deepcopy(manifest)
            inputs.append(ContentInput("plugin.py", "package", registered["code_hash"]))
            operation = "plugin"
        parameters = {"operation": operation, "settings": settings, "profile": profile,
                      "source": "upstream.png" if upstream else source.id + ".png",
                      "metadata": None if upstream else metadata, "resources": resources,
                      "plugin": plugin}
        if not upstream:
            inputs.append(ContentInput("source", "image", source.data["sha256"], source.id))
        adapter = ImageAdapter()
        tool_plan = adapter.plan(self.project.catalog.path.parent, parameters)
        dependencies = (Dependency(upstream, "image.png", "image"),
                        Dependency(upstream, "metadata.json", "timing")) if upstream else ()
        stage = {"scale": "scale", "frames": "frames", "prepare8": "geometry",
                 "prepare16": "geometry"}.get(operation, "color")
        return BuildNode(key, stage, inputs=tuple(inputs), dependencies=dependencies,
            parameters=canonical(parameters), tools=tool_plan.tool_hashes,
            outputs=(OutputSpec("image.png", "image"), OutputSpec("metadata.json", "timing")),
            adapter=adapter.identifier, source_ids=() if upstream else (source.id,))

    def managed_resources(self, settings, roles, recipe, source, mode):
        from .reference_service import ReferenceService
        from .mask_service import MaskService

        recipe = deepcopy(recipe)
        for role in roles:
            if settings[role] != "@asset":
                continue
            record = MaskService(self.project).for_source(source.owner_id, source.id) \
                if role == "mask" else ReferenceService(self.project).profile(source.owner_id, mode)
            key = "managed_" + role
            recipe["resources"][key] = {"sha256": record.data["sha256"],
                "length": record.data["length"], "name": record.id + (
                    ".png" if role == "mask" else ".json")}
            settings[role] = key
            self.color_bindings[record.id] = deepcopy(record.data)
        return recipe

    def mask_for_source(self, recipe, source):
        """Select only declared PNG resources with an explicit exact source-hash binding."""
        exact = legacy_modules()[-1]
        matches = []
        for key, item in recipe["resources"].items():
            path = self.store.path_for(item["sha256"])
            require(path.is_file() and path.stat().st_size == item["length"] and
                    file_hash(path) == item["sha256"],
                    "Deklarierte Maskenressource fehlt/beschädigt.")
            try:
                with Image.open(path) as image:
                    if image.format == "PNG" and \
                            image.info.get(exact.MASK_SOURCE) == source.data["sha256"]:
                        matches.append(key)
            except Image.UnidentifiedImageError:
                continue  # JSON palettes are declared resources, not candidate label masks.
            except (Image.DecompressionBombError, OSError) as error:
                raise StudioError("validation", "Maskenressource kann nicht sicher gelesen werden: "
                                  + item["name"]) from error
        require(len(matches) == 1, "Quellgebundene Materialmaske: genau eine importierte PNG-"
                f"Ressource benötigt, {len(matches)} gefunden für {source.title}.")
        return matches[0]

    def resource(self, role, resource_id, recipe, resources, inputs):
        require(resource_id in recipe["resources"], "Ressource fehlt: " + role)
        data = recipe["resources"][resource_id]
        path = self.store.path_for(data["sha256"])
        require(path.is_file() and path.stat().st_size == data["length"] and
                file_hash(path) == data["sha256"], "Ressource fehlt/ist beschädigt: " + role)
        resources[role] = f"resource-{role}.dat"
        inputs.append(ContentInput(resources[role], "mask" if role == "mask" else "palette",
                                   data["sha256"]))

    def validate_colors(self, mode, settings, recipe, source):
        _, _, _, _, soft, exact = legacy_modules()

        def path(key):
            return self.store.path_for(recipe["resources"][settings[key]]["sha256"])

        try:
            if mode == "soft":
                soft.load_profile(path("reference"))
            elif mode == "fixed":
                exact.load_palette(path("palette"))
            else:
                palette = exact.load_material_profile(path("materials"))
                with Image.open(self.store.path_for(source.data["sha256"])) as image:
                    with exact.load_mask(path("mask"), image.convert("RGBA"),
                                         tuple(source.data["grid"]), palette["materials"],
                                         source.data["sha256"]):
                        pass
        except (ValueError, KeyError, TypeError, AttributeError) as error:
            raise StudioError("validation", "Farbprofil/Materialmaske ungültig: " + str(error)) \
                from error

    @staticmethod
    def source_metadata(source, definition):
        data = source.data
        width, height = data["width"] // data["grid"][0], data["height"] // data["grid"][1]
        pose = next((p for p in definition.poses if p.id == data["slot"]["pose_id"]), None)
        result = {"kind": data["slot"]["kind"], "grid": data["grid"], "frames": data["frames"],
                  "source_grid": data["grid"], "source_indices": list(range(data["frames"])),
                  "source_revision": source.id, "source_sha256": data["sha256"],
                  "slot": data["slot"], "profile": "source", "logical_size": [width, height],
                  "crop_offset": [0, 0], "crop_size": [width, height],
                  "anchor": list(pose.anchor) if pose else [0.5, 1.0]}
        if result["kind"] == "spritesheet":
            result.update(fps=pose.fps, loop=pose.loop, duration=data["frames"] / pose.fps,
                          timing_mode="keep_fps")
        return finish_metadata(result, (width, height))
