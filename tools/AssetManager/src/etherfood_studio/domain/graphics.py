"""Project-local graphics profiles and deterministic per-frame proportions."""

from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
import math
import re

from .models import StudioError

DEFAULT_PROFILES = (
    {"key": "comic_high", "name": "Comic High", "enabled": True, "method": "comic",
     "mode": "factor", "value": 1.0, "colors": 64, "parent": None},
    {"key": "comic_mid", "name": "Comic Mittel", "enabled": True, "method": "comic",
     "mode": "factor", "value": 0.5, "colors": 64, "parent": None},
    {"key": "comic_low", "name": "Comic Low", "enabled": True, "method": "comic",
     "mode": "factor", "value": 0.25, "colors": 64, "parent": None},
    {"key": "pixel_high", "name": "Pixel Art High", "enabled": True, "method": "pixel",
     "mode": "max_edge", "value": 128, "colors": 64, "parent": None},
    {"key": "pixel_low", "name": "Pixel Art Low", "enabled": True, "method": "pixel_low",
     "mode": "factor", "value": 0.9, "colors": 64, "parent": "pixel_high"},
)


def default_profiles() -> list[dict]:
    return deepcopy(list(DEFAULT_PROFILES))


def validate_profiles(values: list) -> dict[str, dict]:
    if not isinstance(values, list) or not 1 <= len(values) <= 64:
        raise StudioError("validation", "Ein bis 64 Projektprofile erforderlich.")
    result = {}
    for item in values:
        if not isinstance(item, dict) or set(item) != set(DEFAULT_PROFILES[0]):
            raise StudioError("validation", "Unbekannte/fehlende Grafikprofilfelder.")
        key = item["key"]
        if (not isinstance(key, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", key)
                or key in result):
            raise StudioError("validation", "Profil-Schlüssel ungültig oder doppelt.")
        if (not isinstance(item["name"], str) or not 0 < len(item["name"].strip()) <= 128
                or type(item["enabled"]) is not bool
                or not isinstance(item["method"], str)
                or item["method"] not in {"comic", "pixel", "pixel_low"}
                or type(item["colors"]) is not int or not 2 <= item["colors"] <= 256):
            raise StudioError("validation", "Ungültiger Profilname, Modus oder Farbzahl.")
        proportional_size(512, 256, item["mode"], item["value"])
        parent = item["parent"]
        if (item["method"] == "pixel_low") != isinstance(parent, str):
            raise StudioError("validation", "Pixel Low benötigt ein Pixel-High-Elternprofil.")
        if parent is not None and not isinstance(parent, str):
            raise StudioError("validation", "Ungültiger Profilbezug.")
        result[key] = deepcopy(item)
    for item in result.values():
        parent = result.get(item["parent"])
        if item["method"] == "pixel_low" and (not parent or parent["method"] != "pixel"):
            raise StudioError("validation", "Pixel Low benötigt ein vorhandenes Pixelprofil.")
    return result


def proportional_size(width: int, height: int, mode: str, value: float) -> tuple[int, int]:
    """Round positive dimensions half-up; maximum edge never upscales."""
    if type(width) is not int or type(height) is not int or min(width, height) < 1:
        raise StudioError("validation", "Positive Frame-Abmessungen erforderlich.")
    if type(value) not in {int, float} or not math.isfinite(value) or value <= 0:
        raise StudioError("validation", "Größe/Faktor muss positiv und endlich sein.")
    if mode == "factor":
        if value > 1:
            raise StudioError("validation", "Downscale-Faktor muss höchstens 1 sein.")
        scale = Decimal(str(value))
    elif mode == "max_edge":
        if value != int(value) or value > 16384:
            raise StudioError("validation", "Maximale Kante: ganze Pixelzahl bis 16384.")
        scale = min(Decimal(1), Decimal(int(value)) / Decimal(max(width, height)))
    else:
        raise StudioError("validation", "Größenmodus muss factor oder max_edge sein.")
    return tuple(max(1, int((Decimal(v) * scale).quantize(Decimal(1), rounding=ROUND_HALF_UP)))
                 for v in (width, height))
