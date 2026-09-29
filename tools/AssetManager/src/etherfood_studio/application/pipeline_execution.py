"""Serial phase execution of frozen, approved pipelines; no legacy jobs or build planner."""

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Event, Lock
import time

from ..domain.assets import require
from ..domain.models import StudioError, new_id, utc_now
from ..domain.pipeline_contract import INPUT, validate_definition
from ..pipelines.pipeline_artifacts import read_outputs, verify_artifact
from ..pipelines.processes import identity
from ..storage.blob_store import file_hash
from ..storage.paths import make_directory, safe_target
from ..storage.sqlite_repository import canonical
from .pipeline_inputs import PipelineInputs, influences, matches
from .pipeline_workspace import PipelineWorkspace
from .pipeline_resources import resolve_resources
from .project_files import component
from .workspace_files import SCRIPT_ROOT, content_hash


def fingerprint(value):
    return content_hash(canonical(value).encode())


class PipelineExecution:
    def __init__(self, project):
        self.project, self.catalog = project, project.catalog
        self.workspace = PipelineWorkspace(project)
        self.inputs = PipelineInputs(self.workspace)
        self.root = self.catalog.path.parent
        self.cancelled = Event()
        if not hasattr(project, "pipeline_run_lock"):
            project.pipeline_run_lock = Lock()
        self.lock = project.pipeline_run_lock
        self.active = False

    def cancel(self):
        self.cancelled.set()

    def plan(self):
        """Read-only dry-run; a valid independent chain survives another chain's errors."""
        usages = self.workspace.usages()
        by_id = {r.id: r for r in usages}
        entries, graphs, snapshots, environment_cache = {}, [], {}, {}
        for usage in usages:
            entry = {"usage": usage, "rows": [], "issues": [], "snapshot": None}
            entries[usage.id] = entry
            try:
                identifier = usage.data["definition_id"]
                if identifier not in snapshots:
                    snapshots[identifier] = self.workspace.snapshot(
                        identifier, environment_cache=environment_cache
                    )
                snapshot = snapshots[identifier]
                entry["snapshot"] = snapshot
                entry["issues"].extend(snapshot["issues"])
                # Validate this usage and its ancestors as one explicit component.
                ancestors, pending = {}, [usage.id]
                while pending:
                    key = pending.pop()
                    require(key in by_id, "Vorgängerverwendung fehlt oder ist inaktiv.")
                    if key in ancestors:
                        continue
                    ancestors[key] = by_id[key]
                    pending.extend(e["usage"] for e in by_id[key].data["connections"])
                self.workspace.usage_order(list(ancestors.values()))
                if not usage.data["connections"]:
                    entry["rows"] = self.inputs.select(usage, snapshot["definition"])
                    entry["issues"].extend(
                        r["reason"] for r in entry["rows"] if r["state"] == "invalid"
                    )
                    for row in entry["rows"]:
                        if row["state"] == "matching":
                            resolve_resources(snapshot, row["inputs"])
                graphs.extend((e["usage"], usage.id) for e in usage.data["connections"])
            except (StudioError, OSError, ValueError, KeyError) as error:
                entry["issues"].append(str(error))
            entry["targets"] = self.target_preview(entry)
            try:
                self.validate_targets(entry)
            except (StudioError, OSError) as error:
                entry["issues"].append(str(error))
        # Invalid components remain rows in the overview, never bypassed graph steps.
        from ..domain.pipeline_contract import topological

        valid = {key for key, entry in entries.items() if not entry["issues"]}
        try:
            order = topological(
                valid,
                [(a, b) for a, b in graphs if a in valid and b in valid],
                {r.id: r.data["order"] for r in usages},
            )
        except StudioError as error:
            for key in valid:
                entries[key]["issues"].append(str(error))
            order = []
        order += [r.id for r in usages if r.id not in order]
        return {"entries": entries, "order": order}

    def target_preview(self, entry):
        snapshot = entry["snapshot"]
        if not snapshot:
            return []
        return [
            {
                "output": f["id"],
                "path": (
                    "{Asset}/Ergebnisse/"
                    if f.get("scope", "asset") == "asset"
                    else "Ergebnisse/Projekt/"
                )
                + entry["usage"].id
                + "/"
                + f["directory"],
            }
            for f in snapshot["definition"]["folders"]
        ]

    def validate_targets(self, entry):
        if not entry["snapshot"]:
            return
        assets = {row["asset_id"] for row in entry["rows"]}
        for folder in entry["snapshot"]["definition"]["folders"]:
            relative = folder["directory"]
            for token in ("pose", "direction", "variant"):
                relative = relative.replace("{" + token + "}", "vorschau")
            for asset in assets:
                if folder.get("scope", "asset") == "project":
                    base = "Ergebnisse/Projekt/" + entry["usage"].id + "/" + asset
                else:
                    base = (
                        (self.project.files.path(asset) / "Ergebnisse" / entry["usage"].id)
                        .relative_to(self.root)
                        .as_posix()
                    )
                safe_target(self.root, base + "/" + relative + "/" + folder["id"] + "/result")

    def _check_cancel(self):
        if self.cancelled.is_set():
            raise StudioError("cancelled", "Durchgang abgebrochen.")

    def _attempt(self, usage, digest, state, detail):
        with self.catalog.transaction():
            self.catalog.db.execute(
                "INSERT INTO pipeline_attempts VALUES (?,?,?,?,?) "
                "ON CONFLICT(usage_id,fingerprint) DO UPDATE SET state=excluded.state, "
                "detail=excluded.detail, updated_at=excluded.updated_at",
                (usage, digest, state, detail, utc_now()),
            )

    def retry(self, usage_id):
        with self.catalog.transaction():
            self.catalog.db.execute(
                "DELETE FROM pipeline_attempts WHERE usage_id=? "
                "AND state IN ('failed','cancelled')",
                (usage_id,),
            )

    def cached(self, usage_id, asset_id, source_key, digest):
        rows = self.catalog.db.execute(
            "SELECT * FROM pipeline_results WHERE usage_id=? AND asset_id=? AND "
            "source_key=? AND fingerprint=? ORDER BY created_at DESC",
            (usage_id, asset_id, source_key, digest),
        ).fetchall()
        for row in rows:
            outputs = json.loads(row["outputs"])
            if self.outputs_valid(outputs):
                return outputs
        return None

    def outputs_valid(self, outputs):
        try:
            for values in outputs.values():
                for item in values:
                    verify_artifact(safe_target(self.root, item["path"]), item)
            return True
        except (StudioError, OSError, ValueError, KeyError):
            return False

    def run(self, *, on_event=lambda event: None, test=False, plan=None):
        require(self.lock.acquire(blocking=False), "Ein Durchgang läuft bereits.")
        self.active = True
        self.project.pipeline_executor = self
        self.cancelled.clear()
        run_id = new_id()
        report = {"id": run_id, "state": "succeeded", "phases": [], "executed": 0, "reused": 0}
        try:
            plan = plan or self.plan()
            directory = make_directory(self.root, ".asset-studio/pipeline-runs/" + run_id)
            # Snapshot every original input before the first script is started.
            for entry in plan["entries"].values():
                for row in entry["rows"]:
                    if row["state"] != "matching":
                        continue
                    for values in row["inputs"].values():
                        for item in values:
                            self.freeze_input(item, directory / "inputs" / row["asset_id"])
                            self.track_file(self.root / item["path"], None, row["asset_id"])
            phases = {}
            for usage_id in plan["order"]:
                self._check_cancel()
                entry = plan["entries"][usage_id]
                usage = entry["usage"]
                phase = {"usage_id": usage_id, "state": "blocked", "reason": "", "rows": []}
                report["phases"].append(phase)
                phases[usage_id] = phase
                if entry["issues"]:
                    phase["reason"] = "\n".join(entry["issues"])
                    report["state"] = "failed"
                    on_event(phase)
                    continue
                snapshot = entry["snapshot"]
                state = self.workspace.state(snapshot["id"])
                if state["paused"] or usage.data["paused"]:
                    phase.update(state="paused", reason="Automatik pausiert.")
                    on_event(phase)
                    continue
                if not test and state["approved_hash"] != snapshot["hash"]:
                    phase["reason"] = "Aktueller ausführbarer Stand benötigt Freigabe."
                    on_event(phase)
                    continue
                if not self.current_definition(entry):
                    phase["reason"] = "Dateistand wurde nach der Planung geändert."
                    on_event(phase)
                    continue
                if any(
                    phases.get(e["usage"], {}).get("state") not in {"current", "succeeded"}
                    for e in usage.data["connections"]
                ):
                    phase["reason"] = "Vorgängerphase nicht vollständig erfolgreich."
                    on_event(phase)
                    continue
                rows = (
                    self.predecessor_rows(entry, phases)
                    if usage.data["connections"]
                    else [deepcopy(r) for r in entry["rows"] if r["state"] == "matching"]
                )
                rows = self.prepare_rows(entry, rows)
                phase_key = fingerprint(
                    {
                        "code": snapshot["hash"],
                        "connections": usage.data["connections"],
                        "targets": usage.data["targets"],
                        "inputs": [self.row_key(entry, r) for r in rows],
                    }
                )
                prior = self.catalog.db.execute(
                    "SELECT state,detail FROM pipeline_attempts "
                    "WHERE usage_id=? AND fingerprint=?",
                    (usage_id, phase_key),
                ).fetchone()
                if prior and prior["state"] in {"failed", "cancelled"} and not test:
                    phase.update(
                        state=prior["state"],
                        reason=prior["detail"] + " · Quelle korrigieren oder Erneut versuchen.",
                    )
                    report["state"] = "failed"
                    on_event(phase)
                    continue
                if not rows:
                    phase.update(state="current", reason="Keine passenden Eingaben.")
                    on_event(phase)
                    continue
                try:
                    phase.update(state="running", reason="")
                    self._attempt(usage_id, phase_key, "running", "")
                    for index, row in enumerate(rows):
                        self._check_cancel()
                        on_event(
                            {
                                "usage_id": usage_id,
                                "state": "running",
                                "completed": index,
                                "total": len(rows),
                            }
                        )
                        digest = self.row_key(entry, row)
                        cached = self.cached(usage_id, row["asset_id"], row["source_key"], digest)
                        if cached is not None and not test:
                            report["reused"] += 1
                            phase["rows"].append(row | {"outputs": cached, "fingerprint": digest})
                            continue
                        outputs = self.execute_row(entry, row, directory, on_event, test=test)
                        phase["rows"].append(row | {"outputs": outputs, "fingerprint": digest})
                        report["executed"] += 1
                    self._check_cancel()
                    pending, checked = [usage_id], set()
                    current = True
                    while pending:
                        key = pending.pop()
                        if key in checked:
                            continue
                        checked.add(key)
                        ancestor = plan["entries"][key]
                        current = current and self.still_current(ancestor)
                        pending.extend(
                            edge["usage"] for edge in ancestor["usage"].data["connections"]
                        )
                    if not test and current:
                        self.publish(entry, phase["rows"])
                    phase.update(
                        state="succeeded" if current else "stale",
                        reason=(
                            "Testlauf; keine Veröffentlichung."
                            if test
                            else "" if current else "Stand während des Laufs geändert."
                        ),
                    )
                    self._attempt(usage_id, phase_key, phase["state"], phase["reason"])
                except (StudioError, OSError, ValueError, KeyError) as error:
                    state = "cancelled" if getattr(error, "code", "") == "cancelled" else "failed"
                    phase.update(state=state, reason=str(error), rows=[])
                    report["state"] = state
                    self._attempt(usage_id, phase_key, state, str(error))
                on_event(phase)
                if self.cancelled.is_set():
                    break
            if self.cancelled.is_set():
                report["state"] = "cancelled"
            elif report["state"] == "succeeded" and any(
                p["state"] in {"blocked", "stale"} for p in report["phases"]
            ):
                report["state"] = "blocked"
            return report
        finally:
            self.active = False
            self.lock.release()

    def row_key(self, entry, row):
        source_ids = {
            a["metadata"].get("source_revision")
            for values in row["inputs"].values()
            for a in values
        }
        return fingerprint(
            {
                "definition": entry["snapshot"]["hash"],
                "connections": entry["usage"].data["connections"],
                "source_key": row["source_key"],
                "bindings": {
                    name: {
                        key: value.get("sha256", value.get("issue"))
                        for key, value in binding.items()
                        if key in source_ids
                    }
                    for name, binding in entry["snapshot"].get("bindings", {}).items()
                },
                "inputs": {
                    key: [influences(a) for a in values] for key, values in row["inputs"].items()
                },
            }
        )

    def current_definition(self, entry):
        try:
            current = self.workspace.snapshot(entry["snapshot"]["id"])
            usage = self.catalog.get(entry["usage"].id)
            return not usage.archived and current["hash"] == entry["snapshot"]["hash"]
        except (StudioError, OSError, ValueError):
            return False

    def still_current(self, entry):
        if not self.current_definition(entry):
            return False
        current = self.catalog.get(entry["usage"].id)
        latest = self.workspace.snapshot(entry["snapshot"]["id"])
        if latest.get("bindings") != entry["snapshot"].get("bindings"):
            return False
        for key in ("targets", "connections", "definition_id"):
            if current.data[key] != entry["usage"].data[key]:
                return False
        if not current.data["connections"]:
            try:
                now = self.inputs.select(current, entry["snapshot"]["definition"])
                return [(r.get("source_key"), r.get("fingerprint"), r["state"]) for r in now] == [
                    (r.get("source_key"), r.get("fingerprint"), r["state"]) for r in entry["rows"]
                ]
            except (StudioError, OSError):
                return False
        return True

    def freeze_input(self, artifact, directory):
        directory.mkdir(parents=True, exist_ok=True)
        source = safe_target(self.root, artifact["path"])
        require(
            file_hash(source) == artifact["sha256"], "Quelle wurde während des Starts geändert."
        )
        target = directory / artifact["sha256"]
        if not target.exists():
            raw = source.read_bytes()
            require(
                content_hash(raw) == artifact["sha256"], "Quelle wurde während des Lesens geändert."
            )
            target.write_bytes(raw)
        artifact["path"] = target.relative_to(self.root).as_posix()

    def predecessor_rows(self, entry, phases):
        grouped = {}
        for edge in entry["usage"].data["connections"]:
            for previous in phases[edge["usage"]]["rows"]:
                key = (previous["asset_id"], previous["source_key"])
                row = grouped.setdefault(
                    key,
                    {
                        "asset_id": key[0],
                        "source_key": key[1],
                        "source_id": previous.get("source_id"),
                        "inputs": {},
                        "state": "matching",
                    },
                )
                row["inputs"].setdefault(edge["in"], []).extend(
                    deepcopy(previous["outputs"].get(edge["out"], []))
                )
        return [grouped[key] for key in sorted(grouped)]

    def prepare_rows(self, entry, rows):
        """Collect is asset-local; map branches retain each source's identity."""
        if not any(
            s["description"].get("execution") == "collect"
            for s in entry["snapshot"]["scripts"].values()
        ):
            return rows
        groups = {}
        for row in rows:
            group = groups.setdefault(
                row["asset_id"],
                {
                    "asset_id": row["asset_id"],
                    "source_key": "@collection",
                    "state": "matching",
                    "inputs": {},
                },
            )
            for port, values in row["inputs"].items():
                for item in values:
                    group["inputs"].setdefault(port, []).append(
                        deepcopy(item)
                        | {"source_group": item.get("source_group", row["source_key"])}
                    )
        return [groups[key] for key in sorted(groups)]

    def execute_row(self, entry, row, directory, on_event, *, test=False):
        snapshot, usage = entry["snapshot"], entry["usage"]
        definition = snapshot["definition"]
        scripts = {key: value["description"] for key, value in snapshot["scripts"].items()}
        order = validate_definition(definition, scripts)
        nodes = {n["id"]: n for n in definition["nodes"]}
        initial = deepcopy(row["inputs"])
        for values in initial.values():
            for item in values:
                item.setdefault("source_group", row["source_key"])
                item.setdefault(
                    "provenance",
                    [
                        {
                            "source_key": item.get("source_key", row["source_key"]),
                            "source_id": item.get("source_id"),
                            "sha256": item["sha256"],
                            "slot": item["metadata"].get("slot"),
                        }
                    ],
                )
        streams = {INPUT: initial}
        for identifier in order:
            if identifier == INPUT:
                continue
            self._check_cancel()
            node = nodes[identifier]
            script = snapshot["scripts"][node["script_id"]]
            inputs = {name: [] for name in script["description"]["inputs"]}
            for edge in definition["connections"]:
                if edge["to"] == identifier:
                    inputs[edge["in"]].extend(streams[edge["from"]].get(edge["out"], []))
            groups = {a.get("source_group") for values in inputs.values() for a in values}
            if script["description"].get("execution") == "collect" or not groups:
                groups = {None}
            elif len(groups) > 1:
                groups.discard(None)
            streams[identifier] = {port: [] for port in script["description"]["outputs"]}
            for group in sorted(groups, key=lambda value: value or ""):
                bound = {
                    port: [
                        a for a in values if group is None or a.get("source_group") in {None, group}
                    ]
                    for port, values in inputs.items()
                }
                outputs = self.execute_node(
                    entry, row, node, script, bound, group, directory, on_event, test=test
                )
                for port, values in outputs.items():
                    streams[identifier][port].extend(values)
        return {
            folder["id"]: deepcopy(streams[folder["node"]].get(folder["port"], []))
            for folder in definition["folders"]
        }

    def execute_node(self, entry, row, node, script, inputs, group, directory, on_event, *, test):
        snapshot, usage = entry["snapshot"], entry["usage"]
        resources = resolve_resources(snapshot, inputs, node.get("resources"))
        key = fingerprint(
            {
                "usage": usage.id,
                "asset": row["asset_id"],
                "node": node["id"],
                "group": group,
                "script": script["hash"],
                "parameters": node["parameters"],
                "resources": {k: content_hash(v) for k, v in resources.items()},
                "runtime": snapshot.get("runtime", {}),
                "inputs": {k: [influences(a) for a in v] for k, v in inputs.items()},
            }
        )
        prior = self.catalog.db.execute(
            "SELECT outputs FROM pipeline_step_cache " "WHERE fingerprint=?", (key,)
        ).fetchone()
        if not test and prior is not None and self.outputs_valid(json.loads(prior[0])):
            return json.loads(prior[0])
        for name, spec in script["description"]["inputs"].items():
            require(
                (inputs[name] or not spec.get("required", True))
                and (len(inputs[name]) <= 1 or spec.get("multiple", False)),
                "Eingang benötigt passende Anzahl Dateien: " + name,
            )
            require(
                all(
                    matches(a | {"name": a.get("name", Path(a["path"]).name)}, spec)
                    for a in inputs[name]
                ),
                "Ergebnisdaten passen nicht zum Eingang " + name,
            )
        call = make_directory(directory, "steps/" + new_id())
        try:
            outputs = self.invoke(script, node["parameters"], inputs, resources, call)
        finally:
            self.track_run(call, usage.id, row["asset_id"])
        provenance = {
            canonical(p): p
            for values in inputs.values()
            for a in values
            for p in a.get("provenance", [])
        }
        for values in outputs.values():
            for item in values:
                item.update(source_group=group, provenance=list(provenance.values()))
        if not test:
            with self.catalog.transaction():
                self.catalog.db.execute(
                    "INSERT OR REPLACE INTO pipeline_step_cache VALUES (?,?,?)",
                    (key, usage.id, canonical(outputs)),
                )
        on_event(
            {
                "usage_id": usage.id,
                "node_id": node["id"],
                "asset_id": row["asset_id"],
                "state": "step_finished",
            }
        )
        return outputs

    def track_file(self, path, usage_id, asset_id):
        relative = path.relative_to(self.root).as_posix()
        safe_target(self.root, relative)
        with self.catalog.transaction():
            self.catalog.db.execute(
                "INSERT OR REPLACE INTO pipeline_run_files VALUES (?,?,?,?)",
                (relative, file_hash(path), usage_id, asset_id),
            )

    def track_run(self, directory, usage_id, asset_id):
        with self.catalog.transaction():
            for path in directory.rglob("*"):
                if path.is_file() and not path.is_symlink():
                    self.track_file(path, usage_id, asset_id)

    def invoke(self, script, parameters, inputs, resources, directory):
        package = directory / "scripts"
        package.mkdir()
        for name, raw in script["files"].items():
            path = safe_target(package, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        # The same artifact may intentionally feed two ports. Give each binding its
        # own path field before rewriting it relative to the frozen invocation.
        bound = {name: [deepcopy(item) for item in values] for name, values in inputs.items()}
        for values in bound.values():
            for item in values:
                self.freeze_input(item, directory / "inputs")
                item["path"] = str((self.root / item["path"]).relative_to(directory))
        frozen_resources = {}
        for name, raw in resources.items():
            target = safe_target(directory, "resources/" + name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            frozen_resources[name] = str(target.relative_to(directory))
        invocation = {
            "description": script["description"],
            "parameters": parameters,
            "source": script["description"]["path"].removeprefix(SCRIPT_ROOT),
            "inputs": bound,
            "resources": frozen_resources,
        }
        (directory / "invocation.json").write_text(canonical(invocation), encoding="utf-8")
        (directory / "process.json").write_text(
            canonical(
                {
                    "python": script["python"],
                    "parent_pid": os.getpid(),
                    "parent_stamp": identity(os.getpid()),
                    "timeout": 300,
                }
            ),
            encoding="utf-8",
        )
        supervisor = Path(__file__).parents[1] / "pipelines/pipeline_supervisor.py"
        with (directory / "supervisor.log").open("wb") as log:
            process = subprocess.Popen(
                [sys.executable, "-I", "-B", str(supervisor), str(directory)],
                stdin=subprocess.PIPE,
                stdout=log,
                stderr=log,
            )
            requested = False
            while process.poll() is None:
                if self.cancelled.is_set() and not requested:
                    try:
                        process.stdin.write(b"cancel\n")
                        process.stdin.flush()
                    except BrokenPipeError:
                        pass
                    requested = True
                time.sleep(0.04)
            process.stdin.close()
        completion = directory / "completion.json"
        require(completion.is_file(), "Kontrollierter Prozessabschluss fehlt; Protokoll prüfen.")
        result = json.loads(completion.read_bytes())
        if result["state"] != "succeeded":
            detail = (
                (directory / "stderr.log").read_bytes()[-4000:].decode("utf-8", errors="replace")
            )
            raise StudioError(result["state"], result["reason"] + "\n" + detail)
        outputs = read_outputs(directory / "output", script["description"]["outputs"])
        for values in outputs.values():
            for item in values:
                item["path"] = (
                    (directory / "output" / item["path"]).relative_to(self.root).as_posix()
                )
        return outputs

    def publish(self, entry, rows):
        usage, snapshot = entry["usage"], entry["snapshot"]
        folders = {f["id"]: f for f in snapshot["definition"]["folders"]}
        with self.catalog.transaction():
            changes = self.catalog.file_changes()
            for row in rows:
                existing = self.catalog.db.execute(
                    "SELECT outputs FROM pipeline_results WHERE "
                    "usage_id=? AND asset_id=? AND source_key=? AND fingerprint=? AND current=1",
                    (usage.id, row["asset_id"], row["source_key"], row["fingerprint"]),
                ).fetchone()
                if (
                    existing
                    and json.loads(existing[0]) == row["outputs"]
                    and self.outputs_valid(row["outputs"])
                ):
                    continue
                publication = {}
                for port, values in row["outputs"].items():
                    folder = folders[port]
                    if folder.get("scope", "asset") == "project":
                        base = "Ergebnisse/Projekt/" + usage.id + "/" + row["asset_id"]
                    else:
                        base = (
                            (self.project.files.path(row["asset_id"]) / "Ergebnisse" / usage.id)
                            .relative_to(self.root)
                            .as_posix()
                        )
                    publication[port] = []
                    for item in values:
                        metadata = item["metadata"]
                        slot = metadata.get("slot", {})
                        relative = folder["directory"]
                        for name, value in {
                            "pose": slot.get("pose_id") or "allgemein",
                            "direction": slot.get("direction") or "alle",
                            "variant": metadata.get("profile") or port,
                        }.items():
                            relative = relative.replace("{" + name + "}", component(str(value)))
                        name = (
                            fingerprint(row["source_key"])[:12]
                            + "-"
                            + row["fingerprint"][:12]
                            + "-"
                            + fingerprint([item.get("source_group"), item["sha256"], item["path"]])[
                                :12
                            ]
                            + "-"
                            + Path(item["path"]).name
                        )
                        path = safe_target(
                            self.root, base + "/" + relative + "/" + port + "/" + name
                        )
                        previous = file_hash(path) if path.is_file() else None
                        require(
                            previous is None or previous == item["sha256"],
                            "Ausgabeziel enthält andere Daten; kein Überschreiben.",
                        )
                        if previous is None:
                            changes.write(path, source=safe_target(self.root, item["path"]))
                        copied = item | {"path": path.relative_to(self.root).as_posix()}
                        verify_artifact(path, copied)
                        publication[port].append(copied)
                        self.catalog.db.execute(
                            "INSERT OR IGNORE INTO current_files VALUES (?,?,?)",
                            (usage.id, copied["path"], copied["sha256"]),
                        )
                self.catalog.db.execute(
                    "UPDATE pipeline_results SET current=0 WHERE usage_id=? "
                    "AND asset_id=? AND source_key=?",
                    (usage.id, row["asset_id"], row["source_key"]),
                )
                self.catalog.db.execute(
                    "INSERT INTO pipeline_results VALUES (?,?,?,?,?,?,?,?,1)",
                    (
                        new_id(),
                        usage.id,
                        row["asset_id"],
                        row["source_key"],
                        row["fingerprint"],
                        snapshot["hash"],
                        canonical(publication),
                        utc_now(),
                    ),
                )
                row["outputs"] = publication
                self.catalog.projection_dirty = True
