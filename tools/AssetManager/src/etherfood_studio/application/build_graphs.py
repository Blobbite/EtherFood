"""Project-to-build projection. Missing future image adapters remain explicitly blocked."""

from pathlib import Path

from ..domain.builds import (
    BuildGraph, BuildNode, ContentInput, Dependency, OutputSpec, STAGES, VariantTarget,
)
from ..domain.sources import SourceKey
from ..domain.models import StudioError
from ..pipelines.adapters import adapter_for
from ..storage.blob_store import file_hash
from ..storage.sqlite_repository import canonical
from .asset_service import AssetService
from .source_import import SourceImportService


def diagnostic_graph() -> BuildGraph:
    """Exercise all nine stages with JSON fixtures, never with artistic output claims."""
    tools = adapter_for("diagnostic").plan(Path("."), {}).tool_hashes
    nodes = []
    for index, stage in enumerate(STAGES):
        dependencies = (Dependency(STAGES[index - 1], "result.json", "diagnostic"),) \
            if index else ()
        nodes.append(BuildNode(stage, stage, dependencies=dependencies,
                               outputs=(OutputSpec("result.json", "diagnostic"),
                                        OutputSpec("report.json", "report")),
                               adapter="diagnostic", tools=tools))
    return BuildGraph(tuple(nodes), (VariantTarget("Diagnosekette", "package"),))


def asset_graph(project, identifier: str, *, cancelled=lambda: False) -> BuildGraph:
    assets = AssetService(project)
    definition = assets.definition(identifier)
    sources = SourceImportService(assets)
    active = sources.active(identifier)
    nodes, variants, by_key, verified_sources = [], [], {}, {}
    poses = {p.id: p for p in definition.poses}
    materials = "supports_materials" in definition.capabilities

    def add(key, stage, kind, dependencies=(), **kwargs):
        if key not in by_key:
            node = BuildNode(key, stage, dependencies=tuple(dependencies),
                             outputs=(OutputSpec("artifact.json", kind),), **kwargs)
            nodes.append(node)
            by_key[key] = node
        return Dependency(key, "artifact.json", kind)

    profile = add("profile", "profile", "palette", blockers=(
        "Farbverarbeitung benötigt eine zugewiesene Projekt-Pipeline mit Farbprofil",
            )) if materials else None
    for variant in definition.expected():
        if cancelled():
            raise StudioError("cancelled", "Dry-run abgebrochen; keine Änderungen geschrieben.")
        pose = poses.get(variant.pose_id)
        source_kind = pose.source_kind if pose else "single_image"
        key = SourceKey(variant.pose_id, variant.direction, source_kind)
        source = active.get(key)
        branch = f"{variant.pose_id or 'static'}/{variant.direction or 'none'}"
        problems, inputs, source_ids = [], (), ()
        metadata = {}
        if source:
            data = source.data
            path = sources.store.path_for(data["sha256"])
            if source.id not in verified_sources:
                try:
                    valid = (data.get("verification") == "verified" and path.is_file() and
                             path.stat().st_size == data["length"] and
                             file_hash(path) == data["sha256"])
                except OSError:
                    valid = False
                verified_sources[source.id] = valid
            valid = verified_sources[source.id]
            if not valid:
                problems.append("Original fehlt, ist ungeprüft oder hat einen falschen Hash")
            inputs = (ContentInput("source", "image", data["sha256"], source.id),)
            source_ids = (source.id,)
            metadata = {name: data[name] for name in ("grid", "frames", "width", "height")}
        else:
            problems.append("Benötigte Quelle fehlt")
        upstream = []
        if materials:
            mask = add(branch + "/mask", "maskcheck", "mask_report", inputs=inputs,
                       blockers=("Materialmasken im Asset-Menü prüfen; "
                                 "Ausführung über eine Projekt-Pipeline",))
            upstream = [profile, mask]
        color = add(branch + "/color", "color", "image", upstream, inputs=inputs,
                    source_ids=source_ids, parameters=canonical(metadata), blockers=tuple(problems))
        frame_key = branch + "/frames/" + str(variant.frames or 1)
        animated = source_kind == "spritesheet"
        frames = add(frame_key, "frames", "image", [color], required=animated,
                     parameters=canonical({"frames": variant.frames, "fps": pose.fps if pose
                                           else None, "loop": pose.loop if pose else False}))
        geometry = add(frame_key + "/geometry", "geometry", "image",
                       [frames if animated else color], parameters=canonical({
                           "anchor": pose.anchor if pose else (0.5, 1.0)}))
        output_key = frame_key + "/" + variant.graphics
        scale = add(output_key + "/scale", "scale", "image", [geometry],
                    parameters=canonical({"graphics": variant.graphics}))
        preview = add(output_key + "/preview", "preview", "preview", [scale])
        checks = add(output_key + "/checks", "checks", "check_report", [scale, preview])
        package = add(output_key + "/package", "package", "package", [scale, checks])
        variants.append(VariantTarget(canonical(variant.to_data()), package.node))
    expected = set(definition.expected())
    for variant in assets.matrix(identifier):
        if variant not in expected:
            variants.append(VariantTarget(canonical(variant.to_data()), None, False))
    return BuildGraph(tuple(nodes), tuple(variants))
