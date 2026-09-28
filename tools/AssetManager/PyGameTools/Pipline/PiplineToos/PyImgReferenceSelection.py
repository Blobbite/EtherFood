"""Explicit, hash-bound reference selection; v2 never changes the eight-direction v1 API."""

from copy import deepcopy
import json
import math
from pathlib import Path, PurePosixPath
import re

from PIL import ImageChops

SELECTION_FORMAT = "pyimg-reference-selection"
SAMPLING = "equal_reference_and_frame_weight; original_RGB; alpha_weighted"


def validate_references(references):
    if not isinstance(references, list) or not 1 <= len(references) <= 32:
        raise ValueError("Eine bis 32 tatsächliche Masterreferenzen auswählen.")
    identities, grids = set(), set()
    for ref in references:
        if not isinstance(ref, dict):
            raise ValueError("Referenz muss ein Objekt sein.")
        required = {"id", "source_revision", "path", "pose", "direction", "sha256",
                    "size", "grid", "frames"}
        if not required <= ref.keys():
            raise ValueError("Referenz benötigt alle Schemafelder, auch Pose/Richtung oder null.")
        for key in ("id", "source_revision", "path"):
            if not isinstance(ref.get(key), str) or not 0 < len(ref[key]) <= 256:
                raise ValueError("Referenz benötigt ID, Quellenrevision und relativen Bildpfad.")
        path = PurePosixPath(ref["path"])
        if (path.is_absolute() or any(p in {"", ".", ".."} for p in ref["path"].split("/"))
                or any(c in ref["path"] for c in "\\:\x00")):
            raise ValueError("Referenzpfad muss innerhalb des Referenzpakets liegen.")
        if ref["id"] in identities:
            raise ValueError("Doppelte Referenz-ID.")
        identities.add(ref["id"])
        if ref.get("direction") not in (None, "N", "NO", "O", "SO", "S", "SW", "W", "NW"):
            raise ValueError("Unbekannte Referenzrichtung.")
        if ref.get("pose") is not None and (not isinstance(ref["pose"], str)
                                            or not 0 < len(ref["pose"]) <= 256):
            raise ValueError("Ungültige Referenzpose.")
        if not isinstance(ref.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", ref[
            "sha256"]):
            raise ValueError("Referenz benötigt einen SHA-256-Quellhash.")
        for key in ("size", "grid"):
            if not isinstance(ref.get(key), list) or len(ref[key]) != 2 or any(
                    type(n) is not int or n < 1 for n in ref[key]):
                raise ValueError("Referenz benötigt positive Bildmaße und ein Raster.")
        if (math.prod(ref["grid"]) > 64 or math.prod(ref["size"]) > 32_000_000
                or any(ref["size"][i] % ref["grid"][i] for i in (0, 1))
                or type(ref.get("frames")) is not int or ref["frames"] != math.prod(ref["grid"])):
            raise ValueError("Referenzgröße, Raster und Framezahl widersprechen sich.")
        grids.add(tuple(ref["grid"]))
    if len(grids) != 1:
        raise ValueError(
            "Gemischte Referenzraster werden in v2 nicht unterstützt; gleiche Raster wählen.")


def validate_selection(value):
    if (not isinstance(value, dict) or value.get("format") != SELECTION_FORMAT
            or type(value.get("version")) is not int or value["version"] != 1
            or value.get("sampling") != SAMPLING):
        raise ValueError("Unbekannte Referenzauswahl-Version oder Gewichtungsregel.")
    if set(value) != {"format", "version", "references", "sampling", "preview_reference"}:
        raise ValueError("Referenzauswahl enthält fehlende oder unbekannte Schemafelder.")
    validate_references(value.get("references"))
    if value.get("preview_reference") not in {r["id"] for r in value["references"]}:
        raise ValueError(
            "Die Vorschau benötigt eine ausdrücklich gewählte Referenz aus der Auswahl.")


def validate_profile(profile):
    """The existing loaders validate color/material contents; this validates v2 provenance."""
    validate_selection({"format": SELECTION_FORMAT, "version": 1,
                        "references": profile.get("references"),
                        "sampling": profile.get("sampling"),
                        "preview_reference": profile.get("preview_reference")})


