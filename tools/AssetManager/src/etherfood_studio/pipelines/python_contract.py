"""Versioned image/metadata boundary; extension code is never needed to verify a result."""

from copy import deepcopy
import math
import re

from ..domain.assets import require
from .image_processing import finish_metadata, validate_metadata

EDITABLE = {"frame_size", "grid", "source_indices", "crop_offset", "crop_size",
            "profile", "fps", "timing_mode"}


def result_metadata(incoming, changes, image_size):
    require(isinstance(changes, dict) and set(changes) <= EDITABLE,
            "Python-Ergebnis enthält nicht erlaubte Metadatenänderungen.")
    meta = {k: deepcopy(v) for k, v in incoming.items()
            if k not in {"contract", "image_sha256"}}
    meta.update(deepcopy(changes))
    require(isinstance(meta.get("profile"), str) and re.fullmatch(
        r"[a-z][a-z0-9_-]{0,63}", meta["profile"]) is not None,
        "Ausgabeprofil benötigt einen stabilen Schlüssel.")
    indices = meta.get("source_indices")
    require(isinstance(indices, list) and all(type(i) is int for i in indices)
            and set(indices) <= set(incoming["source_indices"]),
            "Python-Schritte dürfen keine zusätzlichen Quellframes erfinden.")
    meta["frames"] = len(indices)
    if meta["kind"] == "spritesheet":
        require(type(meta.get("fps")) in {int, float} and meta["fps"] > 0,
                "Wiedergabe-FPS müssen positiv sein.")
        meta["duration"] = meta["frames"] / meta["fps"]
    else:
        require(not {"fps", "timing_mode"} & set(changes),
                "Einzelbilder haben keine Animationseinstellungen.")
    size = meta.get("frame_size")
    require(isinstance(size, list) and len(size) == 2 and
            all(type(v) is int and v > 0 for v in size), "Ungültige Python-Framegröße.")
    require(isinstance(meta.get("crop_size"), list) and len(meta["crop_size"]) == 2 and
            all(type(v) in {int, float} and v > 0 for v in meta["crop_size"]),
            "Ungültiger Python-Zuschnitt.")
    require(isinstance(meta.get("crop_offset"), list) and len(meta["crop_offset"]) == 2 and
            all(type(v) in {int, float} and math.isfinite(v) for v in meta["crop_offset"]),
            "Ungültiger Python-Crop-Offset.")
    finish_metadata(meta, size)
    validate_metadata(meta, image_size)
    return meta


def verify_result(incoming, claimed, image_size):
    expected = result_metadata(incoming, {k: claimed[k] for k in EDITABLE if k in claimed},
                               image_size)
    require(claimed == expected,
            "Python-Ergebnis verändert Quellbindung, Weltgröße oder abgeleitete Metadaten.")
