"""Exakte sRGB-Paletten und Materialfarbreihen; keine Mischung oder LUT-Interpolation.

Labelmasken sind 8-Bit-L/P-PNGs. Ihre Pixelwerte sind Material-IDs, keine Farben.
Raster und Quellhash binden jede Maske an ein konkretes Original-Sheet.
"""
from __future__ import annotations

from functools import lru_cache
import json
import math
from pathlib import Path
import re
import warnings

from PIL import Image, ImageChops, PngImagePlugin

import PyImgColorMatch as color

FIXED_FORMAT = "pyimg-fixed-palette"
MATERIAL_FORMAT = "pyimg-material-colors"
DEFINITIONS_FORMAT = "pyimg-material-definitions"
VERSION = 1
FIXED_METHOD = "Lab_D65_nearest_palette_v1"
MATERIAL_METHOD = "Lab_D65_nearest_material_lightness_v1"
MASK_VERSION = "pyimg_mask_version"
MASK_GRID = "pyimg_grid"
MASK_SOURCE = "pyimg_source_sha256"


def read_json(path):
    path = Path(path)
    if path.stat().st_size > 2_000_000:
        raise ValueError(f"Profil zu groß: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Profil muss ein JSON-Objekt sein: {path}")
    return value


def validate_colors(colors, where):
    if not isinstance(colors, list) or not 1 <= len(colors) <= 256 or any(
            not isinstance(c, list) or len(c) != 3 or any(
                type(v) is not int or not 0 <= v <= 255 for v in c) for c in colors):
        raise ValueError(f"{where}: 1..256 RGB-Tripel mit ganzen Zahlen 0..255 erforderlich.")
    if len({tuple(c) for c in colors}) != len(colors):
        raise ValueError(f"{where}: doppelte RGB-Farben entfernen.")


