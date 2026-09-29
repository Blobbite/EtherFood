"""Logical document paths and exact-file grants; no directory-wide external access."""

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

from ..domain.models import StudioError
from ..storage.paths import real_path


def project_target(root, base, target):
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or parts.query:
        raise StudioError("permission", "Diese Datei benötigt eine gezielte Dateiauswahl.")
    value = unquote(parts.path, encoding="utf-8", errors="strict")
    if "\\" in value or "\x00" in value or ":" in value:
        raise StudioError("blocked", "Ungültiger Dokumentpfad.")
    root = real_path(root)
    path = Path(os.path.abspath(root / value.lstrip("/") if value.startswith("/")
                               else base.parent / value))
    if not path.is_relative_to(root):
        raise StudioError("permission", "Pfad verlässt den erlaubten Projektbereich.")
    # Reject symlinks at every component; a later worker repeats this check before reading.
    return real_path(path, must_exist=False)


@dataclass(frozen=True)
class FileGrant:
    path: Path
    digest: str

    @classmethod
    def select(cls, path, max_bytes):
        path = real_path(path)
        return cls(path, hashlib.sha256(read_image_file(path, max_bytes)).hexdigest())


def read_image_file(path, max_bytes, expected_hash=None):
    path = real_path(path)
    # O_NOFOLLOW also closes the final-component check/open race on supporting platforms.
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise StudioError("blocked", "Bildquelle ist keine reguläre Datei.")
        checked = real_path(path).stat()
        if (before.st_dev, before.st_ino) != (checked.st_dev, checked.st_ino):
            raise StudioError("blocked", "Bildquelle wurde während der Prüfung ersetzt.")
        if before.st_size > max_bytes:
            raise StudioError("blocked", "Bilddatei überschreitet die Größenbegrenzung.")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(max_bytes + 1)
        after = real_path(path).stat()
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise StudioError("permission", "Geänderte Bildquelle benötigt eine erneute Freigabe.")
        if len(raw) > max_bytes or (expected_hash
            and hashlib.sha256(raw).hexdigest() != expected_hash):
            raise StudioError("permission",
                "Bildquelle wurde verändert; erneut auswählen oder prüfen.")
        return raw
    finally:
        os.close(fd)
