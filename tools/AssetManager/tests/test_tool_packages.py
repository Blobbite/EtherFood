"""Real generic jobs, immutable code, complete package transfer and diagnostics."""

from copy import deepcopy
from importlib.metadata import distribution
import json
import sys
import zipfile

from PIL import Image
import pytest

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.build_planner import BuildPlanner
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.recipe_builds import RecipeBuildService
from etherfood_studio.application.recipe_results import RecipeResultService
from etherfood_studio.application.source_import import SourceImportService, SourceSpec
from etherfood_studio.application.tool_environments import ToolEnvironments
from etherfood_studio.application.tool_packages import ToolPackageService
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.sources import expected_sources
from etherfood_studio.storage.blob_store import file_hash


@pytest.fixture
def studio(tmp_path):
    root = tmp_path / "studio"
    root.mkdir()
    project = ProjectService.new(root, "Ablaufeditor")
    yield project
    project.catalog.close()


def example():
    manifest = {
        "contract": "studio-tool-package-v1",
        "id": "report",
        "name": "Dateibericht",
        "version": "1.0.0",
        "description": "Dateien maschinell verarbeiten",
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "dependencies": [],
        "files": ["report.py", "helper.py"],
        "flows": [],
        "steps": [
            {
                "id": "report",
                "name": "Bericht",
                "description": "Berichtet Größe",
                "source": "report.py",
                "entry_point": "run",
                "execution": "map",
                "capabilities": [],
                "parameters": {},
                "inputs": {"image": {"type": "image"}},
                "outputs": {"report": {"type": "json", "directory": "Ergebnisse/Berichte"}},
            }
        ],
    }
    files = {
        "helper.py": b"def size(path):\n    return path.stat().st_size\n",
        "report.py": b"import json\nfrom helper import size\n"
        b"def run(context, inputs, parameters):\n"
        b"    result = context.artifact('report.json', 'json')\n"
        b"    result.path.write_text(json.dumps({'bytes': size(inputs['image'].path)}))\n"
        b"    return {'report': result}\n",
    }
    return manifest, files


def source_asset(project, tmp_path):
    assets = AssetService(project)
    owner = next(row.id for row in project.cards() if row.kind == "global")
    asset = assets.create("Quelle", owner, default_definition("texture").to_data())
    path = tmp_path / "original.png"
    Image.new("RGBA", (16, 8), (20, 40, 80, 200)).save(path)
    imports = SourceImportService(assets)
    key = expected_sources(assets.definition(asset.id))[0]
    imports.import_plan(
        imports.prepare(asset.id, asset.revision_no, [SourceSpec(path, key, 1, 1, 1)])
    )
    return asset, path


def test_real_multifile_job_publication_reuse_and_export(studio, tmp_path):
    service = ToolPackageService(studio)
    manifest, files = example()
    package = service.register(service.inspect_content(manifest, files))
    assert {issue["kind"] for issue in service.diagnostics(package["digest"])} == {
        "approval",
        "environment",
    }
    service.approve(package["digest"])
    environment = ToolEnvironments(studio)
    environment.prepare(manifest)
    assert environment.verify(manifest)["installed"]
    recipe = service.create_recipe(package["digest"], "report")
    asset, original = source_asset(studio, tmp_path)
    original_hash = file_hash(original)
    PipelineService(studio).assign(recipe.id, asset_id=asset.id)
    plan = RecipeBuildService(studio).plan(asset.id)
    run = BuildPlanner(studio).execute(plan)
    assert run["status"] == "succeeded" and run["published"], run
    result = RecipeResultService(studio).latest(asset.id)
    assert result["state"] == "ready", result
    artifact = result["artifacts"][0]
    path = studio.catalog.path.parent / artifact["file_path"]
    assert path.is_relative_to(studio.files.path(asset.id) / "Ergebnisse/Berichte")
    assert json.loads(path.read_text()) == {"bytes": original.stat().st_size}
    assert file_hash(original) == original_hash
    assert all(row.state == "reused" for row in RecipeBuildService(studio).plan(asset.id).nodes)
    exported = tmp_path / "tool.zip"
    service.export(package["digest"], exported)
    imported = service.preview(exported)
    assert imported.digest == package["digest"] and imported.files == files
    assert not imported.issues


def test_missing_file_and_syntax_are_editable_without_importing_code(studio):
    service = ToolPackageService(studio)
    manifest, files = example()
    del files["helper.py"]
    files["report.py"] = b"raise RuntimeError('must never execute on inspection')\ndef run(:\n"
    preview = service.inspect_content(manifest, files)
    assert {item["kind"] for item in preview.issues} == {"file", "syntax"}
    package = service.register(preview)
    with pytest.raises(StudioError):
        service.approve(package["digest"])
    draft = service.draft(package["digest"])
    repaired, files = example()
    repaired["version"] = "1.0.1"
    service.save_draft(draft["id"], repaired, files, draft["revision"])
    updated = service.publish_draft(draft["id"])
    assert updated["digest"] != package["digest"] and not updated["approved"]
    assert len(service.packages()) == 2


