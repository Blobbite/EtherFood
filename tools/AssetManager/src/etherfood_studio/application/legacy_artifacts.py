"""Read-only decoder for result archives created before the current-file migration."""

import hashlib
from ..domain.assets import require
from ..domain.tool_contract import KINDS, compatible
from ..storage.tool_archives import read_archive, read_json


def read_results(directory, ports=None):
    files = read_archive(directory / "artifacts.zip")
    result = read_json((directory / "result.json").read_bytes())
    require(
        isinstance(result, dict)
        and set(result) == {"contract", "ports"}
        and result["contract"] == "studio-artifacts-v1"
        and isinstance(result["ports"], dict),
        "Ungültiger Dateiergebnisvertrag.",
    )
    if ports is not None:
        require(
            set(result["ports"]) == set(ports),
            "Ergebnisausgänge stimmen nicht mit dem Baustein überein.",
        )
    seen = set()
    for port, items in result["ports"].items():
        spec = (ports or {}).get(port, {"type": "file", "multiple": True, "required": False})
        require(
            isinstance(items, list)
            and len(items) <= 1024
            and (items or not spec.get("required", True))
            and (spec.get("multiple", False) or len(items) <= 1),
            "Fehlende oder unerwartet viele Dateien an Ausgang " + port,
        )
        for item in items:
            require(
                isinstance(item, dict)
                and set(item) == {"path", "type", "metadata", "sha256", "length"}
                and item["path"] in files
                and item["path"] not in seen
                and item["type"] in KINDS
                and compatible(item["type"], spec["type"])
                and isinstance(item["metadata"], dict),
                "Ungültige Datei an Ausgang " + port,
            )
            raw = files[item["path"]]
            require(
                item["sha256"] == hashlib.sha256(raw).hexdigest() and item["length"] == len(raw),
                "Ergebnisdatei wurde verändert.",
            )
            if item["type"] in {"image", "spritesheet", "gif"}:
                from io import BytesIO
                from PIL import Image
                from ..pipelines.image_processing import validate_metadata

                with Image.open(BytesIO(raw)) as image:
                    require(
                        image.format == ("GIF" if item["type"] == "gif" else "PNG"),
                        "Bildformat passt nicht zum Ausgang.",
                    )
                    if item["type"] != "gif":
                        if item["metadata"]:
                            validate_metadata(item["metadata"], image.size)
                        require(
                            item["type"] != "spritesheet"
                            or item["metadata"].get("kind") == "spritesheet",
                            "Spritesheet benötigt explizite Raster-/Timingdaten.",
                        )
                    image.verify()
            elif item["type"] == "json":
                read_json(raw)
            elif item["type"] == "html":
                raw.decode("utf-8")
            seen.add(item["path"])
    require(seen == set(files), "Archiv enthält nicht deklarierte Ergebnisse.")
    return result, files
