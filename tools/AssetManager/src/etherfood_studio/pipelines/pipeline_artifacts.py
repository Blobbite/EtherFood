"""Validate typed current-pipeline results without importing user processing code."""

import json
from pathlib import Path

from ..domain.assets import require
from ..domain.pipeline_contract import compatible
from ..domain.tool_contract import relative_name
from ..storage.blob_store import file_hash
from ..storage.paths import safe_target

MAX_OUTPUT_BYTES = 64 * 1024 * 1024
MAX_OUTPUT_TOTAL = 256 * 1024 * 1024


def verify_artifact(path, item):
    require(
        path.is_file() and not path.is_symlink() and 0 <= path.stat().st_size <= MAX_OUTPUT_BYTES,
        "Ergebnis fehlt oder ist zu groß.",
    )
    require(
        path.stat().st_size == item["length"] and file_hash(path) == item["sha256"],
        "Ergebnisdatei stimmt nicht mit dem Nachweis überein.",
    )
    if item["type"] in {"image", "spritesheet", "gif"}:
        from PIL import Image
        from .image_processing import validate_metadata

        with Image.open(path) as image:
            require(
                image.format == ("GIF" if item["type"] == "gif" else "PNG"),
                "Tatsächliches Bildformat passt nicht zum deklarierten Ausgang.",
            )
            require(image.width * image.height <= 32_000_000, "Ergebnis überschreitet Pixelgrenze.")
            if item["type"] == "spritesheet":
                require(
                    item["metadata"].get("kind") == "spritesheet",
                    "Spritesheet benötigt ausdrückliche Raster-/Timingdaten.",
                )
            if item["type"] != "gif" and item["metadata"]:
                validate_metadata(item["metadata"], image.size)
            for index in range(getattr(image, "n_frames", 1)):
                require(index < 4096, "Ergebnis enthält zu viele Animationsframes.")
                image.seek(index)
                image.load()
    elif item["type"] == "json":
        json.loads(path.read_bytes())
    elif item["type"] == "html":
        path.read_text(encoding="utf-8")  # Data only; never render in an active browser here.


def read_outputs(directory, specifications):
    data = json.loads((directory / "result.json").read_bytes())
    require(
        isinstance(data, dict) and set(data) == set(specifications),
        "Ergebnisanschlüsse stimmen nicht mit der Skriptbeschreibung überein.",
    )
    seen, total = set(), 0
    for name, items in data.items():
        spec = specifications[name]
        require(
            isinstance(items, list)
            and len(items) <= 1024
            and (items or not spec.get("required", True))
            and (len(items) <= 1 or spec.get("multiple", False)),
            "Fehlende oder zu viele Ergebnisse an " + name,
        )
        for item in items:
            relative_name(item["path"])
            require(
                item["path"] not in seen
                and item["path"] != "result.json"
                and compatible(item["type"], spec["type"])
                and isinstance(item["metadata"], dict),
                "Ungültiges oder doppelt deklariertes Ergebnis.",
            )
            path = safe_target(directory, item["path"])
            verify_artifact(path, item)
            total += item["length"]
            require(total <= MAX_OUTPUT_TOTAL, "Gesamtergebnis überschreitet die Speichergrenze.")
            seen.add(item["path"])
    actual = set()
    for path in directory.rglob("*"):
        require(not path.is_symlink(), "Ergebnisablage enthält einen symbolischen Link.")
        if path.is_file():
            actual.add(path.relative_to(directory).as_posix())
    require(actual == seen | {"result.json"}, "Nicht deklarierte Ergebnisdateien vorhanden.")
    return data
