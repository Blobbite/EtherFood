"""Bounded, read-only source inspection; never invokes an image processing pipeline."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct
from threading import Event
import zlib

from ..domain.models import StudioError
from .paths import real_path


@dataclass(frozen=True)
class ScanLimits:
    max_files: int = 10000
    max_depth: int = 16
    max_bytes: int = 64 * 1024 * 1024
    max_pixels: int = 32_000_000
    max_report_bytes: int = 1024 * 1024


def check_cancel(cancel: Event) -> None:
    if cancel.is_set():
        raise StudioError("cancelled", "Bestandserfassung abgebrochen; nichts übernommen.")


def stamp(path: Path) -> tuple:
    value = path.stat()
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def read_bytes(path: Path, limit: int, cancel: Event) -> bytes:
    real_path(path)
    before = stamp(path)
    if not path.is_file() or before[2] > limit:
        raise StudioError("limit", "Datei ist zu groß oder keine normale Datei.")
    chunks = []
    length = 0
    with path.open("rb") as source:
        while True:
            check_cancel(cancel)
            block = source.read(min(1024 * 1024, limit + 1 - length))
            if not block:
                break
            chunks.append(block)
            length += len(block)
            if length > limit:
                raise StudioError("limit", "Dateigrößenlimit überschritten.")
    if stamp(path) != before:
        raise StudioError("conflict", "Datei hat sich während der Prüfung geändert.")
    return b"".join(chunks)


def inspect_png(path: Path, limits: ScanLimits, cancel: Event) -> dict:
    """Check chunks/CRC, dimensions and optional plain metadata, not decoded pixels."""
    data = read_bytes(path, limits.max_bytes, cancel)
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise StudioError("validation", "Keine PNG-Signatur.")
    offset, width, height, has_data, ended = 8, 0, 0, False, False
    metadata = {}
    while offset < len(data):
        check_cancel(cancel)
        if offset + 12 > len(data):
            raise StudioError("validation", "Abgeschnittener PNG-Chunk.")
        length, kind = struct.unpack_from(">I4s", data, offset)
        end = offset + length + 12
        if end > len(data):
            raise StudioError("validation", "PNG-Chunk ist unvollständig.")
        chunk = data[offset + 8:end - 4]
        crc = zlib.crc32(chunk, zlib.crc32(kind)) & 0xffffffff
        if crc != struct.unpack_from(">I", data, end - 4)[0]:
            raise StudioError("validation", "PNG-Prüfsumme stimmt nicht.")
        if offset == 8 and (kind != b"IHDR" or length != 13):
            raise StudioError("validation", "PNG-Header fehlt.")
        if kind == b"IHDR":
            if width or length != 13:
                raise StudioError("validation", "Doppelter/ungültiger PNG-Header.")
            width, height = struct.unpack_from(">II", chunk)
            bit_depth, color, compression, filtering, interlace = chunk[8:13]
            depths = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8),
                      4: (8, 16), 6: (8, 16)}
            if bit_depth not in depths.get(color, ()) or compression or filtering \
                    or interlace not in (0, 1):
                raise StudioError("validation", "Ungültiges PNG-Headerformat.")
            if not width or not height or width * height > limits.max_pixels:
                raise StudioError("limit", "PNG-Abmessungen sind ungültig oder zu groß.")
        elif kind == b"IDAT":
            has_data = True
        elif kind == b"tEXt" and chunk.startswith(b"etherfood_variant\0"):
            if metadata or length > 16384:
                raise StudioError("validation", "PNG-Variantenmetadaten doppelt/zu groß.")
            try:
                metadata = json.loads(chunk.split(b"\0", 1)[1].decode("utf-8"))
                if not isinstance(metadata, dict):
                    raise ValueError("object required")
            except (ValueError, UnicodeError) as error:
                raise StudioError("validation", "Ungültige PNG-Variantenmetadaten.") from error
        elif kind == b"IEND":
            ended = True
            if length or end != len(data):
                raise StudioError("validation", "PNG-Ende ist ungültig.")
        offset = end
    if not ended or not has_data:
        raise StudioError("validation", "PNG-Bilddaten oder Abschluss fehlen.")
    return {"sha256": hashlib.sha256(data).hexdigest(), "width": width,
            "height": height, "metadata": metadata}


def inside_reference(root: Path, parent: Path, reference: str) -> Path:
    """Normalize internal relative links, reject outside roots and every symlink component."""
    import os

    if not isinstance(reference, str) or not reference or "\\" in reference or "\0" in reference:
        raise StudioError("path", "Ungültiger externer Verweis.")
    source = Path(reference)
    candidate = Path(os.path.abspath(source if source.is_absolute() else parent / source))
    if not candidate.is_relative_to(root):
        raise StudioError("path", "Verweis liegt außerhalb der gewählten Wurzel.")
    return real_path(candidate)
