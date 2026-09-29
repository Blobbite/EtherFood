"""Public examples and shipped manifests conform to their published contracts."""

from copy import deepcopy
import json
from pathlib import Path

import jsonschema
from referencing import Registry, Resource

from etherfood_studio.application.builtin_tools import preview
from etherfood_studio.application.tool_packages import ToolPackageService
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.tool_contract import empty_workflow


def test_published_schemas_match_runtime_examples():
    root = Path(__file__).resolve().parents[3]
    schemas = {}
    registry = Registry()
    for name in (
        "asset-definition-v2",
        "tool-package-v1",
        "pipeline-recipe-v2",
        "workflow-bundle-v1",
    ):
        schema = json.loads((root / "schemas/asset-studio" / (name + ".json")).read_text())
        jsonschema.Draft202012Validator.check_schema(schema)
        schemas[name] = schema
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))

    def valid(name, value):
        validator = jsonschema.Draft202012Validator(schemas[name], registry=registry)
        validator.validate(value)
        return validator

    example = root / "tools/AssetManager/examples/tool_report/manifest.json"
    manifest = json.loads(example.read_text())
    package = ToolPackageService.inspect_content(
        manifest, {name: (example.parent / name).read_bytes() for name in manifest["files"]}
    )
    assert not package.issues and len(package.files) == 2
    valid("tool-package-v1", package.manifest)
    valid("tool-package-v1", preview().manifest)
    workflow = empty_workflow()
    valid("pipeline-recipe-v2", workflow)
    for flow in preview().manifest["flows"]:
        valid("pipeline-recipe-v2", flow["recipe"])
    asset = default_definition("texture").to_data()
    asset.update(schema_version=2, graphics=[], frames=[])
    validator = valid("asset-definition-v2", asset)
    invalid = deepcopy(asset)
    invalid["graphics"] = ["comic_low"]
    assert list(validator.iter_errors(invalid))
    valid(
        "workflow-bundle-v1",
        {
            "contract": "studio-workflow-bundle-v1",
            "title": "Ablauf",
            "recipe": workflow,
            "packages": [package.digest],
            "resources": {},
        },
    )
    valid(
        "workflow-bundle-v1",
        {
            "contract": "studio-tool-bundle-v1",
            "title": "Paket",
            "root_package": package.digest,
            "packages": [package.digest],
            "resources": {},
        },
    )
