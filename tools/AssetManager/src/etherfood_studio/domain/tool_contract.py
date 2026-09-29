"""Declarative, versioned script packages and composable file-processing recipes."""

from copy import deepcopy
import hashlib
import re

from .assets import CAPABILITIES, require
from .models import new_id

PACKAGE_CONTRACT = "studio-tool-package-v1"
WORKFLOW_CONTRACT = "studio-pipeline-v2"
KINDS = {"image", "spritesheet", "gif", "html", "json", "file"}
KEY = re.compile(r"[a-z][a-z0-9_-]{0,63}")
VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
REQUIREMENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*==[A-Za-z0-9_.+-]+")


def relative_name(value):
    require(
        isinstance(value, str)
        and 0 < len(value) <= 240
        and not any(c in value for c in "\\:\x00")
        and all(
            part not in {"", ".", ".."} and not part.startswith(".") for part in value.split("/")
        ),
        "Ungültiger relativer Paket-/Ausgabepfad.",
    )
    return value


def output_directory(value):
    relative_name(value)
    require(
        not any(c in value for c in '*?"<>|')
        and not value.endswith((" ", "."))
        and value.split("/")[0] not in {"source", "masks", "Pakete"},
        "Ausgabeziel muss ein relativer Ergebnisordner beim Asset sein.",
    )
    return value


def validate_ports(ports, *, outputs=False):
    require(isinstance(ports, dict) and len(ports) <= 32, "Ungültige Anschlussliste.")
    for key, spec in ports.items():
        require(
            isinstance(key, str)
            and KEY.fullmatch(key) is not None
            and isinstance(spec, dict)
            and {"type"}
            <= set(spec)
            <= {"type", "multiple", "required", "directory", "label", "publish"},
            "Anschlussbeschreibung ist ungültig.",
        )
        require(spec["type"] in KINDS, "Unbekannter Anschlusstyp: " + str(spec["type"]))
        for field in {"multiple", "required", "publish"} & set(spec):
            require(type(spec[field]) is bool, "Anschlussschalter muss boolesch sein.")
        if "directory" in spec:
            require(outputs, "Ein Ausgabeziel gehört an einen Ausgang.")
            output_directory(spec["directory"])


def compatible(actual, expected):
    return (
        actual == expected
        or expected == "file"
        or (actual in {"image", "spritesheet"} and expected in {"image", "spritesheet"})
    )


