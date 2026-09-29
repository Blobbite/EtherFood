"""Authoritative current scripts/definitions, with journalled writes and edit conflicts."""

import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

from ..domain.assets import require
from ..domain.models import StudioError, new_id
from ..domain.pipeline_contract import empty_definition, script_description
from ..domain.tool_contract import relative_name
from ..storage.blob_store import file_hash
from ..storage.paths import safe_target
from ..storage.sqlite_repository import canonical
from .project_files import component

SCRIPT_ROOT = ".tools/scrips/"
PIPELINE_ROOT = ".tools/piplins/"
MAX_CURRENT_FILE = 16 * 1024 * 1024


def content_hash(content):
    return hashlib.sha256(content).hexdigest()


def default_script():
    return {
        "entry_point": "run",
        "execution": "map",
        "description": "",
        "inputs": {"input": {"type": "file"}},
        "outputs": {"output": {"type": "file"}},
        "parameters": {},
        "dependencies": [],
        "helpers": [],
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
    }


class WorkspaceFiles:
    def __init__(self, project):
        self.project, self.catalog = project, project.catalog
        self.root = self.catalog.path.parent

    def initialize(self):
        with self.catalog.transaction():
            change = self.catalog.file_changes()
            for name in (SCRIPT_ROOT, PIPELINE_ROOT):
                change.mkdir(safe_target(self.root, name.rstrip("/")))

    def records(self, kind, *, include_archived=False):
        return [
            r for r in self.catalog.records(include_archived=include_archived) if r.kind == kind
        ]

    def path(self, record):
        prefix = SCRIPT_ROOT if record.kind == "script" else PIPELINE_ROOT
        relative = record.data.get("path", "")
        require(relative.startswith(prefix), "Aktuelle Werkzeugdatei hat keine gültige Ablage.")
        return safe_target(self.root, relative)

    def read(self, identifier):
        record = self.catalog.get(identifier)
        path = self.path(record)
        require(path.is_file(), "Aktuelle Datei fehlt: " + record.data["path"])
        require(path.stat().st_size <= MAX_CURRENT_FILE, "Werkzeugdatei ist zu groß.")
        raw = path.read_bytes()
        return raw, content_hash(raw)

    def text(self, identifier):
        raw, digest = self.read(identifier)
        try:
            return raw.decode("utf-8-sig"), digest
        except UnicodeError as error:
            raise StudioError("validation", "Werkzeugdatei benötigt UTF-8.") from error

    def definition(self, identifier):
        record = self.catalog.get(identifier)
        require(record.kind == "pipeline_definition", "Pipelinedefinition auswählen.")
        raw, digest = self.read(identifier)
        try:
            value = json.loads(raw)
            require(value.get("id") == identifier, "Datei enthält eine andere Pipelineidentität.")
            return value, digest
        except (ValueError, AttributeError) as error:
            raise StudioError("validation", "Ablaufdatei ist kein gültiges JSON.") from error

    def _write(self, owner, path, raw, previous=None):
        require(len(raw) <= MAX_CURRENT_FILE, "Werkzeugdatei ist zu groß.")
        target = safe_target(self.root, path)
        if target.is_file() and previous is not None and file_hash(target) == previous:
            if content_hash(raw) == previous:
                return
        self.catalog.file_changes().write(target, content=raw, previous=previous)
        self.catalog.db.execute(
            "INSERT INTO current_files VALUES (?,?,?) ON CONFLICT(owner_id,path) "
            "DO UPDATE SET sha256=excluded.sha256",
            (owner, path, content_hash(raw)),
        )

    def create_script(self, title, *, path=None, code=None, description=None, identifier=None):
        identifier = identifier or new_id()
        relative = path or (component(title) + "--" + identifier[:8] + ".py")
        relative_name(relative)
        require(relative.endswith(".py"), "Eine Python-Datei benötigt die Endung .py.")
        data = default_script() | deepcopy(description or {})
        script_description(data)
        data["path"] = SCRIPT_ROOT + relative
        code = (
            code
            if code is not None
            else (
                "def run(context, inputs, parameters):\n"
                '    """Eingaben prüfen und Ergebnisse in context.output erzeugen."""\n'
                '    raise NotImplementedError("Verarbeitung noch nicht implementiert")\n'
            )
        )
        raw = code.encode("utf-8") if isinstance(code, str) else code
        with self.catalog.transaction():
            record = self.catalog.create(
                "script", title, self.project.project().id, data, identifier=identifier
            )
            self._write(record.id, data["path"], raw)
        return record

    def create_definition(self, title, *, definition=None, identifier=None):
        identifier = identifier or new_id()
        value = deepcopy(definition) if definition is not None else empty_definition(identifier)
        value["id"] = identifier
        path = PIPELINE_ROOT + component(title) + "--" + identifier[:8] + ".json"
        with self.catalog.transaction():
            record = self.catalog.create(
                "pipeline_definition",
                title,
                self.project.project().id,
                {"path": path, "description": ""},
                identifier=identifier,
            )
            self._write(record.id, path, (canonical(value) + "\n").encode())
            self.catalog.db.execute(
                "INSERT INTO pipeline_states(definition_id) VALUES (?)", (record.id,)
            )
        return record

    def save(self, identifier, text, expected_hash, expected_revision):
        record = self.catalog.get(identifier)
        self.project._check_revision(record, expected_revision)
        require(not record.archived, "Inaktive Werkzeugdateien sind schreibgeschützt.")
        raw, actual = self.read(identifier)
        if actual != expected_hash:
            raise StudioError(
                "conflict",
                "Datei wurde extern geändert. Entwurf behalten und "
                "Änderungen vor dem Speichern vergleichen.",
            )
        encoded = text.encode("utf-8") if isinstance(text, str) else text
        if raw.startswith(b"\xef\xbb\xbf") and not encoded.startswith(b"\xef\xbb\xbf"):
            encoded = b"\xef\xbb\xbf" + encoded
        if raw == encoded:
            return record, actual
        with self.catalog.transaction():
            self._write(identifier, record.data["path"], encoded, actual)
            # No code snapshot in the catalog: only metadata and the file identity.
            record = self.catalog.save(
                record, data=record.data | {"saved_hash": content_hash(encoded)}
            )
        return record, content_hash(encoded)

    def save_description(self, identifier, description, expected_revision):
        record = self.catalog.get(identifier)
        self.project._check_revision(record, expected_revision)
        require(record.kind == "script" and not record.archived, "Aktives Skript auswählen.")
        data = record.data | deepcopy(description)
        require(data["path"] == record.data["path"], "Dateien über Verschieben umordnen.")
        script_description(data)
        return self.catalog.save(record, data=data)

    def helper(self, identifier, relative, content, *, expected_hash=None):
        record = self.catalog.get(identifier)
        require(record.kind == "script" and not record.archived, "Aktives Skript auswählen.")
        relative_name(relative)
        with self.catalog.transaction():
            self._write(identifier, SCRIPT_ROOT + relative, content, expected_hash)
            helpers = sorted(set(record.data.get("helpers", [])) | {relative})
            return self.catalog.save(record, data=record.data | {"helpers": helpers})

    def script_files(self, identifier):
        record = self.catalog.get(identifier)
        require(record.kind == "script" and not record.archived, "Skript fehlt oder ist inaktiv.")
        names = set(record.data.get("helpers", []))
        names.add(record.data["path"].removeprefix(SCRIPT_ROOT))
        result = {}
        for name in sorted(names):
            relative_name(name)
            path = safe_target(self.root, SCRIPT_ROOT + name)
            require(path.is_file(), "Benötigte Skript-/Hilfsdatei fehlt: " + name)
            require(path.stat().st_size <= MAX_CURRENT_FILE, "Hilfsdatei ist zu groß: " + name)
            result[name] = path.read_bytes()
        return result

    def create_folder(self, relative):
        relative_name(relative)
        with self.catalog.transaction():
            target = safe_target(self.root, SCRIPT_ROOT + relative)
            require(not target.exists(), "Skriptordner existiert bereits.")
            self.catalog.file_changes().mkdir(target)

    def move(self, old_relative, new_relative):
        """Move actual files; preserve IDs and refuse newly broken local imports."""
        relative_name(old_relative)
        relative_name(new_relative)
        require(
            not new_relative.startswith(old_relative + "/"),
            "Ordner kann nicht in sich selbst verschoben werden.",
        )
        source = safe_target(self.root, SCRIPT_ROOT + old_relative)
        target = safe_target(self.root, SCRIPT_ROOT + new_relative)
        require(source.exists() and not target.exists(), "Quelle fehlt oder Ziel existiert.")
        affected = []

        def relocated(name):
            return (
                new_relative + name[len(old_relative) :]
                if (name == old_relative or name.startswith(old_relative + "/"))
                else name
            )

        for record in self.records("script", include_archived=True):
            name = record.data["path"].removeprefix(SCRIPT_ROOT)
            helpers = record.data.get("helpers", [])
            if relocated(name) == name and all(relocated(h) == h for h in helpers):
                continue
            files = self.script_files(record.id) if not record.archived else {}
            before = local_import_issues(files)
            changed = {relocated(k): v for k, v in files.items()}
            after = local_import_issues(changed)
            after += moved_import_issues(
                files, changed, relocated, record.data.get("bundle_root", "")
            )
            require(
                not after or after == before,
                "Verschieben würde lokale Imports beschädigen: " + "; ".join(after),
            )
            data = record.data | {
                "path": SCRIPT_ROOT + relocated(name),
                "helpers": [relocated(h) for h in helpers],
            }
            if data.get("bundle_root"):
                data["bundle_root"] = relocated(data["bundle_root"])
            affected.append((record, data))
        with self.catalog.transaction():
            self.catalog.file_changes().move(source, target)
            owner = self.project.project().id
            layout = self.catalog.layout(owner)
            order = layout.get("script_tree_order", {})
            if order:
                moved_order = {
                    ("folder:" + relocated(key[7:]) if key.startswith("folder:") else key): rank
                    for key, rank in order.items()
                }
                if moved_order != order:
                    self.catalog.save_layout(owner, layout | {"script_tree_order": moved_order})
            for record, data in affected:
                self.catalog.save(record, data=data)
            rows = self.catalog.db.execute("SELECT * FROM current_files").fetchall()
            for row in rows:
                if not row["path"].startswith(SCRIPT_ROOT):
                    continue
                name = row["path"].removeprefix(SCRIPT_ROOT)
                if name != relocated(name):
                    self.catalog.db.execute(
                        "UPDATE current_files SET path=? WHERE path=?",
                        (SCRIPT_ROOT + relocated(name), row["path"]),
                    )


