"""Small real PNG builds, project boundaries, timing and selective cache invalidation."""

from copy import deepcopy
import json

from PIL import Image
import pytest

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.build_planner import BuildPlanner
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.profile_service import ProfileService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.recipe_builds import RecipeBuildService
from etherfood_studio.application.source_import import SourceImportService, SourceSpec
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.graphics import proportional_size
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.sources import expected_sources
from etherfood_studio.storage.blob_store import file_hash


@pytest.fixture
def pipeline_project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    project = ProjectService.new(root, "Projektpipelines")
    yield project
    project.catalog.close()


def make_asset(project, tmp_path, *, animated=False, size=(512, 256)):
    assets = AssetService(project)
    data = default_definition("effect" if animated else "texture").to_data()
    if animated:
        data["poses"] = data["poses"][:1]
        data["poses"][0]["fps"] = 8.0
    owner = next(r.id for r in project.cards() if r.kind == "global")
    asset = assets.create("Testasset", owner, data)
    frames = 16 if animated else 1
    path = tmp_path / (asset.id + ".png")
    image = Image.new("RGBA", (size[0] * frames, size[1]))
    for index in range(frames):
        frame = Image.new("RGBA", size, (index * 15, 180, 30, 255))
        image.paste(frame, (index * size[0], 0))
    image.save(path)
    imports = SourceImportService(assets)
    key = expected_sources(assets.definition(asset.id))[0]
    plan = imports.prepare(asset.id, asset.revision_no, [SourceSpec(path, key, frames, 1, frames)])
    imports.import_plan(plan)
    return asset, path


def build(project, asset_id):
    plan = RecipeBuildService(project).plan(asset_id)
    report = BuildPlanner(project).execute(plan)
    assert report["status"] == "succeeded", report["actual"]
    outputs = {}
    for row in report["actual"]:
        if row["actual"] in {"built", "reused"}:
            record = project.catalog.get(row["build_id"])
            path = (project.catalog.path.parent / ".asset-studio/jobs" /
                    record.data["job_id"] / "output")
            outputs[row["node"]] = (path, json.loads((path / "metadata.json").read_text()))
    return report, outputs


def test_proportional_rounding():
    assert proportional_size(512, 256, "factor", 0.5) == (256, 128)
    assert proportional_size(512, 256, "max_edge", 128) == (128, 64)
    assert proportional_size(40, 20, "max_edge", 128) == (40, 20)
    assert proportional_size(128, 64, "factor", 0.9) == (115, 58)
    assert proportional_size(5, 3, "factor", 0.5) == (3, 2)
    for value in (0, -1, float("nan"), float("inf")):
        with pytest.raises(StudioError):
            proportional_size(512, 256, "factor", value)


def test_real_graphics_cache_and_internal_pixel_high(pipeline_project, tmp_path):
    project = pipeline_project
    asset, original = make_asset(project, tmp_path)
    before = file_hash(original)
    pipelines = PipelineService(project)
    recipe = pipelines.create("Grafik", "graphics")
    pipelines.assign(recipe.id, asset_id=asset.id)
    report, outputs = build(project, asset.id)
    sizes = {meta["profile"]: meta["frame_size"] for _, meta in outputs.values()}
    assert sizes == {"comic_high": [512, 256], "comic_mid": [256, 128],
                     "comic_low": [128, 64], "pixel_high": [128, 64], "pixel_low": [115, 58]}
    for path, meta in outputs.values():
        assert "fps" not in meta and "loop" not in meta
        assert meta["logical_size"] == [512, 256]
    assert file_hash(original) == before
    again, _ = build(project, asset.id)
    assert all(r["actual"] == "reused" for r in again["actual"])
    profiles = list(ProfileService(project).profiles().values())
    next(p for p in profiles if p["key"] == "comic_low")["value"] = 0.2
    ProfileService(project).save(profiles, project.project().revision_no)
    changed, _ = build(project, asset.id)
    assert sum(r["actual"] == "built" for r in changed["actual"]) == 1
    profiles = list(ProfileService(project).profiles().values())
    for profile in profiles:
        profile["enabled"] = profile["key"] in {"comic_high", "comic_mid", "pixel_low"}
    ProfileService(project).save(profiles, project.project().revision_no)
    plan = RecipeBuildService(project).plan(asset.id)
    assert sum(v.required for v in plan.variants) == 3
    assert any("/pixel_high" in row.node.key for row in plan.nodes)
    build(project, asset.id)


@pytest.mark.parametrize("count", [8, 10, 12, 14])
def test_real_frame_indices_and_duration(pipeline_project, tmp_path, count):
    project = pipeline_project
    asset, _ = make_asset(project, tmp_path, animated=True, size=(4, 2))
    pipelines = PipelineService(project)
    record = pipelines.create("Frames", "frames")
    recipe = deepcopy(record.data["recipe"])
    recipe["steps"][1]["parameters"].update(frames=count, timing="keep_duration", fps=8.0)
    pipelines.save(record.id, recipe, record.revision_no)
    pipelines.assign(record.id, asset_id=asset.id)
    _, outputs = build(project, asset.id)
    path, meta = next(iter(outputs.values()))
    assert meta["source_indices"] == [16 * k // count for k in range(count)]
    assert meta["duration"] == 2.0
    assert meta["fps"] == count / 2
    with Image.open(path / "image.png") as image:
        for k, original in enumerate(meta["source_indices"]):
            pixel = image.getpixel((k % meta["grid"][0] * 4, k // meta["grid"][0] * 2))
            assert pixel[0] == original * 15


def test_assignment_project_scope_and_reload(pipeline_project, tmp_path):
    project = pipeline_project
    pipelines = PipelineService(project)
    first = pipelines.create("Projektstandard", "graphics")
    second = pipelines.create("Typregel", "graphics")
    third = pipelines.create("Explizit", "graphics")
    pipelines.assign(first.id)
    pipelines.assign(second.id, type_id="texture")
    asset, _ = make_asset(project, tmp_path)
    assert pipelines.resolve(asset.id)["recipe"].id == second.id
    pipelines.assign(third.id, asset_id=asset.id)
    assert pipelines.resolve(asset.id)["recipe"].id == third.id
    project.validate_structure()
    root = tmp_path / "other"
    root.mkdir()
    other = ProjectService.new(root, "Anderes Projekt")
    assert PipelineService(other).recipes() == []
    other.catalog.close()
    loaded = ProjectService.open(project.catalog.path.parent, read_only=True)
    assert PipelineService(loaded).resolve(asset.id)["recipe"].id == third.id
    loaded.catalog.close()
    pipelines.assign(second.id, asset_id=asset.id)
    with pytest.raises(StudioError, match="Konflikt"):
        pipelines.resolve(asset.id)
