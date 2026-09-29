"""Bounded, deterministic package archives; inspection never imports Python code."""

from io import BytesIO
import json
from pathlib import Path
import stat
import zipfile
import zlib

from ..domain.assets import require
from ..domain.models import StudioError
from ..domain.tool_contract import relative_name
from .sqlite_repository import canonical

MAX_FILE = 16 * 1024 * 1024
MAX_ARCHIVE = 128 * 1024 * 1024


def read_json(raw):
    require(len(raw) <= 2 * 1024 * 1024, "Paketbeschreibung ist zu groß.")

    def pairs(values):
        result = {}
        for key, value in values:
            require(key not in result, "Doppelter JSON-Schlüssel: " + key)
            result[key] = value
        return result

    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except (UnicodeError, ValueError, TypeError, RecursionError) as error:
        raise StudioError("validation", "Ungültige JSON-Paketbeschreibung.", str(error)) from error


def read_archive(source):
    if isinstance(source, (str, Path)):
        path = Path(source)
        require(
            path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_ARCHIVE,
            "Ungültige oder zu große Paketdatei.",
        )
    else:
        require(
            isinstance(source, bytes) and len(source) <= MAX_ARCHIVE,
            "Ungültige oder zu große Paketdaten.",
        )
        source = BytesIO(source)
    result, seen, total = {}, set(), 0
    try:
        with zipfile.ZipFile(source) as archive:
            require(len(archive.infolist()) <= 2048, "Zu viele Dateien im Paket.")
            for item in archive.infolist():
                relative_name(item.filename[:-1] if item.is_dir() else item.filename)
                require(
                    not item.flag_bits & 1
                    and not stat.S_ISLNK(item.external_attr >> 16)
                    and item.filename not in seen
                    and item.file_size <= MAX_FILE,
                    "Doppelte, verlinkte oder zu große Datei im Paket.",
                )
                seen.add(item.filename)
                if item.is_dir():
                    continue
                total += item.file_size
                require(total <= MAX_ARCHIVE, "Entpacktes Paket überschreitet die Grenze.")
                result[item.filename] = archive.read(item)
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, OSError, zlib.error) as error:
        raise StudioError(
            "validation", "Paketarchiv kann nicht gelesen werden.", str(error)
        ) from error
    return result


def archive_bytes(files):
    stream = BytesIO()
    require(
        len(files) <= 2048 and sum(len(v) for v in files.values()) <= MAX_ARCHIVE,
        "Paketinhalt überschreitet die Grenze.",
    )
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            relative_name(name)
            require(
                isinstance(content, bytes) and len(content) <= MAX_FILE,
                "Ungültiger oder zu großer Dateiinhalt.",
            )
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    return stream.getvalue()


def json_bytes(value):
    return (canonical(value) + "\n").encode("utf-8")
