"""Current file-based pipelines: strict ports, explicit folders and acyclic graphs."""

from copy import deepcopy
import re

from .assets import require
from .models import StudioError
from .tool_contract import KEY, KINDS, REQUIREMENT, relative_name

CONTRACT = "studio-pipeline-v3"
INPUT = "@input"
PORT_FIELDS = {"type", "multiple", "required", "animated", "extensions", "label"}


def compatible(actual, expected):
    """Spritesheets and single images require an explicit conversion step."""
    return actual == expected or expected == "file"


def ports(value):
    require(isinstance(value, dict) and len(value) <= 32, "Ungültige Anschlüsse.")
    for name, spec in value.items():
        require(
            isinstance(name, str) and KEY.fullmatch(name) is not None,
            "Anschluss benötigt einen eindeutigen Namen.",
        )
        require(
            isinstance(spec, dict) and {"type"} <= set(spec) <= PORT_FIELDS,
            "Unbekannte Anschlussfelder: " + name,
        )
        require(spec["type"] in KINDS, "Unbekannter Artefakttyp: " + name)
        for flag in ("multiple", "required", "animated"):
            require(
                flag not in spec or type(spec[flag]) is bool,
                "Anschlussschalter muss boolesch sein: " + name,
            )
        if "extensions" in spec:
            require(
                isinstance(spec["extensions"], list)
                and all(
                    isinstance(v, str) and re.fullmatch(r"\.[a-z0-9]{1,12}", v)
                    for v in spec["extensions"]
                ),
                "Dateiendungen sind ungültig: " + name,
            )
    return value


def script_description(value):
    require(isinstance(value, dict), "Skriptbeschreibung fehlt.")
    for field in ("inputs", "outputs"):
        ports(value.get(field))
    require(
        isinstance(value.get("entry_point"), str) and value["entry_point"].isidentifier(),
        "Python-Einstieg fehlt.",
    )
    require(
        value.get("execution", "map") in {"map", "collect"},
        "Ausführung muss map oder collect sein.",
    )
    require(isinstance(value.get("parameters", {}), dict), "Parameterbeschreibung fehlt.")
    dependencies = value.get("dependencies", [])
    require(
        isinstance(dependencies, list)
        and all(isinstance(v, str) and REQUIREMENT.fullmatch(v) for v in dependencies),
        "Bibliotheken mit festen Versionen deklarieren.",
    )
    for path in value.get("helpers", []):
        relative_name(path)
    return value


def empty_definition(identifier):
    return {
        "contract": CONTRACT,
        "id": identifier,
        "inputs": {},
        "nodes": [],
        "connections": [],
        "folders": [],
        "resources": {},
        "unresolved": [],
    }


def folder_path(value):
    relative_name(value)
    require(not any(c in value for c in '*?"<>|'), "Ungültiges Folder-Ziel.")
    tokens = re.findall(r"\{([^{}]+)\}", value)
    require(
        set(tokens) <= {"pose", "direction", "variant"}, "Unbekannter Platzhalter im Folder-Ziel."
    )
    require(
        not any(c in re.sub(r"\{[^{}]+\}", "", value) for c in "{}"),
        "Ungeschlossener Platzhalter im Folder-Ziel.",
    )
    require(
        not any(
            part.casefold() in {"source", "sources", "masks", "spritesheets"}
            for part in value.split("/")
        ),
        "Geschützter Quell-/Maskenordner.",
    )
    return value


def topological(nodes, edges, order=None):
    """Stable semantic order, independent of screen positions."""
    keys = set(nodes)
    remaining = {key: set() for key in keys}
    for source, target in edges:
        require(
            source in keys and target in keys and source != target,
            "Verbindung enthält einen fehlenden Knoten oder Selbstbezug.",
        )
        remaining[target].add(source)
    result = []
    order = order or {}
    while remaining:
        ready = sorted(
            (key for key, parents in remaining.items() if not parents),
            key=lambda key: (order.get(key, 0), key),
        )
        require(ready, "Die Verbindungen bilden einen Kreis.")
        key = ready[0]
        result.append(key)
        del remaining[key]
        for parents in remaining.values():
            parents.discard(key)
    return result


def validate_definition(data, scripts, *, complete=True):
    try:
        return _validate(data, scripts, complete=complete)
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise StudioError("validation", "Ungültige Pipelinedefinition.", str(error)) from error


