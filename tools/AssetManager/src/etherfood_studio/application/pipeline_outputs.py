"""Known output folders from saved requirements, without importing images or starting jobs."""

from pathlib import PurePosixPath

from ..domain.pipeline_recipes import validate_recipe
from ..domain.models import StudioError
from ..packages.previews.process import validate_directory


def image_directory(kind, pose, profile):
    branch = "spritesheets" if kind == "spritesheet" else "Ergebnisse"
    return str(PurePosixPath(branch, pose, profile))


def profile_paths(key, definitions):
    result = set()
    for definition in definitions:
        if definition.poses:
            result.update(image_directory(p.source_kind, p.export_name, key)
                          for p in definition.poses)
        else:
            result.add(image_directory("single_image", "", key))
    return sorted(result)


def recipe_outputs(recipe, manifests, profiles, definitions=()):
    """Shared display/projection contract; inactive and internal profiles have no target."""
    from ..domain.tool_contract import is_workflow
    if is_workflow(recipe):
        nodes = {node["id"]: node for node in recipe["steps"]}
        poses = {pose.export_name for definition in definitions for pose in definition.poses}
        poses = poses or {"Einzelbild"}
        rows = []
        for name, output in recipe["outputs"].items():
            node = nodes[output["node"]]
            directory = output.get("directory", "Ergebnisse/" + name)
            variant = node["parameters"].get("profile") or "{variante}"
            paths = sorted(directory.replace("{pose}", pose).replace("{variante}", variant)
                           for pose in poses)
            state = "internal" if not output.get("publish", True) else "active" if (
                recipe["enabled"] and node["enabled"]) else "inactive"
            rows.append({"id": "output_" + name, "node": node["id"], "kind": output["type"],
                         "title": output.get("label", name), "state": state, "paths": paths})
        return rows
    requested = set(recipe["profiles"] or (
        [key for definition in definitions for key in definition.graphics]
        if definitions else list(profiles)))
    active = {key for key in requested if key in profiles and profiles[key]["enabled"]}
    parents = {profiles[key]["parent"] for key in active if profiles[key]["parent"]}
    rows, flows = [], {}
    for node in validate_recipe(recipe, manifests):
        key = node["id"]
        incoming = any(flows.get(edge["from"], False) for edge in recipe["connections"]
                       if edge["to"] == key)
        flows[key] = node["operation"] == "source" or incoming
        is_graphics = manifests.get(node["operation"], {}).get("profile_targets", False)
        if is_graphics and node["enabled"]:
            flows[key] &= bool(active)
        enabled = recipe["enabled"] and node["enabled"] and flows[key]
        if is_graphics:
            for profile_key, profile in profiles.items():
                state = "active" if profile_key in active else \
                    "internal" if profile_key in parents else \
                    "disabled" if not profile["enabled"] else "unselected"
                if not enabled:
                    state = "inactive"
                definitions_for_key = [d for d in definitions
                                       if profile_key in (recipe["profiles"] or d.graphics)]
                rows.append({"id": "profile_" + key + "_" + profile_key, "node": key,
                    "kind": "profile", "profile": profile_key, "title": profile["name"],
                    "state": state, "paths": [] if state == "internal" else
                    profile_paths(profile_key, definitions_for_key),
                    "parent": profile["parent"]})
        if node["operation"] == "gif":
            try:
                paths = [validate_directory(node["parameters"]["directory"])]
                state = "active" if enabled else "inactive"
            except (StudioError, ValueError, TypeError):
                paths, state = [], "invalid"
            rows.append({"id": "output_" + key, "node": key, "kind": "gif",
                         "title": "GIF-Vorschauen", "state": state, "paths": paths})
    return rows


OUTPUT_STATES = {"active": "Aktive Ausgabe", "internal": "Nur interne Voraussetzung",
                 "disabled": "Profil deaktiviert", "unselected": "Nicht ausgewählt",
                 "inactive": "Datenfluss inaktiv", "invalid": "Ausgabeordner ungültig"}