@pytest.fixture
def offline_pillow(tmp_path, monkeypatch):
    """Build a wheel from the installed dependency; tests never use a package index."""
    dist = distribution("Pillow")
    tag = next(
        line[5:] for line in dist.read_text("WHEEL").splitlines() if line.startswith("Tag: ")
    )
    wheel = tmp_path / f"pillow-{dist.version}-{tag}.whl"
    with zipfile.ZipFile(wheel, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in dist.files:
            if str(item).startswith("..") or str(item).endswith(".pyc"):
                continue
            path = dist.locate_file(item)
            if path.is_file():
                archive.write(path, str(item))
    original = ToolEnvironments.command

    def local(argv, on_output):
        if "pip" in argv and "install" in argv:
            argv = [*argv, "--no-index", "--find-links", str(tmp_path)]
        return original(argv, on_output)

    monkeypatch.setattr(ToolEnvironments, "command", staticmethod(local))


def test_builtin_resolution_nested_flow_multiple_artifacts(studio, tmp_path, offline_pillow):
    from etherfood_studio.application.builtin_tools import ensure
    from etherfood_studio.domain.pipeline_recipes import step
    from etherfood_studio.domain.tool_contract import empty_workflow, operation
    from etherfood_studio.application.tool_exchange import ToolExchange

    service = ToolPackageService(studio)
    package = ensure(studio)
    ToolEnvironments(studio).prepare(package["manifest"])
    asset, original = source_asset(studio, tmp_path)
    digest = file_hash(original)
    # Exercise actual nested expansion rather than copying a package flow into a recipe.
    recipe = empty_workflow()
    op = operation(package["digest"], "resolution", flow=True)
    node = step(op, service.manifests()[op])
    recipe["steps"].append(node)
    recipe["connections"].append(
        {"from": recipe["steps"][0]["id"], "out": "image", "to": node["id"], "in": "image"}
    )
    recipe["outputs"] = {
        name: {"node": node["id"], "port": name, **port}
        for name, port in service.manifests()[op]["ports"]["outputs"].items()
    }
    record = studio.create_card(
        "pipeline",
        "Varianten",
        studio.project().id,
        {"project_id": studio.project().id, "recipe": recipe},
    )
    PipelineService(studio).assign(record.id, asset_id=asset.id)
    plan = RecipeBuildService(studio).plan(asset.id)
    run = BuildPlanner(studio).execute(plan)
    assert run["status"] == "succeeded", run
    result = RecipeResultService(studio).latest(asset.id)
    assert result["state"] == "ready", result
    artifacts = result["artifacts"]
    assert len(artifacts) == 6 and {item["type"] for item in artifacts} == {"image", "html"}
    images = {item["metadata"]["profile"]: item for item in artifacts if item["type"] == "image"}
    assert images["comic_low"]["metadata"]["frame_size"] == [4, 2]
    assert images["comic_mid"]["metadata"]["frame_size"] == [8, 4]
    assert file_hash(original) == digest
    archive = tmp_path / "flow.zip"
    exchange = ToolExchange(studio)
    exchange.export(record.id, archive)
    preview = exchange.preview(archive)
    assert not preview.issues and len(preview.packages) == 1
    other_root = tmp_path / "other"
    other_root.mkdir()
    other = ProjectService.new(other_root, "Import")
    try:
        imported = ToolExchange(other).register(ToolExchange(other).preview(archive))
        assert imported.data["recipe"] == recipe
        assert not ToolPackageService(other).packages()[0]["approved"]
    finally:
        other.catalog.close()


def test_source_only_asset_migration_has_explicit_targets(studio, tmp_path):
    from etherfood_studio.application.workflow_migration import WorkflowMigration

    asset, original = source_asset(studio, tmp_path)
    pipeline = PipelineService(studio).create("Alt", "graphics")
    definition = AssetService(studio).definition(asset.id).to_data()
    definition["graphics"] = ["comic_low"]
    AssetService(studio).configure(asset.id, definition, studio.catalog.get(asset.id).revision_no)
    PipelineService(studio).assign(pipeline.id, asset_id=asset.id)
    WorkflowMigration(studio).ensure()
    definition = AssetService(studio).definition(asset.id)
    assert definition.schema_version == 2 and definition.graphics == definition.frames == ()
    assert "graphics_profiles" not in studio.project().data
    binding = PipelineService(studio).resolve(asset.id)
    recipe = binding["data"]
    assert recipe["contract"] == "studio-pipeline-v2" and not recipe["profiles"]
    assert len([node for node in recipe["steps"] if node["operation"].startswith("tool:")]) == 1
    assert (
        next(node for node in recipe["steps"] if node["operation"] != "source")["parameters"][
            "profile"
        ]
        == "comic_low"
    )
    assert original.exists()
    before = len(PipelineService(studio).recipes())
    WorkflowMigration(studio).ensure()
    assert len(PipelineService(studio).recipes()) == before
