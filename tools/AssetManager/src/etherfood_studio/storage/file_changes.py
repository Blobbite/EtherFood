"""Recoverable local file changes coordinated with the catalog's outer transaction."""

import json
import os
import shutil

from ..domain.assets import require
from ..domain.models import new_id
from .blob_store import file_hash
from .paths import make_directory, safe_target
from .sqlite_repository import canonical


class FileChanges:
    def __init__(self, catalog, *, journal=None):
        self.catalog, self.root = catalog, catalog.path.parent
        self.identifier = new_id()
        self.operations, self.backups = [], []
        directory = make_directory(self.root, ".asset-studio/file-transactions")
        self.journal = journal or directory / (self.identifier + ".json")

    def record(self, operation):
        self.operations.append(operation)
        temporary = self.journal.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            stream.write(canonical({"id": self.identifier, "operations": self.operations,
                                    "backups": self.backups}) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.journal)

    def relative(self, path):
        return str(path.relative_to(self.root))

    def mkdir(self, path):
        if path == self.root:
            return
        self.mkdir(path.parent)
        safe_target(self.root, self.relative(path))
        if not path.exists():
            self.record({"kind": "directory", "path": self.relative(path)})
            path.mkdir()
        require(path.is_dir(), "Ablage ist kein Ordner: " + self.relative(path))

    def move(self, source, target):
        safe_target(self.root, self.relative(source))
        safe_target(self.root, self.relative(target))
        require(not target.exists(), "Ablageziel existiert bereits: " + self.relative(target))
        self.mkdir(target.parent)
        self.record({"kind": "move", "source": self.relative(source),
                     "target": self.relative(target)})
        source.rename(target)

    def write(self, target, *, content=None, source=None, previous=None):
        """Only replace a file whose exact previous content is owned by this projection."""
        self.mkdir(target.parent)
        safe_target(self.root, self.relative(target))
        if target.exists():
            require(previous is not None and target.is_file() and file_hash(target) == previous,
                    "Fremde oder extern geänderte Datei bleibt erhalten: " + self.relative(target))
        temporary = target.with_name(".studio-" + new_id() + ".tmp")
        self.record({"kind": "temporary", "path": self.relative(temporary)})
        with temporary.open("xb") as output:
            if source is not None:
                with source.open("rb") as incoming:
                    shutil.copyfileobj(incoming, output)
            else:
                output.write(content)
            output.flush()
            os.fsync(output.fileno())
        if target.exists():
            backup = target.with_name(".studio-" + new_id() + ".backup")
            self.backups.append({"path": self.relative(backup), "sha256": previous})
            self.move(target, backup)
        self.move(temporary, target)

    def committed(self):
        self.catalog.db.execute("INSERT INTO file_commits VALUES (?)", (self.identifier,))

    def finish(self):
        for entry in self.backups:
            path = safe_target(self.root, entry["path"])
            if path.exists():
                require(path.is_file() and file_hash(path) == entry["sha256"],
                        "Geänderte Sicherungsdatei wird nicht entfernt.")
                path.unlink()
        self.journal.unlink(missing_ok=True)

    def rollback(self):
        for operation in reversed(self.operations):
            if operation["kind"] == "move":
                source = safe_target(self.root, operation["source"])
                target = safe_target(self.root, operation["target"])
                if target.exists():
                    require(not source.exists(), "Dateikonflikt bei Rücknahme; Journal bleibt.")
                    target.rename(source)
            else:
                path = safe_target(self.root, operation["path"])
                if operation["kind"] == "temporary":
                    path.unlink(missing_ok=True)
                elif path.exists():
                    # Never recursively delete: a foreign file may have appeared meanwhile.
                    path.rmdir()
        self.journal.unlink(missing_ok=True)

    @classmethod
    def recover(cls, catalog):
        directory = safe_target(catalog.path.parent, ".asset-studio/file-transactions")
        if not directory.exists():
            return
        for path in sorted(directory.glob("*.json")):
            safe_target(catalog.path.parent, str(path.relative_to(catalog.path.parent)))
            data = json.loads(path.read_text(encoding="utf-8"))
            require(data["id"] + ".json" == path.name, "Ungültiges Dateiänderungsjournal.")
            change = cls(catalog, journal=path)
            change.identifier = data["id"]
            change.operations, change.backups = data["operations"], data["backups"]
            committed = catalog.db.execute("SELECT 1 FROM file_commits WHERE id=?",
                                            (change.identifier,)).fetchone()
            change.finish() if committed else change.rollback()
