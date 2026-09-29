"""Atomic source deliveries, immutable revisions and explicit draft selection."""

from dataclasses import dataclass, replace
import hashlib
from pathlib import Path
from typing import Callable
from uuid import UUID

from ..domain.assets import DIRECTIONS, require
from ..domain.models import Record, StudioError, new_id, utc_now
from ..domain.sources import SourceKey, expected_sources, matrix_slots, validate_slot
from ..storage.blob_store import BlobStore, file_hash
from ..storage.grid_detection import detect_grid
from ..storage.source_files import check_cancel, inspect_png, verify_unchanged
from ..storage.sqlite_repository import canonical
from .asset_service import AssetService

SOURCE_CONTRACT = "studio-source-v1"


@dataclass(frozen=True)
class SourceSpec:
    path: Path
    key: SourceKey
    columns: int = 16
    rows: int = 1
    frames: int = 16
    external_tool: str = ""
    auto_grid: bool = False

    def validate(self) -> None:
        require(all(type(v) is int and 1 <= v <= 64
                    for v in (self.columns, self.rows, self.frames)),
                "Raster/Framezahl benötigt ganze Zahlen zwischen 1 und 64.")
        require(self.columns * self.rows == self.frames,
                "Spalten × Zeilen muss der Quell-Framezahl entsprechen.")
        require(self.key.kind != "single_image" or self.frames == 1,
                "Source-Einzelbilder benötigen Raster 1×1 und einen Frame.")
        require(isinstance(self.external_tool, str) and len(self.external_tool) <= 128,
                "Name des externen Werkzeugs zu lang.")


@dataclass(frozen=True)
class ImportPlan:
    asset_id: str
    revision: int
    sources: tuple[tuple[SourceSpec, dict], ...]
    required_keys: tuple[SourceKey, ...] = ()


