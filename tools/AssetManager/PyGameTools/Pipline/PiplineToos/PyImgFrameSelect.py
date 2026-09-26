#!/usr/bin/env python3
"""Frames gleichmäßig auswählen; nur die übergebene Arbeitskopie ersetzen."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile

import PyImgGrid as raster


def uniform_indices(source_count: int, target_count: int) -> list[int]:
    """Zyklische Auswahl ohne doppelte Frames, in ursprünglicher Reihenfolge."""
    if not 1 <= target_count <= source_count:
        raise ValueError("Die Zielanzahl muss zwischen 1 und der Quellframezahl liegen.")
    return [index * source_count // target_count for index in range(target_count)]


def reduce_copy(path: Path, *, source_count: int, target_count: int,
                source_grid: raster.Grid | None = None) -> list[int]:
    """Eine zuvor angelegte Kopie atomar durch ein horizontales N×1-Sheet ersetzen."""
    from PIL import Image

    indices = uniform_indices(source_count, target_count)
    raster.validate_target(path)
    frames, _, _ = raster.read_frames(path, frame_count=source_count, source_grid=source_grid)
    width, height = frames[0].size
    sheet = Image.new("RGBA", (width * target_count, height))
    for position, index in enumerate(indices):
        # Ohne Maske: auch RGB-Werte transparenter Pixel bleiben erhalten.
        sheet.paste(frames[index], (position * width, 0))
    fd, temporary = tempfile.mkstemp(prefix=".pyimgselect-", suffix=".png", dir=path.parent)
    os.close(fd)
    try:
        sheet.save(temporary, "PNG", optimize=True, compress_level=9)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return indices