def local_import_issues(files):
    """Resolve relative imports without importing or executing any user module."""
    issues = []
    for name, raw in files.items():
        if not name.endswith(".py"):
            continue
        try:
            tree = ast.parse(raw, filename=name)
        except (SyntaxError, UnicodeError, ValueError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.level:
                continue
            parents = PurePosixPath(name).parent.parts
            if node.level > len(parents) + 1:
                issues.append(f"{name}:{node.lineno}: relativer Import verlässt Skriptbereich")
                continue
            prefix = "/".join(parents[: len(parents) - node.level + 1])
            modules = [node.module] if node.module else [alias.name for alias in node.names]
            for module in modules:
                path = "/".join(v for v in (prefix, module.replace(".", "/")) if v)
                if path + ".py" not in files and path + "/__init__.py" not in files:
                    issues.append(f"{name}:{node.lineno}: Hilfsmodul fehlt: {module}")
    return issues


def moved_import_issues(before, after, relocate, bundle_root):
    """Block moves that break formerly resolved local absolute imports or literal resources."""
    issues = []
    for name, raw in before.items():
        if not name.endswith(".py"):
            continue
        try:
            tree = ast.parse(raw)
        except (SyntaxError, UnicodeError, ValueError):
            continue
        old_roots = [str(PurePosixPath(name).parent), bundle_root, ""]
        new_roots = [str(PurePosixPath(relocate(name)).parent), relocate(bundle_root), ""]

        def candidates(roots, relative):
            return ["/".join(v for v in (root, relative) if v and v != ".") for root in roots]

        for node in ast.walk(tree):
            modules = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else (
                    [node.module]
                    if isinstance(node, ast.ImportFrom) and not node.level and node.module
                    else []
                )
            )
            for module in modules:
                relative = module.replace(".", "/")
                old = candidates(old_roots, relative)
                new = candidates(new_roots, relative)
                exists = lambda paths, files: any(
                    path + suffix in files for path in paths for suffix in (".py", "/__init__.py")
                )
                if exists(old, before) and not exists(new, after):
                    issues.append(f"{name}:{node.lineno}: Import wird ungültig: {module}")
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value in before
            ):
                if node.value not in after:
                    issues.append(
                        f"{name}:{node.lineno}: Dateiverweis vor Verschieben anpassen: {node.value}"
                    )
    return issues
