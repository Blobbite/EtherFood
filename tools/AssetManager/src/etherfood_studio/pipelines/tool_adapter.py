"""Generic, typed file results using the existing cancellable job supervisor."""

import hashlib
import json
from pathlib import Path
import sys

from ..domain.assets import require
from ..domain.pipeline_recipes import validate_parameters
from ..domain.tool_contract import KINDS, compatible, validate_package
from ..storage.blob_store import file_hash
from ..storage.tool_archives import read_archive, read_json
from .base import CommandPlan, verify_files

OUTPUTS = ("artifacts.zip", "result.json")


def read_results(directory, ports=None):
    files = read_archive(directory / "artifacts.zip")
    result = read_json((directory / "result.json").read_bytes())
    require(
        isinstance(result, dict)
        and set(result) == {"contract", "ports"}
        and result["contract"] == "studio-artifacts-v1"
        and isinstance(result["ports"], dict),
        "Ungültiger Dateiergebnisvertrag.",
    )
    if ports is not None:
        require(
            set(result["ports"]) == set(ports),
            "Ergebnisausgänge stimmen nicht mit dem Baustein überein.",
        )
    seen = set()
    for port, items in result["ports"].items():
        spec = (ports or {}).get(port, {"type": "file", "multiple": True, "required": False})
        require(
            isinstance(items, list)
            and len(items) <= 1024
            and (items or not spec.get("required", True))
            and (spec.get("multiple", False) or len(items) <= 1),
            "Fehlende oder unerwartet viele Dateien an Ausgang " + port,
        )
        for item in items:
            require(
                isinstance(item, dict)
                and set(item) == {"path", "type", "metadata", "sha256", "length"}
                and item["path"] in files
                and item["path"] not in seen
                and item["type"] in KINDS
                and compatible(item["type"], spec["type"])
                and isinstance(item["metadata"], dict),
                "Ungültige Datei an Ausgang " + port,
            )
            raw = files[item["path"]]
            require(
                item["sha256"] == hashlib.sha256(raw).hexdigest() and item["length"] == len(raw),
                "Ergebnisdatei wurde verändert.",
            )
            if item["type"] in {"image", "spritesheet", "gif"}:
                from io import BytesIO
                from PIL import Image
                from .image_processing import validate_metadata

                with Image.open(BytesIO(raw)) as image:
                    require(
                        image.format == ("GIF" if item["type"] == "gif" else "PNG"),
                        "Bildformat passt nicht zum Ausgang.",
                    )
                    if item["type"] != "gif":
                        if item["metadata"]:
                            validate_metadata(item["metadata"], image.size)
                        require(
                            item["type"] != "spritesheet"
                            or item["metadata"].get("kind") == "spritesheet",
                            "Spritesheet benötigt explizite Raster-/Timingdaten.",
                        )
                    image.verify()
            elif item["type"] == "json":
                read_json(raw)
            elif item["type"] == "html":
                raw.decode("utf-8")
            seen.add(item["path"])
    require(seen == set(files), "Archiv enthält nicht deklarierte Ergebnisse.")
    return result, files


class ToolAdapter:
    identifier = "studio-tool"

    def validate(self, parameters):
        require(
            isinstance(parameters, dict)
            and set(parameters)
            == {
                "package_hash",
                "manifest",
                "entry",
                "python",
                "environment",
                "settings",
                "inputs",
                "source",
                "metadata",
                "resources",
            },
            "Ungültiger Skriptauftrag.",
        )
        require(
            isinstance(parameters["inputs"], list) and isinstance(parameters["resources"], dict),
            "Ungültige Dateibindungen.",
        )
        if parameters["manifest"] is None:
            require(
                parameters["entry"] == "source"
                and parameters["source"]
                and parameters["metadata"]
                and parameters["package_hash"] is None,
                "Ungültiger Quellauftrag.",
            )
        else:
            validate_package(parameters["manifest"])
            entries = {step["id"]: step for step in parameters["manifest"]["steps"]}
            require(parameters["entry"] in entries, "Paketeinstieg fehlt.")
            validate_parameters(parameters["settings"], entries[parameters["entry"]]["parameters"])

    def plan(self, workspace, parameters):
        self.validate(parameters)
        worker = Path(__file__).with_name("tool_worker.py")
        python = parameters["python"] if parameters["manifest"] else sys.executable
        require(Path(python).is_file(), "Verwalteter Python-Interpreter fehlt.")
        # The SDK and built-in algorithms are part of the execution identity.
        root = Path(__file__).parents[1]
        paths = [
            path
            for folder in ("domain", "storage", "pipelines", "packages")
            for path in (root / folder).rglob("*.py")
        ]
        hashes = [(str(p), file_hash(p)) for p in paths]
        hashes.extend(
            (("python", file_hash(Path(python))), ("environment", parameters["environment"]))
        )
        return CommandPlan(
            (python, "-I", "-B", str(worker), str(workspace)), OUTPUTS, tuple(sorted(hashes))
        )

    def execute(self, request, workspace):
        plan = self.plan(workspace, json.loads(request.parameters))
        require(
            plan.argv == request.argv
            and plan.tool_hashes == request.tool_hashes
            and plan.outputs == request.outputs,
            "Skriptumgebung hat sich seit der Planung geändert.",
        )
        return plan.argv

    def verify(self, request, workspace):
        parameters = json.loads(request.parameters)
        ports = (
            {"image": {"type": "image"}}
            if parameters["manifest"] is None
            else next(
                step["outputs"]
                for step in parameters["manifest"]["steps"]
                if step["id"] == parameters["entry"]
            )
        )
        files = verify_files(workspace / "output", request.outputs)
        read_results(workspace / "output", ports)
        return files
