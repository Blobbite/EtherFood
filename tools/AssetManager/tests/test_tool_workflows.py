"""End-to-end image chains, portable nested tools and lossless legacy migration."""

from copy import deepcopy
from io import BytesIO
import json
import zipfile

from PIL import Image
import pytest

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.build_planner import BuildPlanner
from etherfood_studio.application.builtin_tools import ensure
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.recipe_builds import RecipeBuildService
from etherfood_studio.application.recipe_results import RecipeResultService
from etherfood_studio.application.tool_environments import ToolEnvironments
from etherfood_studio.application.tool_exchange import ToolExchange
from etherfood_studio.application.tool_packages import ToolPackageService
from etherfood_studio.application.workflow_migration import WorkflowMigration
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.pipeline_recipes import step, validate_recipe
from etherfood_studio.domain.tool_contract import empty_workflow, expand_workflow, operation
from etherfood_studio.storage.blob_store import file_hash
from etherfood_studio.storage.tool_archives import read_archive, read_json
from test_pipeline_processing import asset_source
from test_tool_packages import example, offline_pillow, source_asset, studio


def append(recipe, service, digest, entry, parent, *, input_port="image", output_port="image"):
    name = operation(digest, entry)
    node = step(name, service.manifests()[name])
    recipe["steps"].append(node)
    recipe["connections"].append(
        {"from": parent, "out": output_port, "to": node["id"], "in": input_port}
    )
    return node


def record(studio, asset, recipe):
    row = studio.create_card(
        "pipeline",
        "Verarbeitung",
        studio.project().id,
        {"project_id": studio.project().id, "recipe": recipe},
    )
    PipelineService(studio).assign(row.id, asset_id=asset.id)
    return row


def test_grid_scale_frames_gif_and_pose_report(studio, tmp_path, offline_pillow):
    asset, original = asset_source(studio, tmp_path, count=16, margins=True)
    original_hash = file_hash(original)
    service = ToolPackageService(studio)
    package = ensure(studio)
    ToolEnvironments(studio).prepare(package["manifest"])
    recipe = empty_workflow()
    grid = append(recipe, service, package["digest"], "grid", recipe["steps"][0]["id"])
    comic = append(recipe, service, package["digest"], "comic_low", grid["id"])
    comic["parameters"]["value"] = 0.5
    frames = append(recipe, service, package["digest"], "frames", comic["id"])
    frames["parameters"].update(frames=8, timing="keep_duration")
    gif = append(recipe, service, package["digest"], "gif", frames["id"])
    gif["parameters"].update(source_timing=False, fps=12)
    report = append(
        recipe,
        service,
        package["digest"],
        "pose_compare",
        gif["id"],
        input_port="images",
        output_port="gif",
    )
    recipe["outputs"] = {
        "sheet": {
            "node": frames["id"],
            "port": "image",
            "type": "image",
            "directory": "Ergebnisse/{pose}/Comic",
        },
        "gif": {"node": gif["id"], "port": "gif", "type": "gif", "directory": "GIFs/{pose}"},
        "report": {"node": report["id"], "port": "html", "type": "html", "directory": "Vergleiche"},
    }
    row = record(studio, asset, recipe)
    result = BuildPlanner(studio).execute(RecipeBuildService(studio).plan(asset.id, row.id))
    assert result["status"] == "succeeded" and result["published"], result
    artifacts = RecipeResultService(studio).latest(asset.id)["artifacts"]
    assert len(artifacts) == 3
    image = next(item for item in artifacts if item["type"] == "spritesheet")
    assert image["metadata"]["frames"] == 8 and image["metadata"]["frame_size"] == [2, 1]
    assert image["metadata"]["crop_offset"] == [2, 1]
    preview = next(item for item in artifacts if item["type"] == "gif")
    assert preview["metadata"]["duration"] == pytest.approx(8 / 12)
    with Image.open(studio.catalog.path.parent / preview["file_path"]) as picture:
        assert picture.n_frames == 8 and picture.size == (2, 1)
    html = next(item for item in artifacts if item["type"] == "html")
    content = (studio.catalog.path.parent / html["file_path"]).read_text()
    assert "data:image/gif;base64," in content and "__POSE_DATA__" not in content
    assert file_hash(original) == original_hash


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


def test_failures_cancellation_and_draft_tests_preserve_published_results(studio, tmp_path):
    service = ToolPackageService(studio)
    manifest, files = example()
    package = service.register(service.inspect_content(manifest, files))
    service.approve(package["digest"])
    ToolEnvironments(studio).prepare(manifest)
    asset, original = source_asset(studio, tmp_path)
    row = service.create_recipe(package["digest"], "report")
    PipelineService(studio).assign(row.id, asset_id=asset.id)
    built = BuildPlanner(studio).execute(RecipeBuildService(studio).plan(asset.id, row.id))
    assert built["published"]
    index = studio.files.path(asset.id) / "Ergebnisse/aktuell.json"
    before = index.read_bytes()
    original_hash = file_hash(original)
    result = service.test(package["digest"], "report", asset.id)
    assert result["status"] == "succeeded" and not result["published"]
    assert index.read_bytes() == before
    files["report.py"] = (
        b"def run(context, inputs, parameters):\n    raise RuntimeError('controlled failure')\n"
    )
    manifest["version"] = "1.0.1"
    failed = service.register(service.inspect_content(manifest, files))
    service.approve(failed["digest"])
    result = service.test(failed["digest"], "report", asset.id)
    assert result["status"] == "incomplete" and not result["published"]
    files["report.py"] = (
        b"import time\ndef run(context, inputs, parameters):\n"
        b"    context.log('READY_TO_CANCEL')\n    time.sleep(20)\n"
    )
    manifest["version"] = "1.0.2"
    pending = service.register(service.inspect_content(manifest, files))
    service.approve(pending["digest"])
    events = []
    result = service.test(
        pending["digest"],
        "report",
        asset.id,
        on_event=events.append,
        cancelled=lambda: any(
            event.get("phase") == "execute" and "/environments/" in str(event.get("argv"))
            for event in events
        ),
    )
    assert any(item["actual"] == "cancelled" for item in result["actual"]), result
    assert index.read_bytes() == before and file_hash(original) == original_hash


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


