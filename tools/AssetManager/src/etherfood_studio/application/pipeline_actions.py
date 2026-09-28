"""Discover optional package services without importing their Python modules."""

from .pipeline_service import PipelineService
from .plugin_service import PluginService


def condition(values, rule):
    return all(values.get(key) in allowed for key, allowed in rule.items())


class PipelineActions:
    def __init__(self, project):
        self.project = project

    def for_step(self, node, scope):
        if not node["enabled"]:
            return []
        operation = node["operation"]
        if operation.startswith("python:"):
            actions = PluginService(self.project).actions(operation)
        else:
            manifest = PipelineService(self.project).manifests().get(operation, {})
            actions = manifest.get("actions", [])
        return [a for a in actions if a.get("scope", "step") == scope]

    def for_recipe(self, recipe, scope):
        result, seen = [], set()
        if not recipe["enabled"]:
            return result
        for node in recipe["steps"]:
            for action in self.for_step(node, scope):
                key = node["operation"], action["id"]
                if key not in seen:
                    result.append((node, action))
                    seen.add(key)
        return result
