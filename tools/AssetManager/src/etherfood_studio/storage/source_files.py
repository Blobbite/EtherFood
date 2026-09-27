"""Bounded PNG decoding and stable-file checks before immutable registration."""

from pathlib import Path
from typing import Callable

from ..config import Configuration
from ..domain.assets import require
from ..domain.models import StudioError
from .blob_store import file_hash
from .paths import real_path


def check_cancel(cancelled: Callable[[], bool]) -> None:
    if cancelled():
        raise StudioError("cancelled", "Quellimport abgebrochen; aktiver Stand unverändert.")


def stamp(path: Path) -> tuple[int, ...]:
    info = real_path(path).stat()
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def inspect_png(path: Path, config: Configuration,
                cancelled: Callable[[], bool] = lambda: False) -> dict:
    try:
        from PIL import Image
    except ImportError as error:
        raise StudioError("unavailable", "Pillow für Bildimporte erforderlich.") from error
    try:
        check_cancel(cancelled)
        path = real_path(path)
        require(path.is_file() and path.suffix.lower() == ".png", "PNG-Datei auswählen.")
        before = stamp(path)
        require(0 < before[2] <= config.max_file_bytes, "PNG überschreitet die Dateigröße.")
        with Image.open(path) as image:
            require(image.format == "PNG" and not getattr(image, "is_animated", False),
                    "Nur einzelne PNG-Bilder/Spritesheets, keine APNG-Animation.")
            width, height = image.size
            require(0 < width * height <= config.max_pixels, "PNG überschreitet die Pixelgrenze.")
            image.verify()
        check_cancel(cancelled)
        with Image.open(path) as image:
            image.load()  # Also reject intact headers with truncated/corrupt pixel data.
        digest = file_hash(path)
        require(before == stamp(path), "PNG wurde während der Prüfung verändert.")
        check_cancel(cancelled)
        return {"sha256": digest, "length": before[2], "width": width, "height": height,
                "stamp": before}
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        raise StudioError("validation", "PNG unvollständig oder nicht lesbar.", str(error)) \
            from error


def verify_unchanged(path: Path, info: dict) -> None:
    try:
        if stamp(path) != info["stamp"] or file_hash(path) != info["sha256"] \
                or stamp(path) != info["stamp"]:
            raise StudioError("conflict", "Quelle seit der Prüfung verändert; erneut prüfen.")
    except OSError as error:
        raise StudioError("conflict", "Quelle seit der Prüfung nicht mehr lesbar.") from error
