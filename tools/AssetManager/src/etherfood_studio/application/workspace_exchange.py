"""Portable current-file bundles with complete helper content and no transferred trust."""

from copy import deepcopy
import json
from pathlib import Path
import stat
from tempfile import TemporaryDirectory
import zipfile

from ..domain.assets import require
from ..domain.models import StudioError, new_id
from ..domain.pipeline_contract import validate_definition
from ..domain.tool_contract import relative_name
from ..storage.blob_store import BlobStore
from ..storage.file_changes import FileChanges
from ..storage.paths import safe_target
from ..storage.sqlite_repository import canonical
from .workspace_files import WorkspaceFiles, SCRIPT_ROOT, content_hash

CONTRACT = "studio-current-tools-v1"
LIMIT = 128 * 1024 * 1024


def resource_blobs(value):
    if isinstance(value, dict):
        if "sha256" in value:
            yield value
        else:
            for child in value.values():
                yield from resource_blobs(child)
    elif isinstance(value, list):
        for child in value:
            yield from resource_blobs(child)


class WorkspaceExchange:
    def __init__(self, project):
        self.project, self.catalog = project, project.catalog
        self.files = WorkspaceFiles(project)

    def export(self, identifier, target):
        record = self.catalog.get(identifier)
        scripts, definitions, content = [], [], {}
        if record.kind == "pipeline_definition":
            value, _ = self.files.definition(identifier)
            definitions.append({"title": record.title, "value": value})
            identifiers = sorted({n["script_id"] for n in value["nodes"]})
            for resource in resource_blobs(value.get("resources", {})):
                digest = resource["sha256"]
                raw = BlobStore(self.catalog, self.files.root).path_for(digest).read_bytes()
                require(content_hash(raw) == digest, "Ressource wurde verändert.")
                content["resources/" + digest] = raw
        else:
            require(record.kind == "script", "Skript oder Pipeline auswählen.")
            identifiers = [identifier]
        for key in identifiers:
            row = self.catalog.get(key)
            files = self.files.script_files(key)
            entry = {
                "id": key,
                "title": row.title,
                "description": row.data,
                "files": {name: "files/" + key + "/" + name for name in files},
            }
            scripts.append(entry)
            content.update({entry["files"][name]: raw for name, raw in files.items()})
        manifest = {
            "contract": CONTRACT,
            "scripts": scripts,
            "definitions": definitions,
            "hashes": {name: content_hash(raw) for name, raw in content.items()},
        }
        require(sum(map(len, content.values())) <= LIMIT, "Werkzeugbündel ist zu groß.")
        target = Path(target)
        require(not target.is_symlink(), "Exportziel darf kein symbolischer Link sein.")
        temporary = target.with_name("." + target.name + "." + new_id())
        try:
            with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("manifest.json", canonical(manifest))
                for name, raw in content.items():
                    archive.writestr(name, raw)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        return manifest

    def inspect(self, path):
        require(path.is_file() and path.stat().st_size <= LIMIT, "Import fehlt oder ist zu groß.")
        try:
            with zipfile.ZipFile(path) as archive:
                info = archive.infolist()
                names = [item.filename for item in info]
                require(
                    len(info) <= 4096 and len(names) == len(set(names)),
                    "Zu viele oder doppelte Dateien im Bündel.",
                )
                require(
                    sum(item.file_size for item in info) <= LIMIT, "Entpacktes Bündel ist zu groß."
                )
                for item in info:
                    relative_name(item.filename)
                    require(
                        not stat.S_ISLNK(item.external_attr >> 16) and not item.is_dir(),
                        "Nur reguläre Bündeldateien zulässig.",
                    )
                require("manifest.json" in names, "Bündelbeschreibung fehlt.")
                manifest = json.loads(archive.read("manifest.json"))
                require(manifest.get("contract") == CONTRACT, "Unbekannter Bündelvertrag.")
                hashes = manifest["hashes"]
                require(
                    set(names) == set(hashes) | {"manifest.json"}, "Unbeschriebene Bündelinhalte."
                )
                files = {}
                for name, digest in hashes.items():
                    raw = archive.read(name)
                    require(content_hash(raw) == digest, "Bündeldatei wurde verändert: " + name)
                    files[name] = raw
                return manifest, files
        except (zipfile.BadZipFile, KeyError, TypeError, ValueError) as error:
            raise StudioError("validation", "Ungültiges Werkzeugbündel.", str(error)) from error

    def import_file(self, path):
        path = Path(path)
        if path.suffix.casefold() == ".py":
            require(path.stat().st_size <= 16 * 1024 * 1024, "Skriptdatei ist zu groß.")
            raw = path.read_bytes()
            raw.decode("utf-8-sig")
            return {
                "scripts": [self.files.create_script(path.stem, code=raw).id],
                "definitions": [],
            }
        try:
            with zipfile.ZipFile(path) as archive:
                legacy = bool({"workflow.json", "toolkit.json"} & set(archive.namelist()))
        except zipfile.BadZipFile as error:
            raise StudioError("validation", "Ungültiges Werkzeugbündel.") from error
        if legacy:
            return self.import_legacy(path)
        manifest, content = self.inspect(path)
        mapping, result = {}, {"scripts": [], "definitions": []}
        require(
            len({s["id"] for s in manifest["scripts"]}) == len(manifest["scripts"]),
            "Doppelte Skriptidentität im Bündel.",
        )
        # Import catalog, files and resources atomically, without executing code.
        with self.catalog.transaction():
            for script in manifest["scripts"]:
                identifier = new_id()
                mapping[script["id"]] = identifier
                folder = "Import/" + identifier + "/"
                description = deepcopy(script["description"])
                entry = description["path"].removeprefix(SCRIPT_ROOT)
                require(entry in script["files"], "Einstiegsdatei fehlt im Bündel.")
                for name in script["files"]:
                    relative_name(name)
                helpers = [name for name in script["files"] if name != entry]
                require(
                    set(description.get("helpers", [])) == set(helpers),
                    "Hilfsdateien und Beschreibung widersprechen sich.",
                )
                description["helpers"] = [folder + name for name in helpers]
                description["bundle_root"] = folder.rstrip("/") + (
                    "/" + description["bundle_root"] if description.get("bundle_root") else ""
                )
                row = self.files.create_script(
                    script["title"],
                    identifier=identifier,
                    path=folder + entry,
                    code=content[script["files"][entry]],
                    description=description,
                )
                for name in helpers:
                    self.files._write(
                        row.id, SCRIPT_ROOT + folder + name, content[script["files"][name]]
                    )
                result["scripts"].append(row.id)
            for definition in manifest["definitions"]:
                value = deepcopy(definition["value"])
                for node in value["nodes"]:
                    require(node["script_id"] in mapping, "Verwendetes Skript fehlt im Bündel.")
                    node["script_id"] = mapping[node["script_id"]]
                from .pipeline_workspace import PipelineWorkspace

                validate_definition(
                    value, PipelineWorkspace(self.project).descriptions(), complete=False
                )
                for resource in resource_blobs(value.get("resources", {})):
                    raw = content["resources/" + resource["sha256"]]
                    with TemporaryDirectory(prefix="studio-resource-") as temporary:
                        source = Path(temporary) / "resource"
                        source.write_bytes(raw)
                        BlobStore(self.catalog, self.files.root).import_file(source)
                row = self.files.create_definition(definition["title"], definition=value)
                result["definitions"].append(row.id)
        return result

    def import_legacy(self, path):
        """One-time conversion of complete old bundles directly to current files."""
        from .tool_exchange import ToolExchange
        from .workspace_migration import WorkspaceMigration
        from ..domain.pipeline_recipes import BUILTINS
        from ..domain.tool_contract import (
            package_manifests,
            operation,
            resolve_local,
            expand_workflow,
        )

        preview = ToolExchange(self.project).preview(path)
        migration = WorkspaceMigration(self.project)
        mapping, manifests = {}, dict(BUILTINS)
        result = {"scripts": [], "definitions": []}
        batch = new_id()
        with self.catalog.transaction():
            for package in preview.packages:
                manifests.update(package_manifests(package.manifest, package.digest))
                for entry in package.manifest["steps"]:
                    key = operation(package.digest, entry["id"])
                    script = migration.import_script(
                        "import:" + batch + ":" + key, package.manifest, entry, package.files
                    )
                    mapping[key] = script.id
                    result["scripts"].append(script.id)
            for digest, raw in preview.resources.items():
                require(content_hash(raw) == digest, "Importressource wurde verändert.")
                with TemporaryDirectory(prefix="studio-resource-") as temporary:
                    source = Path(temporary) / "resource"
                    source.write_bytes(raw)
                    BlobStore(self.catalog, self.files.root).import_file(source)
            flows = [(preview.title, preview.recipe)] if preview.recipe else []
            if preview.root_package:
                package = next(p for p in preview.packages if p.digest == preview.root_package)
                flows.extend(
                    (flow["name"], resolve_local(flow["recipe"], package.digest))
                    for flow in package.manifest["flows"]
                )
            for title, recipe in flows:
                identifier = new_id()
                value = migration.convert(
                    identifier, expand_workflow(recipe, manifests), mapping, manifests
                )
                row = self.files.create_definition(title, definition=value, identifier=identifier)
                result["definitions"].append(row.id)
        return result
