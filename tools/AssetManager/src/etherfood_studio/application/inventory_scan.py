"""Explicit read-only inventory jobs; every mapping remains a reviewable proposal."""

from collections import Counter
from dataclasses import dataclass, replace
import os
from pathlib import Path
import re
from threading import Event
from typing import Callable

from ..domain.assets import AssetDefinition, DIRECTIONS, VariantKey
from ..domain.models import StudioError
from ..storage.inventory_files import ScanLimits, check_cancel, inspect_png
from ..storage.paths import real_path


@dataclass(frozen=True)
class Candidate:
    path: str
    sha256: str
    width: int
    height: int
    grid: tuple[int, int] | None
    variant: VariantKey | None
    state: str
    notes: tuple[str, ...]


@dataclass(frozen=True)
class ScanResult:
    root: Path
    definition: AssetDefinition
    candidates: tuple[Candidate, ...]
    problems: tuple[str, ...]
    reports: tuple[dict, ...]
    pages: tuple[dict, ...]
    skipped: int

    def matrix(self) -> dict[VariantKey, str]:
        valid = [c.variant for c in self.candidates if c.state in {"proposal", "duplicate"}]
        matrix = self.definition.matrix(set(valid))
        for key, count in Counter(valid).items():
            if count > 1:
                matrix[key] = "conflict"
        return matrix


def one(values: list, label: str, notes: list[str]):
    unique = list(dict.fromkeys(values))
    if len(unique) > 1:
        notes.append(f"Widersprüchliche {label}: {unique}")
        return None
    return unique[0] if unique else None


def propose(path: Path, root: Path, definition: AssetDefinition, info: dict,
            expected: frozenset[VariantKey]) -> Candidate:
    relative = path.relative_to(root).as_posix()
    # Include selected root ancestors for scans directly inside a profile/frame folder.
    parts = path.parts
    tokens = path.stem.split("_")
    notes = []
    meta = info["metadata"]
    allowed = {"pose", "direction", "graphics", "frames", "grid"}
    if set(meta) - allowed:
        notes.append("Unbekannte Variantenmetadaten; manuell klären.")
    poses = {p.export_name: p for p in definition.poses}
    pose_names = [name for name in poses if name in parts or
                  re.search(r"(?:^|_)" + re.escape(name) + r"(?:_spritesheet)?_", path.stem)]
    named_pose = re.search(r"(?:^|_)([a-z][a-z0-9-]*)_spritesheet_", path.stem)
    if named_pose:
        pose_names.append(named_pose.group(1))
    for key in ("pose", "direction", "graphics"):
        if key in meta and not isinstance(meta[key], str):
            notes.append(f"Ungültiger Metadatentyp: {key}")
    if "frames" in meta and type(meta["frames"]) is not int:
        notes.append("Ungültiger Metadatentyp: frames")
    if "pose" in meta and isinstance(meta["pose"], str):
        pose_names.append(meta["pose"])
    pose_name = one(pose_names, "Posen", notes)
    pose = poses.get(pose_name)
    directions = [v for v in tokens if v in DIRECTIONS]
    if "direction" in meta and isinstance(meta["direction"], str):
        directions.append(meta["direction"])
    direction = one(directions, "Richtungen", notes)
    graphics = [v for v in parts if v in definition.profile_keys]
    if "graphics" in meta and isinstance(meta["graphics"], str):
        graphics.append(meta["graphics"])
    graphic = one(graphics, "Grafikprofile", notes)
    frames = [int(m.group(1)) for part in parts
              if (m := re.fullmatch(r"spritesheet-fram(\d{1,3})", part))]
    if type(meta.get("frames")) is int:
        frames.append(meta["frames"])
    grids = [(int(m.group(1)), int(m.group(2)))
             for m in re.finditer(r"(?:^|_)(\d{1,3})x(\d{1,3})(?=_|$)", path.stem)]
    if "grid" in meta:
        value = meta["grid"]
        if isinstance(value, list) and len(value) == 2 and all(type(v) is int for v in value):
            grids.append(tuple(value))
        else:
            notes.append("Ungültige Rastermetadaten.")
    grid = one(grids, "Raster", notes)
    static = "static_image" in definition.capabilities
    single = static or (pose and pose.source_kind == "single_image")
    if single:
        if grid not in (None, (1, 1)) or any(f != 1 for f in frames):
            notes.append("Einzelbild widerspricht Raster/Frameangabe.")
        grid = (1, 1)
        frame_count = None if static else 1
    else:
        if grid:
            frames.append(grid[0] * grid[1])
        frame_count = one(frames, "Framezahlen", notes)
        if not pose:
            notes.append("Pose nicht eindeutig bekannt; Exportnamen/Ordner prüfen.")
    if not grid or min(grid) <= 0 or info["width"] % grid[0] or info["height"] % grid[1]:
        notes.append("Raster fehlt oder teilt die Bildabmessungen nicht.")
    if not graphic:
        notes.append("Grafikprofil fehlt oder ist widersprüchlich.")
    if "directional" in definition.capabilities:
        if direction not in DIRECTIONS:
            notes.append("Richtung fehlt oder ist unbekannt.")
    elif direction:
        notes.append("Richtungsangabe bei nicht gerichtetem Asset.")
    if any(v.casefold() in {"masks", "mask", "masken"} for v in parts):
        notes.append("Masken sind keine Laufzeit-Spritesheets; separaten Bestand wählen.")
    key = VariantKey(pose.id if pose else None, direction, graphic, frame_count) \
        if graphic and (static or pose) else None
    state = "needs_review" if notes or key is None else "proposal"
    if state == "proposal" and key not in expected:
        state = "not_required"
        notes.append("Diese Kombination wird von den Asset-Anforderungen nicht verlangt.")
    notes.append("Herkunft unbekannt; Dateiname beweist weder Original noch Ableitung.")
    notes.append("PNG-Struktur/Raster geprüft; Pixelinhalt und Laufrichtung nicht bewertet.")
    return Candidate(relative, info["sha256"], info["width"], info["height"], grid,
                     key, state, tuple(notes))


