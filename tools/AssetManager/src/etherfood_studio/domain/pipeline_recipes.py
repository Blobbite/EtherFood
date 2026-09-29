"""Declarative recipes: project ownership, typed edges and no executable Python imports."""

from copy import deepcopy
import math
import re

from ..packages import manifests as bundled_manifests
from .assets import CAPABILITIES, require
from .models import new_id

CONTRACT = "studio-pipeline-v1"
TIMING_MODES = {"keep_fps": "Wiedergabe-FPS beibehalten",
                "keep_duration": "Animationsdauer beibehalten"}


def parameter(kind, default, **kwargs):
    return {"type": kind, "default": default, **kwargs}


# Shipped recipes are declarative packages. Python/UI is imported only on invocation.
BUILTINS = bundled_manifests()
TEMPLATES = {key: spec["template"] for key, spec in BUILTINS.items() if spec.get("template")}
TEMPLATES["empty"] = "Leeres Rezept"


def step(identifier: str, manifest: dict) -> dict:
    return {"id": new_id(), "operation": identifier, "enabled": True,
            "parameters": {k: deepcopy(v["default"]) for k, v in manifest["parameters"].items()}}


def template(identifier: str) -> dict:
    require(identifier in TEMPLATES, "Unbekannte Pipeline-Vorlage.")
    nodes = [step("source", BUILTINS["source"])]
    edges = []
    if identifier != "empty":
        nodes.append(step(identifier, BUILTINS[identifier]))
        edges.append({"from": nodes[0]["id"], "out": "image",
                      "to": nodes[1]["id"], "in": "image"})
    return {"contract": CONTRACT, "category": TEMPLATES[identifier], "enabled": True,
            "steps": nodes, "connections": edges, "profiles": [], "capabilities": [],
            "resources": {}, "overridable": [], "legacy_unresolved": []}


def validate_parameters(values: dict, definitions: dict) -> None:
    require(isinstance(values, dict) and set(values) == set(definitions),
            "Parameter stimmen nicht mit dem registrierten Schritt überein.")
    for key, spec in definitions.items():
        value, kind = values[key], spec["type"]
        if kind in {"integer", "number"}:
            require(type(value) in ({int} if kind == "integer" else {int, float}) and
                    math.isfinite(value) and spec["minimum"] <= value <= spec["maximum"],
                    "Ungültige Zahl: " + key)
        elif kind == "boolean":
            require(type(value) is bool, "Ungültiger Schalter: " + key)
        else:
            require(isinstance(value, str) and len(value) <= 512, "Ungültiger Text: " + key)
            if kind == "choice":
                require(value in spec["choices"], "Unbekannte Auswahl: " + key)
            require(kind in {"choice", "resource", "string"}, "Unbekannter Parametertyp.")


