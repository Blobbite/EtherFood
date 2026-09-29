"""End-to-end image chains, portable nested tools and lossless legacy migration."""

from copy import deepcopy
from io import BytesIO
import json
import zipfile

from PIL import Image
import pytest

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.builtin_tools import ensure
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.tool_environments import ToolEnvironments
from etherfood_studio.application.tool_exchange import ToolExchange
from etherfood_studio.application.tool_packages import ToolPackageService
from etherfood_studio.application.workflow_migration import WorkflowMigration
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.pipeline_recipes import step, validate_recipe
from etherfood_studio.domain.tool_contract import empty_workflow, expand_workflow, operation
from etherfood_studio.storage.blob_store import file_hash
from etherfood_studio.storage.tool_archives import read_archive, read_json
from legacy_fixtures import asset_source
from legacy_fixtures import example, offline_pillow, source_asset, studio

def test_migration_preserves_all_inherited_flows_and_rule_overrides(studio, tmp_path):
    asset, _ = source_asset(studio, tmp_path)
    assets = AssetService(studio)
    definition = assets.definition(asset.id).to_data()
    definition["graphics"] = ["comic_low"]
    assets.configure(asset.id, definition, assets.asset(asset.id).revision_no)
    service = PipelineService(studio)
    graphics = service.create("Grafik", "graphics")
    colors = service.create("Farbe", "source_color")
    value = deepcopy(colors.data["recipe"])
    node = value["steps"][1]
    key = node["id"] + ".strength"
    value["overridable"] = [key]
    service.save(colors.id, value, colors.revision_no)
    service.assign(graphics.id, type_id="texture")
    assignment = service.assign(colors.id, type_id="texture", overrides={key: 0.25})
    WorkflowMigration(studio).ensure()
    selected = [service.resolve(asset.id, row.id) for row in service.recipes()]
    selected = [row for row in selected if row]
    assert len(selected) == 2
    operations = [node for binding in selected for node in binding["data"]["steps"]]
    assert [n["parameters"]["profile"] for n in operations if "profile" in n["parameters"]] == [
        "comic_low"
    ]
    assert (
        next(n for n in operations if n["operation"].endswith(":colors"))["parameters"]["strength"]
        == 0.25
    )
    # The inherited rule itself retains the override for assets created later.
    rule = studio.catalog.get(assignment.id)
    assert not rule.data["overrides"]
    rule_recipe = service.recipe(rule.data["recipe_id"]).data["recipe"]
    assert rule_recipe["steps"][1]["parameters"]["strength"] == 0.25
    revisions = [(row.id, row.revision_no) for row in studio.catalog.records()]
    WorkflowMigration(studio).ensure()
    assert revisions == [(row.id, row.revision_no) for row in studio.catalog.records()]


def test_nested_package_export_contains_foreign_tools_and_resources(studio, tmp_path):
    service = ToolPackageService(studio)
    manifest, files = example()
    dependency = service.register(service.inspect_content(manifest, files))
    _, recipe = service.recipe_data(dependency["digest"], "report")
    manifest = {
        **manifest,
        "id": "composition",
        "name": "Zusammensetzung",
        "steps": [],
        "files": ["README.txt"],
        "flows": [
            {"id": "reports", "name": "Berichte", "description": "Berichtsablauf", "recipe": recipe}
        ],
    }
    package = service.register(service.inspect_content(manifest, {"README.txt": b"Reports"}))
    exchange = ToolExchange(studio)
    target = tmp_path / "composition.zip"
    exchange.export_package(package["digest"], target)
    preview = exchange.preview(target)
    assert preview.root_package == package["digest"] and not preview.issues
    assert {p.digest for p in preview.packages} == {package["digest"], dependency["digest"]}
    assert exchange.register(preview)["digest"] == package["digest"]
    assert not any("environment" in key or "approved" in key for key in read_archive(target))


def test_missing_imports_and_changed_environment_are_diagnosed_and_repaired(studio):
    manifest, files = example()
    files["helper.py"] = b"import definitely_missing_studio_module\ndef size(path): return 1\n"
    service = ToolPackageService(studio)
    package = service.register(service.inspect_content(manifest, files))
    environments = ToolEnvironments(studio)
    receipt = environments.prepare(manifest)
    issues = service.diagnostics(package["digest"])
    missing = next(item for item in issues if item["kind"] == "import")
    assert missing["path"] == "helper.py" and missing["line"] == 1
    path = environments.directory(manifest) / "studio-environment.json"
    path.write_text("{}")
    assert environments.diagnostics(manifest)[0]["kind"] == "environment"
    assert environments.prepare(manifest)["installed"] == receipt["installed"]


def test_cycles_invalid_ports_and_archive_paths_are_rejected(studio):
    manifest, files = example()
    recipe = empty_workflow()
    recipe["steps"].append(
        {"id": "loop", "operation": "local-flow:loop", "enabled": True, "parameters": {}}
    )
    recipe["connections"] = [
        {"from": recipe["steps"][0]["id"], "out": "image", "to": "loop", "in": "image"}
    ]
    recipe["outputs"] = {"report": {"node": "loop", "port": "report", "type": "json"}}
    manifest["flows"] = [
        {"id": "loop", "name": "Schleife", "description": "Zyklus", "recipe": recipe}
    ]
    service = ToolPackageService(studio)
    package = service.register(service.inspect_content(manifest, files))
    root = deepcopy(recipe)
    root["steps"][1]["operation"] = operation(package["digest"], "loop", flow=True)
    with pytest.raises(StudioError, match="rekursiver"):
        expand_workflow(root, service.manifests())
    root["outputs"]["report"]["publish"] = "yes"
    with pytest.raises(StudioError, match="boolesch"):
        validate_recipe(root, service.manifests())
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("../outside.py", b"never")
    with pytest.raises(StudioError):
        read_archive(stream.getvalue())
    with pytest.raises(StudioError):
        read_json(b'{"duplicate":1,"duplicate":2}')
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("helpers/", b"")
        archive.writestr("helpers/size.py", b"value = 1\n")
    assert read_archive(stream.getvalue()) == {"helpers/size.py": b"value = 1\n"}