def test_relative_helpers_multiple_files_and_named_collect_input(studio, tmp_path):
    service = ToolPackageService(studio)
    manifest, _ = example()
    manifest["files"] = ["steps/__init__.py", "steps/helper.py", "steps/report.py", "collect.py"]
    entry = manifest["steps"][0]
    entry["source"] = "steps/report.py"
    entry["outputs"] = {"reports": {"type": "json", "multiple": True}}
    manifest["steps"].append(
        {
            **deepcopy(entry),
            "id": "collect",
            "name": "Zusammenfassen",
            "source": "collect.py",
            "execution": "collect",
            "inputs": {"reports": {"type": "json", "multiple": True}},
            "outputs": {"total": {"type": "json", "directory": "Ergebnisse/Summe"}},
        }
    )
    files = {
        "steps/__init__.py": b'LABEL = "Berichte"\n',
        "steps/helper.py": b"def value(index):\n    return str(index + 1)\n",
        "steps/report.py": b"from .helper import value\nfrom . import LABEL\n"
        b"def run(context, inputs, parameters):\n"
        b"    context.log(LABEL)\n    reports = []\n"
        b"    for index in range(2):\n"
        b"        output = context.artifact(str(index) + '.json', 'json')\n"
        b"        output.path.write_text(value(index))\n        reports.append(output)\n"
        b"    return {'reports': reports}\n",
        "collect.py": b"import json\ndef run(context, inputs, parameters):\n"
        b"    total = sum(json.loads(item.path.read_text()) for item in inputs['reports'])\n"
        b"    output = context.artifact('total.json', 'json')\n"
        b"    output.path.write_text(str(total))\n    return {'total': output}\n",
    }
    package = service.register(service.inspect_content(manifest, files))
    service.approve(package["digest"])
    ToolEnvironments(studio).prepare(manifest)
    asset, _ = source_asset(studio, tmp_path)
    _, recipe = service.recipe_data(package["digest"], "report")
    node = append(
        recipe,
        service,
        package["digest"],
        "collect",
        recipe["steps"][1]["id"],
        input_port="reports",
        output_port="reports",
    )
    recipe["outputs"] = {
        "sum": {
            "node": node["id"],
            "port": "total",
            "type": "json",
            "directory": "Ergebnisse/Summe",
        }
    }
    row = record(studio, asset, recipe)
    result = BuildPlanner(studio).execute(RecipeBuildService(studio).plan(asset.id, row.id))
    assert result["status"] == "succeeded" and result["published"], result
    artifacts = RecipeResultService(studio).latest(asset.id)["artifacts"]
    assert len(artifacts) == 1
    assert json.loads((studio.catalog.path.parent / artifacts[0]["file_path"]).read_text()) == 3


def test_empty_optional_output_publishes_and_required_output_is_rejected(studio, tmp_path):
    from etherfood_studio.pipelines.tool_adapter import read_results

    service = ToolPackageService(studio)
    manifest, files = example()
    manifest["steps"][0]["outputs"]["report"]["required"] = False
    files["report.py"] = b"def run(context, inputs, parameters):\n    return {'report': []}\n"
    package = service.register(service.inspect_content(manifest, files))
    service.approve(package["digest"])
    ToolEnvironments(studio).prepare(manifest)
    asset, original = source_asset(studio, tmp_path)
    original_hash = file_hash(original)
    recipe = service.create_recipe(package["digest"], "report")
    PipelineService(studio).assign(recipe.id, asset_id=asset.id)
    plan = RecipeBuildService(studio).plan(asset.id, recipe.id)
    result = BuildPlanner(studio).execute(plan)
    assert result["status"] == "succeeded" and result["published"], result
    index = json.loads((studio.files.path(asset.id) / "Ergebnisse/aktuell.json").read_text())
    assert index["artifacts"] == []
    assert file_hash(original) == original_hash
    assert all(node.state == "reused" for node in RecipeBuildService(studio).plan(asset.id).nodes)
    report = next(item for item in result["actual"] if item["node"] == plan.variants[0].node)
    job = studio.catalog.get(report["build_id"]).data["job_id"]
    directory = studio.catalog.path.parent / ".asset-studio/jobs" / job / "output"
    with pytest.raises(StudioError, match="Ausgang report"):
        read_results(directory, {"report": {"type": "json"}})
