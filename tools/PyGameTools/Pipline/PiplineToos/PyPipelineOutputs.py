"""Gemeinsame Schreibregeln: prüfen, fehlende Ausgaben erstellen oder bewusst ersetzen."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile


def validate(path: Path) -> None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"Ausgabe ist ein Link oder keine reguläre Datei: {path}")
    for parent in path.parents:
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            raise ValueError(f"Ausgabeordner ist ein Link oder kein Verzeichnis: {parent}")


def action(path: Path, overwrite: bool = False) -> str:
    validate(path)
    return ("ERSETZEN" if overwrite else "SKIP") if path.exists() else "NEU"


def should_write(path: Path, *, overwrite: bool = False, dry_run: bool = False) -> bool:
    mode = action(path, overwrite)
    print(f"[{mode}{'; Plan' if dry_run else ''}] {path}", flush=True)
    return not dry_run and mode != "SKIP"


def write_text(path: Path, content: str, *, overwrite: bool = False) -> None:
    if not should_write(path, overwrite=overwrite):
        return
    fd, name = tempfile.mkstemp(prefix=".pipeline-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)