def scan_inventory(root: Path, definition: AssetDefinition, *, limits: ScanLimits | None = None,
                   cancel: Event | None = None, progress: Callable | None = None) -> ScanResult:
    from .inventory_reports import inspect_page, inspect_report

    limits, cancel = limits or ScanLimits(), cancel or Event()
    root = real_path(root)
    if not root.is_dir():
        raise StudioError("path", "Bestandswurzel muss ein Ordner sein.")
    candidates, problems, reports, pages = [], [], [], []
    expected = frozenset(definition.expected())
    skipped, seen = 0, 0
    pending = [(root, 0)]
    while pending:
        directory, depth = pending.pop()
        check_cancel(cancel)
        try:
            real_path(directory)
            with os.scandir(directory) as entries:
                for entry in entries:
                    check_cancel(cancel)
                    seen += 1
                    if seen > limits.max_files:
                        raise StudioError("limit", "Bestand zu groß; kleineren Unterordner wählen.")
                    path = Path(entry.path)
                    relative = path.relative_to(root).as_posix()
                    if entry.is_symlink():
                        problems.append(relative + ": Symlink wird nicht verfolgt.")
                    elif entry.is_dir(follow_symlinks=False):
                        if entry.name.startswith(".") or entry.name == "__pycache__":
                            skipped += 1
                        elif depth >= limits.max_depth:
                            problems.append(relative + ": Maximale Ordnertiefe erreicht.")
                        else:
                            pending.append((path, depth + 1))
                    elif entry.is_file(follow_symlinks=False):
                        try:
                            if path.suffix.lower() == ".png":
                                info = inspect_png(path, limits, cancel)
                                candidates.append(propose(path, root, definition, info, expected))
                            elif entry.name in {
                                "build-info.json", "pruefung.json", "color-build.json",
                            }:
                                reports.append(inspect_report(path, root, limits, cancel))
                            elif path.suffix.lower() in {".html", ".htm"}:
                                pages.append(inspect_page(path, root, limits, cancel))
                            else:
                                skipped += 1
                        except (OSError, StudioError, ValueError) as error:
                            check_cancel(cancel)
                            problems.append(relative + ": " + str(error))
                    else:
                        problems.append(relative + ": Keine reguläre Datei.")
                    if progress and seen % 20 == 0:
                        progress(seen)
        except OSError as error:
            problems.append(directory.relative_to(root).as_posix() + ": " + str(error))
    counts = Counter(c.variant for c in candidates if c.state == "proposal")
    candidates = [replace(c, state="duplicate", notes=(
        "Mehrere Dateien für dieselbe Variante; höchstens eine bewusst auswählen.", *c.notes,
    )) if c.state == "proposal" and counts[c.variant] > 1 else c for c in candidates]
    check_cancel(cancel)
    return ScanResult(root, definition, tuple(sorted(candidates, key=lambda c: c.path)),
                      tuple(sorted(problems)), tuple(reports), tuple(pages), skipped)