def _validate(data, scripts, *, complete):
    require(
        isinstance(data, dict) and data.get("contract") == CONTRACT,
        "Unbekannte Pipelinedefinition.",
    )
    ports(data["inputs"])
    require(isinstance(data.get("resources", {}), dict), "Ressourcenbeschreibung ist ungültig.")
    for name, resource in data.get("resources", {}).items():
        relative_name(name)
        require(isinstance(resource, dict), "Ressource muss beschrieben sein: " + name)
    require(
        isinstance(data["nodes"], list) and len(data["nodes"]) <= 512,
        "Pipeline hat zu viele Knoten.",
    )
    descriptions = {INPUT: {"outputs": data["inputs"], "inputs": {}}}
    for node in data["nodes"]:
        require(
            isinstance(node["id"], str) and node["id"] not in descriptions,
            "Doppelte Knotenkennung.",
        )
        require(node["script_id"] in scripts, "Verwendetes Skript fehlt oder ist inaktiv.")
        descriptions[node["id"]] = script_description(scripts[node["script_id"]])
        parameters = node.get("parameters", {})
        if "resources" in node:
            require(
                isinstance(node["resources"], list)
                and all(
                    isinstance(name, str) and name in data.get("resources", {})
                    for name in node["resources"]
                ),
                "Knotenressourcen müssen vorhandene deklarierte Namen verwenden.",
            )
        require(isinstance(parameters, dict), "Knotenparameter sind ungültig.")
        from .pipeline_recipes import validate_parameters

        validate_parameters(parameters, descriptions[node["id"]].get("parameters", {}))
    seen, incoming, edges = set(), {}, []
    for edge in data["connections"]:
        source, target = edge["from"], edge["to"]
        require(
            source in descriptions and target in descriptions and target != INPUT,
            "Verbindung enthält einen unbekannten Knoten.",
        )
        outputs, inputs = descriptions[source]["outputs"], descriptions[target]["inputs"]
        require(
            edge["out"] in outputs and edge["in"] in inputs,
            "Verbindung benötigt vorhandene benannte Anschlüsse.",
        )
        token = (source, edge["out"], target, edge["in"])
        require(token not in seen, "Verbindung ist doppelt.")
        seen.add(token)
        actual, expected = outputs[edge["out"]], inputs[edge["in"]]
        require(
            compatible(actual["type"], expected["type"]),
            "Anschlusstypen passen nicht; einen ausdrücklichen Umwandlungsschritt ergänzen.",
        )
        require(
            not actual.get("multiple") or expected.get("multiple"),
            "Mehrfachausgang benötigt einen Mehrfacheingang.",
        )
        key = (target, edge["in"])
        incoming[key] = incoming.get(key, 0) + 1
        require(
            incoming[key] <= 1 or expected.get("multiple", False),
            "Einzeleingang ist mehrfach verbunden.",
        )
        edges.append((source, target))
    ordered = topological(descriptions, edges)
    names = set()
    require(isinstance(data["folders"], list), "Folder-Liste fehlt.")
    for folder in data["folders"]:
        name = folder["id"]
        require(
            isinstance(name, str) and KEY.fullmatch(name) and name not in names,
            "Folder benötigt einen eindeutigen Ausgangsnamen.",
        )
        names.add(name)
        require(
            folder["node"] in descriptions
            and folder["port"] in descriptions[folder["node"]]["outputs"],
            "Folder-Ausgang fehlt.",
        )
        require(
            folder.get("scope", "asset") in {"asset", "project"},
            "Folder benötigt Asset- oder Projektablage.",
        )
        folder_path(folder["directory"])
    if complete:
        require(
            not data.get("unresolved"),
            "Übernahme offen: " + "; ".join(str(v) for v in data.get("unresolved", [])),
        )
        require(data["folders"], "Mindestens ein verbundener Folder als Ausgabeziel fehlt.")
        for key, spec in descriptions.items():
            for name, port in spec["inputs"].items():
                require(
                    not port.get("required", True) or (key, name) in incoming,
                    "Notwendiger Eingang fehlt: " + key + "/" + name,
                )
    return ordered


def output_ports(definition, scripts):
    nodes = {n["id"]: scripts[n["script_id"]]["outputs"] for n in definition["nodes"]}
    nodes[INPUT] = definition["inputs"]
    return {
        folder["id"]: deepcopy(nodes[folder["node"]][folder["port"]])
        for folder in definition["folders"]
    }
