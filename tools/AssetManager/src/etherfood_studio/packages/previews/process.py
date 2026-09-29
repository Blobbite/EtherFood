"""Export and independently check GIF previews without changing the PNG stream."""

import json
from pathlib import PurePosixPath

from PIL import Image

from ...domain.assets import require
from ...pipelines.image_processing import expected_metadata, legacy_modules, split_frames
from ...storage.blob_store import file_hash
from ...storage.sqlite_repository import canonical


def validate_directory(value):
    path = PurePosixPath(value)
    require(isinstance(value, str) and value == path.as_posix() and
            len(path.parts) >= 2 and path.parts[0] == "previews" and
            all(part not in {".", ".."} and not part.startswith(".") and
                not any(c in part for c in '\\:*?"<>|\x00') and
                not part.endswith((" ", ".")) for part in path.parts),
            "Ausgabeordner muss ein relativer Unterordner von previews sein.")
    return value


def gif_module():
    legacy_modules()
    import PyImgGif

    return PyImgGif


def settings(metadata, parameters):
    require(metadata["kind"] == "spritesheet", "GIF-Vorschauen benötigen ein Spritesheet.")
    fps = metadata["fps"] if parameters["timing"] == "pose" else parameters["fps"]
    require(1 <= fps <= 100, "GIF benötigt 1 bis 100 FPS; eigene Vorschau-FPS wählen.")
    return {"contract": "studio-gif-preview-v1", "source_revision": metadata["source_revision"],
            "source_sha256": metadata["source_sha256"], "frames": metadata["frames"],
            "frame_size": metadata["frame_size"], "fps": fps, "loop": metadata["loop"],
            "directory": validate_directory(parameters["directory"])}


def apply(image, metadata, operation, parameters, resources, profile):
    settings(metadata, parameters)
    return image, expected_metadata(image, metadata, operation, parameters, profile)


def write_artifacts(image, metadata, parameters, output):
    expected = settings(metadata, parameters)
    frames = split_frames(image, metadata["grid"])
    try:
        gif_module().save_gif(frames, output / "preview.gif", expected["fps"],
                              loop=expected["loop"])
    finally:
        for frame in frames:
            frame.close()
    expected["sha256"] = file_hash(output / "preview.gif")
    (output / "preview.json").write_text(canonical(expected) + "\n", encoding="utf-8")


def verify_artifacts(image, metadata, parameters, output):
    expected = settings(metadata, parameters)
    expected["sha256"] = file_hash(output / "preview.gif")
    require((output / "preview.json").stat().st_size <= 65536, "Zu große GIF-Metadaten.")
    actual = json.loads((output / "preview.json").read_text(encoding="utf-8"))
    require(actual == expected, "GIF-Metadaten widersprechen Quelle, Timing oder Ausgabeziel.")
    with Image.open(output / "preview.gif") as gif:
        require(gif.format == "GIF" and gif.size == tuple(expected["frame_size"]) and
                1 <= gif.n_frames <= expected["frames"] and
                gif.info.get("loop") == (0 if expected["loop"] else None),
                "GIF passt nicht zur geplanten Animation.")
        duration = 0
        for index in range(gif.n_frames):
            gif.seek(index)
            gif.load()
            duration += gif.info.get("duration", 0)
        require(duration == sum(gif_module().frame_durations(expected["frames"], expected["fps"])),
                "GIF-Wiedergabedauer stimmt nicht mit den Eingangsframes überein.")
