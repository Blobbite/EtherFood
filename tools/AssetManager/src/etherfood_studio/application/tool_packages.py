"""Immutable multi-file tool packages, explicit trust, editable drafts and transfer."""

import ast
import base64
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import tempfile
import sys
import zipfile

from ..domain.assets import require
from ..domain.models import StudioError, new_id
from ..domain.tool_contract import (
    PACKAGE_CONTRACT,
    empty_workflow,
    operation,
    package_manifests,
    resolve_local,
    validate_package,
)
from ..storage.blob_store import BlobStore, file_hash
from ..storage.paths import safe_target
from ..storage.sqlite_repository import canonical
from ..storage.tool_archives import (
    MAX_FILE,
    archive_bytes,
    json_bytes,
    read_archive,
    read_json,
)


@dataclass(frozen=True)
class PackagePreview:
    manifest: dict
    files: dict
    digest: str
    issues: tuple[dict, ...]


def package_digest(manifest, files):
    hashes = {
        name: hashlib.sha256(files[name]).hexdigest() if name in files else None
        for name in manifest["files"]
    }
    return hashlib.sha256(json_bytes({"manifest": manifest, "files": hashes})).hexdigest()


def code_issues(manifest, files):
    result = []
    parsed = {}
    for name in manifest["files"]:
        if name not in files:
            result.append({"kind": "file", "path": name, "message": "Paketdatei fehlt: " + name})
        elif name.endswith(".py"):
            try:
                tree = ast.parse(files[name], filename=name)
                parsed[name] = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
            except (SyntaxError, UnicodeError, ValueError) as error:
                result.append(
                    {
                        "kind": "syntax",
                        "path": name,
                        "line": getattr(error, "lineno", 1),
                        "message": str(error),
                    }
                )
    for entry in manifest["steps"]:
        if entry["source"] in parsed and entry["entry_point"] not in parsed[entry["source"]]:
            result.append(
                {
                    "kind": "entry",
                    "path": entry["source"],
                    "message": "Einstiegsfunktion fehlt: " + entry["entry_point"],
                }
            )
        elif entry["source"] in parsed:
            function = parsed[entry["source"]][entry["entry_point"]]
            arguments = function.args
            positional = len(arguments.posonlyargs) + len(arguments.args)
            required = positional - len(arguments.defaults)
            if (
                required > 3
                or positional < 3
                and arguments.vararg is None
                or any(default is None for default in arguments.kw_defaults)
            ):
                result.append(
                    {
                        "kind": "interface",
                        "path": entry["source"],
                        "line": function.lineno,
                        "message": "Einstieg muss run(context, inputs, parameters) akzeptieren.",
                    }
                )
    return result