def load_selection(path):
    import PyImgColorMatch as color

    path = Path(path)
    if path.stat().st_size > 2_000_000:
        raise ValueError("Referenzauswahl überschreitet die Dateigrenze.")
    value = json.loads(path.read_text(encoding="utf-8"))
    validate_selection(value)
    root = path.parent.resolve()
    for ref in value["references"]:
        source = root / ref["path"]
        if any(p.is_symlink() for p in (source, *source.parents)) or not source.resolve(
            ).is_relative_to(root):
            raise ValueError("Unsicherer Referenzpfad.")
        if color.sha256(source) != ref["sha256"]:
            raise ValueError("Referenzquelle verändert: " + ref["path"])
    return value


def make_profile(selection, resolve, mode="soft", *, definitions=None, resolve_mask=None):
    """Resolve is a trusted API callback; manifests contain only data, never Python paths."""
    import PyImgColorMatch as color
    import PyImgFixedColors as exact

    validate_selection(selection)
    if mode not in {"soft", "fixed", "material"}:
        raise ValueError("Unbekannter Farbmodus.")
    if mode == "material":
        if definitions is None or resolve_mask is None:
            raise ValueError("Materialprofil benötigt Definitionen und gebundene Referenzmasken.")
        exact.validate_materials(definitions.get("materials"), definitions=True)
    samples, mask_records = [], []
    material_samples = {m["id"]: [] for m in definitions["materials"]} if mode == "material" else {}
    for ref in selection["references"]:
        path = Path(resolve(ref))
        if color.sha256(path) != ref["sha256"]:
            raise ValueError("Referenzquelle verändert: " + ref["path"])
        with color.load_png(path) as image:
            if list(image.size) != ref["size"]:
                raise ValueError("Bildgröße passt nicht zur gewählten Referenz.")
            if mode != "material":
                samples.extend(color.balanced_samples(image, ref["grid"]))
            else:
                mask_path = Path(resolve_mask(ref))
                mask_digest = color.sha256(mask_path)
                with exact.load_mask(mask_path, image, ref["grid"], definitions["materials"],
                                     ref["sha256"]) as mask:
                    for material in definitions["materials"]:
                        mid = material["id"]
                        with mask.point([255 if i == mid else 0 for i in range(256)]) as selected:
                            with image.getchannel("A") as alpha, ImageChops.multiply(alpha,
                                selected) as visible:
                                with image.copy() as labelled:
                                    labelled.putalpha(visible)
                                    for box in color.frame_boxes(image.size, ref["grid"]):
                                        with labelled.crop(box) as frame, frame.getchannel(
                                            "A") as channel:
                                            if channel.getbbox():
                                                material_samples[mid].extend(
                                                    color.balanced_samples(frame, (1, 1)))
                if color.sha256(mask_path) != mask_digest:
                    raise ValueError("Referenzmaske während Profilbildung verändert.")
                mask_records.append({"reference_id": ref["id"], "sha256": mask_digest})
        if color.sha256(path) != ref["sha256"]:
            raise ValueError("Referenz während Profilbildung verändert.")
    base = {"version": 2, "references": deepcopy(selection["references"]),
            "sampling": SAMPLING, "preview_reference": selection["preview_reference"]}
    if mode != "material":
        base.update(format=color.FORMAT, method=color.METHOD, colors=color.sampled_palette(
            samples, 256),
                    pixel_palette=color.sampled_palette(samples, 64),
                        samples_per_frame=color.SAMPLES_PER_FRAME)
        return exact.make_palette(base) if mode == "fixed" else base
    materials = []
    for material in definitions["materials"]:
        values = material_samples[material["id"]]
        if not values:
            raise ValueError("Keine gelabelten Referenzpixel für Material " + material["name"])
        colors = color.sampled_palette(values, material["levels"])
        colors.sort(key=lambda c: (color.rgb_to_lab(tuple(v / 255 for v in c))[0], c))
        materials.append({"id": material["id"], "name": material["name"], "colors": colors})
    return base | {"format": exact.MATERIAL_FORMAT, "color_space": "sRGB", "materials": materials,
                   "derivation": {"definitions_sha256": color.fingerprint(definitions),
                       "reference_masks": mask_records, "visual_review_required": True,
                       "sampling": "equal_weight_per_visible_material_frame; alpha_weighted"}}
