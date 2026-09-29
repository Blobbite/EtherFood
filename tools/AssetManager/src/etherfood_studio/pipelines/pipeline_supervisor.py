"""A small parent watchdog and process-group owner, independent of legacy jobs."""

import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from etherfood_studio.pipelines.processes import identity, require_supported, stop_group
from etherfood_studio.storage.sqlite_repository import canonical


def supervise(directory):
    request = json.loads((directory / "process.json").read_bytes())
    result = {"state": "failed", "reason": "Prozess nicht gestartet."}
    process = None
    selector = selectors.DefaultSelector()
    try:
        require_supported()
        environment = dict(os.environ)
        for key in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP"):
            environment.pop(key, None)
        worker = Path(__file__).with_name("pipeline_worker.py")
        with (
            (directory / "stdout.log").open("xb") as out,
            (directory / "stderr.log").open("xb") as err,
        ):
            process = subprocess.Popen(
                [request["python"], "-I", "-B", str(worker), str(directory)],
                cwd=directory,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=err,
                env=environment,
                start_new_session=True,
            )
            selector.register(sys.stdin, selectors.EVENT_READ)
            deadline = time.monotonic() + request["timeout"]
            result = {"state": "succeeded", "reason": ""}
            while True:
                if identity(request["parent_pid"]) != request["parent_stamp"]:
                    result = {"state": "cancelled", "reason": "Anwendung wurde beendet."}
                    break
                if time.monotonic() >= deadline:
                    result = {"state": "failed", "reason": "Zeitlimit überschritten."}
                    break
                if selector.select(0.04):
                    message = os.read(sys.stdin.fileno(), 1024)
                    if not message or b"cancel" in message:
                        result = {"state": "cancelled", "reason": "Durchgang abgebrochen."}
                        break
                state = os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
                if state is not None:
                    break
            stop_group(process.pid)
            code = process.wait()
            process = None
            if result["state"] == "succeeded" and code:
                result = {"state": "failed", "reason": f"Skript beendet mit Exit-Code {code}."}
            result["exit_code"] = code
    except Exception as error:
        result = {"state": "failed", "reason": str(error)}
    finally:
        if process is not None:
            stop_group(process.pid)
            process.wait()
        selector.close()
        (directory / "completion.json").write_text(canonical(result), encoding="utf-8")


if __name__ == "__main__":
    supervise(Path(sys.argv[1]))
