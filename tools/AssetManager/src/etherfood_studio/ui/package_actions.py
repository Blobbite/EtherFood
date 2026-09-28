"""Explicitly invoked trusted package UI; discovery/rendering never evaluates Python."""

from copy import deepcopy
import hashlib

from ..domain.assets import require
from ..domain.models import StudioError
from ..domain.pipeline_recipes import validate_parameters


def invoke(service, identifier, action_id, parameters, parent, *, context=None):
    row = service.trusted(identifier)
    manifest = row["manifest"]
    action = next((a for a in manifest.get("actions", []) if a["id"] == action_id), None)
    require(action is not None, "Paketaktion ist nicht registriert oder nicht freigegeben.")
    validate_parameters(parameters, manifest["parameters"])
    source = service.store.path_for(row["code_hash"])
    code = source.read_bytes()
    require(hashlib.sha256(code).hexdigest() == row["code_hash"], "Paketcode wurde verändert.")
    namespace = {"__name__": "studio_trusted_ui_extension", "__file__": str(source)}
    try:
        exec(compile(code, str(source), "exec"), namespace)
        function = namespace[action["entry_point"]]
        result = function(parent, deepcopy(parameters)) if action.get("scope", "step") == \
            "step" else function(context, deepcopy(parameters), parent)
    except Exception as error:
        raise StudioError("plugin", "Paketaktion fehlgeschlagen: " + str(error)) from error
    current = service.trusted(identifier)
    require(current["code_hash"] == row["code_hash"] and current["manifest"] == manifest,
            "Paket während der Aktion geändert; Änderungen nicht übernommen.")
    if result is not None:
        validate_parameters(result, manifest["parameters"])
    return result


def invoke_step(project, node, action_id, parent, *, asset_id=None, recipe_id=None):
    context = {"project": project, "asset_id": asset_id, "recipe_id": recipe_id}
    operation = node["operation"]
    if operation.startswith("python:"):
        from ..application.plugin_service import PluginService
        return invoke(PluginService(project), operation, action_id, node["parameters"], parent,
                      context=context)
    from ..packages import action
    return action(operation, action_id, context, node["parameters"], parent)
