"""One package invocation, inside its own interpreter and frozen job workspace."""

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from etherfood_studio.domain.assets import require
from etherfood_studio.domain.tool_contract import compatible
from etherfood_studio.pipelines.tool_sdk import Artifact, Context
from etherfood_studio.storage.tool_archives import (
    MAX_FILE,
    archive_bytes,
    json_bytes,
    read_archive,
    read_json,
)


def extract(files, target):
    target.mkdir(parents=True)
    for name, content in files.items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def run(workspace):
    request = read_json((workspace / "request.json").read_bytes())
    parameters = json.loads(request["parameters"])
    scratch = workspace / "work"
    scratch.mkdir()
    context = Context(scratch / "output", scratch / "package")
    if parameters["manifest"] is None:
        output = context.artifact(
            "source.png",
            "spritesheet" if parameters["metadata"]["kind"] == "spritesheet" else "image",
            parameters["metadata"],
        )
        output.path.write_bytes((workspace / "input" / parameters["source"]).read_bytes())
        outputs = {"image": output}
    else:
        archive = read_archive(workspace / "input/package.zip")
        manifest = read_json(archive.pop("manifest.json"))
        require(
            manifest == parameters["manifest"], "Paketmanifest stimmt nicht mit Auftrag überein."
        )
        extract(archive, context.package)
        entry = next(step for step in manifest["steps"] if step["id"] == parameters["entry"])
        incoming = {key: [] for key in entry["inputs"]}
        for index, binding in enumerate(parameters["inputs"]):
            files = read_archive(workspace / "input" / binding["archive"])
            data = read_json((workspace / "input" / binding["result"]).read_bytes())
            target = scratch / ("input-" + str(index))
            extract(files, target)
            for item in data["ports"][binding["out"]]:
                spec = entry["inputs"][binding["in"]]
                require(
                    compatible(item["type"], spec["type"])
                    and (
                        spec["type"] != "spritesheet"
                        or item["metadata"].get("kind") == "spritesheet"
                    ),
                    "Dateityp passt nicht zum Eingang " + binding["in"],
                )
                incoming[binding["in"]].append(
                    Artifact(target / item["path"], item["type"], item["metadata"])
                )
        for key, spec in entry["inputs"].items():
            values = incoming[key]
            require(
                (values or not spec.get("required", True))
                and (spec.get("multiple", False) or len(values) <= 1),
                "Eingang benötigt "
                + ("Dateien: " if spec.get("multiple") else "genau eine Datei: ")
                + key,
            )
            if not spec.get("multiple", False):
                incoming[key] = values[0] if values else None
        context.resources = {
            name: workspace / "input" / file for name, file in parameters["resources"].items()
        }
        sys.path.insert(0, str(context.package))
        source = context.package / entry["source"]
        sys.path.insert(0, str(source.parent))
        namespace = "studio_user_tool"
        package_module = ModuleType(namespace)
        package_module.__path__ = [str(context.package)]
        sys.modules[namespace] = package_module
        relative = source.relative_to(context.package)
        parts = list(relative.parent.parts)
        if source.stem != "__init__":
            parts.append(source.stem if source.stem.isidentifier() else "entry")
        module_name = ".".join([namespace, *parts])
        spec = importlib.util.spec_from_file_location(module_name, source)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        outputs = getattr(module, entry["entry_point"])(context, incoming, parameters["settings"])
        require(
            isinstance(outputs, dict) and set(outputs) == set(entry["outputs"]),
            "run muss für jeden deklarierten Ausgang ein Artifact oder eine Liste liefern.",
        )
    files, ports = {}, {}
    for key, values in outputs.items():
        values = values if isinstance(values, list) else [values]
        ports[key] = []
        for artifact in values:
            require(isinstance(artifact, Artifact), "Ausgang ist kein Artifact: " + key)
            path = artifact.path
            require(
                not path.is_symlink()
                and path.resolve().is_relative_to(context.output.resolve())
                and path.is_file(),
                "Ausgang muss eine Datei aus context.output sein.",
            )
            name = path.relative_to(context.output).as_posix()
            require(name not in files, "Jede Ausgabedatei darf nur einmal deklariert werden.")
            require(
                path.stat().st_size <= MAX_FILE,
                "Einzelergebnis überschreitet die Dateigrößengrenze.",
            )
            content = path.read_bytes()
            files[name] = content
            ports[key].append(
                {
                    "path": name,
                    "type": artifact.type,
                    "metadata": artifact.metadata,
                    "length": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                }
            )
    (workspace / "output/artifacts.zip").write_bytes(archive_bytes(files))
    (workspace / "output/result.json").write_bytes(
        json_bytes({"contract": "studio-artifacts-v1", "ports": ports})
    )


if __name__ == "__main__":
    run(Path(sys.argv[1]))