def validate_package(data):
    from .pipeline_recipes import validate_parameters

    require(
        isinstance(data, dict)
        and set(data)
        == {
            "contract",
            "id",
            "name",
            "version",
            "description",
            "python",
            "dependencies",
            "files",
            "steps",
            "flows",
        }
        and data["contract"] == PACKAGE_CONTRACT,
        "Unbekannter oder unvollständiger Werkzeugpaketvertrag.",
    )
    require(
        isinstance(data["id"], str)
        and KEY.fullmatch(data["id"]) is not None
        and isinstance(data["version"], str)
        and VERSION.fullmatch(data["version"]),
        "Paket benötigt eine ID und eine Version wie 1.0.0.",
    )
    for field in ("name", "description"):
        require(
            isinstance(data[field], str) and 0 < len(data[field]) <= 2048,
            "Paketname/Beschreibung fehlt oder ist zu lang.",
        )
    require(
        isinstance(data["python"], str) and re.fullmatch(r"3\.[0-9]{1,2}", data["python"]),
        "Python-Version als Haupt-/Nebenversion angeben, beispielsweise 3.11.",
    )
    dependencies = data["dependencies"]
    require(
        isinstance(dependencies, list)
        and len(dependencies) <= 64
        and all(isinstance(v, str) and REQUIREMENT.fullmatch(v) for v in dependencies),
        "Bibliotheken mit festen Versionen angeben, beispielsweise Pillow==12.1.1.",
    )
    names = [re.sub(r"[-_.]+", "-", v.split("==")[0]).lower() for v in dependencies]
    require(len(names) == len(set(names)), "Bibliothek mehrfach angegeben.")
    files = data["files"]
    require(
        isinstance(files, list)
        and 1 <= len(files) <= 256
        and all(isinstance(v, str) for v in files)
        and len(files) == len(set(files)),
        "Paket benötigt eine eindeutige Liste seiner Dateien.",
    )
    for name in files:
        relative_name(name)
        require(
            name != "manifest.json" and not name.endswith((".pyc", ".pyo")),
            "Manifest und Python-Caches sind keine zusätzlichen Paketdateien.",
        )
    require(
        isinstance(data["steps"], list)
        and isinstance(data["flows"], list)
        and 1 <= len(data["steps"]) + len(data["flows"]) <= 128,
        "Ein Paket benötigt mindestens einen Baustein oder Ablauf.",
    )
    ids = set()
    for item in data["steps"]:
        require(
            isinstance(item, dict)
            and set(item)
            == {
                "id",
                "name",
                "description",
                "source",
                "entry_point",
                "inputs",
                "outputs",
                "parameters",
                "capabilities",
                "execution",
            },
            "Ungültige Bausteinbeschreibung.",
        )
        validate_entry(item, ids)
        require(
            item["source"] in files
            and item["source"].endswith(".py")
            and isinstance(item["entry_point"], str)
            and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", item["entry_point"]),
            "Baustein benötigt eine deklarierte Python-Datei und einen Funktionsnamen.",
        )
        validate_ports(item["inputs"])
        validate_ports(item["outputs"], outputs=True)
        require(
            bool(item["outputs"]) and item["execution"] in {"map", "collect"},
            "Baustein benötigt Ausgänge und map- oder collect-Ausführung.",
        )
        require(
            isinstance(item["capabilities"], list)
            and set(item["capabilities"]) <= set(CAPABILITIES),
            "Unbekannte Asset-Fähigkeit.",
        )
        require(
            isinstance(item["parameters"], dict) and len(item["parameters"]) <= 64,
            "Ungültige Bausteineinstellungen.",
        )
        for spec in item["parameters"].values():
            require(
                isinstance(spec, dict) and {"type", "default"} <= set(spec),
                "Parameter benötigt Typ und Vorgabewert.",
            )
        validate_parameters(
            {k: v["default"] for k, v in item["parameters"].items()}, item["parameters"]
        )
    for flow in data["flows"]:
        require(
            isinstance(flow, dict) and set(flow) == {"id", "name", "description", "recipe"},
            "Ungültiger Paketeinstieg.",
        )
        validate_entry(flow, ids)
        require(is_workflow(flow["recipe"]), "Paketeinstieg benötigt einen Ablaufvertrag v2.")


def validate_entry(item, ids):
    require(
        isinstance(item.get("id"), str)
        and KEY.fullmatch(item["id"]) is not None
        and item["id"] not in ids
        and isinstance(item.get("name"), str)
        and 0 < len(item["name"]) <= 128
        and isinstance(item.get("description"), str),
        "Baustein-/Ablaufkennung fehlt oder ist doppelt.",
    )
    ids.add(item["id"])


def is_workflow(recipe):
    return isinstance(recipe, dict) and recipe.get("contract") == WORKFLOW_CONTRACT


def empty_workflow():
    source = {"id": new_id(), "operation": "source", "enabled": True, "parameters": {}}
    return {
        "contract": WORKFLOW_CONTRACT,
        "category": "Eigener Ablauf",
        "enabled": True,
        "steps": [source],
        "connections": [],
        "resources": {},
        "overridable": [],
        "legacy_unresolved": [],
        "capabilities": [],
        "profiles": [],
        "outputs": {},
    }


def operation(package_hash, entry, *, flow=False):
    return ("flow:" if flow else "tool:") + package_hash + ":" + entry


