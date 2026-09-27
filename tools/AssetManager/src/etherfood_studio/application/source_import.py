"""Atomic source deliveries, immutable revisions and explicit draft selection."""

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Callable
from uuid import UUID

from ..domain.assets import DIRECTIONS, require
from ..domain.models import Record, StudioError, new_id, utc_now
from ..domain.sources import SourceKey, expected_sources, matrix_slots, validate_slot
from ..storage.blob_store import BlobStore, file_hash
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
                cancelled: Callable[[], bool] = lambda: False,
                progress: Callable[[int], None] = lambda value: None) -> ImportPlan:
        self._record(identifier, revision)
        definition = self.assets.definition(identifier)
        require(0 < len(specs) <= 128, "Zwischen 1 und 128 Quellen je Lieferung auswählen.")
        require(len({s.key for s in specs}) == len(specs),
                "Doppelte Pose-/Richtungszuordnung: eine Datei wählen oder getrennt importieren.")
        sources = []
        for index, spec in enumerate(specs):
            spec.validate()
            validate_slot(definition, spec.key)
            info = inspect_png(spec.path, self.project.config, cancelled)
            require(info["width"] % spec.columns == info["height"] % spec.rows == 0,
                    "Bildmaße sind nicht ohne Rest durch das gewählte Raster teilbar.")
            sources.append((spec, info))
            progress(index + 1)
        self._record(identifier, revision)
        return ImportPlan(identifier, revision, tuple(sources))

    def import_plan(self, plan: ImportPlan, *, replace_active: bool = False,
                    cancelled: Callable[[], bool] = lambda: False,
                    progress: Callable[[int], None] = lambda value: None) -> list[Record]:
        record = self._record(plan.asset_id, plan.revision)
        require(0 < len(plan.sources) <= 128 and
                len({s.key for s, _ in plan.sources}) == len(plan.sources),
                "Ungültige oder doppelte Zuordnungen im Importplan.")
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
        bindings = self.assets.asset(identifier).data.get("active_sources", {})
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

    def fingerprint(self, identifier: str) -> str | None:
        rows = self.matrix(identifier)
        if any(r["required"] and r["state"] != "imported" for r in rows):
            return None
        bindings = {r["key"].token: r["revision"].id for r in rows if r["state"] == "imported"}
        return hashlib.sha256(canonical(bindings).encode()).hexdigest()

    def activate(self, identifier: str, revision_id: str, expected_revision: int) -> None:
        record = self._record(identifier, expected_revision)
        revision = self.catalog.get(revision_id)
        require(revision in self.revisions(identifier), "Keine Quellenrevision dieses Assets.")
        key = self.validate_revision(revision)
        validate_slot(self.assets.definition(identifier), key)
        path = self.store.path_for(revision.data["sha256"])
        require(self.availability(revision) == "imported" and
                file_hash(path) == revision.data["sha256"],
                "Quellkopie fehlt, ist beschädigt oder nicht geprüft; erneut importieren.")
        with self.catalog.transaction():
            record = self._record(identifier, expected_revision)
            active = dict(record.data.get("active_sources", {}))
            if active.get(key.token) != revision.id:
                active[key.token] = revision.id
                self.catalog.save(record, data={**record.data, "active_sources": active})
