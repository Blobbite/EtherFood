"""Separate archive and timed trash for originals and individual project references."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json

from ..domain.assets import require
from ..domain.models import StudioError
from ..domain.relations import CARD_KINDS, validate_relation
from ..storage.blob_store import BlobStore, file_hash
from ..storage.paths import safe_target
from ..storage.sqlite_repository import canonical
from .commands import Command


def utc(value):
    require(value.tzinfo is not None, "Bereinigungszeit benötigt eine Zeitzone.")
    return value.astimezone(timezone.utc)


class LifecycleService:
    def __init__(self, project, *, now=lambda: datetime.now(timezone.utc)):
        self.project, self.catalog, self.now = project, project.catalog, now
        self.root = self.catalog.path.parent

    def state(self, identifier):
        row = self.catalog.db.execute(
            "SELECT * FROM lifecycle WHERE id=?", (identifier,)
        ).fetchone()
        return {**dict(row), "previous": json.loads(row["previous"])} if row else None

    def entries(self, state):
        return [
            self.state(row[0])
            for row in self.catalog.db.execute(
                "SELECT id FROM lifecycle WHERE state=? ORDER BY removed_at,id", (state,)
            )
        ]

    def subtree(self, identifier):
        records = self.catalog.records(include_archived=True)
        result, previous = {identifier}, set()
        while previous != result:
            previous = set(result)
            result.update(r.id for r in records if r.owner_id in previous)
        return result

    def normalize(self, identifiers):
        values = list(dict.fromkeys(identifiers))
        descendants = set()
        objects = {r.id for r in self.catalog.records(include_archived=True)}
        for key in values:
            if key in objects:
                descendants.update(self.subtree(key) - {key})
        return [key for key in values if key not in descendants]

    def impact(self, identifiers):
        result = []
        records = self.catalog.records(include_archived=True)
        for identifier in self.normalize(identifiers):
            record = next((r for r in records if r.id == identifier), None)
            if record:
                subtree = self.subtree(identifier)
                dependents = [
                    r
                    for r in records
                    if r.kind == "pipeline_usage"
                    and (
                        r.data["definition_id"] in subtree
                        or set(r.data["targets"]) & subtree
                        or any(e["usage"] in subtree for e in r.data["connections"])
                    )
                ]
                if record.kind == "script":
                    from .pipeline_workspace import PipelineWorkspace

                    workspace = PipelineWorkspace(self.project)
                    for definition in workspace.definitions(include_archived=True):
                        try:
                            data, _ = workspace.files.definition(definition.id)
                            if any(n["script_id"] == identifier for n in data["nodes"]):
                                dependents.extend(
                                    workspace.usages(definition.id, include_archived=True)
                                )
                        except StudioError:
                            continue
                result.append(
                    {
                        "id": identifier,
                        "title": record.title,
                        "kind": record.kind,
                        "children": [r.title for r in records if r.id in subtree - {identifier}],
                        "usages": sorted({r.title for r in dependents}),
                        "connections": [
                            e
                            for e in self.catalog.relations(include_inactive=True)
                            if e["source_id"] in subtree or e["target_id"] in subtree
                        ],
                    }
                )
            else:
                edge = self._edge(identifier)
                result.append(
                    {
                        "id": identifier,
                        "title": "Verwendung: " + self.catalog.get(edge["target_id"]).title,
                        "kind": "reference",
                        "children": [],
                        "usages": [],
                        "connections": [edge],
                    }
                )
        return result

    def _edge(self, identifier):
        row = self.catalog.db.execute(
            "SELECT * FROM relations WHERE id=? AND kind='uses'", (identifier,)
        ).fetchone()
        require(row is not None, "Verwendung wurde nicht gefunden.")
        return dict(row)

    def change(self, identifiers, state):
        require(state in {"archived", "trash"}, "Ungültige Ablage.")
        now = utc(self.now())
        with self.catalog.transaction():
            for identifier in self.normalize(identifiers):
                previous_state = self.state(identifier)
                if previous_state and previous_state["state"] == state:
                    continue
                require(
                    not previous_state or previous_state["state"] != "trash",
                    "Papierkorbinhalt zuerst ausdrücklich wiederherstellen.",
                )
                row = self.catalog.db.execute(
                    "SELECT 1 FROM objects WHERE id=?", (identifier,)
                ).fetchone()
                if row:
                    record = self.catalog.get(identifier)
                    require(
                        record.kind not in {"project", "global"}
                        and not record.data.get("automation"),
                        "Projektwurzel, Systemrahmen und Grunddokumente bleiben erhalten.",
                    )
                    previous = {
                        "archived": record.archived,
                        "owner_id": record.owner_id,
                        "state": previous_state,
                    }
                    self.catalog.save(record, archived=True)
                    kind = "object"
                else:
                    previous, kind = {
                        "edge": self._edge(identifier),
                        "state": previous_state,
                    }, "reference"
                removed = now.isoformat() if state == "trash" else None
                deadline = (now + timedelta(days=30)).isoformat() if state == "trash" else None
                self.catalog.db.execute(
                    "INSERT OR REPLACE INTO lifecycle VALUES (?,?,?,?,?,?)",
                    (identifier, kind, state, removed, deadline, canonical(previous)),
                )
                self.catalog.projection_dirty = True
        self.notify()

    def restore(self, identifier, *, target=None):
        item = self.state(identifier)
        require(item is not None, "Inhalt ist nicht in Archiv oder Papierkorb.")
        with self.catalog.transaction():
            if item["entity_kind"] == "reference":
                edge = self._edge(identifier)
                parent = self.project.require_active_card(target or edge["source_id"])
                original = self.project.require_active_card(edge["target_id"])
                remaining = [e for e in self.catalog.relations() if e["id"] != identifier]
                validate_relation(parent, original, "uses", remaining)
                require(
                    not any(
                        e["source_id"] == parent.id
                        and e["target_id"] == original.id
                        and e["kind"] == "uses"
                        for e in remaining
                    ),
                    "Verwendung existiert am Ziel.",
                )
                self.catalog.db.execute(
                    "UPDATE relations SET source_id=? WHERE id=?", (parent.id, identifier)
                )
            else:
                record = self.catalog.get(identifier)
                parent_id = target or record.owner_id
                parent = self.project.require_active_card(parent_id)
                if record.kind in CARD_KINDS:
                    validate_relation(
                        replace(record, archived=False),
                        parent,
                        "belongs_to",
                        [e for e in self.catalog.relations() if e["source_id"] != record.id],
                    )
                elif record.kind in {"script", "pipeline_definition"}:
                    require(parent.kind == "project", "Werkzeuge gehören zum Projekt.")
                elif record.kind not in {"document", "task", "issue"}:
                    raise StudioError(
                        "validation", "Dieses Objekt folgt seinem ursprünglichen Besitzer."
                    )
                if record.kind in CARD_KINDS:
                    self.catalog.db.execute(
                        "UPDATE relations SET target_id=? WHERE source_id=? "
                        "AND kind='belongs_to'",
                        (parent_id, identifier),
                    )
                self.catalog.save(record, archived=False, owner_id=parent_id)
            self.catalog.db.execute("DELETE FROM lifecycle WHERE id=?", (identifier,))
            self.catalog.projection_dirty = True
        self.notify()

    def command(self, commands, identifiers, state=None, *, target=None):
        identifiers = self.normalize(identifiers)
        snapshots = {key: self.state(key) for key in identifiers}
        owners = {}
        for key in identifiers:
            row = self.catalog.db.execute(
                "SELECT owner_id,archived FROM objects WHERE id=?", (key,)
            ).fetchone()
            owners[key] = dict(row) if row else {"edge": self._edge(key)}

        def forward():
            if state:
                self.change(identifiers, state)
            else:
                for key in identifiers:
                    self.restore(key, target=target)

        def backward():
            for key in identifiers:
                old = owners[key]
                if "edge" in old:
                    self._edge(key)  # Purged references cannot be resurrected by old Undo.
                    self.catalog.db.execute(
                        "UPDATE relations SET source_id=?,target_id=? WHERE id=?",
                        (old["edge"]["source_id"], old["edge"]["target_id"], key),
                    )
                else:
                    record = self.catalog.get(key)
                    self.catalog.save(
                        record, archived=bool(old["archived"]), owner_id=old["owner_id"]
                    )
                    self.catalog.db.execute(
                        "UPDATE relations SET target_id=? WHERE source_id=? "
                        "AND kind='belongs_to'",
                        (old["owner_id"], key),
                    )
                self.catalog.db.execute("DELETE FROM lifecycle WHERE id=?", (key,))
                prior = snapshots[key]
                if prior:
                    self.catalog.db.execute(
                        "INSERT INTO lifecycle VALUES (?,?,?,?,?,?)",
                        (
                            key,
                            prior["entity_kind"],
                            prior["state"],
                            prior["removed_at"],
                            prior["purge_at"],
                            canonical(prior["previous"]),
                        ),
                    )
            self.catalog.projection_dirty = True
            self.notify()

        commands.execute(
            Command(
                (
                    "Wiederherstellen und zuordnen"
                    if state is None
                    else "Archivieren" if state == "archived" else "In Papierkorb entfernen"
                ),
                forward,
                backward,
            )
        )

    def due(self):
        now = utc(self.now())
        return [
            item
            for item in self.entries("trash")
            if datetime.fromisoformat(item["purge_at"]) <= now
        ]

    def purge(self, *, on_purged=lambda identifiers: None):
        due = self.due()
        if not due:
            return []
        lock = getattr(self.project, "pipeline_run_lock", None)
        require(
            lock is None or not lock.locked(),
            "Laufenden Durchgang vor endgültiger Bereinigung sicher beenden.",
        )
        completed = []
        for item in due:
            current = self.state(item["id"])
            if current != item:
                continue
            with self.catalog.transaction():
                if item["entity_kind"] == "reference":
                    self.catalog.db.execute("DELETE FROM relations WHERE id=?", (item["id"],))
                    self.catalog.db.execute("DELETE FROM lifecycle WHERE id=?", (item["id"],))
                else:
                    self._purge_objects(self.subtree(item["id"]))
                self.catalog.projection_dirty = True
            completed.append(item["id"])
        if completed:
            on_purged(completed)
            self.notify()
        return completed

    def _purge_objects(self, identifiers):
        records = {r.id: r for r in self.catalog.records(include_archived=True)}
        require(
            not any(records[key].kind in {"project", "global"} for key in identifiers),
            "Systemrahmen dürfen nicht bereinigt werden.",
        )
        files = {}
        gallery_rows = []
        for row in self.catalog.db.execute("SELECT * FROM current_files"):
            if row["owner_id"] in identifiers:
                files[row["path"]] = row["sha256"]
        for row in self.catalog.db.execute("SELECT * FROM managed_files"):
            owned_gallery = any(
                row["path"].startswith("Ergebnisse/" + key + "/")
                for key in identifiers
                if records[key].kind == "pipeline_usage"
            )
            if row["owner_id"] in identifiers or owned_gallery:
                folder = self.project.files.path(row["owner_id"])
                files[(folder / row["path"]).relative_to(self.root).as_posix()] = row["sha256"]
                if owned_gallery:
                    gallery_rows.append((row["owner_id"], row["path"]))
        for row in self.catalog.db.execute("SELECT * FROM document_files"):
            if row["id"] in identifiers:
                folder = self.project.files.path(row["owner_id"])
                files[(folder / row["path"]).relative_to(self.root).as_posix()] = row["sha256"]
        results = list(self.catalog.db.execute("SELECT * FROM pipeline_results"))
        for row in results:
            if row["usage_id"] in identifiers or row["asset_id"] in identifiers:
                for values in json.loads(row["outputs"]).values():
                    files.update((value["path"], value["sha256"]) for value in values)
        result_paths = {
            value["path"]
            for row in results
            if row["usage_id"] in identifiers or row["asset_id"] in identifiers
            for values in json.loads(row["outputs"]).values()
            for value in values
        }
        run_paths = {
            r["path"]: r["sha256"]
            for r in self.catalog.db.execute("SELECT * FROM pipeline_run_files")
            if r["usage_id"] in identifiers or r["asset_id"] in identifiers
        }
        files.update(run_paths)
        protected = {
            r["path"]
            for r in self.catalog.db.execute("SELECT * FROM current_files")
            if r["owner_id"] not in identifiers and r["path"] not in result_paths
        }
        for record in records.values():
            if record.id not in identifiers and record.kind == "script":
                protected.add(record.data["path"])
                protected.update(".tools/scrips/" + name for name in record.data.get("helpers", []))
        for row in results:
            if row["usage_id"] not in identifiers and row["asset_id"] not in identifiers:
                protected.update(
                    value["path"]
                    for values in json.loads(row["outputs"]).values()
                    for value in values
                )
        change = self.catalog.file_changes()
        for name, digest in files.items():
            if name not in protected:
                change.delete(safe_target(self.root, name), digest)
        deleted_paths = set(files) - protected
        for owner, name in gallery_rows:
            self.catalog.db.execute(
                "DELETE FROM managed_files WHERE owner_id=? AND path=?", (owner, name)
            )
        for name in deleted_paths:
            self.catalog.db.execute("DELETE FROM current_files WHERE path=?", (name,))
            self.catalog.db.execute("DELETE FROM pipeline_run_files WHERE path=?", (name,))
        for row in self.catalog.db.execute(
            "SELECT fingerprint,outputs FROM pipeline_step_cache"
        ).fetchall():
            if any(
                item["path"] in deleted_paths
                for values in json.loads(row["outputs"]).values()
                for item in values
            ):
                self.catalog.db.execute(
                    "DELETE FROM pipeline_step_cache WHERE fingerprint=?", (row["fingerprint"],)
                )
        for row in results:
            if row["usage_id"] in identifiers or row["asset_id"] in identifiers:
                self.catalog.db.execute(
                    "DELETE FROM pipeline_result_evidence WHERE id=?", (row["id"],)
                )
        removed_edges = [
            e["id"]
            for e in self.catalog.relations(include_inactive=True)
            if e["source_id"] in identifiers or e["target_id"] in identifiers
        ]
        for key in removed_edges:
            self.catalog.db.execute("DELETE FROM lifecycle WHERE id=?", (key,))
        tables = {r[0] for r in self.catalog.db.execute("SELECT name FROM sqlite_master")}
        ordered = sorted(
            identifiers, key=lambda key: self._depth(records[key], records), reverse=True
        )
        blob_candidates = set()
        for key in ordered:
            blob_candidates.update(hashes(records[key].data))
            for old in self.catalog.history(key):
                blob_candidates.update(hashes(old["data"]))
            self.catalog.db.execute(
                "DELETE FROM relations WHERE source_id=? OR target_id=?", (key, key)
            )
            for table, column in (
                ("revisions", "object_id"),
                ("layouts", "object_id"),
                ("lifecycle", "id"),
                ("card_paths", "id"),
                ("managed_files", "owner_id"),
                ("document_files", "id"),
                ("current_files", "owner_id"),
                ("pipeline_states", "definition_id"),
                ("pipeline_attempts", "usage_id"),
                ("pipeline_step_cache", "usage_id"),
            ):
                if table in tables:
                    self.catalog.db.execute(f"DELETE FROM {table} WHERE {column}=?", (key,))
            self.catalog.db.execute(
                "DELETE FROM pipeline_results WHERE usage_id=? OR asset_id=?", (key, key)
            )
            self.catalog.db.execute("DELETE FROM objects WHERE id=?", (key,))
        for row in self.catalog.db.execute(
            "SELECT id,detail FROM pipeline_result_evidence"
        ).fetchall():
            if json.loads(row["detail"]).get("asset_id") in identifiers:
                self.catalog.db.execute(
                    "DELETE FROM pipeline_result_evidence WHERE id=?", (row["id"],)
                )
        retained = set()
        for record in self.catalog.records(include_archived=True):
            retained.update(hashes(record.data))
            for old in self.catalog.history(record.id):
                retained.update(hashes(old["data"]))
            if record.kind == "pipeline_definition":
                from .workspace_files import WorkspaceFiles

                try:
                    value, _ = WorkspaceFiles(self.project).definition(record.id)
                    retained.update(hashes(value))
                except (StudioError, OSError):
                    # An unreadable definition may still need these bytes after repair.
                    retained.update(blob_candidates)
        if "tool_packages" in tables:
            retained.update(
                row[0] for row in self.catalog.db.execute("SELECT archive_hash FROM tool_packages")
            )
        if "pipeline_plugins" in tables:
            retained.update(
                row[0] for row in self.catalog.db.execute("SELECT code_hash FROM pipeline_plugins")
            )
        store = BlobStore(self.catalog, self.root)
        for digest in blob_candidates - retained:
            path = store.path_for(digest)
            if path.is_file():
                change.delete(path, digest)
                self.catalog.db.execute("DELETE FROM blobs WHERE sha256=?", (digest,))

    @staticmethod
    def _depth(record, records):
        depth, seen = 0, set()
        while record.owner_id in records and record.id not in seen:
            seen.add(record.id)
            record = records[record.owner_id]
            depth += 1
        return depth

    def notify(self):
        executor = getattr(self.project, "pipeline_executor", None)
        if executor and executor.active:
            executor.cancel()
        callback = getattr(self.project, "pipeline_changed", None)
        if callback:
            callback()


def hashes(data):
    values = set()
    if isinstance(data, dict):
        for key, value in data.items():
            if (
                key in {"sha256", "archive_hash", "code_hash"}
                and isinstance(value, str)
                and len(value) == 64
                and not set(value) - set("0123456789abcdef")
            ):
                values.add(value)
            else:
                values.update(hashes(value))
    elif isinstance(data, list):
        for value in data:
            values.update(hashes(value))
    return values
