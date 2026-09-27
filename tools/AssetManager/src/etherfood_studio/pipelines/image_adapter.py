"""Real PNG adapter using the established supervisor, input copies and output verification."""

import json
from pathlib import Path
import re
import sys

from PIL import Image

from ..domain.assets import require
from ..domain.graphics import proportional_size
from ..domain.models import StudioError
from ..domain.pipeline_recipes import BUILTINS, validate_parameters
from ..storage.blob_store import file_hash
from ..storage.sqlite_repository import canonical
from .base import CommandPlan, verify_files
from .image_processing import (
    TOOL_ROOT, expected_metadata, legacy_modules, material_mask, split_frames, validate_metadata,
)

PIPELINES = Path(__file__).parent


class ImageAdapter:
    identifier = "studio-image"

    def validate(self, parameters):
        require(isinstance(parameters, dict) and set(parameters) == {
            "operation", "settings", "profile", "source", "metadata", "resources", "plugin"},
            "Ungültiger Bildauftrag.")
        operation = parameters["operation"]
        require(isinstance(operation, str) and operation in {
            "prepare8", "prepare16", "frames", "scale", "color", "source_color", "plugin"},
            "Unbekannter Bildschritt.")
        require(isinstance(parameters["resources"], dict), "Ungültige Bildressourcen.")
        for name in [parameters["source"], *parameters["resources"].values()]:
            require(isinstance(name, str) and 0 < len(name) <= 160 and
                    not any(c in name for c in "/\\:\x00") and name not in {".", ".."},
                    "Bildschritte verwenden nur benannte Arbeitskopien.")
        settings, profile, plugin = (parameters[key] for key in ("settings", "profile", "plugin"))
        require(isinstance(settings, dict), "Ungültige Bildparameter.")
        resources = set(parameters["resources"])
        allowed = set()
        if operation in {"prepare8", "prepare16", "frames"}:
            definitions = BUILTINS[operation]["parameters"]
            if operation == "frames" and settings.get("timing") == "keep_duration":
                definitions = {k: v for k, v in definitions.items() if k != "fps"}
            validate_parameters(settings, definitions)
        elif operation == "scale":
            require(settings == {} and isinstance(profile, dict) and set(profile) == {
                "key", "method", "mode", "value", "colors", "parent"}, "Ungültiges Grafikprofil.")
            require(isinstance(profile["key"], str) and
                    re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", profile["key"]) is not None and
                    isinstance(profile["method"], str) and
                    profile["method"] in {"comic", "pixel", "pixel_low"} and
                    type(profile["colors"]) is int and 2 <= profile["colors"] <= 256,
                    "Unbekanntes Grafikverfahren/Profil oder ungültige Farbanzahl.")
            proportional_size(1, 1, profile["mode"], profile["value"])
            if profile["method"] == "pixel_low":
                require(isinstance(profile["parent"], str) and profile["parent"] != profile["key"],
                        "Pixel Low benötigt ein anderes Pixel-High-Profil als Eingang.")
            else:
                require(profile["parent"] is None, "Comic/Pixel High entstehen aus dem HD-Eingang.")
            if profile["method"] == "pixel":
                allowed = {"palette"} if resources else set()
        elif operation in {"color", "source_color"}:
            require(isinstance(settings.get("mode"), str) and
                    settings["mode"] in {"soft", "fixed", "material"}, "Ungültiger Farbmodus.")
            keys = ["mode", "strength", "max_distance"] if settings["mode"] == "soft" else ["mode"]
            definitions = {key: BUILTINS["color"]["parameters"][key] for key in keys}
            validate_parameters(settings, definitions)
            allowed = {"soft": {"reference"}, "fixed": {"palette"},
                       "material": {"materials", "mask", "original"}}[settings["mode"]]
        else:
            require(isinstance(plugin, dict) and set(plugin) == {
                "id", "version", "entry_point", "code_hash", "manifest_sha256", "dependencies"}
                and all(isinstance(v, str) for k, v in plugin.items() if k != "dependencies") and
                plugin["id"].startswith("python:") and bool(plugin["version"]) and
                plugin["entry_point"].isidentifier() and
                re.fullmatch(r"[a-f0-9]{64}", plugin["code_hash"]) is not None and
                re.fullmatch(r"[a-f0-9]{64}", plugin["manifest_sha256"]) is not None and
                isinstance(plugin["dependencies"], list) and len(plugin["dependencies"]) <= 16 and
                all(isinstance(v, str) and re.fullmatch(
                    r"[A-Za-z0-9][A-Za-z0-9_.-]*==[A-Za-z0-9][A-Za-z0-9_.+-]*", v)
                    for v in plugin["dependencies"]),
                "Ungültiger Python-Erweiterungsvertrag.")
        require(resources == allowed, "Fehlende oder nicht unterstützte Eingangsressourcen.")
        require(operation == "scale" or profile is None, "Grafikprofil ohne Skalierung.")
        require(operation == "plugin" or plugin is None, "Python-Code ohne Erweiterungsschritt.")
        if parameters["metadata"] is None:
            require(parameters["source"] == "upstream.png", "Metadaten des Bildeingangs fehlen.")
        else:
            validate_metadata(parameters["metadata"])
        try:
            require(len(canonical(parameters)) <= 65536, "Zu große Bildparameter.")
        except (ValueError, TypeError) as error:
            raise StudioError("validation", "Bildparameter sind kein endliches JSON.") from error

    def validate_inputs(self, parameters, inputs):
        expected = {parameters["source"], *parameters["resources"].values()}
        if parameters["metadata"] is None:
            expected.add("upstream.json")
        else:
            source = next((item for item in inputs if item.name == parameters["source"]), None)
            require(source is not None and source.sha256 == parameters["metadata"]["source_sha256"]
                    and source.revision_id == parameters["metadata"]["source_revision"],
                    "Bildeingang stimmt nicht mit der eingefrorenen Quellrevision überein.")
        if parameters["plugin"]:
            expected.add("plugin.py")
        require(expected == {item.name for item in inputs},
                "Arbeitskopien stimmen nicht mit den erforderlichen Bildeingängen überein.")

    def plan(self, workspace, parameters):
        self.validate(parameters)
        script = PIPELINES / "image_worker.py"
        sources = list(PIPELINES.glob("*.py")) + list((PIPELINES.parent / "domain").glob("*.py"))
        sources += list((TOOL_ROOT / "PiplineToos").glob("*.py"))
        sources += list((TOOL_ROOT / "2-SpritesheetResolution-Pipline").glob("*.py"))
        sources += [Path(Image.__file__), Path(Image.core.__file__), Path(sys.executable)]
        hashes = tuple((str(p), file_hash(p)) for p in sorted(set(sources)))
        return CommandPlan((sys.executable, "-I", "-B", str(script), str(workspace)),
                           ("image.png", "metadata.json"), hashes)

    def execute(self, request, workspace):
        plan = self.plan(workspace, json.loads(request.parameters))
        require(plan.argv == request.argv and plan.outputs == request.outputs and
                plan.tool_hashes == request.tool_hashes,
                "Bildwerkzeuge seit Dry-run verändert; erneut planen.")
        return plan.argv

    def verify(self, request, workspace):
        parameters = json.loads(request.parameters)
        self.validate(parameters)
        self.validate_inputs(parameters, request.inputs)
        for item in request.inputs:
            path = workspace / "input" / item.name
            require(path.is_file() and not path.is_symlink() and
                    path.stat().st_size == item.length and file_hash(path) == item.sha256,
                    "Arbeitskopie während der Verarbeitung verändert.")
        output = workspace / "output"
        files = verify_files(output, request.outputs)
        require((output / "metadata.json").stat().st_size <= 65536,
                "Bildmetadaten überschreiten die Größe des Ergebnisvertrags.")
        meta = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
        require(isinstance(meta, dict) and meta.get("contract") == "studio-image-result-v1" and
                meta.get("image_sha256") == file_hash(output / "image.png"),
                "Bild-/Metadatenbindung ist ungültig.")
        source, incoming, resources = load_input(workspace, parameters)
        expected = expected_metadata(source, incoming, parameters["operation"],
                                     parameters["settings"], parameters["profile"])
        claimed = {k: v for k, v in meta.items() if k not in {"contract", "image_sha256"}}
        require(claimed == expected,
                "Ergebnis widerspricht der geplanten Geometrie, Frameauswahl oder Quellbindung.")
        with Image.open(output / "image.png") as image, source:
            require(image.format == "PNG" and image.mode == "RGBA" and
                    getattr(image, "n_frames", 1) == 1,
                    "PNG-Ergebnis passt nicht zu Raster/Frames/Geometrie.")
            validate_metadata(meta, image.size)
            image.load()
            verify_pixels(image, source, incoming, meta, parameters, resources)
        return files


