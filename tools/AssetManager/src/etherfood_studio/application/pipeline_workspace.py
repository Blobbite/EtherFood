"""Definitions, project usages and local approval of the current executable files."""

import ast
from copy import deepcopy
from pathlib import Path
import sys

from ..domain.assets import require
from ..domain.models import StudioError, utc_now
from ..domain.pipeline_contract import (
    compatible,
    output_ports,
    script_description,
    topological,
    validate_definition,
)
from ..storage.sqlite_repository import canonical
from .workspace_files import WorkspaceFiles, SCRIPT_ROOT, content_hash, local_import_issues


class PipelineWorkspace:
    def __init__(self, project):
        self.project, self.catalog = project, project.catalog
        self.files = WorkspaceFiles(project)

    def definitions(self, *, include_archived=False):
        return self.files.records("pipeline_definition", include_archived=include_archived)

    def scripts(self, *, include_archived=False):
        return self.files.records("script", include_archived=include_archived)

    def descriptions(self):
        return {row.id: row.data for row in self.scripts()}

    def usages(self, definition_id=None, *, include_archived=False):
        return sorted(
            (
                r
                for r in self.catalog.records(include_archived=include_archived)
                if r.kind == "pipeline_usage"
                and (definition_id is None or r.data["definition_id"] == definition_id)
            ),
            key=lambda r: (r.data.get("order", 0), r.created_at, r.id),
        )

    def use(self, definition_id, targets=(), *, title=None):
        definition = self.catalog.get(definition_id)
        require(
            definition.kind == "pipeline_definition" and not definition.archived,
            "Eine aktive Pipelinedefinition auswählen.",
        )
        self.files.definition(definition_id)
        data = {
            "definition_id": definition_id,
            "targets": sorted(set(targets)),
            "connections": [],
            "order": len(self.usages()),
            "paused": False,
            "unresolved": [],
        }
        self._targets(data["targets"])
        return self.project.create_card(
            "pipeline_usage", title or definition.title, self.project.project().id, data
        )

    def _targets(self, targets):
        require(isinstance(targets, list), "Eingabezuordnung muss eine Liste sein.")
        for identifier in targets:
            target = self.project.require_active_card(identifier)
            require(
                target.kind in {"project", "global", "act", "chapter", "package", "asset"},
                "Dieses Ziel enthält keine zulässigen Asseteingaben.",
            )

    def update_usage(
        self, identifier, *, targets=None, connections=None, paused=None, expected_revision
    ):
        record = self.catalog.get(identifier)
        require(
            record.kind == "pipeline_usage" and not record.archived,
            "Aktive Pipelineverwendung auswählen.",
        )
        self.project._check_revision(record, expected_revision)
        data = deepcopy(record.data)
        if targets is not None:
            data["targets"] = sorted(set(targets))
        if connections is not None:
            data["connections"] = deepcopy(connections)
        if paused is not None:
            data["paused"] = bool(paused)
        self._targets(data["targets"])
        require(
            not (data["targets"] and data["connections"]),
            "Ergebniseingänge und Originalquellen dürfen nicht still gemischt werden.",
        )
        from dataclasses import replace

        candidates = [replace(r, data=data) if r.id == identifier else r for r in self.usages()]
        self.usage_order(candidates)
        return self.catalog.save(record, data=data)

    def reorder(self, identifiers):
        rows = self.usages()
        require(
            set(identifiers) == {r.id for r in rows} and len(identifiers) == len(rows),
            "Reihenfolge muss alle aktiven Verwendungen genau einmal enthalten.",
        )
        with self.catalog.transaction():
            for index, identifier in enumerate(identifiers):
                row = self.catalog.get(identifier)
                if row.data["order"] != index:
                    self.catalog.save(row, data=row.data | {"order": index})

    def usage_order(self, rows=None):
        rows = self.usages() if rows is None else rows
        by_id = {row.id: row for row in rows}
        definitions, outputs = {}, {}
        descriptions = self.descriptions()
        edges, occupied = [], {}
        for row in rows:
            definition = self.catalog.get(row.data["definition_id"])
            require(not definition.archived, "Verwendete Definition ist inaktiv: " + row.title)
            value, _ = self.files.definition(definition.id)
            definitions[row.id] = value
            outputs[row.id] = output_ports(value, descriptions)
        for row in rows:
            seen = set()
            require(
                not (row.data["targets"] and row.data["connections"]),
                "Original- und Ergebniseingaben sind widersprüchlich zugeordnet.",
            )
            for edge in row.data["connections"]:
                source = edge["usage"]
                require(
                    source in by_id and source != row.id,
                    "Vorgängerverwendung fehlt, ist inaktiv oder verweist auf sich selbst.",
                )
                token = (source, edge["out"], edge["in"])
                require(token not in seen, "Ergebnisverbindung ist doppelt.")
                seen.add(token)
                inputs = definitions[row.id]["inputs"]
                require(
                    edge["out"] in outputs[source] and edge["in"] in inputs,
                    "Ergebnisverbindung benötigt vorhandene benannte Anschlüsse.",
                )
                actual, expected = outputs[source][edge["out"]], inputs[edge["in"]]
                require(
                    compatible(actual["type"], expected["type"]),
                    "Ergebnistyp passt nicht zum Eingang der Folgepipeline.",
                )
                require(
                    not actual.get("multiple") or expected.get("multiple"),
                    "Mehrfachausgang benötigt einen Mehrfacheingang.",
                )
                key = (row.id, edge["in"])
                occupied[key] = occupied.get(key, 0) + 1
                require(
                    occupied[key] <= 1 or expected.get("multiple"),
                    "Einzeleingang hat mehrere Ergebnisverbindungen.",
                )
                edges.append((source, row.id))
            if row.data["connections"]:
                for name, port in definitions[row.id]["inputs"].items():
                    require(
                        not port.get("required", True) or (row.id, name) in occupied,
                        "Ergebniseingang fehlt: " + name + " · " + row.title,
                    )
        return topological(by_id, edges, {r.id: r.data["order"] for r in rows})

    def scope(self, usage):
        require(not usage.archived, "Verwendung ist inaktiv.")
        require(not usage.data.get("unresolved"), "Alte Zuordnung benötigt eine Entscheidung.")
        if usage.data["connections"]:
            return []  # Only explicit predecessor results; never original fallback.
        self._targets(usage.data["targets"])
        identifiers = set()
        for target in usage.data["targets"]:
            identifiers.update(self.project.content_scope(target))
        return sorted(
            (r for r in self.project.cards() if r.id in identifiers and r.kind == "asset"),
            key=lambda r: r.id,
        )

    def script_snapshot(self, identifier, *, verify_environment=True, environment_cache=None):
        record = self.catalog.get(identifier)
        require(not record.archived, "Verwendetes Skript ist inaktiv: " + record.title)
        description = deepcopy(record.data)
        script_description(description)
        files = self.files.script_files(identifier)
        issues = local_import_issues(files)
        entries = {}
        for name, raw in files.items():
            if not name.endswith(".py"):
                continue
            try:
                tree = ast.parse(raw, filename=name)
                entries[name] = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
            except (SyntaxError, UnicodeError, ValueError) as error:
                issues.append(str(error))
        name = description["path"].removeprefix(SCRIPT_ROOT)
        if name in entries:
            entry = entries[name].get(description["entry_point"])
            if entry is None:
                issues.append("Einstiegsfunktion fehlt: " + description["entry_point"])
            else:
                args = entry.args
                count = len(args.posonlyargs) + len(args.args)
                if (
                    count - len(args.defaults) > 3
                    or count < 3
                    and args.vararg is None
                    or any(v is None for v in args.kw_defaults)
                ):
                    issues.append("Einstieg muss run(context, inputs, parameters) akzeptieren.")
        manifest = {
            "python": description.get(
                "python", f"{sys.version_info.major}." f"{sys.version_info.minor}"
            ),
            "dependencies": description["dependencies"],
            "files": list(files),
        }
        environment = {"python": sys.version, "dependencies": []}
        executable = sys.executable
        if manifest["dependencies"]:
            from .tool_environments import ToolEnvironments

            manager = ToolEnvironments(self.project)
            try:
                cache = environment_cache if environment_cache is not None else {}
                key = manager.identity(manifest)
                if key not in cache:
                    cache[key] = (
                        manager.verify(manifest)
                        if verify_environment
                        else manager.receipt(manifest)
                    )
                environment = cache[key]
                executable = str(manager.python(manager.directory(manifest)))
                if verify_environment:
                    issues.extend(v["message"] for v in manager.import_diagnostics(manifest, files))
            except (StudioError, OSError, ValueError, KeyError, TypeError) as error:
                issues.append("Bibliotheksumgebung prüfen/einrichten: " + str(error))
        elif verify_environment:
            issues.extend(import_issues(files))
        executable_data = {
            k: v for k, v in description.items() if k not in {"description", "saved_hash", "order"}
        }
        fingerprint = content_hash(
            canonical(
                {
                    "description": executable_data,
                    "files": {k: content_hash(v) for k, v in files.items()},
                    "environment": environment,
                }
            ).encode()
        )
        return {
            "id": identifier,
            "description": description,
            "files": files,
            "hash": fingerprint,
            "issues": issues,
            "python": executable,
            "environment": environment,
        }

    def snapshot(self, identifier, *, verify_environment=True, environment_cache=None):
        record = self.catalog.get(identifier)
        require(
            record.kind == "pipeline_definition" and not record.archived,
            "Pipelinedefinition fehlt oder ist inaktiv.",
        )
        value, file_digest = self.files.definition(identifier)
        cache = environment_cache if environment_cache is not None else {}
        scripts = {
            key: self.script_snapshot(
                key, verify_environment=verify_environment, environment_cache=cache
            )
            for key in {n["script_id"] for n in value["nodes"]}
        }
        description = {k: v["description"] for k, v in scripts.items()}
        validate_definition(value, description)
        issues = [message for script in scripts.values() for message in script["issues"]]
        from ..storage.blob_store import BlobStore, file_hash

        resources = {}
        for name, resource in value.get("resources", {}).items():
            if "binding" in resource:
                continue
            path = BlobStore(self.catalog, self.catalog.path.parent).path_for(resource["sha256"])
            require(
                path.is_file() and file_hash(path) == resource["sha256"],
                "Benötigte Ressource fehlt oder wurde verändert: " + name,
            )
            raw = path.read_bytes()
            require(content_hash(raw) == resource["sha256"], "Ressource beim Lesen geändert.")
            resources[name] = raw
        meaningful = {k: v for k, v in value.items() if k not in {"title", "description", "layout"}}
        runtime = Path(__file__).parents[1] / "pipelines"
        runtime_hashes = {
            name: content_hash((runtime / name).read_bytes())
            for name in (
                "pipeline_worker.py",
                "pipeline_artifacts.py",
                "tool_sdk.py",
                "image_processing.py",
            )
        }
        # Repository-owned algorithms called by the SDK are executable dependencies too.
        from ..pipelines.image_processing import TOOL_ROOT

        for path in sorted((runtime.parent / "packages").glob("*/process.py")):
            runtime_hashes["packages/" + path.parent.name + "/process.py"] = content_hash(
                path.read_bytes()
            )
        for folder in ("PiplineToos", "2-SpritesheetResolution-Pipline"):
            for path in sorted((TOOL_ROOT / folder).glob("*.py")):
                runtime_hashes[folder + "/" + path.name] = content_hash(path.read_bytes())
        digest = content_hash(
            canonical(
                {
                    "definition": meaningful,
                    "runtime": runtime_hashes,
                    "scripts": {k: v["hash"] for k, v in scripts.items()},
                }
            ).encode()
        )
        from .pipeline_resources import freeze_bindings

        bindings = freeze_bindings(self.project, value.get("resources", {}))
        return {
            "id": identifier,
            "definition": value,
            "scripts": scripts,
            "bindings": bindings,
            "hash": digest,
            "file_hash": file_digest,
            "issues": issues,
            "resources": resources,
            "runtime": runtime_hashes,
        }

    def state(self, identifier):
        row = self.catalog.db.execute(
            "SELECT * FROM pipeline_states WHERE definition_id=?", (identifier,)
        ).fetchone()
        require(row is not None, "Prüfstatus der Pipeline fehlt.")
        return dict(row)

    def check(self, identifier):
        digest, issues = None, []
        try:
            snapshot = self.snapshot(identifier)
            digest, issues = snapshot["hash"], snapshot["issues"]
        except (StudioError, OSError) as error:
            issues.append(str(error))
        with self.catalog.transaction():
            self.catalog.db.execute(
                "UPDATE pipeline_states SET checked_hash=?,error=?,checked_at=? "
                "WHERE definition_id=?",
                (digest, "\n".join(issues), utc_now(), identifier),
            )
        from .pipeline_execution import PipelineExecution

        plan = PipelineExecution(self.project).plan()
        selected = [
            entry
            for entry in plan["entries"].values()
            if entry["usage"].data["definition_id"] == identifier
        ]
        input_issues = [issue for entry in selected for issue in entry["issues"]]
        return {
            "valid": not issues and not input_issues,
            "code_valid": not issues,
            "hash": digest,
            "issues": list(dict.fromkeys(issues + input_issues)),
            "usages": [r.id for r in self.usages(identifier)],
            "plan": [
                (
                    {
                        "usage_id": entry["usage"].id,
                        "issues": entry["issues"],
                        "inputs": [
                            {k: v for k, v in row.items() if k not in {"inputs", "fingerprint"}}
                            for row in entry["rows"]
                        ],
                        "targets": entry["targets"],
                        "steps": [n["id"] for n in entry["snapshot"]["definition"]["nodes"]],
                    }
                    if entry["snapshot"]
                    else {"usage_id": entry["usage"].id, "issues": entry["issues"]}
                )
                for entry in selected
            ],
        }

    def approve(self, identifier, checked_hash):
        snapshot = self.snapshot(identifier)
        state = self.state(identifier)
        require(
            not snapshot["issues"]
            and not state["error"]
            and checked_hash is not None
            and checked_hash == state["checked_hash"] == snapshot["hash"],
            "Aktuellen ausführbaren Stand zuerst erfolgreich prüfen.",
        )
        with self.catalog.transaction():
            self.catalog.db.execute(
                "UPDATE pipeline_states SET approved_hash=? " "WHERE definition_id=?",
                (checked_hash, identifier),
            )

    def pause(self, identifier, paused):
        with self.catalog.transaction():
            self.catalog.db.execute(
                "UPDATE pipeline_states SET paused=? WHERE definition_id=?",
                (int(paused), identifier),
            )

    def status(self, identifier):
        state = self.state(identifier)
        if state["checked_at"] is None:
            try:
                self.files.read(identifier)
                return "yellow", "Neu oder übernommen; Prüfung und Freigabe erforderlich."
            except (StudioError, OSError) as error:
                return "red", str(error)
        try:
            # No interpreter subprocess on the GUI thread. Full validation runs
            # in the worker at Check and again before every execution.
            snapshot = self.snapshot(identifier, verify_environment=False)
            if snapshot["issues"]:
                return "red", "\n".join(snapshot["issues"])
        except (StudioError, OSError) as error:
            return "red", str(error)
        if state["checked_hash"] != snapshot["hash"]:
            return "yellow", "Aktuellen Stand prüfen und freigeben."
        if state["error"]:
            return "red", state["error"]
        if state["approved_hash"] != snapshot["hash"]:
            return "yellow", "Geprüft; ausdrückliche Freigabe erforderlich."
        return "green", "Aktueller Stand geprüft und lokal freigegeben."


def import_issues(files):
    """Only the stdlib and SDK are implicit; external imports need declared libraries."""
    local = {
        part
        for name in files
        for part in (
            name.split("/")[0].removesuffix(".py"),
            name.rsplit("/", 1)[-1].removesuffix(".py"),
        )
    }
    allowed = local | sys.stdlib_module_names | {"etherfood_studio"}
    issues = []
    for name, raw in files.items():
        if not name.endswith(".py"):
            continue
        try:
            tree = ast.parse(raw)
        except (SyntaxError, UnicodeError, ValueError):
            continue
        for node in ast.walk(tree):
            names = (
                [v.name for v in node.names]
                if isinstance(node, ast.Import)
                else (
                    [node.module]
                    if isinstance(node, ast.ImportFrom) and not node.level and node.module
                    else []
                )
            )
            for module in names:
                if module.split(".")[0] not in allowed:
                    issues.append(f"{name}:{node.lineno}: Bibliothek deklarieren: {module}")
    return sorted(set(issues))