def validate_references(refs):
    if not isinstance(refs, list) or len(refs) != 8 or any(not isinstance(r, dict) for r in refs):
        raise ValueError("Profil benötigt Herkunftsdaten aller acht Stand-Richtungen.")
    if [r.get("direction") for r in refs] != list(color.DIRECTIONS):
        raise ValueError("Stand-Richtungen im Profil: N, NO, O, SO, S, SW, W, NW erforderlich.")
    frame_counts = set()
    for ref in refs:
        grid = ref.get("grid")
        size = ref.get("size")
        if (not isinstance(ref.get("path"), str) or not ref["path"]
                or not isinstance(ref.get("sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", ref["sha256"])
                or not isinstance(grid, list) or len(grid) != 2
                or any(type(n) is not int or n < 1 for n in grid)
                or math.prod(grid) > 64
                or not isinstance(size, list) or len(size) != 2
                or any(type(n) is not int or n < 1 for n in size)):
            raise ValueError("Ungültige Stand-Herkunft: Pfad, SHA-256, Größe und Raster erforderlich.")
        list(color.frame_boxes(size, grid))
        if type(ref.get("frames")) is not int or ref["frames"] != math.prod(grid):
            raise ValueError("Framezahl widerspricht Stand-Raster im Profil.")
        frame_counts.add(ref["frames"])
    if len(frame_counts) != 1:
        raise ValueError("Alle Stand-Richtungen müssen dieselbe Framezahl haben.")


def validate_header(profile, expected):
    if (not isinstance(profile, dict) or profile.get("format") != expected
            or type(profile.get("version")) is not int or profile["version"] != VERSION):
        raise ValueError(f"Erwartetes Profilformat: {expected}, Version {VERSION}.")


def validate_materials(materials, definitions=False):
    if not isinstance(materials, list) or not 1 <= len(materials) <= 255:
        raise ValueError("1..255 Materialdefinitionen erforderlich.")
    ids, names = set(), set()
    for material in materials:
        if not isinstance(material, dict):
            raise ValueError("Jedes Material muss ein JSON-Objekt sein.")
        mid, name = material.get("id"), material.get("name")
        if type(mid) is not int or not 1 <= mid <= 255 or mid in ids:
            raise ValueError("Material-IDs müssen eindeutig zwischen 1 und 255 liegen; 0 ist Hintergrund.")
        if not isinstance(name, str) or not name.strip() or name.casefold() in names:
            raise ValueError("Materialnamen müssen nichtleer und eindeutig sein.")
        ids.add(mid)
        names.add(name.casefold())
        if definitions:
            levels = material.get("levels")
            if type(levels) is not int or not 1 <= levels <= 256:
                raise ValueError(f"Material {name}: levels muss zwischen 1 und 256 liegen.")
        else:
            validate_colors(material.get("colors"), f"Material {name}")


def load_palette(path):
    profile = read_json(path)
    validate_header(profile, FIXED_FORMAT)
    if profile.get("color_space") != "sRGB":
        raise ValueError("Festfarbenprofil benötigt color_space: sRGB.")
    validate_colors(profile.get("colors"), "Festpalette")
    validate_references(profile.get("references"))
    return profile


def load_material_profile(path):
    profile = read_json(path)
    validate_header(profile, MATERIAL_FORMAT)
    if profile.get("color_space") != "sRGB":
        raise ValueError("Materialprofil benötigt color_space: sRGB.")
    validate_materials(profile.get("materials"))
    validate_references(profile.get("references"))
    return profile


def load_definitions(path):
    definitions = read_json(path)
    validate_header(definitions, DEFINITIONS_FORMAT)
    validate_materials(definitions.get("materials"), definitions=True)
    return definitions


def make_palette(reference_profile):
    """Konkrete gemeinsame 64er-Palette des bestehenden Stand-Profils festschreiben."""
    validate_references(reference_profile.get("references"))
    colors = [list(c) for c in dict.fromkeys(tuple(c) for c in reference_profile["pixel_palette"])]
    validate_colors(colors, "Stand-Palette")
    return {"format": FIXED_FORMAT, "version": VERSION, "color_space": "sRGB",
            "colors": colors, "references": reference_profile["references"],
            "derivation": {"reference_profile_sha256": color.fingerprint(reference_profile),
                           "sampling": reference_profile["sampling"],
                           "palette": "pixel_palette; up to 64 colors; review visually"}}


def mask_metadata(grid, source_sha256):
    info = PngImagePlugin.PngInfo()
    info.add_text(MASK_VERSION, "1")
    info.add_text(MASK_GRID, f"{grid[0]}x{grid[1]}")
    info.add_text(MASK_SOURCE, source_sha256)
    return info


def mask_error(region, path, reason, grid):
    bounds = region.getbbox()
    if bounds:
        x, y = bounds[:2]
        fw, fh = region.width // grid[0], region.height // grid[1]
        frame = y // fh * grid[0] + x // fw + 1
        count = region.histogram()[255]
        raise ValueError(f"Maske {path}: {reason}; {count} Pixel, erster Bereich bei "
                         f"({x}, {y}), Frame {frame}. Materialmarkierungen prüfen.")


def validate_labels(mask, image, materials, path="<Maske>", grid=(1, 1)):
    if mask.mode != "L" or mask.size != image.size:
        raise ValueError(f"Maske {path}: Größe oder Labelmodus passt nicht zur Quelle.")
    ids = {m["id"] for m in materials}
    histogram = mask.histogram()
    unknown = [i for i, n in enumerate(histogram) if n and i != 0 and i not in ids]
    if unknown:
        raise ValueError(f"Maske {path}: unbekannte Material-IDs {unknown}.")
    with image.getchannel("A") as alpha:
        visible = alpha.point([0] + [255]*255)
    with visible, mask.point([255] + [0]*255) as unlabelled:
        with ImageChops.multiply(visible, unlabelled) as missing:
            mask_error(missing, path, "fehlende Zuordnung (ID 0 bei Alpha > 0)", grid)
        with ImageChops.invert(visible) as hidden, ImageChops.invert(unlabelled) as labelled:
            with ImageChops.multiply(hidden, labelled) as conflict:
                mask_error(conflict, path, "Material auf unsichtbarem Hintergrund (dort ID 0 verwenden)", grid)
    return {str(i): n for i, n in enumerate(histogram) if i and n}


def load_mask(path, image, grid, materials, source_sha256):
    path = Path(path)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError(f"Maskenpfad darf keine symbolischen Links enthalten: {path}")
    if not path.is_file():
        raise ValueError(f"Materialmaske fehlt: {path}. Mit --prepare-masks Vorlagen erstellen und markieren.")
    with path.open("rb") as stream:
        header = stream.read(26)
    if len(header) < 26 or not header.startswith(b"\x89PNG\r\n\x1a\n") or header[24] != 8:
        raise ValueError(f"Maske muss eine 8-Bit-Label-PNG sein: {path}")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as source:
            if (source.mode not in {"L", "P"} or getattr(source, "n_frames", 1) != 1
                    or source.size != image.size or "transparency" in source.info):
                raise ValueError(f"Maske {path}: statische L/P-Label-PNG ohne Transparenz in Größe {image.size} erforderlich.")
            expected = {MASK_VERSION: "1", MASK_GRID: f"{grid[0]}x{grid[1]}", MASK_SOURCE: source_sha256}
            for key, value in expected.items():
                if source.info.get(key) != value:
                    raise ValueError(f"Maske {path}: {key} fehlt oder passt nicht zur Quelle "
                                     f"(erwartet: {value}). Raster, Framefolge und Quellbindung prüfen.")
            # P-Pixel sind Indizes, NICHT per Graustufen-Konvertierung zu lesende RGB-Farben.
            mask = Image.frombytes("L", source.size, source.tobytes())
    try:
        validate_labels(mask, image, materials, path, grid)
    except Exception:
        mask.close()
        raise
    return mask


def mask_preview(mask, image, materials):
    """Anschauliche ID-Farben, unabhängig von den tatsächlichen Materialfarben."""
    palette = [0]*768
    for material in materials:
        mid = material["id"]
        palette[mid*3:mid*3+3] = preview_color(mid)
    with Image.frombytes("P", mask.size, mask.tobytes()) as indexed:
        indexed.putpalette(palette)
        result = indexed.convert("RGBA")
    with image.getchannel("A") as alpha:
        result.putalpha(alpha)
    return result


def preview_color(mid):
    # Nur Legendenfarben für Label-IDs, keine automatisch erkannten Zielfarben.
    return [(mid*97) % 192 + 48, (mid*57) % 192 + 48, (mid*137) % 192 + 48]


class PaletteMapper:
    def __init__(self, colors, lightness=False):
        validate_colors(colors, "Zielpalette")
        self.colors = [bytes(c) for c in colors]
        self.lab = [color.rgb_to_lab(tuple(v/255 for v in c)) for c in colors]
        self.lightness = lightness
        self.nearest = lru_cache(maxsize=65536)(self._nearest)

    def _nearest(self, rgb):
        lab = color.rgb_to_lab(tuple(v/255 for v in rgb))
        if self.lightness:
            index = min(range(len(self.lab)), key=lambda i: (self.lab[i][0]-lab[0])**2)
        else:
            index = min(range(len(self.lab)), key=lambda i: sum((a-b)**2 for a, b in zip(self.lab[i], lab)))
        # min wählt bei Gleichstand den ersten Eintrag der verbindlichen Profilreihenfolge.
        return self.colors[index]


class FixedMatcher:
    def __init__(self, profile):
        self.mapper = PaletteMapper(profile["colors"])

    def apply(self, image):
        return apply_exact(image, {1: self.mapper})


class MaterialMatcher:
    def __init__(self, profile):
        self.materials = profile["materials"]
        validate_materials(self.materials)
        self.mappers = {m["id"]: PaletteMapper(m["colors"], lightness=True) for m in self.materials}

    def apply(self, image, mask):
        validate_labels(mask, image, self.materials)
        return apply_exact(image, self.mappers, mask)


def apply_exact(image, mappers, mask=None):
    if image.mode != "RGBA":
        raise ValueError("Exakte Abbildung benötigt ein nach sRGB normalisiertes RGBA-Bild.")
    raw = image.tobytes()
    result = bytearray(raw)
    labels = mask.tobytes() if mask is not None else None
    for pixel, alpha in enumerate(memoryview(raw)[3::4]):
        if alpha:
            offset = pixel*4
            mapper = mappers[labels[pixel] if labels is not None else 1]
            result[offset:offset+3] = mapper.nearest(raw[offset:offset+3])
    return Image.frombytes("RGBA", image.size, bytes(result))


def verify_palette(image, profile, mask=None):
    """Unabhängige Zugehörigkeitsprüfung; Referenzkopien explizit nicht hier prüfen."""
    if mask is None:
        allowed = {bytes(c) for c in profile["colors"]}
        actual = {bytes(c[:3]) for _, c in image.getcolors(image.width*image.height) if c[3]}
        if not actual <= allowed:
            raise ValueError("Festfarbenprüfung fehlgeschlagen: RGB außerhalb der Zielpalette.")
        return {"palette_exact": True, "used_colors": len(actual)}
    allowed = {m["id"]: {bytes(c) for c in m["colors"]} for m in profile["materials"]}
    labels, raw = mask.tobytes(), image.tobytes()
    used = set()
    for pixel, alpha in enumerate(memoryview(raw)[3::4]):
        if alpha:
            key = labels[pixel], raw[pixel*4:pixel*4+3]
            if key not in used:
                if key[1] not in allowed.get(key[0], set()):
                    raise ValueError(f"Materialprüfung fehlgeschlagen: RGB außerhalb Material-ID {key[0]}.")
                used.add(key)
    return {"material_palette_exact": True, "used_material_colors": len(used),
            "unassigned_pixels": 0, "material_labels_visually_verified": False}


def make_material_profile(references, definitions, masks, root):
    """Farbreihen nur aus tatsächlich gelabelten Stand-Pixeln bilden.

    Jeder Frame, in dem ein Material sichtbar ist, liefert gleich viele Samples.
    Nicht sichtbare Materialien liefern keine erfundenen Farben.
    """
    validate_materials(definitions["materials"], definitions=True)
    if [d for _, d, _ in references] != list(color.DIRECTIONS):
        raise ValueError("Alle acht Stand-Richtungen erforderlich.")
    records, mask_records = [], []
    samples = {m["id"]: [] for m in definitions["materials"]}
    for path, direction, grid in references:
        try:
            relative = path.relative_to(root)
        except ValueError as exc:
            raise ValueError("Zum Materialexport müssen die Stand-Referenzen innerhalb QUELLE liegen.") from exc
        source_hash = color.sha256(path)
        mask_path = masks / relative
        with color.load_png(path) as image, load_mask(
                mask_path, image, grid, definitions["materials"], source_hash) as mask:
            records.append({"path": str(path), "direction": direction, "sha256": source_hash,
                            "size": list(image.size), "grid": list(grid), "frames": math.prod(grid),
                            "color_management": image.info["color_management"]})
            mask_records.append({"path": str(relative), "sha256": color.sha256(mask_path)})
            for material in definitions["materials"]:
                mid = material["id"]
                with mask.point([255 if i == mid else 0 for i in range(256)]) as selected:
                    with image.getchannel("A") as alpha, ImageChops.multiply(alpha, selected) as masked_alpha:
                        with image.copy() as material_image:
                            material_image.putalpha(masked_alpha)
                            for box in color.frame_boxes(image.size, grid):
                                with material_image.crop(box) as frame:
                                    with frame.getchannel("A") as frame_alpha:
                                        present = frame_alpha.getbbox() is not None
                                    if present:
                                        samples[mid].extend(color.balanced_samples(frame, (1, 1)))
    validate_references(records)
    materials = []
    for material in definitions["materials"]:
        values = samples[material["id"]]
        if not values:
            raise ValueError(f"Keine markierten Stand-Pixel für Material {material['name']}.")
        colors = color.sampled_palette(values, material["levels"])
        colors = [list(c) for c in dict.fromkeys(tuple(c) for c in colors)]
        colors.sort(key=lambda c: (color.rgb_to_lab(tuple(v/255 for v in c))[0], c))
        materials.append({"id": material["id"], "name": material["name"], "colors": colors})
    return {"format": MATERIAL_FORMAT, "version": VERSION, "color_space": "sRGB",
            "references": records, "materials": materials,
            "derivation": {"sampling": "equal_weight_per_visible_material_frame; alpha_weighted",
                           "definitions_sha256": color.fingerprint(definitions),
                           "reference_masks": mask_records, "visual_review_required": True}}
