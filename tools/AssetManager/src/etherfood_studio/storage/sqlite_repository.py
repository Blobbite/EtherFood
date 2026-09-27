"""Transactional catalog, backups, optimistic edits and explicit snapshots."""

from contextlib import contextmanager
from dataclasses import asdict, replace
import json
from pathlib import Path
import math
import sqlite3
from threading import RLock
from typing import Any, Iterator
from uuid import UUID

from ..domain.models import (
    IMMUTABLE, KINDS, MAX_SNAPSHOT, Record, StudioError, UNTRUSTED_IMPORT, new_id, utc_now,
)
from .migrations import CURRENT_VERSION, MIGRATIONS
from .paths import real_path, safe_target


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False)


class Catalog:
    """One controlled connection; workers return results to its owning service."""

    def __init__(self, path: Path, *, create: bool = False,
                 target_version: int = CURRENT_VERSION, read_only: bool = False) -> None:
        self.path = real_path(path, must_exist=not create)
        self._lock = RLock()
        self._depth = 0
        self.last_backup: Path | None = None
        if create:
            target = safe_target(self.path.parent, self.path.name)
            try:
                with target.open("xb"):
                    pass
            except FileExistsError as exc:
                raise StudioError("conflict", "Katalog existiert bereits.") from exc
        try:
            mode = "ro" if read_only else "rw"
            self.db = sqlite3.connect(self.path.as_uri() + "?mode=" + mode, uri=True,
                                      isolation_level=None, check_same_thread=False, timeout=5)
            self.db.row_factory = sqlite3.Row
            self.db.execute("PRAGMA foreign_keys=ON")
            exists = self.db.execute(
                "SELECT name FROM sqlite_master WHERE name='schema_version'",
            ).fetchone()
            if not exists and not create:
                raise StudioError("validation", "Datei ist kein Studio-Katalog.")
            version = self.db.execute("SELECT version FROM schema_version").fetchone()[0] \
                if exists else 0
            if version > target_version:
                raise StudioError("validation", "Katalogversion ist neuer als diese Anwendung.")
            if version < target_version:
                if read_only:
                    raise StudioError("unavailable", "Katalog zuerst regulär öffnen/migrieren.")
                if version:
                    self.last_backup = self.path.with_name(
                        self.path.name + ".studio-backup-" + new_id(),
                    )
                    with sqlite3.connect(self.last_backup) as backup:
                        self.db.backup(backup)
                with self.transaction():
                    for step in range(version + 1, target_version + 1):
                        for statement in MIGRATIONS[step]:
                            self.db.execute(statement)
                        self.db.execute("UPDATE schema_version SET version=?", (step,))
            if self.db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise StudioError("integrity", "Katalog ist beschädigt.")
        except (sqlite3.Error, StudioError) as exc:
            if hasattr(self, "db"):
                self.db.close()
            if isinstance(exc, StudioError):
                raise
            raise StudioError("storage", "Katalog konnte nicht geöffnet werden.", str(exc)) from exc

    def close(self) -> None:
        self.db.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        with self._lock:
            outer = self._depth == 0
            if outer:
                self.db.execute("BEGIN IMMEDIATE")
            self._depth += 1
            try:
                yield
                if outer:
                    self.db.execute("COMMIT")
            except Exception:
                if outer and self.db.in_transaction:
                    self.db.execute("ROLLBACK")
                raise
            finally:
                self._depth -= 1

    @staticmethod
    def _decode(row: sqlite3.Row) -> Record:
        value = dict(row)
        try:
            value["data"] = json.loads(value["data"])
            UUID(value["id"])
            if (not isinstance(value["data"], dict) or value["kind"] not in KINDS
                    or not isinstance(value["title"], str) or not value["title"].strip()):
                raise ValueError("Ungültige Metadaten")
        except (ValueError, TypeError, AttributeError) as exc:
            raise StudioError("integrity", "Katalog: ungültige Metadaten.", str(exc)) from exc
        value["archived"] = bool(value["archived"])
        return Record(**value)

    def get(self, identifier: str) -> Record:
        row = self.db.execute("SELECT * FROM objects WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise StudioError("validation", "Datensatz nicht gefunden.", identifier)
        return self._decode(row)

    def records(self, *, include_archived: bool = False) -> list[Record]:
        query = "SELECT * FROM objects"
        if not include_archived:
            query += " WHERE archived=0"
        return [self._decode(row) for row in self.db.execute(query + " ORDER BY id")]

    def create(self, kind: str, title: str, owner_id: str | None = None,
               data: dict | None = None, *, identifier: str | None = None) -> Record:
        if kind not in KINDS or not title.strip() or len(title) > 256:
            raise StudioError("validation", "Typ oder Titel ist ungültig (maximal 256 Zeichen).")
        identifier = identifier or new_id()
        UUID(identifier)
        now = utc_now()
        record = Record(identifier, kind, title.strip(), owner_id, data or {}, 1, False, now, now)
        with self.transaction():
            self._insert(record)
        return record

    def _insert(self, record: Record) -> None:
        self.db.execute("INSERT INTO objects VALUES (?,?,?,?,?,?,?,?,?)", (
            record.id, record.kind, record.title, record.owner_id, canonical(record.data),
            record.revision_no, int(record.archived), record.created_at, record.updated_at,
        ))
        self._history(record)

    def _history(self, record: Record) -> None:
        self.db.execute("INSERT INTO revisions VALUES (?,?,?)", (
            record.id, record.revision_no, canonical(asdict(record)),
        ))

    def save(self, record: Record, *, title: str | None = None, data: dict | None = None,
             owner_id: str | None = None, archived: bool | None = None) -> Record:
        if record.kind in IMMUTABLE:
            raise StudioError("validation", "Registrierte Revision ist unveränderlich.")
        changed = replace(
            record, title=record.title if title is None else title.strip(),
            data=record.data if data is None else data,
            owner_id=record.owner_id if owner_id is None else owner_id,
            archived=record.archived if archived is None else archived,
            revision_no=record.revision_no + 1, updated_at=utc_now(),
        )
        if not changed.title or len(changed.title) > 256:
            raise StudioError("validation", "Titel fehlt oder ist zu lang.")
        with self.transaction():
            result = self.db.execute(
                "UPDATE objects SET title=?,owner_id=?,data=?,revision_no=?,archived=?,"
                "updated_at=? WHERE id=? AND revision_no=?",
                (changed.title, changed.owner_id, canonical(changed.data), changed.revision_no,
                 int(changed.archived), changed.updated_at, record.id, record.revision_no),
            )
            if result.rowcount != 1:
                raise StudioError("conflict", "Neuere Änderung vorhanden. Bitte neu laden.")
            self._history(changed)
        return changed

    def history(self, identifier: str) -> list[dict]:
        return [json.loads(row[0]) for row in self.db.execute(
            "SELECT snapshot FROM revisions WHERE object_id=? ORDER BY revision_no", (identifier,),
        )]

    def relations(self) -> list[dict]:
        return [dict(row) for row in self.db.execute("SELECT * FROM relations ORDER BY id")]

    def add_relation(self, source: str, target: str, kind: str,
                     *, identifier: str | None = None) -> str:
        identifier = identifier or new_id()
        with self.transaction():
            self.db.execute("INSERT INTO relations VALUES (?,?,?,?)",
                            (identifier, source, target, kind))
        return identifier

    def remove_relation(self, identifier: str) -> None:
        with self.transaction():
            self.db.execute("DELETE FROM relations WHERE id=?", (identifier,))

    def layout(self, identifier: str) -> dict:
        row = self.db.execute(
            "SELECT data FROM layouts WHERE object_id=?", (identifier,),
        ).fetchone()
        data = json.loads(row[0]) if row else {}
        self.validate_layout(data)
        return data

    @staticmethod
    def validate_layout(data: dict) -> None:
        if not isinstance(data, dict):
            raise StudioError("validation", "Ungültige Layoutdaten.")
        for key in ("x", "y", "w", "h"):
            value = data.get(key)
            if value is not None and (not isinstance(value, (float, int))
                                      or not math.isfinite(value)):
                raise StudioError("validation", "Nur endliche Zahlen für Position und Größe.")
            if key in {"w", "h"} and value is not None and not 1 <= value <= 10000:
                raise StudioError("validation", "Kartengröße außerhalb zulässiger Grenzen.")
        if "collapsed" in data and not isinstance(data["collapsed"], bool):
            raise StudioError("validation", "Ungültiger Gruppenzustand.")
        if "manual" in data:
            if not isinstance(data["manual"], dict) or set(data["manual"]) - {"x", "y"}:
                raise StudioError("validation", "Ungültige gespeicherte Anordnung.")
            Catalog.validate_layout(data["manual"])

    def save_layout(self, identifier: str, data: dict) -> None:
        self.validate_layout(data)
        with self.transaction():
            self.db.execute("INSERT INTO layouts VALUES (?,?) ON CONFLICT(object_id) "
                            "DO UPDATE SET data=excluded.data", (identifier, canonical(data)))

    def inventory_root(self, root: Path) -> str:
        """Local machine binding; intentionally absent from portable metadata snapshots."""
        path = str(real_path(root))
        with self.transaction():
            row = self.db.execute(
                "SELECT id FROM inventory_roots WHERE local_path=?", (path,),
            ).fetchone()
            if row:
                return row[0]
            identifier = new_id()
            self.db.execute("INSERT INTO inventory_roots VALUES (?,?)", (identifier, path))
            return identifier

    def inventory_path(self, identifier: str) -> Path:
        row = self.db.execute(
            "SELECT local_path FROM inventory_roots WHERE id=?", (identifier,),
        ).fetchone()
        if not row:
            raise StudioError("path", "Lokale Bestandswurzel fehlt; neu erfassen.")
        return real_path(Path(row[0]))

    def export_snapshot(self) -> str:
        with self.transaction():
            objects = [asdict(item) for item in self.records(include_archived=True)]
            layouts = {item["id"]: self.layout(item["id"]) for item in objects}
            return canonical({"schema_version": 1, "kind": "metadata_snapshot",
                              "objects": objects, "relations": self.relations(),
                              "layouts": layouts})

    def import_snapshot(self, content: str) -> None:
        if len(content.encode("utf-8")) > MAX_SNAPSHOT:
            raise StudioError("validation", "Snapshot überschreitet die Größenbegrenzung.")
        try:
            value = json.loads(content)
            if set(value) != {"schema_version", "kind", "objects", "relations", "layouts"}:
                raise ValueError("Unbekannte Snapshot-Felder")
            if value["schema_version"] != 1 or value["kind"] != "metadata_snapshot":
                raise ValueError("Unbekannte Snapshot-Version")
            records = [Record(**row) for row in value["objects"]]
            for record in records:
                UUID(record.id)
                if record.kind not in KINDS or not record.title or record.revision_no < 1:
                    raise ValueError("Ungültiger Datensatz")
        except (ValueError, TypeError, KeyError) as exc:
            raise StudioError("validation", "Snapshot ist ungültig.", str(exc)) from exc
        accepted = {row.id for row in records if row.kind not in UNTRUSTED_IMPORT}
        with self.transaction():
            if self.records(include_archived=True):
                raise StudioError("conflict", "Import nur in einen neuen leeren Katalog erlaubt.")
            for record in records:
                if record.id not in accepted:
                    continue
                data = dict(record.data)
                data.pop("evidence", None)
                data.pop("approval", None)
                if record.kind in {"task", "issue"}:
                    data["status"] = "open"
                if record.kind in IMMUTABLE:
                    data["verification"] = "not_run"
                self._insert(replace(record, data=data))
            for relation in value["relations"]:
                if relation["source_id"] in accepted and relation["target_id"] in accepted:
                    self.add_relation(relation["source_id"], relation["target_id"],
                                      relation["kind"], identifier=relation["id"])
            for identifier, layout in value["layouts"].items():
                if identifier in accepted:
                    self.save_layout(identifier, layout)
