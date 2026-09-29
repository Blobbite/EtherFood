"""Real image algorithms after migration, executed through current files and phase runner."""

from PIL import Image
import pytest
from etherfood_studio.storage.blob_store import file_hash
from etherfood_studio.pipelines.image_processing import legacy_modules
from etherfood_studio.application.pipeline_execution import PipelineExecution
from etherfood_studio.application.pipeline_results import PipelineResults
from etherfood_studio.application.pipeline_workspace import PipelineWorkspace
from etherfood_studio.application.workspace_migration import WorkspaceMigration
from etherfood_studio.application.tool_environments import ToolEnvironments
from test_pipeline_workspace import project
from legacy_fixtures import (
    asset_source,
    recipe_for,
    append_step,
    palette_file,
    resource,
    offline_pillow,
)


@pytest.fixture(autouse=True)
def local_dependencies(offline_pillow):
    pass


def prepare_legacy(project):
    WorkspaceMigration(project).run()
    workspace = PipelineWorkspace(project)
    for script in workspace.scripts():
        if script.data["dependencies"]:
            ToolEnvironments(project).prepare(script.data)
    for definition in workspace.definitions():
        checked = workspace.check(definition.id)
        assert checked["valid"], checked
        workspace.approve(definition.id, checked["hash"])
    return workspace


def run(project, asset):
    prepare_legacy(project)
    report = PipelineExecution(project).run()
    assert report["state"] == "succeeded", report
    latest = PipelineResults(project).latest(asset.id)
    assert latest["state"] == "ready", latest
    return report, [item | {"image_path": item["file_path"]} for item in latest["artifacts"]]


def open_artifact(project, item):
    return Image.open(project.catalog.path.parent / item["image_path"])


@pytest.mark.parametrize("count", [8, 16])
def test_prepare_matches_source_grid_crop_anchor_and_preserves_original(project, tmp_path, count):
    asset, original = asset_source(project, tmp_path, count=count, margins=True)
    before = file_hash(original)
    recipe_for(project, asset, "prepare" + str(count))
    _, artifacts = run(project, asset)
    meta = artifacts[0]["metadata"]
    assert meta["grid"] == [4, count // 4]
    assert meta["logical_size"] == [8, 4] and meta["crop_offset"] == [2, 1]
    assert meta["crop_size"] == [4, 2] and meta["frame_size"] == [4, 2]
    assert meta["pixel_anchor"] == [2, 3]
    assert meta["source_indices"] == list(range(count))
    assert meta["fps"] == 8.0 and meta["duration"] == count / 8
    assert file_hash(original) == before
    copies = list((project.catalog.path.parent / ".asset-studio/pipeline-runs").rglob("inputs/*"))
    assert any(p.is_file() and p.stat().st_ino != original.stat().st_ino for p in copies)


@pytest.mark.parametrize("mode", ["soft", "fixed"])
def test_color_workflows_use_existing_algorithms_and_preserve_alpha(project, tmp_path, mode):
    count = 1 if mode == "soft" else 16
    asset, original = asset_source(project, tmp_path, count=count, alpha=173)
    colors = palette_file(tmp_path, mode=mode,
                          colors=[[55, 90, 165]] if mode == "soft" else None)

    def configure(recipe):
        node = recipe["steps"][-1]
        role = "reference" if mode == "soft" else "palette"
        node["parameters"].update(mode=mode, **{role: resource(project, recipe, role, colors)})
        if mode == "soft":
            node["parameters"].update(strength=1.0, max_distance=50.0)
        if count > 1:
            append_step(recipe, "frames",
                        parameters={"frames": 10, "fps": 12.0, "timing": "keep_fps"})

    recipe_for(project, asset, "source_color" if count == 1 else "color", configure)
    _, artifacts = run(project, asset)
    meta = artifacts[0]["metadata"]
    with open_artifact(project, artifacts[0]) as image:
        assert image.getchannel("A").getextrema() == (173, 173)
        assert image.getpixel((0, 0))[:3] != (40, 80, 160)
        if mode == "fixed":
            assert {color[:3] for _, color in image.getcolors()} <= {(12, 24, 36), (100, 120, 140)}
            assert meta["source_indices"] == [16 * k // 10 for k in range(10)]
            assert meta["duration"] == 10 / 12 and meta["fps"] == 12.0
        else:
            assert not {"fps", "loop", "duration", "timing_mode"} & set(meta)
    assert file_hash(original) == meta["source_sha256"]


def test_material_mask_follows_crop_reduction_and_nearest_scaling(project, tmp_path):
    asset, original = asset_source(project, tmp_path, count=16, margins=True)
    materials = palette_file(tmp_path, mode="material")
    exact = legacy_modules()[-1]
    mask_file = tmp_path / "mask.png"
    with Image.open(original) as image:
        mask = image.getchannel("A").point([0] + [1] * 255)
        mask.save(mask_file, pnginfo=exact.mask_metadata((16, 1), file_hash(original)))

    def configure(recipe):
        append_step(recipe, "frames", parameters={"frames": 8})
        append_step(recipe, "graphics")
        recipe["profiles"] = ["comic_mid", "pixel_low"]
        append_step(recipe, "color", parameters={"mode": "material",
            "materials": resource(project, recipe, "materials", materials),
            "mask": resource(project, recipe, "mask", mask_file)})

    recipe_for(project, asset, "prepare16", configure)
    _, artifacts = run(project, asset)
    assert len(artifacts) == 2
    for item in artifacts:
        meta = item["metadata"]
        assert meta["source_indices"] == list(range(0, 16, 2))
        assert meta["crop_offset"] == [2, 1] and meta["logical_size"] == [8, 4]
        with open_artifact(project, item) as image:
            assert {color[:3] for _, color in image.getcolors()} <= {(12, 24, 36), (100, 120, 140)}


def test_independent_branches_with_identical_frames_have_distinct_targets(project, tmp_path):
    asset, _ = asset_source(project, tmp_path, count=16)

    def configure(recipe):
        previous = recipe["steps"][-1]
        node = append_step(recipe, "frames", parameters={"fps": 12})
        recipe["connections"][-1]["from"] = recipe["steps"][0]["id"]
        assert node["id"] != previous["id"]

    recipe_for(project, asset, "frames", configure)
    _, artifacts = run(project, asset)
    assert len(artifacts) == 2
    assert {item["metadata"]["fps"] for item in artifacts} == {8, 12}
    assert all(item["metadata"]["frames"] == 8 for item in artifacts)


def test_small_sources_do_not_upscale_and_semitransparent_pixels_follow_legacy(project, tmp_path):
    asset, _ = asset_source(project, tmp_path, size=(12, 8), alpha=127)
    recipe_for(project, asset, "graphics")
    _, artifacts = run(project, asset)
    profiles = {item["metadata"]["profile"]: item for item in artifacts}
    assert profiles["pixel_high"]["metadata"]["frame_size"] == [12, 8]
    with open_artifact(project, profiles["pixel_high"]) as image:
        assert image.getchannel("A").getextrema() == (0, 0)
    with open_artifact(project, profiles["comic_mid"]) as image:
        assert image.getchannel("A").getextrema() == (127, 127)
