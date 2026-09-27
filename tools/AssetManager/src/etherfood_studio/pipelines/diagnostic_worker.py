"""Synthetic subprocess fixture, never an artistic build or approval."""

import json
from pathlib import Path
import subprocess
import sys
import time


def main() -> int:
    mode, value = sys.argv[1:3]
    print("Diagnose gestartet", flush=True)
    print("Diagnose stderr", file=sys.stderr, flush=True)
    if mode == "exit7":
        return 7
    if mode == "child":
        subprocess.Popen([sys.executable, "-I", "-B", "-c",
                          "import time; from pathlib import Path; time.sleep(1.5); "
                          "Path('late-child.txt').write_text('Must not survive cancellation')"])
        print("child-ready", flush=True)
    if mode in {"slow", "child"}:
        for _ in range(60):
            time.sleep(0.1)
    if mode != "missing":
        Path("result.json").write_text(json.dumps({"diagnostic": True, "value": value}),
                                        encoding="utf-8")
        Path("report.json").write_text('{"diagnostic":true,"verified":true}', encoding="utf-8")
    print("Fertig", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
