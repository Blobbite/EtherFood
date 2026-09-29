"""Run one explicitly approved, frozen script in a controlled processing workspace."""

import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from etherfood_studio.domain.assets import require
from etherfood_studio.domain.pipeline_contract import compatible
from etherfood_studio.pipelines.tool_sdk import Artifact, Context
from etherfood_studio.storage.blob_store import file_hash
from etherfood_studio.storage.paths import safe_target
from etherfood_studio.storage.sqlite_repository import canonical


def run(directory):
    request = json.loads((directory / "invocation.json").read_bytes())
    description = request["description"]
    package = directory / "scripts"
    output = directory / "output"
    output.mkdir()
    incoming = {}
    for name, spec in description["inputs"].items():
        values = request["inputs"].get(name, [])
        require(
            (values or not spec.get("required", True))
            and (len(values) <= 1 or spec.get("multiple", False)),
            "Eingang benötigt passende Anzahl Dateien: " + name,
        )
        artifacts = []
        for item in values:
            path = safe_target(directory, item["path"])
            require(
                compatible(item["type"], spec["type"]) and file_hash(path) == item["sha256"],
                "Eingabetyp oder eingefrorene Eingabebytes stimmen nicht.",
            )
            artifacts.append(Artifact(path, item["type"], item["metadata"]))
        incoming[name] = artifacts if spec.get("multiple") else artifacts[0] if artifacts else None
    resources = {name: safe_target(directory, path) for name, path in request["resources"].items()}
    bundle = (
        safe_target(package, description["bundle_root"])
        if description.get("bundle_root")
        else package
    )
    context = Context(output, bundle, resources)
    source = safe_target(package, request["source"])
    namespace = "studio_current_script"
    parent = ModuleType(namespace)
    parent.__path__ = [str(package)]
    sys.modules[namespace] = parent
    parts = list(source.relative_to(package).with_suffix("").parts)
    # Namespace parents support relative imports without executing package __init__ on discovery.
    for count in range(1, len(parts)):
        key = ".".join([namespace, *parts[:count]])
        module = ModuleType(key)
        module.__path__ = [str(package.joinpath(*parts[:count]))]
        sys.modules[key] = module
    sys.path[:0] = [str(source.parent), str(bundle), str(package)]
    spec = importlib.util.spec_from_file_location(".".join([namespace, *parts]), source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    result = getattr(module, description["entry_point"])(context, incoming, request["parameters"])
    require(
        isinstance(result, dict) and set(result) == set(description["outputs"]),
        "run muss für jeden Ausgang ein Artifact oder eine Liste zurückgeben.",
    )
    outputs = {}
    for name, values in result.items():
        values = values if isinstance(values, list) else [values]
        outputs[name] = []
        for artifact in values:
            require(isinstance(artifact, Artifact), "Ausgang benötigt ein Artifact: " + name)
            relative = artifact.path.relative_to(output).as_posix()
            path = safe_target(output, relative)
            require(path.is_file(), "Ergebnisdatei fehlt: " + relative)
            outputs[name].append(
                {
                    "path": relative,
                    "type": artifact.type,
                    "metadata": artifact.metadata,
                    "sha256": file_hash(path),
                    "length": path.stat().st_size,
                }
            )
    (output / "result.json").write_text(canonical(outputs), encoding="utf-8")


if __name__ == "__main__":
    run(Path(sys.argv[1]))
