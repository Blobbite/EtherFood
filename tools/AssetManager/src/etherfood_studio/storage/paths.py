"""Central path boundaries for a local single-user workspace."""

from pathlib import Path
import re
import unicodedata

from ..config import ALIASES
from ..domain.models import StudioError

RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)


def real_path(path: Path, *, must_exist: bool = True) -> Path:
    absolute = path.absolute()
    if ".." in absolute.parts:
        raise StudioError("validation", "Elternpfade sind nicht erlaubt.")
    for part in (absolute, *absolute.parents):
        if part.is_symlink():
            raise StudioError("validation", "Symlink-Pfade werden nicht verwendet.")
    if must_exist and not absolute.exists():
        raise StudioError("unavailable", "Pfad ist nicht verfügbar.", str(absolute))
    return absolute.resolve(strict=must_exist)


def validate_roots(roots: dict[str, Path], *, require_available: bool = True) -> None:
    if set(roots) - set(ALIASES):
        raise StudioError("validation", "Unbekannter Wurzelalias.")
    resolved = [real_path(path, must_exist=require_available) for path in roots.values()]
    for index, left in enumerate(resolved):
        if require_available and not left.is_dir():
            raise StudioError("validation", "Eine Datenwurzel ist kein Verzeichnis.")
        for right in resolved[index + 1:]:
            a = unicodedata.normalize("NFC", str(left)).casefold()
            b = unicodedata.normalize("NFC", str(right)).casefold()
            if a == b or a.startswith(b + "/") or b.startswith(a + "/"):
                raise StudioError("validation", "Datenwurzeln dürfen sich nicht überlappen.")


def safe_target(root: Path, relative: str) -> Path:
    base = real_path(root)
    if not base.is_dir() or not relative or "\\" in relative:
        raise StudioError("validation", "Ungültiges relatives Schreibziel.")
    parts = relative.split("/")
    current = base
    for name in parts:
        if (name in {"", ".", ".."} or ":" in name or RESERVED.match(name)
                or name.endswith((" ", ".")) or any(ord(char) < 32 for char in name)
                or unicodedata.normalize("NFC", name) != name):
            raise StudioError("validation", "Unsicherer oder nicht normalisierter Dateiname.")
        if current.exists():
            if not current.is_dir():
                raise StudioError("validation", "Ein übergeordneter Pfad ist keine Ablage.")
            for sibling in current.iterdir():
                normalized = unicodedata.normalize("NFC", sibling.name).casefold()
                if normalized == name.casefold() and sibling.name != name:
                    raise StudioError("conflict", "Dateiname kollidiert auf anderen Plattformen.")
        current = current / name
        real_path(current, must_exist=False)
    if not current.resolve().is_relative_to(base):
        raise StudioError("validation", "Schreibziel verlässt seine Datenwurzel.")
    return current


def make_directory(root: Path, relative: str) -> Path:
    for index in range(1, len(relative.split("/")) + 1):
        current = safe_target(root, "/".join(relative.split("/")[:index]))
        current.mkdir(exist_ok=True)
    return safe_target(root, relative)