class SourceImportService:
    def __init__(self, assets: AssetService) -> None:
        self.assets = assets
        self.project, self.catalog = assets.project, assets.project.catalog
        self.store = BlobStore(self.catalog, self.project.config.roots["WORKSPACE_ROOT"],
                               self.project.config)

    def _record(self, identifier: str, revision: int) -> Record:
        record = self.assets.asset(identifier)
        if record.revision_no != revision:
            raise StudioError("conflict", "Asset inzwischen geändert; Import erneut prüfen.")
        return record

    def prepare(self, identifier: str, revision: int, specs: list[SourceSpec], *,
                required_keys: tuple[SourceKey, ...] = (),
                cancelled: Callable[[], bool] = lambda: False,
                progress: Callable[[int], None] = lambda value: None) -> ImportPlan:
        self._record(identifier, revision)
        definition = self.assets.definition(identifier)
        require(0 < len(specs) <= 128, "Zwischen 1 und 128 Quellen je Lieferung auswählen.")
        require(len({s.key for s in specs}) == len(specs),
                "Doppelte Pose-/Richtungszuordnung: eine Datei wählen oder getrennt importieren.")
        require(not required_keys or {s.key for s in specs} == set(required_keys),
                "Für diese Aktion alle ausgewählten Richtungen genau einmal liefern; "
                "andere Posen/Richtungen dürfen nicht ersetzt werden.")
        sources = []
        for index, spec in enumerate(specs):
            validate_slot(definition, spec.key)
            info = inspect_png(spec.path, self.project.config, cancelled)
            if spec.auto_grid:
                columns, rows = detect_grid(spec.path, self.project.config, cancelled)
                verify_unchanged(spec.path, info)
                spec = replace(spec, columns=columns, rows=rows, frames=columns * rows,
                               auto_grid=False)
            spec.validate()
            require(info["width"] % spec.columns == info["height"] % spec.rows == 0,
                    "Bildmaße sind nicht ohne Rest durch das gewählte Raster teilbar.")
            sources.append((spec, info))
            progress(index + 1)
        self._record(identifier, revision)
        return ImportPlan(identifier, revision, tuple(sources), required_keys)

    def import_plan(self, plan: ImportPlan, *, replace_active: bool = False,
                    cancelled: Callable[[], bool] = lambda: False,
                    progress: Callable[[int], None] = lambda value: None) -> list[Record]:
        record = self._record(plan.asset_id, plan.revision)
        require(0 < len(plan.sources) <= 128 and
                len({s.key for s, _ in plan.sources}) == len(plan.sources),
                "Ungültige oder doppelte Zuordnungen im Importplan.")
        require(not plan.required_keys or {s.key for s, _ in plan.sources} ==
                set(plan.required_keys), "Unvollständige oder veränderte Posenlieferung.")
        for spec, _ in plan.sources:
            spec.validate()
            validate_slot(self.assets.definition(plan.asset_id), spec.key)
        active = dict(record.data.get("active_sources", {}))
        if not replace_active and any(s.key.token in active for s, _ in plan.sources):
            raise StudioError("conflict", "Zuordnung bereits aktiv; Ersetzen bewusst bestätigen.")
        delivery = new_id()
        journal = {"kind": "source_delivery", "asset_id": plan.asset_id,
                   "count": len(plan.sources)}
        self.store.journal.record(delivery, "planned", journal)
        try:
            copied = []
            for index, (spec, info) in enumerate(plan.sources):
                check_cancel(cancelled)
                verify_unchanged(spec.path, info)
                blob = self.store.import_file(spec.path, cancelled=cancelled)
                require(blob["sha256"] == info["sha256"], "Quellbytes beim Kopieren verändert.")
                inspected = inspect_png(spec.path, self.project.config, cancelled)
                require(inspected == info, "Quelle während der Übernahme verändert.")
                copied.append((spec, info))
                progress(index + 1)
            # No revision or active pointer is written before the whole delivery is stable.
            for spec, info in copied:
                check_cancel(cancelled)
                verify_unchanged(spec.path, info)
            with self.catalog.transaction():
                record = self._record(plan.asset_id, plan.revision)
                revisions = []
                for spec, info in copied:
                    data = {k: v for k, v in info.items() if k != "stamp"}
                    data.update({"schema_version": 1, "contract": SOURCE_CONTRACT,
                        "slot": spec.key.to_data(), "grid": [spec.columns, spec.rows],
                        "frames": spec.frames, "original_name": spec.path.name,
                        "external_tool": spec.external_tool, "imported_at": utc_now(),
                        "delivery_id": delivery, "verification": "verified"})
                    revision = self.catalog.create("source_revision", spec.path.name,
                                                   plan.asset_id, data)
                    revisions.append(revision)
                    active[spec.key.token] = revision.id
                check_cancel(cancelled)
                self.catalog.save(record, data={**record.data, "active_sources": active})
                self.store.journal.record(delivery, "registered", journal)
            return revisions
        except Exception as error:
            self.store.journal.record(delivery, "interrupted", journal | {"error": str(error)})
            raise

    def revisions(self, identifier: str) -> list[Record]:
        return sorted((r for r in self.catalog.records() if r.kind == "source_revision"
                       and r.owner_id == identifier and r.data.get("contract") == SOURCE_CONTRACT),
                      key=lambda r: (r.created_at, r.id))

    def active(self, identifier: str) -> dict[SourceKey, Record]:
        result = {}
        record = self.catalog.get(identifier)
        require(record.kind == "asset", "Quellenzuordnung benötigt ein Asset.")
        bindings = record.data.get("active_sources", {})
        require(isinstance(bindings, dict), "Ungültige aktive Quellenzuordnungen.")
        for token, revision_id in bindings.items():
            revision = self.catalog.get(revision_id)
            require(revision.kind == "source_revision" and revision.owner_id == identifier
                    and revision.data.get("contract") == SOURCE_CONTRACT,
                    "Aktive Quelle gehört nicht zu diesem Asset.")
            key = self.validate_revision(revision)
            require(key.token == token, "Aktive Quellenzuordnung widerspricht der Revision.")
            result[key] = revision
        return result

    @staticmethod
    def validate_revision(revision: Record) -> SourceKey:
        try:
            data = revision.data
            require(data["schema_version"] == 1, "Unbekannte Quellenvertragsversion.")
            key = SourceKey(**data["slot"])
            require(key.kind in {"single_image", "spritesheet"}
                    and key.direction in (*DIRECTIONS, None), "Ungültige Quellenzuordnung.")
            if key.pose_id is not None:
                UUID(key.pose_id)
            SourceSpec(Path(data["original_name"]), key, *data["grid"], data["frames"],
                       data["external_tool"]).validate()
            require(all(type(data[k]) is int and data[k] > 0 for k in
                        ("width", "height", "length")), "Ungültige Quellmaße.")
            require(data["width"] % data["grid"][0] == data["height"] % data["grid"][1] == 0,
                    "Quellmaße passen nicht zum Raster.")
            require(isinstance(data["sha256"], str) and len(data["sha256"]) == 64 and
                    not set(data["sha256"]) - set("0123456789abcdef"), "Ungültiger Quellhash.")
            return key
        except (KeyError, TypeError, ValueError, AttributeError) as error:
            raise StudioError("validation", "Ungültige Quellenrevision.") from error

    def availability(self, revision: Record) -> str:
        data = revision.data
        if data.get("verification") != "verified":
            return "unverified"
        try:
            path = self.store.path_for(data["sha256"])
            return "imported" if path.is_file() and path.stat().st_size == data["length"] \
                else "unavailable"
        except (OSError, StudioError):
            return "unavailable"

    def matrix(self, identifier: str) -> list[dict]:
        definition = self.assets.definition(identifier)
        active = self.active(identifier)
        required = set(expected_sources(definition))
        keys = dict.fromkeys((*matrix_slots(definition), *active))
        return [{"key": key, "required": key in required,
                 "state": self.availability(active[key]) if key in active else
                 "missing" if key in required else "not_required",
                 "revision": active.get(key)} for key in keys]

    def delivery_matrix(self, identifier: str) -> list[dict]:
        """Full preparation requirements, independent of one recipe's processing inputs."""
        definition = self.assets.definition(identifier)
        active = self.active(identifier)
        keys = dict.fromkeys(expected_sources(definition))
        for key in tuple(keys):
            keys[SourceKey(key.pose_id, key.direction, "single_image")] = None
        return [{"key": key, "required": True,
                 "state": self.availability(active[key]) if key in active else "missing",
                 "revision": active.get(key)} for key in keys]

    def fingerprint(self, identifier: str) -> str | None:
        rows = self.matrix(identifier)
        if any(r["required"] and r["state"] != "imported" for r in rows):
            return None
        bindings = {r["key"].token: r["revision"].id for r in rows if r["state"] == "imported"}
        return hashlib.sha256(canonical(bindings).encode()).hexdigest()

    def activate(self, identifier: str, revision_id: str, expected_revision: int) -> None:
        self.activate_many(identifier, [revision_id], expected_revision)

    def activate_many(self, identifier: str, revision_ids: list[str],
                      expected_revision: int) -> None:
        self._record(identifier, expected_revision)
        require(0 < len(revision_ids) <= 128, "Eine bis 128 Quellenrevisionen auswählen.")
        available = {r.id: r for r in self.revisions(identifier)}
        bindings = {}
        for revision_id in revision_ids:
            require(revision_id in available, "Keine Quellenrevision dieses Assets.")
            revision = available[revision_id]
            key = self.validate_revision(revision)
            validate_slot(self.assets.definition(identifier), key)
            require(key.token not in bindings, "Doppelte Quellenzuordnung in der Lieferung.")
            path = self.store.path_for(revision.data["sha256"])
            require(self.availability(revision) == "imported" and
                    file_hash(path) == revision.data["sha256"],
                    "Quellkopie fehlt, ist beschädigt oder nicht geprüft; erneut importieren.")
            bindings[key.token] = revision_id
        with self.catalog.transaction():
            record = self._record(identifier, expected_revision)
            active = dict(record.data.get("active_sources", {}))
            if any(active.get(key) != value for key, value in bindings.items()):
                active.update(bindings)
                self.catalog.save(record, data={**record.data, "active_sources": active})

    def activate_pose_delivery(self, identifier: str, pose_id: str | None,
                               delivery_id: str, expected_revision: int) -> None:
        required = {key for key in expected_sources(self.assets.definition(identifier))
                    if key.pose_id == pose_id}
        revisions = [r for r in self.revisions(identifier)
                     if r.data["delivery_id"] == delivery_id
                     and SourceKey(**r.data["slot"]) in required]
        require(required and {SourceKey(**r.data["slot"]) for r in revisions} == required,
                "Lieferung enthält nicht alle aktuell benötigten Richtungen dieser Pose.")
        self.activate_many(identifier, [r.id for r in revisions], expected_revision)
