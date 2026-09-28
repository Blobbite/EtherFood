"""Read-only shipped manifests; discovery never imports processing or UI code."""

from copy import deepcopy
import importlib
import json
from pathlib import Path

ROOT = Path(__file__).parent
BUNDLES = ("source", "graphics", "animation", "colors")


def manifests():
    result = {}
    for bundle in BUNDLES:
        data = json.loads((ROOT / bundle / "manifest.json").read_text(encoding="utf-8"))
        for step in data["steps"]:
            result[step["id"]] = deepcopy(step)
    return result


def bundle_for(operation):
    key = "graphics" if operation == "scale" else operation
    return manifests()[key]["package"].removeprefix("studio:")


def files(operation):
    directory = ROOT / bundle_for(operation)
    return [p for p in directory.iterdir() if p.suffix in {".json", ".py"}]


def process(image, metadata, operation, parameters, resources, profile):
    bundle = bundle_for(operation)
    module = importlib.import_module(__name__ + "." + bundle + ".process")
    return module.apply(image, metadata, operation, parameters, resources, profile)


def action(operation, identifier, context, parameters, parent):
    spec = next(a for a in manifests()[operation]["actions"] if a["id"] == identifier)
    module = importlib.import_module(__name__ + "." + bundle_for(operation) + ".services")
    return getattr(module, spec["entry_point"])(context, deepcopy(parameters), parent)