def package_manifests(manifest, package_hash):
    result = {}
    for entry in manifest["steps"]:
        item = deepcopy(entry)
        item.update(
            package_hash=package_hash,
            package_id=manifest["id"],
            version=manifest["version"],
            contract=PACKAGE_CONTRACT,
            actions=[],
            dependencies=manifest["dependencies"],
        )
        item["ports"] = {"inputs": item["inputs"], "outputs": item["outputs"]}
        item["inputs"] = {k: v["type"] for k, v in item["inputs"].items()}
        item["outputs"] = {k: v["type"] for k, v in item["outputs"].items()}
        result[operation(package_hash, entry["id"])] = item
    for entry in manifest["flows"]:
        outputs = entry["recipe"]["outputs"]
        result[operation(package_hash, entry["id"], flow=True)] = {
            **deepcopy(entry),
            "contract": PACKAGE_CONTRACT,
            "package_hash": package_hash,
            "package_id": manifest["id"],
            "version": manifest["version"],
            "inputs": {"image": "image"},
            "outputs": {key: port["type"] for key, port in outputs.items()},
            "parameters": {},
            "capabilities": [],
            "actions": [],
            "ports": {
                "inputs": {"image": {"type": "image"}},
                "outputs": {
                    key: {
                        k: v
                        for k, v in port.items()
                        if k in {"type", "directory", "publish", "multiple", "label"}
                    }
                    for key, port in outputs.items()
                },
            },
        }
    return result


def resolve_local(recipe, package_hash):
    result = deepcopy(recipe)
    for node in result["steps"]:
        for prefix, flow in (("local:", False), ("local-flow:", True)):
            if node["operation"].startswith(prefix):
                node["operation"] = operation(
                    package_hash, node["operation"][len(prefix) :], flow=flow
                )
    return result


def expand_workflow(recipe, manifests, *, stack=()):
    """Inline immutable subflows while retaining explicitly exposed output ports."""
    require(len(stack) <= 16, "Teilabläufe sind zu tief verschachtelt.")
    result = deepcopy(recipe)
    for node in list(result["steps"]):
        name = node["operation"]
        if not name.startswith("flow:"):
            continue
        require(name in manifests and name not in stack, "Fehlender oder rekursiver Teilablauf.")
        manifest = manifests[name]
        nested = expand_workflow(
            resolve_local(manifest["recipe"], manifest["package_hash"]),
            manifests,
            stack=(*stack, name),
        )
        sources = [n for n in nested["steps"] if n["operation"] == "source"]
        require(len(sources) == 1, "Teilablauf benötigt genau einen Asset-Eingang.")
        incoming = [e for e in result["connections"] if e["to"] == node["id"]]
        outgoing = [e for e in result["connections"] if e["from"] == node["id"]]
        require(len(incoming) == 1, "Teilablauf benötigt eine Eingangsverbindung.")
        ids = {
            n["id"]: "nested_"
            + hashlib.sha256((node["id"] + ":" + n["id"]).encode()).hexdigest()[:32]
            for n in nested["steps"]
        }
        source_id = sources[0]["id"]
        replacement = []
        for child in nested["steps"]:
            if child["id"] == source_id:
                continue
            replacement.append(
                {**child, "id": ids[child["id"]], "enabled": node["enabled"] and child["enabled"]}
            )
        result["steps"] = [n for n in result["steps"] if n["id"] != node["id"]] + replacement
        result["connections"] = [
            e for e in result["connections"] if node["id"] not in {e["from"], e["to"]}
        ]
        for edge in nested["connections"]:
            result["connections"].append(
                {
                    **edge,
                    "to": ids[edge["to"]],
                    "from": incoming[0]["from"] if edge["from"] == source_id else ids[edge["from"]],
                    "out": incoming[0]["out"] if edge["from"] == source_id else edge["out"],
                }
            )
        for edge in outgoing:
            require(edge["out"] in nested["outputs"], "Teilablaufausgang fehlt.")
            port = nested["outputs"][edge["out"]]
            result["connections"].append(
                {
                    **edge,
                    "from": incoming[0]["from"] if port["node"] == source_id else ids[port["node"]],
                    "out": incoming[0]["out"] if port["node"] == source_id else port["port"],
                }
            )
        for output in result["outputs"].values():
            if output["node"] == node["id"]:
                port = nested["outputs"][output["port"]]
                output.update(
                    node=incoming[0]["from"] if port["node"] == source_id else ids[port["node"]],
                    port=incoming[0]["out"] if port["node"] == source_id else port["port"],
                )
        for key, value in nested["resources"].items():
            require(
                key not in result["resources"] or result["resources"][key] == value,
                "Teilabläufe verwenden widersprüchliche Ressourcenkennungen.",
            )
            result["resources"][key] = value
    return result
