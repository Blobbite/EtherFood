"""Conservative grid suggestions; dimensions alone never imply a sprite layout."""

from pathlib import Path
import re

from ..domain.assets import require
from .source_files import check_cancel


def named_grid(name: str) -> tuple[int, int] | None:
    hints = {(int(m[1]), int(m[2])) for m in re.finditer(
        r"(?<!\d)(\d+)\s*[xX×]\s*(\d+)(?!\d)", Path(name).stem,
    ) if 1 <= int(m[1]) * int(m[2]) <= 64 and min(int(m[1]), int(m[2])) > 0}
    require(len(hints) <= 1, "Widersprüchliche Raster im Dateinamen; Raster manuell wählen.")
    return next(iter(hints), None)


def _parts(projection: list[int]) -> int:
    bands = []
    start = None
    for index, occupied in enumerate([*projection, 0]):
        if occupied and start is None:
            start = index
        elif not occupied and start is not None:
            bands.append((start, index))
            start = None
    count = len(bands)
    require(0 < count <= 64 and len(projection) % count == 0,
            "Kein eindeutiges regelmäßiges Raster; bitte manuell wählen.")
    size = len(projection) // count
    require(all(index * size <= start < end <= (index + 1) * size
                for index, (start, end) in enumerate(bands)),
            "Bildabstände sind nicht eindeutig regelmäßig; Raster manuell wählen.")
    return count


def detect_grid(path, config, cancelled=lambda: False) -> tuple[int, int]:
    from PIL import Image
    check_cancel(cancelled)
    require(path.stat().st_size <= config.max_file_bytes, "PNG überschreitet die Dateigröße.")
    with Image.open(path) as image:
        require(0 < image.width * image.height <= config.max_pixels,
                "PNG überschreitet die Pixelgrenze.")
        named = named_grid(path.name)
        if named:
            require(image.width % named[0] == image.height % named[1] == 0,
                    "Raster aus dem Dateinamen passt nicht zu den Pixelmaßen; manuell prüfen.")
            return named
        alpha = image.convert("RGBA").getchannel("A")
        require(alpha.getextrema()[0] < 16,
                "Ohne Rasterangabe oder klare Transparenzabstände: Raster manuell wählen.")
        mask = alpha.point([0] * 16 + [255] * 240)
        columns, rows = (_parts(axis) for axis in mask.getprojection())
        require(1 < columns * rows <= 64,
                "Kein eindeutiges Spritesheet-Raster erkannt; bitte manuell wählen.")
        width, height = image.width // columns, image.height // rows
        for row in range(rows):
            for column in range(columns):
                check_cancel(cancelled)
                require(mask.crop((column * width, row * height, (column + 1) * width,
                                   (row + 1) * height)).getbbox() is not None,
                        "Leere Rasterzellen: Framezahl und Raster manuell bestätigen.")
        return columns, rows
