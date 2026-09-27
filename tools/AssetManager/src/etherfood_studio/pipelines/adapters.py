"""Allowlisted diagnostics only; never execute scripts supplied by imported assets."""

import json
from pathlib import Path
import sys

from ..domain.models import StudioError
from ..storage.blob_store import file_hash
from .base import BuildRequest, CommandPlan, verify_files

PIPELINES = Path(__file__).parent
TOOL_ROOT = PIPELINES.parents[2] / "PyGameTools"
MODES = ("success", "exit7", "missing", "slow", "child")


class DiagnosticAdapter:
    identifier = "diagnostic"

    def validate(self, parameters: dict) -> None:
        if (set(parameters) - {"mode", "value"} or
                parameters.get("mode", "success") not in MODES or
                not isinstance(parameters.get("value", ""), str) or
                len(parameters.get("value", "")) > 4096):
            raise StudioError("validation", "Ungültige Diagnoseparameter.")

    def plan(self, workspace: Path, parameters: dict) -> CommandPlan:
        self.validate(parameters)
        script = PIPELINES / "diagnostic_worker.py"
        argv = (sys.executable, "-I", "-B", str(script), parameters.get("mode", "success"),
                parameters.get("value", ""))
        outputs = ("result.json", "report.json")
        if parameters.get("mode") == "child":
            outputs += ("late-child.txt",)
        return CommandPlan(argv, outputs, self.hashes(script))

    @staticmethod
    def hashes(script: Path) -> tuple[tuple[str, str], ...]:
        return tuple((str(p), file_hash(p)) for p in sorted(set(
            list(PIPELINES.glob("*.py")) + [script])))

    def execute(self, request: BuildRequest, workspace: Path) -> tuple[str, ...]:
        plan = self.plan(workspace, json.loads(request.parameters))
        if (plan.argv != request.argv or plan.outputs != request.outputs or
                plan.tool_hashes != request.tool_hashes):
            raise StudioError("conflict", "Werkzeug/Plan seit Auftragserstellung verändert.")
        return plan.argv

    def verify(self, request: BuildRequest, workspace: Path) -> list[dict]:
        root = workspace / "output"
        files = verify_files(root, request.outputs)
        result = json.loads((root / "result.json").read_text(encoding="utf-8"))
        report = json.loads((root / "report.json").read_text(encoding="utf-8"))
        if (result != {"diagnostic": True, "value": json.loads(request.parameters).get("value", "")}
                or report != {"diagnostic": True, "verified": True}):
            raise StudioError("integrity", "Diagnosebericht passt nicht zum Auftrag.")
        return files


class FramReduceHelpAdapter(DiagnosticAdapter):
    identifier = "framreduce-help"

    def validate(self, parameters: dict) -> None:
        if parameters:
            raise StudioError("validation",
                              "Die Werkzeugprüfung akzeptiert keine freien Argumente.")

    def plan(self, workspace: Path, parameters: dict) -> CommandPlan:
        self.validate(parameters)
        script = TOOL_ROOT / "Pipline/1-SpritesheetFramReduce-Pipline" / \
            "PyPiplineStart-SpritesheetFramReduce.py"
        if not script.is_file():
            raise StudioError("unavailable", "Registrierter FramReduce-Starter fehlt.")
        helpers = TOOL_ROOT / "Pipline/PiplineToos"
        hashes = dict(self.hashes(script))
        hashes.update((str(p), file_hash(p)) for p in sorted(helpers.glob("*.py")))
        return CommandPlan((sys.executable, "-I", "-B", str(script), "--help"),
                           ("help.txt",), tuple(sorted(hashes.items())))

    def verify(self, request: BuildRequest, workspace: Path) -> list[dict]:
        # Exit code alone is insufficient: persist and validate the complete help artifact.
        data = (workspace / "logs/stdout.log").read_bytes()
        if b"--dry-run" not in data or b"--frames" not in data or not data.strip():
            raise StudioError("integrity", "Starter liefert nicht den erwarteten Help-Vertrag.")
        with (workspace / "output/help.txt").open("xb") as stream:
            stream.write(data)
        return verify_files(workspace / "output", request.outputs)


REGISTRY = {a.identifier: a for a in (DiagnosticAdapter(), FramReduceHelpAdapter())}


def adapter_for(identifier: str):
    if identifier not in REGISTRY:
        raise StudioError("validation", "Pipeline-Adapter ist nicht registriert.")
    return REGISTRY[identifier]