def validate_recipe(data: dict, manifests=None) -> list[dict]:
    """Validate structure; missing tools/references remain visibly blocked drafts."""
    manifests = BUILTINS if manifests is None else manifests
    from .tool_contract import WORKFLOW_CONTRACT, compatible, is_workflow, validate_ports

    modern = is_workflow(data)
    fields = set(template("empty")) | ({"outputs"} if modern else set())
    require(
        isinstance(data, dict)
        and set(data) == fields
        and data["contract"] in {CONTRACT, WORKFLOW_CONTRACT},
        "Unbekanntes oder unvollständiges Pipeline-Schema.",
    )
    require(type(data["enabled"]) is bool and isinstance(data["category"], str) and
            0 < len(data["category"]) <= 128, "Ungültige Pipeline-Kategorie/Aktivierung.")
    for name in ("profiles", "capabilities", "overridable", "legacy_unresolved"):
        require(isinstance(data[name], list) and len(data[name]) <= 256 and
                all(isinstance(v, str) and len(v) <= 512 for v in data[name]) and
                len(set(data[name])) == len(data[name]), "Ungültige Rezeptliste: " + name)
    require(set(data["capabilities"]) <= set(CAPABILITIES), "Unbekannte Asset-Fähigkeit.")
    require(isinstance(data["resources"], dict) and len(data["resources"]) <= 128,
            "Zu viele oder ungültige Ressourcen.")
    for key, resource in data["resources"].items():
        require(re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", key) is not None and
                isinstance(resource, dict) and set(resource) == {"sha256", "length", "name"} and
                isinstance(resource["sha256"], str) and
                re.fullmatch(r"[a-f0-9]{64}", resource["sha256"]) is not None and
                type(resource["length"]) is int and 0 < resource["length"] <= 32 * 1024 * 1024 and
                isinstance(resource["name"], str) and 0 < len(resource["name"]) <= 128 and
                not any(c in resource["name"] for c in "/\\:"), "Ungültige Ressource.")
    nodes, edges = data["steps"], data["connections"]
    require(isinstance(nodes, list) and 1 <= len(nodes) <= 128 and
            isinstance(edges, list) and len(edges) <= 256, "Ungültige Rezeptgröße.")
    by_id = {}
    for node in nodes:
        require(
            isinstance(node, dict)
            and set(node) == {"id", "operation", "enabled", "parameters"}
            and isinstance(node["id"], str)
            and re.fullmatch(r"[a-zA-Z0-9_-]{1,160}", node["id"]) is not None
            and node["id"] not in by_id
            and type(node["enabled"]) is bool
            and isinstance(node["operation"], str)
            and len(node["operation"]) <= 256
            and isinstance(node["parameters"], dict),
            "Ungültiger/doppelter Pipeline-Schritt.",
        )
        by_id[node["id"]] = node
        if node["operation"] in manifests:
            validate_parameters(node["parameters"], manifests[node["operation"]]["parameters"])
    seen, incoming, children = set(), {}, {key: [] for key in by_id}
    for edge in edges:
        require(isinstance(edge, dict) and set(edge) == {"from", "out", "to", "in"} and
                all(isinstance(v, str) for v in edge.values()), "Ungültige Verbindung.")
        left, right = by_id.get(edge["from"]), by_id.get(edge["to"])
        identity = tuple(edge[k] for k in ("from", "out", "to", "in"))
        spec = manifests.get(right["operation"], {}) if right else {}
        multiple = spec.get("ports", {}).get("inputs", {}).get(edge["in"], {}).get("multiple")
        require(
            left is not None
            and right is not None
            and identity not in seen
            and ((edge["to"], edge["in"]) not in incoming or modern and multiple),
            "Fehlende/mehrfache Eingangsverbindung.",
        )
        seen.add(identity)
        incoming[(edge["to"], edge["in"])] = edge["from"]
        children[edge["from"]].append(edge["to"])
        lm, rm = manifests.get(left["operation"]), manifests.get(right["operation"])
        if lm and rm:
            if modern:
                many = (
                    lm.get("ports", {})
                    .get("outputs", {})
                    .get(edge["out"], {})
                    .get("multiple", False)
                )
                require(not many or multiple, "Eine Dateiliste benötigt einen Mehrfacheingang.")
            require(
                edge["out"] in lm["outputs"]
                and edge["in"] in rm["inputs"]
                and (
                    compatible(lm["outputs"][edge["out"]], rm["inputs"][edge["in"]])
                    if modern
                    else lm["outputs"][edge["out"]] == rm["inputs"][edge["in"]]
                ),
                "Verbindung hat unpassende Ein-/Ausgabetypen.",
            )
    pending = {key: sum(e["to"] == key for e in edges) for key in by_id}
    ready = [key for key, count in pending.items() if not count]
    ordered = []
    while ready:
        key = ready.pop(0)
        ordered.append(by_id[key])
        for child in children[key]:
            pending[child] -= 1
            if not pending[child]:
                ready.append(child)
    require(len(ordered) == len(nodes), "Zyklus im technischen Pipeline-Canvas.")
    allowed = {
        n["id"] + "." + p
        for n in nodes
        for p in n["parameters"]
        if (n["operation"] not in manifests and n["operation"].startswith("python:"))
        or manifests.get(n["operation"], {}).get("parameters", {}).get(p, {}).get("type")
        in {"number", "integer", "boolean", "choice", "resource", "string"}
    }
    require(set(data["overridable"]) <= allowed, "Nicht freigebbarer lokaler Parameter.")
    if modern:
        require(not data["profiles"], "Abläufe v2 verwenden Bausteine statt Projektprofilen.")
        require(
            isinstance(data["outputs"], dict) and len(data["outputs"]) <= 128,
            "Ungültige Ablaufausgänge.",
        )
        exposed = set()
        for name, port in data["outputs"].items():
            require(
                isinstance(name, str)
                and re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", name)
                and isinstance(port, dict)
                and {"node", "port", "type"}
                <= set(port)
                <= {"node", "port", "type", "directory", "publish", "multiple", "label"}
                and port["node"] in by_id,
                "Ungültiger oder fehlender Ablaufausgang.",
            )
            validate_ports(
                {name: {key: value for key, value in port.items() if key not in {"node", "port"}}},
                outputs=True,
            )
            require(
                isinstance(port["port"], str) and (port["node"], port["port"]) not in exposed,
                "Jeden Bausteinausgang nur einmal veröffentlichen.",
            )
            exposed.add((port["node"], port["port"]))
            manifest = manifests.get(by_id[port["node"]]["operation"])
            if manifest:
                require(
                    manifest["outputs"].get(port["port"]) == port["type"],
                    "Ablaufausgang passt nicht zum Bausteinausgang.",
                )
                multiple = (
                    manifest.get("ports", {})
                    .get("outputs", {})
                    .get(port["port"], {})
                    .get("multiple", False)
                )
                require(
                    port.get("multiple", False) == multiple,
                    "Ablaufausgang muss die Dateiliste des Bausteins übernehmen.",
                )
    return ordered


def blockers(data: dict, manifests: dict) -> list[str]:
    validate_recipe(data, manifests)
    reasons = list(data["legacy_unresolved"])
    if not data["enabled"]:
        reasons.append("Pipeline ist deaktiviert")
    for node in data["steps"]:
        manifest = manifests.get(node["operation"])
        if manifest is None:
            reasons.append("Werkzeug fehlt: " + node["operation"])
            continue
        connected = {e["in"] for e in data["connections"] if e["to"] == node["id"]}
        required = {
            key
            for key in manifest["inputs"]
            if manifest.get("ports", {}).get("inputs", {}).get(key, {}).get("required", True)
        }
        if required - connected:
            reasons.append("Eingang fehlt: " + manifest["name"])
        if not node["enabled"]:
            if manifest["inputs"] != manifest["outputs"]:
                reasons.append("Schritt kann nicht typgleich durchreichen: " + manifest["name"])
            continue
        parameters = node["parameters"]
        if node["operation"] in {"color", "source_color"}:
            needed = {"soft": ["reference"], "fixed": ["palette"],
                      "material": ["materials", "mask"]}[parameters["mode"]]
            for name in needed:
                if parameters[name] == "@asset":
                    continue  # Managed, source-bound color resources; resolved in the dry-run.
                if name == "mask" and parameters[name] == "@source":
                    continue  # Resolved by source hash, with ambiguity errors in the dry-run.
                if parameters[name] not in data["resources"]:
                    reasons.append("Farbmodus benötigt Ressource: " + name)
    if all(n["operation"] == "source" or not n["enabled"] for n in data["steps"]):
        reasons.append("Noch kein aktiver Verarbeitungsschritt")
    return reasons
