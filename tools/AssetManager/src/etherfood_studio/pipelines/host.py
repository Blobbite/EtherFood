"""Trusted supervisor. Copies inputs, owns children, writes raw logs and verifies outputs."""

import os
from pathlib import Path
import selectors
import shutil
import subprocess
import sys
import time

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from etherfood_studio.pipelines.adapters import adapter_for
from etherfood_studio.pipelines.base import BuildRequest, read_json, write_json
from etherfood_studio.pipelines.processes import identity, require_supported, stop_group
from etherfood_studio.storage.blob_store import file_hash
from etherfood_studio.storage.paths import safe_target
from etherfood_studio.storage.sqlite_repository import canonical


class Supervisor:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.request = BuildRequest.from_data(read_json(workspace / "request.json"))
        self.sequence = 0
        self.process = None
        self.events = (workspace / "logs/events.jsonl").open("x", encoding="utf-8")

    def emit(self, kind: str, **data) -> None:
        self.sequence += 1
        event = {"job_id": self.request.job_id, "seq": self.sequence, "kind": kind, **data}
        line = canonical(event) + "\n"
        self.events.write(line)
        self.events.flush()
        try:
            sys.stdout.write(line)
            sys.stdout.flush()
        except BrokenPipeError:
            pass  # Parent watchdog still cancels the process group.

    def run(self) -> None:
        result = {"status": "failed", "exit_code": None, "files": [], "reason": ""}
        try:
            require_supported()
            self.emit("started")
            adapter = adapter_for(self.request.adapter)
            argv = adapter.execute(self.request, self.workspace)
            self.emit("phase", phase="inputs")
            project = self.workspace.parents[2]
            for item in self.request.inputs:
                source = safe_target(project, item.source)
                if source.stat().st_size != item.length or file_hash(source) != item.sha256:
                    raise ValueError("Geschützte Quelle verändert/fehlt")
                target = safe_target(self.workspace / "input", item.name)
                with source.open("rb") as incoming, target.open("xb") as output:
                    shutil.copyfileobj(incoming, output)
                if file_hash(target) != item.sha256:
                    raise ValueError("Arbeitskopie stimmt nicht mit Quelle überein")
            self.emit("phase", phase="execute", argv=list(argv),
                      tool_hashes=dict(self.request.tool_hashes))
            result.update(self.execute(argv))
            if result["status"] == "succeeded":
                self.emit("phase", phase="verify")
                result["files"] = adapter.verify(self.request, self.workspace)
                self.emit("progress", completed=1, total=1)
        except Exception as exc:
            result.update(status="failed", reason=str(exc))
        finally:
            if self.process is not None:
                try:
                    stop_group(self.process.pid)
                    self.process.wait()
                except Exception as exc:
                    result.update(status="interrupted", reason=str(exc))
            if result["status"] != "succeeded":
                self.emit("error" if result["status"] == "failed" else "warning",
                          message=result["reason"])
            result["job_id"] = self.request.job_id
            result["request_sha256"] = file_hash(self.workspace / "request.json")
            write_json(self.workspace / "result.json", result)
            self.emit("finished", **result)
            self.events.close()

    def execute(self, argv: tuple[str, ...]) -> dict:
        environment = dict(os.environ)
        for key in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP"):
            environment.pop(key, None)
        with (self.workspace / "logs/stdout.log").open("xb") as out, \
                (self.workspace / "logs/stderr.log").open("xb") as err:
            self.process = subprocess.Popen(argv, cwd=self.workspace / "output",
                                            env=environment, stdin=subprocess.DEVNULL,
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                            start_new_session=True)
            write_json(self.workspace / "process.json",
                       {"pid": self.process.pid, "stamp": identity(self.process.pid)})
            selector = selectors.DefaultSelector()
            selector.register(self.process.stdout, selectors.EVENT_READ, out)
            selector.register(self.process.stderr, selectors.EVENT_READ, err)
            selector.register(sys.stdin, selectors.EVENT_READ, None)
            deadline = time.monotonic() + self.request.timeout
            reason, status = "", "succeeded"
            try:
                while True:
                    parent_alive = identity(self.request.owner_pid) == self.request.owner_stamp
                    if not parent_alive or time.monotonic() >= deadline:
                        status = "interrupted" if not parent_alive else "failed"
                        reason = ("Anwendung beendet" if not parent_alive
                                  else "Zeitlimit überschritten")
                        break
                    for key, _ in selector.select(0.04):
                        data = os.read(key.fd, 65536)
                        if key.data is None:
                            if not data or b"cancel" in data:
                                status, reason = "cancelled", "Vom Benutzer abgebrochen"
                        elif data:
                            key.data.write(data)
                            key.data.flush()
                        else:
                            selector.unregister(key.fileobj)
                    if status != "succeeded":
                        break
                    # WNOWAIT keeps the group leader unreaped until descendants are stopped.
                    state = os.waitid(os.P_PID, self.process.pid,
                                      os.WEXITED | os.WNOHANG | os.WNOWAIT)
                    if state is not None:
                        break
                stop_group(self.process.pid)
                code = self.process.wait()
                # All managed writers are gone. Drain final raw bytes, without text decoding.
                for stream, log in ((self.process.stdout, out), (self.process.stderr, err)):
                    log.write(stream.read())
                    stream.close()
                self.process = None
                if status == "succeeded" and code != 0:
                    status, reason = "failed", f"Werkzeug beendet mit Exit-Code {code}"
                return {"status": status, "reason": reason, "exit_code": code}
            finally:
                selector.close()


if __name__ == "__main__":
    Supervisor(Path(sys.argv[1])).run()