def load_input(workspace, parameters):
    incoming = workspace / "input"
    _, _, _, _, soft, _ = legacy_modules()
    image = soft.load_png(incoming / parameters["source"])
    meta = parameters["metadata"]
    if meta is None:
        path = incoming / "upstream.json"
        require(path.stat().st_size <= 65536, "Zu große Eingangsmetadaten.")
        meta = json.loads(path.read_text(encoding="utf-8"))
        require(isinstance(meta, dict) and meta.get("contract") == "studio-image-result-v1" and
                meta.get("image_sha256") == file_hash(incoming / parameters["source"]),
                "Eingangsmetadaten gehören nicht zu diesem Bild.")
    validate_metadata(meta, image.size)
    resources = {key: incoming / name for key, name in parameters["resources"].items()}
    return image, meta, resources


def verify_pixels(image, source, incoming, meta, parameters, resources):
    """Check exact-frame/palette/alpha invariants without repeating expensive color fitting."""
    grid, selection, _, _, soft, exact = legacy_modules()
    operation, settings, profile = (parameters[key] for key in ("operation", "settings", "profile"))
    frames = split_frames(source, incoming["grid"])
    expected = None
    if operation.startswith("prepare"):
        box = grid.get_common_content_box(frames)
        expected = grid.pack_frames([f.crop(box) for f in frames], tuple(meta["grid"]),
                                    optimize=False)
    elif operation == "frames":
        frames = [frames[i] for i in selection.uniform_indices(len(frames), settings["frames"])]
        expected = grid.pack_frames(frames, tuple(meta["grid"]), optimize=False)
    elif operation == "scale" and profile["method"] == "pixel_low":
        frames = [f.resize(tuple(meta["frame_size"]), Image.Resampling.NEAREST) for f in frames]
        expected = grid.pack_frames(frames, tuple(meta["grid"]), optimize=False)
    elif operation == "scale" and profile["method"] == "comic" and source.size == image.size:
        expected = source
    if expected is not None:
        require(image.tobytes() == expected.tobytes(),
                "Frame-/Pixelableitung entspricht nicht dem Plan.")
    if operation in {"color", "source_color"}:
        soft.verify_pixels(source, image)
        if settings["mode"] == "fixed":
            exact.verify_palette(image, exact.load_palette(resources["palette"]))
        elif settings["mode"] == "material":
            palette = exact.load_material_profile(resources["materials"])
            with material_mask(resources["mask"], resources["original"], meta, palette) as mask:
                exact.verify_palette(image, palette, mask)
    if operation == "scale" and profile["method"] == "pixel":
        require(not any(image.getchannel("A").histogram()[1:255]),
                "Pixel High benötigt binäres Alpha.")
        if "palette" in resources:
            exact.verify_palette(image, exact.load_palette(resources["palette"]))
        else:
            require(image.convert("RGB").getcolors(profile["colors"]) is not None,
                    "Pixel High überschreitet die angeforderte Farbanzahl.")
