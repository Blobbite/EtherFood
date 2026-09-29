"""Recoverable migration of bound legacy code into authoritative current project files."""

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
from uuid import NAMESPACE_URL, uuid5
import zipfile

from ..domain.assets import require
from ..domain.models import StudioError, utc_now
from ..domain.pipeline_contract import INPUT, empty_definition
from ..domain.tool_contract import expand_workflow, is_workflow, operation
from ..storage.blob_store import file_hash
from ..storage.paths import make_directory, safe_target
from ..storage.sqlite_repository import canonical
from .pipeline_workspace import PipelineWorkspace
from .project_files import component
from .workspace_files import PIPELINE_ROOT, SCRIPT_ROOT, WorkspaceFiles, content_hash

MIGRATION = "current-pipeline-files-v1"


def migrated_id(value):
    return str(uuid5(NAMESPACE_URL, "etherfood-current-pipeline:" + value))


class WorkspaceMigration:
    def __init__(self, project):
        self.project, self.catalog = project, project.catalog
        self.root = self.catalog.path.parent
        self.files = WorkspaceFiles(project)

    def state(self):
        row = self.catalog.db.execute(
            "SELECT * FROM workspace_migrations WHERE name=?", (MIGRATION,)
        ).fetchone()
        return dict(row) if row else None

    def backup(self):
        directory = make_directory(self.root, ".asset-studio/migrations/" + MIGRATION)
        database = directory / "catalog.sqlite"
        if database.exists():
            require(
                (directory / "manifest.json").is_file(),
                "Unvollständige Migrationssicherung; zuerst wiederherstellen.",
            )
            return directory
        temporary = directory / "catalog.pending"
        with sqlite3.connect(temporary) as copy:
            self.catalog.db.backup(copy)
        paths = set()
        for row in self.catalog.db.execute(
            "SELECT owner_id,path FROM managed_files UNION SELECT owner_id,path FROM document_files"
        ):
            folder = self.catalog.db.execute(
                "SELECT path FROM card_paths WHERE id=?", (row["owner_id"],)
            ).fetchone()
            prefix = folder[0] + "/" if folder else ""
            path = safe_target(self.root, prefix + row["path"])
            if path.is_file():
                paths.add(path)
        tables = {r[0] for r in self.catalog.db.execute("SELECT name FROM sqlite_master")}
        if "jobs" in tables:
            from ..pipelines.processes import identity

            for job in self.catalog.db.execute("SELECT * FROM jobs"):
                require(
                    job["status"] not in {"running", "cancelling"}
                    or identity(job["owner_pid"]) != job["owner_stamp"],
                    "Alte Verarbeitung läuft noch; vor Übernahme kontrolliert beenden.",
                )
                folder = safe_target(self.root, ".asset-studio/jobs/" + job["id"])
                if folder.is_dir():
                    for path in folder.rglob("*"):
                        safe_target(self.root, path.relative_to(self.root).as_posix())
                        if path.is_file():
                            paths.add(path)
        manifest = []
        with zipfile.ZipFile(directory / "managed-files.zip", "w") as archive:
            for path in sorted(paths):
                name = path.relative_to(self.root).as_posix()
                digest = file_hash(path)
                archive.write(path, name)
                require(file_hash(path) == digest, "Datei während Sicherung geändert: " + name)
                manifest.append({"path": name, "sha256": digest, "length": path.stat().st_size})
        (directory / "manifest.json").write_text(
            canonical(
                {
                    "contract": MIGRATION,
                    "created_at": utc_now(),
                    "database": file_hash(temporary),
                    "files": manifest,
                }
            ),
            encoding="utf-8",
        )
        temporary.rename(database)
        return directory

    def run(self, *, checkpoint=lambda step: None):
        state = self.state()
        if state and state["state"] == "files_ready":
            return self.finish(json.loads(state["detail"]), checkpoint)
        from .pipeline_service import PipelineService
        from .tool_packages import ToolPackageService

        legacy = PipelineService(self.project)
        packages = ToolPackageService(self.project)
        old = [r for r in self.catalog.records(include_archived=True) if r.kind == "pipeline"]
        registered = packages.packages()
        drafts = list(self.catalog.db.execute("SELECT id FROM tool_drafts"))
        tables = {r[0] for r in self.catalog.db.execute("SELECT name FROM sqlite_master")}
        has_legacy = bool(
            old
            or registered
            or drafts
            or "jobs" in tables
            and self.catalog.db.execute("SELECT 1 FROM jobs LIMIT 1").fetchone()
            or any(r.kind == "build" for r in self.catalog.records(include_archived=True))
        )
        backup = self.backup() if has_legacy else None
        result = {
            "backup": backup.relative_to(self.root).as_posix() if backup else None,
            "definitions": [],
            "scripts": [],
            "usages": [],
            "notices": [],
        }
        # One SQL transaction and the existing file journal: interrupted conversion is reversible.
        with self.catalog.transaction():
            self.files.initialize()
            if any(not is_workflow(r.data["recipe"]) for r in old):
                from .workflow_migration import WorkflowMigration

                WorkflowMigration(self.project).ensure()
                old = [
                    r for r in self.catalog.records(include_archived=True) if r.kind == "pipeline"
                ]
            manifests = legacy.manifests()
            expanded = {}
            for record in old:
                recipe = record.data["recipe"]
                if not is_workflow(recipe):
                    from .workflow_migration import WorkflowMigration
                    from .builtin_tools import ensure
                    from .profile_service import ProfileService

                    profiles = ProfileService(self.project).profiles()
                    recipe = WorkflowMigration(self.project).convert(
                        recipe, list(profiles), profiles, ensure(self.project)
                    )
                expanded[record.id] = expand_workflow(recipe, legacy.manifests())
            manifests = legacy.manifests()
            needed = {n["operation"] for v in expanded.values() for n in v["steps"]}
            bindings = self.effective_bindings(legacy)
            overrides = {
                r.id: expand_workflow(
                    legacy._overrides(
                        self.catalog.get(r.data["recipe_id"]).data["recipe"], r.data["overrides"]
                    ),
                    manifests,
                )
                for r, _, _ in bindings
                if r.data.get("overrides")
            }
            mapping = {}
            for package in packages.packages():
                manifest = package["manifest"]
                files = packages.contents(package["digest"])
                for entry in manifest["steps"]:
                    key = operation(package["digest"], entry["id"])
                    # An implicitly registered old example library is not an explicit import.
                    if manifest["id"] == "etherfood-images" and key not in needed:
                        continue
                    record = self.import_script(key, manifest, entry, files)
                    mapping[key] = record.id
                    result["scripts"].append(record.id)
            for row in drafts:
                draft = packages.load_draft(row["id"])
                for entry in draft["manifest"]["steps"]:
                    record = self.import_script(
                        "draft:" + row["id"] + ":" + entry["id"],
                        draft["manifest"],
                        entry,
                        draft["files"],
                        draft=True,
                    )
                    result["scripts"].append(record.id)
            checkpoint("scripts")
            for record in old:
                value = self.convert(record.id, expanded[record.id], mapping, manifests)
                path = PIPELINE_ROOT + record.id + "/pipeline.json"
                self.files._write(record.id, path, (canonical(value) + "\n").encode())
                data = {
                    "path": path,
                    "description": "Übernommene Pipelinedefinition",
                    "legacy_documents": True,
                }
                converted = replace(
                    record,
                    kind="pipeline_definition",
                    data=data,
                    revision_no=record.revision_no + 1,
                    updated_at=utc_now(),
                )
                self.catalog.db.execute(
                    "UPDATE objects SET kind=?,data=?,revision_no=?," "updated_at=? WHERE id=?",
                    (
                        converted.kind,
                        canonical(data),
                        converted.revision_no,
                        converted.updated_at,
                        record.id,
                    ),
                )
                self.catalog._history(converted)
                self.catalog.db.execute(
                    "DELETE FROM relations WHERE source_id=? OR target_id=?", (record.id, record.id)
                )
                self.catalog.db.execute(
                    "INSERT INTO pipeline_states(definition_id) VALUES (?)", (record.id,)
                )
                if not expanded[record.id]["enabled"]:
                    self.catalog.db.execute(
                        "UPDATE pipeline_states SET paused=1 WHERE definition_id=?", (record.id,)
                    )
                result["definitions"].append(record.id)
            checkpoint("definitions")
            for assignment, targets, issues in bindings:
                data = {
                    "definition_id": assignment.data["recipe_id"],
                    "targets": targets,
                    "connections": [],
                    "order": len(result["usages"]),
                    "paused": False,
                    "unresolved": issues,
                    "migration_note": (
                        "Übernommene wirksame Assetauswahl; "
                        "neue Bereichszuordnung ausdrücklich wählen."
                    ),
                }
                if assignment.data.get("overrides"):
                    variant_id = migrated_id("assignment:" + assignment.id)
                    variant = self.convert(variant_id, overrides[assignment.id], mapping, manifests)
                    record = self.files.create_definition(
                        assignment.title + " · Altparameter",
                        definition=variant,
                        identifier=variant_id,
                    )
                    data["definition_id"] = record.id
                    result["definitions"].append(record.id)
                converted = replace(
                    assignment,
                    kind="pipeline_usage",
                    data=data,
                    owner_id=self.project.project().id,
                    revision_no=assignment.revision_no + 1,
                    updated_at=utc_now(),
                )
                self.catalog.db.execute(
                    "UPDATE objects SET kind=?,data=?,owner_id=?,revision_no=?,"
                    "updated_at=? WHERE id=?",
                    (
                        converted.kind,
                        canonical(data),
                        converted.owner_id,
                        converted.revision_no,
                        converted.updated_at,
                        converted.id,
                    ),
                )
                self.catalog._history(converted)
                self.catalog.add_relation(converted.id, converted.owner_id, "belongs_to")
                result["usages"].append(converted.id)
            checkpoint("usages")
            self.catalog.db.execute(
                "INSERT OR REPLACE INTO workspace_migrations VALUES (?,?,?)",
                (MIGRATION, "files_ready", canonical(result)),
            )
        return self.finish(result, checkpoint)

    def finish(self, result, checkpoint):
        from .retire_jobs import RetireJobs

        retired = RetireJobs(self.project).run(backup=result["backup"], checkpoint=checkpoint)
        result["retirement"] = retired
        with self.catalog.transaction():
            for record in self.catalog.records(include_archived=True):
                if record.archived:
                    self.catalog.db.execute(
                        "INSERT OR IGNORE INTO lifecycle VALUES (?,?,?,NULL,NULL,?)",
                        (
                            record.id,
                            "object",
                            "archived",
                            canonical({"archived": False, "owner_id": record.owner_id}),
                        ),
                    )
            self.catalog.db.execute(
                "UPDATE workspace_migrations SET detail=? WHERE name=?",
                (canonical(result), MIGRATION),
            )
        return result

    def import_script(self, key, manifest, entry, files, *, draft=False):
        identifier = migrated_id(key)
        folder = "Übernommen/" + component(manifest["id"]) + "-" + identifier[:8] + "/"
        description = {
            "entry_point": entry["entry_point"],
            "execution": entry["execution"],
            "description": entry["description"] + (" · früherer Entwurf" if draft else ""),
            "python": manifest["python"],
            "dependencies": manifest["dependencies"],
            "bundle_root": folder.rstrip("/"),
            "parameters": entry["parameters"],
            "inputs": self.ports(entry["inputs"]),
            "outputs": self.ports(entry["outputs"]),
            "helpers": [],
        }
        raw = files.get(entry["source"])
        if raw is None:
            # Keep an explicitly invalid editable draft instead of silently using another version.
            raw = b"# Urspruengliche Skriptdatei fehlt; vor Verwendung reparieren.\n"
        if manifest["id"] == "etherfood-images" and entry["id"] == "colors":
            description["inputs"]["original"] = {"type": "file", "required": False}
            raw += (
                "\n# Übernahme: Original ist ein ausdrücklich verbundener Eingang.\n"
                "_migrated_color_run = " + entry["entry_point"] + "\n"
                "def " + entry["entry_point"] + "(context, inputs, parameters):\n"
                "    original = inputs.get('original')\n"
                "    if original is not None:\n"
                "        context.resources['original'] = original.path\n"
                "    return _migrated_color_run(context, inputs, parameters)\n"
            ).encode()
        record = self.files.create_script(
            entry["name"] + (" · Entwurf" if draft else ""),
            path=folder + entry["source"],
            code=raw,
            description=description,
            identifier=identifier,
        )
        helpers = []
        for name, content in files.items():
            if name == entry["source"]:
                continue
            self.files._write(identifier, SCRIPT_ROOT + folder + name, content)
            helpers.append(folder + name)
        if helpers:
            record = self.catalog.save(record, data=record.data | {"helpers": helpers})
        return record

    @staticmethod
    def ports(values):
        result = {
            k: {
                field: value
                for field, value in v.items()
                if field in {"type", "multiple", "required", "label"}
            }
            for k, v in values.items()
        }
        # The old image port explicitly accepted both raster kinds. Preserve that
        # broader contract as file data, without weakening the new strict image type.
        for port in result.values():
            if port["type"] in {"image", "spritesheet"}:
                if port["type"] == "spritesheet":
                    port["animated"] = True
                port["type"] = "file"
        return result

    def effective_bindings(self, legacy):
        assignments = [
            r
            for r in self.catalog.records(include_archived=True)
            if r.kind == "pipeline_assignment"
        ]
        targets = {r.id: [] for r in assignments}
        issues = {r.id: [] for r in assignments}
        for asset in self.project.cards():
            if asset.kind != "asset" or "asset_definition" not in asset.data:
                continue
            try:
                matches = legacy.matching_assignments(asset.id)
                highest = max((priority for priority, _, _ in matches), default=0)
                winners = [r for priority, r, _ in matches if priority == highest]
                if len(winners) > 1:
                    for row in winners:
                        issues[row.id].append("Mehrdeutige Altzuordnung: " + asset.title)
                elif winners:
                    targets[winners[0].id].append(asset.id)
            except StudioError as error:
                for row in assignments:
                    issues[row.id].append(str(error))
        return [(row, sorted(targets[row.id]), issues[row.id]) for row in assignments]

    def convert(self, identifier, legacy, mapping, manifests):
        value = empty_definition(identifier)
        value["resources"] = deepcopy(legacy["resources"])
        value["unresolved"] = list(legacy.get("legacy_unresolved", []))
        sources = {n["id"] for n in legacy["steps"] if n["operation"] == "source"}
        require(len(sources) == 1, "Übernahme benötigt genau einen eindeutigen Quelleingang.")
        expected = {
            manifests[n["operation"]]["inputs"].get(edge["in"])
            for edge in legacy["connections"]
            for n in legacy["steps"]
            if edge["from"] in sources and edge["to"] == n["id"] and n["operation"] in manifests
        }
        expected.discard(None)
        input_type = next(iter(expected)) if len(expected) == 1 else "file"
        if input_type in {"image", "spritesheet"}:
            input_type = "file"
        value["inputs"] = {"image": {"type": input_type}}
        if "spritesheet" in expected:
            value["inputs"]["image"]["animated"] = True
        if len(expected - {"image", "spritesheet"}) > 1:
            value["unresolved"].append(
                "Alte Quelle speist verschieden deklarierte Bildtypen; "
                "Eingänge ausdrücklich aufteilen."
            )
        for node in legacy["steps"]:
            if node["id"] in sources:
                continue
            script_id = mapping.get(node["operation"])
            if script_id is None:
                value["unresolved"].append("Skriptzuordnung fehlt: " + node["operation"])
                continue
            value["nodes"].append(
                {
                    "id": node["id"],
                    "script_id": script_id,
                    "parameters": deepcopy(node["parameters"]),
                }
            )
            if not node["enabled"]:
                value["unresolved"].append(
                    "Deaktivierter Altschritt benötigt Entscheidung: " + node["operation"]
                )
        value["connections"] = [
            {**e, "from": INPUT if e["from"] in sources else e["from"]}
            for e in legacy["connections"]
        ]
        for node in value["nodes"]:
            description = self.catalog.get(node["script_id"]).data
            settings = node["parameters"]
            keys = []
            for role, target in list(settings.items()):
                if not isinstance(target, str) or target not in {"@asset", "@source"}:
                    if isinstance(target, str) and target in value["resources"]:
                        keys.append(target)
                    continue
                name = "bound_" + node["id"].replace("-", "") + "_" + role
                if role == "mask":
                    binding = (
                        {"binding": "source_mask"}
                        if target == "@asset"
                        else {
                            "binding": "declared_mask",
                            "candidates": [v for v in value["resources"].values() if "sha256" in v],
                        }
                    )
                else:
                    binding = {"binding": "color_profile", "mode": settings.get("mode", "fixed")}
                value["resources"][name] = binding
                settings[role] = name
                keys.append(name)
            node["resources"] = keys
            if "original" in description["inputs"] and node["parameters"].get("mode") == "material":
                value["connections"].append(
                    {"from": INPUT, "out": "image", "to": node["id"], "in": "original"}
                )
        for name, output in legacy["outputs"].items():
            if not output.get("publish", True):
                continue
            folder = {
                "id": name.lower().replace("_", "-")[:64],
                "node": INPUT if output["node"] in sources else output["node"],
                "port": output["port"],
                "scope": "asset",
                "directory": output.get("directory", "Ergebnisse/" + name).replace(
                    "{variante}", "{variant}"
                ),
            }
            value["folders"].append(folder)
        return value