class ToolPackageService:
    def __init__(self, project):
        self.project, self.catalog = project, project.catalog
        self.store = BlobStore(self.catalog, self.catalog.path.parent)

    @staticmethod
    def inspect_content(manifest, files):
        try:
            validate_package(manifest)
            require(
                set(files) <= set(manifest["files"])
                and all(isinstance(v, bytes) and len(v) <= MAX_FILE for v in files.values()),
                "Nicht deklarierte oder zu große Paketdatei.",
            )
            issues = code_issues(manifest, files)
            digest = package_digest(manifest, files)
            local = package_manifests(manifest, digest)
            from ..domain.pipeline_recipes import BUILTINS, validate_recipe

            for flow in manifest["flows"]:
                recipe = resolve_local(flow["recipe"], digest)
                validate_recipe(recipe, {**BUILTINS, **local})
            return PackagePreview(deepcopy(manifest), dict(files), digest, tuple(issues))
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            raise StudioError(
                "validation", "Ungültiger Werkzeugpaketinhalt.", str(error)
            ) from error

    def preview(self, path):
        path = Path(path)
        require(path.is_file() and not path.is_symlink(), "Paketdatei fehlt oder ist ein Link.")
        if path.suffix.lower() == ".py":
            require(path.stat().st_size <= MAX_FILE, "Python-Datei ist zu groß.")
            manifest = {
                "contract": PACKAGE_CONTRACT,
                "id": "script-" + new_id()[:8],
                "name": path.stem,
                "description": "Importiertes Python-Skript; Anschlüsse und Bibliotheken prüfen.",
                "version": "1.0.0",
                "python": f"{sys.version_info.major}.{sys.version_info.minor}",
                "dependencies": [],
                "files": [path.name],
                "flows": [],
                "steps": [
                    {
                        "id": "process",
                        "name": path.stem,
                        "description": "Importierter Skriptbaustein",
                        "source": path.name,
                        "entry_point": "run",
                        "execution": "map",
                        "parameters": {},
                        "capabilities": [],
                        "inputs": {"image": {"type": "image"}},
                        "outputs": {
                            "image": {"type": "image", "directory": "Ergebnisse/eigener-baustein"}
                        },
                    }
                ],
            }
            return self.inspect_content(manifest, {path.name: path.read_bytes()})
        if zipfile.is_zipfile(path):
            contents = read_archive(path)
            require("manifest.json" in contents, "manifest.json fehlt im Werkzeugpaket.")
            manifest = read_json(contents.pop("manifest.json"))
        else:
            require(path.stat().st_size <= 2 * 1024 * 1024, "Paketbeschreibung ist zu groß.")
            manifest = read_json(path.read_bytes())
            validate_package(manifest)
            contents = {}
            for name in manifest["files"]:
                source = safe_target(path.parent.resolve(), name)
                if source.is_file():
                    require(source.stat().st_size <= MAX_FILE, "Paketdatei ist zu groß: " + name)
                    contents[name] = source.read_bytes()
        return self.inspect_content(manifest, contents)

    def packages(self):
        if not self.catalog.db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='tool_packages'"
        ).fetchone():
            return []
        return [
            self.details(row[0])
            for row in self.catalog.db.execute("SELECT digest FROM tool_packages ORDER BY rowid")
        ]

    def details(self, digest):
        row = self.catalog.db.execute(
            "SELECT * FROM tool_packages WHERE digest=?", (digest,)
        ).fetchone()
        require(row is not None, "Werkzeugpaket fehlt: " + digest)
        result = dict(row)
        result["manifest"] = read_json(row["manifest"].encode())
        result["files"] = json.loads(row["files"])
        return result

    def manifests(self):
        result = {}
        for package in self.packages():
            result.update(package_manifests(package["manifest"], package["digest"]))
        return result

    def contents(self, digest):
        package = self.details(digest)
        path = self.store.path_for(package["archive_hash"])
        require(
            path.is_file() and file_hash(path) == package["archive_hash"],
            "Werkzeugpaket fehlt oder wurde verändert.",
        )
        files = read_archive(path)
        manifest = read_json(files.pop("manifest.json"))
        require(
            manifest == package["manifest"] and package_digest(manifest, files) == digest,
            "Werkzeugpaket stimmt nicht mit seiner registrierten Version überein.",
        )
        return files

    def register(self, preview, *, bundled=False):
        checked = self.inspect_content(preview.manifest, preview.files)
        require(checked.digest == preview.digest, "Werkzeugpaket seit Vorschau verändert.")
        existing = self.catalog.db.execute(
            "SELECT digest FROM tool_packages WHERE digest=?", (checked.digest,)
        ).fetchone()
        if existing:
            return self.details(checked.digest)
        archive = archive_bytes({"manifest.json": json_bytes(checked.manifest), **checked.files})
        with tempfile.TemporaryDirectory(prefix="studio-tool-import-") as directory:
            path = Path(directory) / "package.zip"
            path.write_bytes(archive)
            with self.catalog.transaction():
                blob = self.store.import_file(path)
                hashes = {
                    name: hashlib.sha256(content).hexdigest()
                    for name, content in checked.files.items()
                }
                self.catalog.db.execute(
                    "INSERT INTO tool_packages VALUES (?,?,?,?,?)",
                    (
                        checked.digest,
                        canonical(checked.manifest),
                        canonical(hashes),
                        blob["sha256"],
                        int(bundled and not checked.issues),
                    ),
                )
        return self.details(checked.digest)

    def diagnostics(self, digest, *, environment=True):
        package = self.details(digest)
        issues = code_issues(package["manifest"], self.contents(digest))
        if package["manifest"]["steps"] and not package["approved"]:
            issues.append(
                {"kind": "approval", "message": "Diese Codeversion ist nicht freigegeben."}
            )
        if environment and package["manifest"]["steps"]:
            from .tool_environments import ToolEnvironments

            environments = ToolEnvironments(self.project)
            missing = environments.diagnostics(package["manifest"])
            issues += missing
            if not missing:
                issues += [
                    issue
                    for issue in environments.import_diagnostics(
                        package["manifest"], self.contents(digest)
                    )
                    if not issue["conditional"]
                ]
        return issues

    def approve(self, digest):
        package = self.details(digest)
        require(
            not code_issues(package["manifest"], self.contents(digest)),
            "Unvollständigen oder syntaktisch ungültigen Code zuerst im Entwurf korrigieren.",
        )
        with self.catalog.transaction():
            self.catalog.db.execute("UPDATE tool_packages SET approved=1 WHERE digest=?", (digest,))

    def revoke(self, digest):
        self.details(digest)
        with self.catalog.transaction():
            self.catalog.db.execute("UPDATE tool_packages SET approved=0 WHERE digest=?", (digest,))

    def trusted(self, digest):
        issues = self.diagnostics(digest)
        require(not issues, "; ".join(item["message"] for item in issues))
        return self.details(digest)

    def export(self, digest, path):
        package = self.details(digest)
        data = archive_bytes(
            {"manifest.json": json_bytes(package["manifest"]), **self.contents(digest)}
        )
        with Path(path).open("xb") as stream:
            stream.write(data)

    def recipe_data(self, digest, entry_id):
        from ..domain.pipeline_recipes import step

        package = self.details(digest)
        manifests = package_manifests(package["manifest"], digest)
        flow = next((v for v in package["manifest"]["flows"] if v["id"] == entry_id), None)
        if flow:
            recipe = resolve_local(flow["recipe"], digest)
            name = flow["name"]
        else:
            identifier = operation(digest, entry_id)
            require(identifier in manifests, "Baustein fehlt im Werkzeugpaket.")
            spec = manifests[identifier]
            recipe = empty_workflow()
            node = step(identifier, spec)
            recipe["steps"].append(node)
            for port in spec["inputs"]:
                if spec["inputs"][port] in {"image", "spritesheet"}:
                    recipe["connections"].append(
                        {
                            "from": recipe["steps"][0]["id"],
                            "out": "image",
                            "to": node["id"],
                            "in": port,
                        }
                    )
            recipe["outputs"] = {
                key: {
                    "node": node["id"],
                    "port": key,
                    **{k: v for k, v in value.items() if k != "required"},
                }
                for key, value in spec["ports"]["outputs"].items()
            }
            name = spec["name"]
        recipe["category"] = name
        return name, recipe

    def create_recipe(self, digest, entry_id, title=None):
        from .pipeline_service import PipelineService

        name, recipe = self.recipe_data(digest, entry_id)
        service = PipelineService(self.project)
        return self.project.create_card(
            "pipeline",
            title or name,
            service.project_id,
            {"project_id": service.project_id, "recipe": recipe},
        )

    def test(
        self, digest, entry_id, asset_id, *, cancelled=lambda: False, on_event=lambda event: None
    ):
        from types import SimpleNamespace
        from .build_planner import BuildPlanner
        from .tool_builds import ToolBuildService

        name, recipe = self.recipe_data(digest, entry_id)
        record = SimpleNamespace(id=new_id(), title=name, revision_no=1)
        binding = {
            "recipe": record,
            "data": recipe,
            "assignment": SimpleNamespace(id=new_id()),
            "origin": "Paketentwurf-Testlauf",
        }
        plan = ToolBuildService(self.project).plan(asset_id, binding)
        return BuildPlanner(self.project).execute(
            plan, cancelled=cancelled, on_event=on_event, publish=False
        )

    def draft(self, digest):
        package = self.details(digest)
        identifier = new_id()
        with self.catalog.transaction():
            self.catalog.db.execute(
                "INSERT INTO tool_drafts VALUES (?,?,?,?,1)",
                (
                    identifier,
                    digest,
                    canonical(package["manifest"]),
                    canonical(
                        {
                            name: base64.b64encode(content).decode("ascii")
                            for name, content in self.contents(digest).items()
                        }
                    ),
                ),
            )
        return self.load_draft(identifier)

    def load_draft(self, identifier):
        row = self.catalog.db.execute(
            "SELECT * FROM tool_drafts WHERE id=?", (identifier,)
        ).fetchone()
        require(row is not None, "Paketentwurf fehlt.")
        return {
            **dict(row),
            "manifest": json.loads(row["manifest"]),
            "files": {
                name: base64.b64decode(content)
                for name, content in json.loads(row["files"]).items()
            },
        }

    def save_draft(self, identifier, manifest, files, revision):
        require(
            sum(len(v) for v in files.values()) <= 32 * 1024 * 1024, "Paketentwurf ist zu groß."
        )
        with self.catalog.transaction():
            require(
                self.load_draft(identifier)["revision"] == revision,
                "Entwurf wurde inzwischen geändert; erneut laden.",
            )
            self.catalog.db.execute(
                "UPDATE tool_drafts SET manifest=?, files=?, revision=revision+1 WHERE id=?",
                (
                    canonical(manifest),
                    canonical(
                        {
                            name: base64.b64encode(data).decode("ascii")
                            for name, data in files.items()
                        }
                    ),
                    identifier,
                ),
            )
        return self.load_draft(identifier)

    def publish_draft(self, identifier):
        draft = self.load_draft(identifier)
        preview = self.inspect_content(draft["manifest"], draft["files"])
        require(not preview.issues, "; ".join(v["message"] for v in preview.issues))
        if draft["base_digest"]:
            base = self.details(draft["base_digest"])
            require(
                preview.digest == base["digest"]
                or preview.manifest["version"] != base["manifest"]["version"],
                "Geänderten Code unter einer neuen Paketversion übernehmen.",
            )
        return self.register(preview)
