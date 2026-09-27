"""Declarative recipes: project ownership, typed edges and no executable Python imports."""

from copy import deepcopy
import math
import re

from .assets import CAPABILITIES, require
from .models import new_id

CONTRACT = "studio-pipeline-v1"
TIMING_MODES = {"keep_fps": "Wiedergabe-FPS beibehalten",
                "keep_duration": "Animationsdauer beibehalten"}


def parameter(kind, default, **kwargs):
    return {"type": kind, "default": default, **kwargs}


BUILTINS = {
    "source": {"name": "Projektquelle", "inputs": {}, "outputs": {"image": "image"},
               "parameters": {}, "capabilities": []},
    "graphics": {"name": "Grafikprofile", "parameters": {"palette": parameter("resource", "")},
                 "capabilities": []},
    "prepare8": {"name": "Spritesheet · 8 Frames", "parameters": {},
                 "capabilities": ["animated"]},
    "prepare16": {"name": "Spritesheet · 16 Frames", "parameters": {},
                  "capabilities": ["animated"]},
    "frames": {"name": "Frameauswahl und Timing", "capabilities": ["animated"],
               "parameters": {"frames": parameter("integer", 8, minimum=1, maximum=64),
                   "timing": parameter("choice", "keep_fps", choices=list(TIMING_MODES)),
                   "fps": parameter("number", 8.0, minimum=0.01, maximum=240)}},
    "color": {"name": "Spritesheet-Farbverarbeitung", "capabilities": [],
              "parameters": {
                  "mode": parameter("choice", "soft", choices=["soft", "fixed", "material"]),
                  "reference": parameter("resource", ""),
                  "palette": parameter("resource", ""),
                  "materials": parameter("resource", ""),
                  "mask": parameter("resource", ""),
                  "strength": parameter("number", 0.6, minimum=0.0, maximum=1.0),
                  "max_distance": parameter("number", 18.0, minimum=1.0, maximum=50.0)}},
    "source_color": {"name": "Source-Farbverarbeitung", "capabilities": ["static_image"],
                     "parameters": {}},
}
BUILTINS["source_color"]["parameters"] = deepcopy(BUILTINS["color"]["parameters"])
for identifier, manifest in BUILTINS.items():
    manifest.update(id=identifier, version="1", description=manifest["name"])
    manifest.setdefault("inputs", {"image": "image"})
    manifest.setdefault("outputs", {"image": "image"})

TEMPLATES = {"graphics": "Grafik-Assets", "prepare8": "Spritesheets mit 8 Frames",
             "prepare16": "Spritesheets mit 16 Frames", "frames": "Frame-Reduktion und Timing",
             "color": "Spritesheet-Farbverarbeitung", "source_color": "Source-Farbverarbeitung",
             "empty": "Leeres Rezept"}


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
    fields = set(template("empty"))
    require(isinstance(data, dict) and set(data) == fields and data["contract"] == CONTRACT,
            "Unbekanntes oder unvollständiges Pipeline-Schema.")
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
        require(isinstance(node, dict) and set(node) == {"id", "operation", "enabled",
                "parameters"} and isinstance(node["id"], str) and
                re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", node["id"]) is not None and
                node["id"] not in by_id and type(node["enabled"]) is bool and
                isinstance(node["operation"], str) and len(node["operation"]) <= 128 and
                isinstance(node["parameters"], dict), "Ungültiger/doppelter Pipeline-Schritt.")
        by_id[node["id"]] = node
        if node["operation"] in manifests:
            validate_parameters(node["parameters"], manifests[node["operation"]]["parameters"])
    seen, incoming, children = set(), {}, {key: [] for key in by_id}
    for edge in edges:
        require(isinstance(edge, dict) and set(edge) == {"from", "out", "to", "in"} and
                all(isinstance(v, str) for v in edge.values()), "Ungültige Verbindung.")
        left, right = by_id.get(edge["from"]), by_id.get(edge["to"])
        identity = tuple(edge[k] for k in ("from", "out", "to", "in"))
        require(left is not None and right is not None and identity not in seen and
                (edge["to"], edge["in"]) not in incoming, "Fehlende/mehrfache Eingangsverbindung.")
        seen.add(identity)
        incoming[(edge["to"], edge["in"])] = edge["from"]
        children[edge["from"]].append(edge["to"])
        lm, rm = manifests.get(left["operation"]), manifests.get(right["operation"])
        if lm and rm:
            require(edge["out"] in lm["outputs"] and edge["in"] in rm["inputs"] and
                    lm["outputs"][edge["out"]] == rm["inputs"][edge["in"]],
                    "Verbindung hat unpassende Ein-/Ausgabetypen.")
    pending = {key: sum(v == key for v, _ in incoming) for key in by_id}
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
    allowed = {n["id"] + "." + p for n in nodes for p in n["parameters"]
               if (n["operation"] not in manifests and n["operation"].startswith("python:")) or
               manifests.get(n["operation"], {}).get("parameters", {}).get(p, {}).get(
                   "type") in {"number", "integer", "boolean", "choice", "resource"}}
    require(set(data["overridable"]) <= allowed, "Nicht freigebbarer lokaler Parameter.")
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
        if set(manifest["inputs"]) - connected:
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
                if name == "mask" and parameters[name] == "@source":
                    continue  # Resolved by source hash, with ambiguity errors in the dry-run.
                if parameters[name] not in data["resources"]:
                    reasons.append("Farbmodus benötigt Ressource: " + name)
    if all(n["operation"] == "source" or not n["enabled"] for n in data["steps"]):
        reasons.append("Noch kein aktiver Verarbeitungsschritt")
    return reasons
