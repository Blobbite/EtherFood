"""Gemeinsamer Referenz-Farbabgleich für PNGs; Python/Pillow, ohne Frame-Verschiebung.

Das Profil beschreibt Farbbereiche, keine erkannten Körperteile. Gleiche RGB-Werte
werden in jedem Bild gleich abgebildet. Die interpolierte Farbtabelle erhält
Abstufungen; es findet keine Palettenquantisierung der HD-Ausgaben statt.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import io
import json
import math
import os
from pathlib import Path
import tempfile
import warnings

from PIL import Image, ImageChops, ImageCms, ImageFilter

FORMAT = "pyimg-reference-colors"
VERSION = 1
METHOD = "Lab_D65_chroma_projection_smooth_lut_v1"
MAX_PIXELS = 64_000_000
DIRECTIONS = ("N", "NO", "O", "SO", "S", "SW", "W", "NW")
SAMPLES_PER_FRAME = 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def load_png(path: Path) -> Image.Image:
    """8-Bit-PNG in sRGB lesen; ICC farbmetrisch umrechnen, Alpha/RGB bei Alpha=0 erhalten."""
    if path.is_symlink():
        raise ValueError(f"Bild ist ein symbolischer Link: {path}")
    with path.open("rb") as stream:
        header = stream.read(26)
    if not header.startswith(b"\x89PNG\r\n\x1a\n") or len(header) < 26:
        raise ValueError(f"Keine PNG-Datei: {path}")
    if header[24] == 16:
        raise ValueError(f"16-Bit-PNG zuerst ausdrücklich als 8-Bit-sRGB exportieren: {path}")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as source:
            if getattr(source, "n_frames", 1) != 1 or source.width * source.height > MAX_PIXELS:
                raise ValueError(f"Statisches PNG mit höchstens {MAX_PIXELS} Pixeln erforderlich: {path}")
            icc = source.info.get("icc_profile")
            if not icc and "srgb" not in source.info:
                gamma = source.info.get("gamma", 0.45455)
                chrom = source.info.get("chromaticity", (0.3127, 0.3290, 0.64, 0.33, 0.30, 0.60, 0.15, 0.06))
                expected = (0.3127, 0.3290, 0.64, 0.33, 0.30, 0.60, 0.15, 0.06)
                if abs(gamma - 0.45455) > 0.005 or len(chrom) != 8 or any(
                        abs(a-b) > 0.002 for a, b in zip(chrom, expected)):
                    raise ValueError(f"Abweichendes PNG-Farbprofil: zuerst nach sRGB konvertieren: {path}")
            image = source.convert("RGBA")
            management = "sRGB" if "srgb" in source.info else "untagged_assumed_sRGB"
            if icc:
                try:
                    profile = ImageCms.ImageCmsProfile(io.BytesIO(icc))
                    base = source.convert("L") if source.mode in {"L", "LA", "1"} else source.convert("RGB")
                    converted = ImageCms.profileToProfile(base, profile, ImageCms.createProfile("sRGB"),
                                                          renderingIntent=1, outputMode="RGB").convert("RGBA")
                    alpha = image.getchannel("A")
                    converted.putalpha(alpha)
                    converted.paste(image, (0, 0), alpha.point([255]+[0]*255))
                    image.close()
                    image = converted
                    management = "ICC_to_sRGB_relative_colorimetric"
                except (OSError, ValueError, ImageCms.PyCMSError) as exc:
                    raise ValueError(f"ICC-Profil nicht nach sRGB konvertierbar: {path}: {exc}") from exc
            image.info.clear()
            image.info["color_management"] = management
            return image


def frame_boxes(size, grid):
    width, height = size
    columns, rows = grid
    if columns < 1 or rows < 1 or width % columns or height % rows:
        raise ValueError(f"Bildgröße {size} passt nicht zu Raster {columns}x{rows}.")
    fw, fh = width // columns, height // rows
    for row in range(rows):
        for column in range(columns):
            yield column * fw, row * fh, (column+1) * fw, (row+1) * fh


def balanced_samples(image: Image.Image, grid, count=SAMPLES_PER_FRAME):
    """Jeder nichtleere Frame liefert gleich viele alpha-gewichtete Originalfarben.

    Kein Resize/Compositing: Teiltransparenz zählt anteilig, unsichtbares RGB nie.
    Leere Referenzframes sind ein Fehler, damit Richtungen gleich gewichtet bleiben.
    """
    samples = []
    for index, box in enumerate(frame_boxes(image.size, grid)):
        with image.crop(box) as frame:
            weights = Counter()
            for n, rgba in frame.getcolors(frame.width * frame.height) or []:
                if rgba[3]:
                    weights[rgba[:3]] += n * rgba[3]
        total = sum(weights.values())
        if not total:
            raise ValueError(f"Leerer Referenzframe {index + 1}.")
        items = iter(sorted(weights.items()))
        rgb, cumulative = next(items)
        for i in range(count):
            threshold = (i + 0.5) * total / count
            while cumulative < threshold:
                rgb, weight = next(items)
                cumulative += weight
            samples.append(rgb)
    return samples


def sampled_palette(samples, colors):
    with Image.new("RGB", (len(samples), 1)) as strip:
        strip.putdata(samples)
        with strip.quantize(colors=colors, method=Image.Quantize.MEDIANCUT,
                            dither=Image.Dither.NONE) as indexed:
            raw = indexed.getpalette()
            return [raw[i*3:i*3+3] for _, i in sorted(indexed.getcolors(), key=lambda x: (-x[0], x[1]))]


def make_profile(references):
    """references: acht (Pfad, Richtung, Raster)-Tripel in Richtungsreihenfolge."""
    if [direction for _, direction, _ in references] != list(DIRECTIONS):
        raise ValueError("Referenz benötigt genau N, NO, O, SO, S, SW, W, NW.")
    samples, records = [], []
    counts = {math.prod(grid) for _, _, grid in references}
    if len(counts) != 1:
        raise ValueError("Alle Referenzrichtungen müssen dieselbe Framezahl haben.")
    for path, direction, grid in references:
        with load_png(path) as image:
            samples.extend(balanced_samples(image, grid))
            records.append({"path": str(path), "direction": direction, "sha256": sha256(path),
                            "size": list(image.size), "grid": list(grid), "frames": math.prod(grid),
                            "color_management": image.info["color_management"]})
    return {"format": FORMAT, "version": VERSION, "method": METHOD,
            "reference": "Stand: alle acht Richtungen und alle Frames",
            "sampling": "equal_direction_and_frame_weight; original_RGB; alpha_weighted",
            "samples_per_frame": SAMPLES_PER_FRAME, "references": records,
            "colors": sampled_palette(samples, 256),
            "pixel_palette": sampled_palette(samples, 64),
            "limits": "Farbähnlichkeit, keine Materialerkennung; ähnliche Materialien visuell prüfen."}


def load_profile(path: Path):
    if path.stat().st_size > 2_000_000:
        raise ValueError(f"Farbprofil zu groß: {path}")
    profile = json.loads(path.read_text(encoding="utf-8"))
    if (profile.get("format"), profile.get("version"), profile.get("method")) != (FORMAT, VERSION, METHOD):
        raise ValueError("Kein unterstütztes Referenz-Farbprofil; color_profile.json von PyImgTestColor ist ein anderes Format.")
    for key, limit in (("colors", 256), ("pixel_palette", 256)):
        colors = profile.get(key)
        if not isinstance(colors, list) or not 1 <= len(colors) <= limit or any(
                not isinstance(c, list) or len(c) != 3 or any(type(v) is not int or not 0 <= v <= 255 for v in c)
                for c in colors):
            raise ValueError(f"Ungültige Palette im Profil: {key}")
    refs = profile.get("references", [])
    if [r.get("direction") for r in refs] != list(DIRECTIONS) or any(
            not isinstance(r.get("path"), str) or not isinstance(r.get("sha256"), str)
            or len(r["sha256"]) != 64 or not isinstance(r.get("grid"), list)
            or len(r["grid"]) != 2 or any(type(n) is not int or n < 1 for n in r["grid"])
            for r in refs):
        raise ValueError("Farbprofil enthält keine gültigen acht Referenzrichtungen.")
    return profile


def rgb_to_lab(rgb):
    # sRGB -> XYZ (D65) -> CIELAB; keine ICC-Lab(D50)-Werte mischen.
    r, g, b = (v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb)
    xyz = ((0.4124564*r + 0.3575761*g + 0.1804375*b) / 0.95047,
           0.2126729*r + 0.7151522*g + 0.0721750*b,
           (0.0193339*r + 0.1191920*g + 0.9503041*b) / 1.08883)
    x, y, z = (v ** (1/3) if v > (6/29)**3 else v / (3*(6/29)**2) + 4/29 for v in xyz)
    return 116*y - 16, 500*(x-y), 200*(y-z)


def lab_to_rgb(lab):
    light, a, b = lab
    fy = (light + 16) / 116
    x, y, z = (v**3 if v > 6/29 else 3*(6/29)**2*(v-4/29)
               for v in (fy+a/500, fy, fy-b/200))
    x, z = x * 0.95047, z * 1.08883
    values = (3.2404542*x - 1.5371385*y - 0.4985314*z,
              -0.9692660*x + 1.8760108*y + 0.0415560*z,
              0.0556434*x - 0.2040259*y + 1.0572252*z)
    return tuple(12.92*v if v <= 0.0031308 else 1.055*v**(1/2.4)-0.055 for v in values)


def smooth(value):
    t = min(1.0, max(0.0, value))
    return t*t*(3-2*t)


class ColorMatcher:
    """Ein fester Transform pro Referenzprofil, unabhängig von Bild/Frame-Inhalt."""

    def __init__(self, profile, strength=0.75, max_distance=18.0):
        if not math.isfinite(strength) or not 0 <= strength <= 1:
            raise ValueError("Stärke muss zwischen 0 und 1 liegen.")
        if not math.isfinite(max_distance) or not 1 <= max_distance <= 50:
            raise ValueError("Maximaler Farbabstand muss zwischen 1 und 50 liegen.")
        self.colors = [rgb_to_lab(tuple(v/255 for v in c)) for c in profile["colors"]]
        self.strength, self.max_distance = strength, max_distance
        self.lut = None

    def transform(self, r, g, b):
        light, a, bb = rgb_to_lab((r, g, b))
        target = min(self.colors, key=lambda c: (c[0]-light)**2 + (c[1]-a)**2 + (c[2]-bb)**2)
        distance = math.sqrt((target[0]-light)**2 + (target[1]-a)**2 + (target[2]-bb)**2)
        # Unbekannte Farbbereiche und fast neutrale Konturen behalten. Sanfte Grenzen.
        weight = (self.strength * smooth(distance - 1.0)
                  * (1-smooth((distance/self.max_distance - 0.65) / 0.35))
                  * smooth((math.hypot(a, bb)-3)/5) * smooth((light-2)/6))
        if weight <= 1e-8:
            return r, g, b
        # Lichtverlauf erhalten, Farbton und Farbigkeit zur Referenz ziehen.
        wanted = (light, a + weight*(target[1]-a), bb + weight*(target[2]-bb))
        result = lab_to_rgb(wanted)
        if min(result) < 0 or max(result) > 1:
            # Bei Gamutgrenzen schrittweise zur gültigen Ausgangsfarbe zurückgehen.
            low, high = 0.0, 1.0
            for _ in range(12):
                amount = (low+high)/2
                candidate = lab_to_rgb((light, a+amount*(wanted[1]-a), bb+amount*(wanted[2]-bb)))
                if min(candidate) >= 0 and max(candidate) <= 1:
                    low = amount
                else:
                    high = amount
            result = lab_to_rgb((light, a+low*(wanted[1]-a), bb+low*(wanted[2]-bb)))
        return tuple(min(1, max(0, v)) for v in result)

    def apply(self, image):
        if self.lut is None:
            self.lut = ImageFilter.Color3DLUT.generate(33, self.transform)
        # RGB-LUT wird interpoliert, keine feste HD-Palette. Alpha niemals filtern.
        alpha = image.getchannel("A")
        result = image.convert("RGB").filter(self.lut).convert("RGBA")
        result.putalpha(alpha)
        hidden = alpha.point([255] + [0]*255)
        result.paste(image, (0, 0), hidden)  # Auch unsichtbares RGB exakt erhalten.
        return result


def verify_pixels(before, after):
    if before.size != after.size or before.getchannel("A").tobytes() != after.getchannel("A").tobytes():
        raise ValueError("Prüfung fehlgeschlagen: Größe oder Transparenz verändert.")
    diff = ImageChops.difference(before.convert("RGB"), after.convert("RGB"))
    r, g, b = diff.split()
    maximum = ImageChops.lighter(ImageChops.lighter(r, g), b)
    hidden = before.getchannel("A").point([255] + [0]*255)
    if ImageChops.multiply(maximum, hidden).getbbox():
        raise ValueError("Prüfung fehlgeschlagen: unsichtbare RGB-Pixel verändert.")
    visible = before.getchannel("A").point([0]+[255]*255)
    changed = ImageChops.multiply(maximum.point([0]+[255]*255), visible)
    return {"size_and_alpha_unchanged": True, "hidden_rgb_unchanged": True,
            "visible_pixels": visible.histogram()[255], "changed_pixels": changed.histogram()[255],
            "max_rgb_channel_change": maximum.getextrema()[1]}


def save_png(image, path):
    fd, name = tempfile.mkstemp(prefix=".color-", suffix=".png", dir=path.parent)
    os.close(fd)
    try:
        image.save(name, format="PNG")
        with load_png(Path(name)) as saved:
            if saved.tobytes() != image.tobytes():
                raise ValueError(f"PNG-Prüfung fehlgeschlagen: {path}")
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def palette_image(profile):
    """Dieselbe Pixelpalette in jeder Resolution-Verarbeitung wiederverwenden."""
    palette = Image.new("P", (1, 1))
    colors = profile["pixel_palette"]
    padded = colors + [colors[-1]] * (256-len(colors))
    palette.putpalette([v for rgb in padded for v in rgb])
    return palette
