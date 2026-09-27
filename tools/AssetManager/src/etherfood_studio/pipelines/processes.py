"""Linux process identities and managed groups; no arbitrary-process termination."""

import os
from pathlib import Path
import signal
import time

from ..domain.models import StudioError


def identity(pid: int) -> str:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return fields[19] if fields[0] != "Z" else ""
    except (OSError, IndexError):
        return ""


def require_supported() -> None:
    if os.name != "posix" or not identity(os.getpid()):
        raise StudioError("unavailable", "Sichere Auftragsverwaltung benötigt derzeit Linux /proc.")


def group_members(group: int) -> list[int]:
    members = []
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        try:
            fields = (path / "stat").read_text().rsplit(")", 1)[1].split()
            if int(fields[2]) == group and fields[0] != "Z":
                members.append(int(path.name))
        except (OSError, IndexError, ValueError):
            pass
    return members


def stop_group(group: int) -> None:
    # Called only while our direct child is alive/unreaped; PID cannot be recycled.
    for sig, grace in ((signal.SIGTERM, 0.3), (signal.SIGKILL, 2.0)):
        try:
            os.killpg(group, sig)
        except ProcessLookupError:
            return
        until = time.monotonic() + grace
        while group_members(group) and time.monotonic() < until:
            time.sleep(0.02)
        if not group_members(group):
            return
    raise StudioError("cleanup", "Kindprozesse noch aktiv; Auftrag bleibt gesperrt.")
