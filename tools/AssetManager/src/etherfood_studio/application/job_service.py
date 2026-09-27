"""Shared job admission, frozen workspaces and verified completion for Qt and CLI."""

import json
import math
import os
from pathlib import Path
import selectors
import subprocess
import sys
from typing import Callable

from ..domain.models import StudioError, new_id
from ..pipelines.adapters import PIPELINES, adapter_for
from ..pipelines.base import BuildRequest, InputFile, read_json, write_json
from ..pipelines.processes import identity, require_supported
from ..storage.blob_store import BlobStore, file_hash
from ..storage.job_store import JobStore
from ..storage.paths import make_directory, safe_target
from ..storage.sqlite_repository import canonical


class JobService:
    def __init__(self, project, *, max_parallel: int = 2):
        if not 1 <= max_parallel <= 8:
            raise StudioError("validation", "Parallelität muss zwischen 1 und 8 liegen.")
        self.project = project
        self.root = project.catalog.path.parent
        self.store = JobStore(project.catalog)
        self.max_parallel = max_parallel
        self.store.recover()

    def workspace(self, identifier: str) -> Path:
        from uuid import UUID

        if str(UUID(identifier)) != identifier:
            raise StudioError("validation", "Ungültige Auftrags-ID.")
        return safe_target(self.root, f".asset-studio/jobs/{identifier}")

    def prepare(self, owner_id: str, adapter: str = "diagnostic", parameters: dict | None = None,
                *, source_ids: tuple[str, ...] = (), timeout: float = 30,
                resource_key: str | None = None,
                bindings: tuple[InputFile, ...] = ()) -> BuildRequest:
        require_supported()
        self.project.require_active_card(owner_id)
        if not math.isfinite(timeout) or not 0.05 <= timeout <= 3600:
            raise StudioError("validation", "Ungültiges Zeitlimit (0,05–3600 Sekunden).")
        identifier = new_id()
        parameters = parameters or {}
        adapter_object = adapter_for(adapter)
        adapter_object.validate(parameters)
        if adapter == "studio-image" and parameters.get("operation") == "plugin":
            from .plugin_service import PluginService
            from ..domain.pipeline_recipes import validate_parameters
            from ..pipelines.fingerprints import digest

            supplied = parameters["plugin"]
            plugin = PluginService(self.project).trusted(supplied["id"])
            if (plugin["code_hash"] != supplied["code_hash"] or
                    plugin["manifest"]["entry_point"] != supplied["entry_point"] or
                    plugin["manifest"]["version"] != supplied["version"] or
                    digest(plugin["manifest"]) != supplied["manifest_sha256"] or
                    plugin["manifest"]["dependencies"] != supplied["dependencies"] or
                    not any(b.name == "plugin.py" and b.sha256 == plugin["code_hash"]
                            for b in bindings)):
                raise StudioError("integrity",
                                  "Python-Auftrag stimmt nicht mit der Freigabe überein.")
            validate_parameters(parameters["settings"], plugin["manifest"]["parameters"])
        directory = self.workspace(identifier)
        plan = adapter_object.plan(directory, parameters)
        inputs = []
        for source_id in source_ids:
            source = self.project.catalog.get(source_id)
            if source.kind != "source_revision" or source.owner_id != owner_id:
                raise StudioError("validation",
                                  "Nur registrierte Originale dieses Assets verwenden.")
            digest = source.data["sha256"]
            path = BlobStore(self.project.catalog, self.root).path_for(digest)
            inputs.append(InputFile(source.id, str(path.relative_to(self.root)),
                                    source.id + ".png", digest, source.data["length"]))
        for binding in bindings:
            self.validate_binding(owner_id, binding)
            inputs.append(binding)
        if len({item.name for item in inputs}) != len(inputs):
            raise StudioError("validation", "Doppelte Eingabedateinamen im Bildauftrag.")
        if adapter == "studio-image":
            if parameters["metadata"] is not None and \
                    parameters["metadata"]["source_revision"] not in source_ids:
                raise StudioError("validation",
                                  "Bildeingang benötigt eine Originalrevision dieses Assets.")
            adapter_object.validate_inputs(parameters, inputs)
        request = BuildRequest(identifier, owner_id, adapter, canonical(parameters), tuple(inputs),
                               plan.outputs, plan.argv, plan.tool_hashes,
                               resource_key or f"{owner_id}:{adapter}", timeout,
                               os.getpid(), identity(os.getpid()))
        self.store.reserve(request, self.max_parallel)
        try:
            for name in ("input", "output", "logs"):
                make_directory(self.root, f".asset-studio/jobs/{identifier}/{name}")
            write_json(directory / "request.json", request.to_data())
        except Exception as error:
            self.store.finish(identifier, {"status": "failed", "reason": str(error)})
            raise
        return request

    def validate_binding(self, owner_id, binding):
        if (not isinstance(binding, InputFile) or type(binding.length) is not int or
                binding.length < 1 or not isinstance(binding.name, str) or
                binding.name in {"", ".", ".."} or any(c in binding.name for c in "/\\:\x00")):
            raise StudioError("validation", "Ungültiger Vertrag für eine Arbeitskopie.")
        path = safe_target(self.root, binding.source)
        blob = self.project.catalog.db.execute("SELECT length FROM blobs WHERE sha256=?",
                                                (binding.sha256,)).fetchone()
        registered = blob and path == BlobStore(self.project.catalog, self.root).path_for(
            binding.sha256) and blob[0] == binding.length
        if not registered:
            build = self.project.catalog.get(binding.revision_id)
            registered = (build.kind == "build" and build.owner_id == owner_id and
                build.data.get("contract") == "studio-build-v1" and
                binding.source == f".asset-studio/jobs/{build.data['job_id']}/output/" +
                path.name and any(item["path"] == path.name and
                    item["sha256"] == binding.sha256 and item["length"] == binding.length
                    for item in build.data["outputs"]))
            if registered:
                from ..storage.build_cache import BuildCache

                expected = tuple(item["path"] for item in build.data["outputs"])
                BuildCache(self.project.catalog).verify(build, expected, build.data["dependencies"])
        if not registered:
            raise StudioError("validation", "Eingabe ist kein registrierter Blob/Asset-Build.")
        if path.stat().st_size != binding.length or file_hash(path) != binding.sha256:
            raise StudioError("integrity", "Abhängigkeit/Ressource wurde verändert.")

    def host_argv(self, request: BuildRequest) -> tuple[str, ...]:
        return (sys.executable, "-I", "-B", str(PIPELINES / "host.py"),
                str(self.workspace(request.job_id)))

    def consume(self, identifier: str, line: bytes) -> dict:
        event = json.loads(line)
        self.store.event(identifier, event)
        return event

    def complete(self, identifier: str, code: int) -> dict:
        try:
            directory = self.workspace(identifier)
            result = read_json(directory / "result.json")
            events = self.store.events(identifier)
            if (code != 0 or result.get("job_id") != identifier or
                    result.get("request_sha256") != file_hash(directory / "request.json") or
                    not events or events[-1].get("kind") != "finished" or
                    events[-1].get("status") != result.get("status")):
                raise ValueError("Prozessabschluss stimmt nicht mit geprüftem Ergebnis überein")
        except (OSError, ValueError, StudioError) as error:
            result = {"status": "interrupted", "reason": str(error), "exit_code": code}
        self.store.finish(identifier, result)
        return self.store.get(identifier)["result"]

    def start_failed(self, identifier: str, reason: str) -> dict:
        result = {"status": "failed", "reason": "Prozessstart fehlgeschlagen: " + reason}
        self.store.finish(identifier, result)
        return result

    def run(self, request: BuildRequest, *, cancelled: Callable[[], bool] = lambda: False,
            on_event: Callable[[dict], None] = lambda event: None) -> dict:
        directory = self.workspace(request.job_id)
        with (directory / "logs/host-stderr.log").open("xb") as error_log:
            try:
                process = subprocess.Popen(self.host_argv(request), stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE, stderr=error_log,
                                            cwd=directory)
            except OSError as error:
                return self.start_failed(request.job_id, str(error))
            selector = selectors.DefaultSelector()
            selector.register(process.stdout, selectors.EVENT_READ)
            pending, sent = b"", False
            try:
                while process.poll() is None or selector.get_map():
                    try:
                        if cancelled() and not sent:
                            process.stdin.write(b"cancel\n")
                            process.stdin.flush()
                            self.store.cancelling(request.job_id)
                            sent = True
                        for key, _ in selector.select(0.05):
                            data = os.read(key.fd, 65536)
                            if not data:
                                selector.unregister(key.fileobj)
                            pending += data
                            while b"\n" in pending:
                                line, pending = pending.split(b"\n", 1)
                                on_event(self.consume(request.job_id, line))
                    except KeyboardInterrupt:
                        cancelled = lambda: True
                return self.complete(request.job_id, process.wait())
            finally:
                selector.close()
                process.stdin.close()
                process.stdout.close()
