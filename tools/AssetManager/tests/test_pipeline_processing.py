"""Synthetic PNG integration checks for processing, frozen plans and published derivations."""

from copy import deepcopy
import json

from PIL import Image
import pytest

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.build_planner import BuildPlanner
from etherfood_studio.application.job_service import JobService
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.profile_service import ProfileService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.recipe_builds import RecipeBuildService
from etherfood_studio.application.recipe_results import RecipeResultService
from etherfood_studio.application.source_import import SourceImportService, SourceSpec
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.pipeline_recipes import BUILTINS, step
from etherfood_studio.domain.sources import expected_sources
from etherfood_studio.pipelines.base import BuildRequest
from etherfood_studio.pipelines.image_adapter import ImageAdapter
from etherfood_studio.pipelines.image_processing import legacy_modules
from etherfood_studio.storage.blob_store import BlobStore, file_hash
from etherfood_studio.storage.job_store import JobStore
from etherfood_studio.storage.sqlite_repository import canonical


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    value = ProjectService.new(root, "Bildpipelines")
    yield value
    value.catalog.close()


def asset_source(project, tmp_path, *, count=1, size=(8, 4), margins=False, alpha=255):
    assets = AssetService(project)
    data = default_definition("texture" if count == 1 else "effect").to_data()
    if count > 1:
        data["poses"] = data["poses"][:1]
        data["poses"][0]["fps"] = 8.0
    owner = next(r.id for r in project.cards() if r.kind == "global")
    asset = assets.create("Synthetisches Bild", owner, data)
    image = Image.new("RGBA", (size[0] * count, size[1]))
    for index in range(count):
        frame = Image.new("RGBA", size)
        rect = (2, 1, size[0] - 2, size[1] - 1) if margins else (0, 0, *size)
        frame.paste((40 + index * 10, 80, 160, alpha), rect)
        image.paste(frame, (index * size[0], 0))
    path = tmp_path / (asset.id + ".png")
    image.save(path)
    imports = SourceImportService(assets)
    key = expected_sources(assets.definition(asset.id))[0]
    imports.import_plan(imports.prepare(asset.id, asset.revision_no,
        [SourceSpec(path, key, count, 1, count)]))
    return asset, path


def recipe_for(project, asset, template, edit=None):
    service = PipelineService(project)
    record = service.create("Bildrezept", template)
    if edit:
        recipe = deepcopy(record.data["recipe"])
        edit(recipe)
        record = service.save(record.id, recipe, record.revision_no)
    service.assign(record.id, asset_id=asset.id)
    return record


def append_step(recipe, operation, *, enabled=True, parameters=None):
    node = step(operation, BUILTINS[operation])
    node["enabled"] = enabled
    node["parameters"].update(parameters or {})
    recipe["connections"].append({"from": recipe["steps"][-1]["id"], "out": "image",
                                  "to": node["id"], "in": "image"})
    recipe["steps"].append(node)
    return node


def resource(project, recipe, key, path):
    blob = BlobStore(project.catalog, project.catalog.path.parent).import_file(path)
    recipe["resources"][key] = {"sha256": blob["sha256"], "length": blob["length"],
                                "name": path.name}
    return key


def palette_file(tmp_path, *, mode="fixed", colors=None):
    _, _, _, _, soft, exact = legacy_modules()
    colors = colors or [[12, 24, 36], [100, 120, 140]]
    refs = [{"path": "stand.png", "direction": direction, "sha256": "0" * 64,
             "size": [8, 4], "grid": [1, 1], "frames": 1} for direction in soft.DIRECTIONS]
    if mode == "soft":
        value = {"format": soft.FORMAT, "version": 1, "method": soft.METHOD,
                 "references": refs, "colors": colors, "pixel_palette": colors}
    else:
        value = {"format": exact.FIXED_FORMAT if mode == "fixed" else exact.MATERIAL_FORMAT,
                 "version": 1, "color_space": "sRGB", "references": refs}
        value.update({"colors": colors} if mode == "fixed" else
                     {"materials": [{"id": 1, "name": "Gewebe", "colors": colors}]})
    path = tmp_path / (mode + ".json")
    path.write_text(canonical(value), encoding="utf-8")
    return path


def run(project, asset):
    report = BuildPlanner(project).execute(RecipeBuildService(project).plan(asset.id))
    assert report["status"] == "succeeded", report["actual"]
    latest = RecipeResultService(project).latest(asset.id)
    assert latest["state"] == "ready", latest
    return report, latest["artifacts"]


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
    job = JobStore(project.catalog).rows()[0]
    workspace = JobService(project).workspace(job["id"])
    copied = workspace / "input" / job["request"]["inputs"][0]["name"]
    assert copied.stat().st_ino != original.stat().st_ino


def test_prepare_alternatives_and_static_reduction_rejected_before_jobs(project, tmp_path):
    asset, _ = asset_source(project, tmp_path, count=8)
    recipe_for(project, asset, "prepare16")
    with pytest.raises(StudioError, match="Quellframezahl"):
        RecipeBuildService(project).plan(asset.id)
    static, _ = asset_source(project, tmp_path)
    recipe_for(project, static, "frames")
    with pytest.raises(StudioError, match="Fähigkeiten|Einzelbilder"):
        RecipeBuildService(project).plan(static.id)
    assert JobStore(project.catalog).rows() == []


def test_custom_three_profiles_and_pixel_palette_are_real(project, tmp_path):
    asset, _ = asset_source(project, tmp_path, count=16, size=(256, 128))
    profiles = list(ProfileService(project).profiles().values())
    for profile in profiles:
        profile["enabled"] = profile["key"] in {"comic_high", "pixel_low"}
    profiles.append({**profiles[0], "key": "mini-hd", "name": "Eigene Variante", "value": 0.125})
    ProfileService(project).save(profiles, project.project().revision_no)
    recipe_for(project, asset, "graphics", lambda r: r.update(
        profiles=["comic_high", "pixel_high", "pixel_low", "mini-hd"]))
    report, artifacts = run(project, asset)
    assert len(artifacts) == 3 and report["plan"]["counts"]["not_required"] == 1
    by_profile = {item["metadata"]["profile"]: item for item in artifacts}
    assert by_profile["mini-hd"]["metadata"]["frame_size"] == [32, 16]
    assert by_profile["pixel_low"]["metadata"]["frame_size"] == [115, 58]
    high_row = next(row for row in report["actual"] if row["node"].endswith("/pixel_high"))
    high_record = project.catalog.get(high_row["build_id"])
    high = RecipeResultService(project).metadata(high_record)
    with open_artifact(project, high) as image, \
            open_artifact(project, by_profile["pixel_low"]) as low:
        palette = {color for _, color in image.getcolors()}
        assert {color for _, color in low.getcolors()} <= palette and len(palette) <= 64
        for index in range(16):
            assert low.getpixel((index * 115, 0)) == image.getpixel((index * 128, 0))


def test_deactivated_leaf_bypasses_preserves_settings_and_cache(project, tmp_path):
    asset, _ = asset_source(project, tmp_path)
    record = recipe_for(project, asset, "graphics",
                        lambda r: append_step(r, "color", enabled=False))
    first, artifacts = run(project, asset)
    assert len(artifacts) == 5
    recipe = deepcopy(record.data["recipe"])
    recipe["steps"][-1]["parameters"].update(strength=0.1, mode="material")
    PipelineService(project).save(record.id, recipe, record.revision_no)
    project.catalog.save_layout(record.id, {"x": 321, "y": 123, "width": 250, "height": 180})
    second, _ = run(project, asset)
    assert all(item["actual"] == "reused" for item in second["actual"])
    assert {r["fingerprint"] for r in first["actual"]} == \
        {r["fingerprint"] for r in second["actual"]}


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


@pytest.mark.parametrize("failure", ["missing", "geometry", "format", "source_hash"])
def test_material_missing_and_invalid_resources_block_dry_run(project, tmp_path, failure):
    asset, original = asset_source(project, tmp_path, count=16)
    materials = palette_file(tmp_path, mode="material")
    exact = legacy_modules()[-1]
    mask = tmp_path / "mask.png"
    info = exact.mask_metadata((16, 1),
                               "0" * 64 if failure == "source_hash" else file_hash(original))
    Image.new("L", (128 if failure != "geometry" else 127, 4), 1).save(mask, pnginfo=info)
    if failure == "format":
        materials.write_text('{"format":"other","version":1}', encoding="utf-8")

    def configure(recipe):
        recipe["steps"][-1]["parameters"].update(mode="material",
            materials=resource(project, recipe, "materials", materials),
            mask="absent" if failure == "missing" else resource(project, recipe, "mask", mask))

    recipe_for(project, asset, "color", configure)
    with pytest.raises((StudioError, ValueError), match="Ressource|Maske|Profil"):
        RecipeBuildService(project).plan(asset.id)
    assert JobStore(project.catalog).rows() == []


def test_shared_palette_invalidates_only_pixel_dependants(project, tmp_path):
    asset, _ = asset_source(project, tmp_path, size=(32, 16))
    palette = palette_file(tmp_path)
    record = recipe_for(project, asset, "graphics", lambda r: r["steps"][-1]["parameters"].update(
        palette=resource(project, r, "palette", palette)))
    run(project, asset)
    palette = palette_file(tmp_path, colors=[[20, 40, 60], [90, 110, 130]])
    recipe = deepcopy(record.data["recipe"])
    resource(project, recipe, "palette", palette)
    PipelineService(project).save(record.id, recipe, record.revision_no)
    plan = RecipeBuildService(project).plan(asset.id)
    assert {r.node.key.split("/")[-1] for r in plan.nodes if r.state == "stale"} == {
        "pixel_high", "pixel_low"}
    run(project, asset)


def test_frozen_snapshot_runs_old_revision_and_current_status_is_stale(project, tmp_path):
    asset, _ = asset_source(project, tmp_path, count=16)
    record = recipe_for(project, asset, "frames")
    plan = RecipeBuildService(project).plan(asset.id)
    recipe = deepcopy(record.data["recipe"])
    recipe["steps"][-1]["parameters"].update(frames=10, fps=12)
    PipelineService(project).save(record.id, recipe, record.revision_no)
    report = BuildPlanner(project).execute(plan)
    assert report["status"] == "succeeded" and report["published"]
    latest = RecipeResultService(project).latest(asset.id)
    assert latest["state"] == "stale" and latest["recipe_revision"] == record.revision_no
    assert latest["artifacts"][0]["metadata"]["frames"] == 8
    assert latest["artifacts"][0]["metadata"]["fps"] == 8
    assert json.loads(report["plan"]["snapshot"])["recipe"] != recipe


def test_cancelled_partial_job_never_publishes_or_mutates_original(project, tmp_path):
    asset, original = asset_source(project, tmp_path, count=16, size=(64, 32))
    recipe_for(project, asset, "graphics")
    plan = RecipeBuildService(project).plan(asset.id)
    before = file_hash(original)
    cancelled = []

    def event(value):
        if value["kind"] == "phase" and value.get("phase") == "execute":
            cancelled.append(True)

    report = BuildPlanner(project).execute(plan, cancelled=lambda: bool(cancelled), on_event=event)
    assert report["status"] == "incomplete" and not report["published"]
    assert any(row["actual"] == "cancelled" for row in report["actual"])
    assert RecipeResultService(project).latest(asset.id)["state"] == "not_started"
    assert file_hash(original) == before
    assert project.catalog.db.execute("SELECT count(*) FROM build_cache").fetchone()[0] == 0


@pytest.mark.parametrize("damage", ["shape", "indices", "anchor", "source", "pixels"])
def test_verifier_rejects_consistent_but_wrong_worker_claims(project, tmp_path, damage):
    asset, _ = asset_source(project, tmp_path, count=16)
    recipe_for(project, asset, "frames")
    run(project, asset)
    job = JobStore(project.catalog).rows()[0]
    request = BuildRequest.from_data(job["request"])
    workspace = JobService(project).workspace(job["id"])
    path = workspace / "output/metadata.json"
    meta = json.loads(path.read_text())
    image_path = workspace / "output/image.png"
    if damage == "shape":
        with Image.open(image_path) as image:
            altered = image.resize((8, 4))
        altered.save(image_path)
        meta.update(grid=[8, 1], frame_size=[1, 4])
    elif damage == "indices":
        meta["source_indices"] = list(range(8))
    elif damage == "anchor":
        meta["anchor"] = [0, 0]
        meta["pixel_anchor"] = [0, 0]
    elif damage == "source":
        meta["source_sha256"] = "0" * 64
    else:
        Image.new("RGBA", (32, 8), "red").save(image_path)
    meta["image_sha256"] = file_hash(image_path)
    path.write_text(canonical(meta), encoding="utf-8")
    with pytest.raises(StudioError, match="Ergebnis|Raster|Frame|Plan"):
        ImageAdapter().verify(request, workspace)
    assert RecipeResultService(project).latest(asset.id)["state"] == "invalid"


def test_adapter_rejects_invalid_parameters_before_job_admission(project, tmp_path):
    asset, _ = asset_source(project, tmp_path)
    recipe_for(project, asset, "graphics")
    row = RecipeBuildService(project).plan(asset.id).nodes[0]
    valid = json.loads(row.node.parameters)
    cases = []
    for update in ({"source": "../original.png"}, {"metadata": {}}, {"resources": []},
                   {"settings": {"unused": 1}}, {"plugin": {"arbitrary": "path"}}):
        cases.append({**valid, **update})
    for value in (0, -1, float("nan"), float("inf")):
        cases.append({**valid, "profile": {**valid["profile"], "value": value}})
    for parameters in cases:
        with pytest.raises(StudioError):
            JobService(project).prepare(asset.id, "studio-image", parameters,
                                        source_ids=row.node.source_ids)
    assert JobStore(project.catalog).rows() == []


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


def test_failed_new_attempt_retains_previous_complete_publication(project, tmp_path):
    asset, _ = asset_source(project, tmp_path, count=16)
    record = recipe_for(project, asset, "frames")
    previous, _ = run(project, asset)
    recipe = deepcopy(record.data["recipe"])
    recipe["steps"][-1]["parameters"]["frames"] = 10
    PipelineService(project).save(record.id, recipe, record.revision_no)
    report = BuildPlanner(project).execute(RecipeBuildService(project).plan(asset.id),
                                           cancelled=lambda: True)
    assert not report["published"] and report["status"] == "incomplete"
    latest = RecipeResultService(project).latest(asset.id)
    assert latest["run_id"] == previous["run_id"]
    assert latest["last_run_status"] == "incomplete" and latest["state"] == "stale"
    assert latest["artifacts"][0]["metadata"]["frames"] == 8


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


@pytest.mark.parametrize("failure", ["size", "network", "input_write", "missing"])
def test_trusted_python_worker_rejects_invalid_results_and_side_effects(project, tmp_path, failure):
    from etherfood_studio.application.plugin_service import PluginService

    asset, original = asset_source(project, tmp_path)
    before = file_hash(original)
    manifest = {"contract": "studio-python-step-v1", "id": "python:failure_fixture",
                "name": "Absichtlich ungültiger Test", "version": "1", "description": "Test",
                "parameters": {}, "inputs": {"image": "image"}, "outputs": {"image": "image"},
                "capabilities": [], "entry_point": "process", "dependencies": []}
    manifest_path, code_path = tmp_path / "manifest.json", tmp_path / "worker.py"
    manifest_path.write_text(canonical(manifest), encoding="utf-8")
    body = {"size": "return image.resize((1, 1))", "missing": "return None",
            "network": "import socket\n    socket.socket()\n    return image",
            "input_write": "from pathlib import Path\n    Path(__file__).write_text('changed')\n"
                           "    return image"}[failure]
    code_path.write_text("def process(image, parameters):\n    " + body + "\n", encoding="utf-8")
    plugins = PluginService(project)
    registered = plugins.register(manifest_path, code_path)
    plugins.approve(manifest["id"], registered["code_hash"])

    def configure(recipe):
        node = step(manifest["id"], manifest)
        recipe["connections"].append({"from": recipe["steps"][0]["id"], "out": "image",
                                      "to": node["id"], "in": "image"})
        recipe["steps"].append(node)

    recipe_for(project, asset, "empty", configure)
    report = BuildPlanner(project).execute(RecipeBuildService(project).plan(asset.id))
    assert report["status"] == "incomplete" and not report["published"]
    assert report["actual"][0]["actual"] == "failed"
    assert file_hash(original) == before
    assert project.catalog.db.execute("SELECT count(*) FROM build_cache").fetchone()[0] == 0


def test_disabled_targets_are_not_required_even_without_originals(project):
    assets = AssetService(project)
    owner = next(r.id for r in project.cards() if r.kind == "global")
    asset = assets.create("Noch ohne Quelle", owner, default_definition("texture").to_data())
    profiles = list(ProfileService(project).profiles().values())
    for profile in profiles:
        profile["enabled"] = False
    ProfileService(project).save(profiles, project.project().revision_no)
    recipe_for(project, asset, "graphics")
    plan = RecipeBuildService(project).plan(asset.id)
    assert plan.nodes == () and plan.counts["not_required"] == 5
    assert RecipeBuildService(project).dry_run()[0]["state"] == "excluded"
    assert JobStore(project.catalog).rows() == []


def test_source_bound_masks_select_direction_and_detect_ambiguity(project, tmp_path):
    assets = AssetService(project)
    owner = next(r.id for r in project.cards() if r.kind == "global")
    data = default_definition("character").to_data()
    data["directions"] = ["N", "SW"]
    asset = assets.create("Richtungen", owner, data)
    imports = SourceImportService(assets)
    slots = expected_sources(assets.definition(asset.id))
    specs, masks = [], []
    exact = legacy_modules()[-1]
    for index, key in enumerate(slots):
        path = tmp_path / (key.direction + ".png")
        Image.new("RGBA", (32, 2), (20 + index * 100, 40, 60, 255)).save(path)
        specs.append(SourceSpec(path, key, 16, 1, 16))
        mask = tmp_path / (key.direction + "-mask.png")
        Image.new("L", (32, 2), index + 1).save(mask,
            pnginfo=exact.mask_metadata((16, 1), file_hash(path)))
        masks.append(mask)
    imports.import_plan(imports.prepare(asset.id, asset.revision_no, specs))
    colors = palette_file(tmp_path, mode="material")
    palette = json.loads(colors.read_text())
    palette["materials"].append({"id": 2, "name": "Metall", "colors": [[200, 220, 240]]})
    colors.write_text(canonical(palette), encoding="utf-8")

    def configure(recipe):
        recipe["steps"][-1]["parameters"].update(mode="material", mask="@source",
            materials=resource(project, recipe, "materials", colors))
        for index, mask in enumerate(masks):
            resource(project, recipe, "mask" + str(index), mask)

    record = recipe_for(project, asset, "color", configure)
    _, artifacts = run(project, asset)
    assert len(artifacts) == 2
    for item in artifacts:
        with open_artifact(project, item) as image:
            color = image.getpixel((0, 0))[:3]
            if item["metadata"]["slot"]["direction"] == "SW":
                assert color == (200, 220, 240)
            else:
                assert color in {(12, 24, 36), (100, 120, 140)}
    recipe = deepcopy(record.data["recipe"])
    recipe["resources"]["duplicate"] = deepcopy(recipe["resources"]["mask0"])
    record = PipelineService(project).save(record.id, recipe, record.revision_no)
    with pytest.raises(StudioError, match="genau eine"):
        RecipeBuildService(project).plan(asset.id)
    recipe["resources"].pop("duplicate")
    recipe["steps"][-1]["parameters"]["mask"] = "mask0"
    PipelineService(project).save(record.id, recipe, record.revision_no)
    with pytest.raises(StudioError, match="Materialmaske"):
        RecipeBuildService(project).plan(asset.id)


def test_exact_color_order_requires_explicit_final_mapping(project, tmp_path):
    asset, _ = asset_source(project, tmp_path, count=16)
    colors = palette_file(tmp_path)

    def configure(recipe):
        recipe["steps"][-1]["parameters"].update(mode="fixed",
            palette=resource(project, recipe, "palette", colors))
        append_step(recipe, "graphics")
        recipe["profiles"] = ["comic_mid"]

    record = recipe_for(project, asset, "color", configure)
    with pytest.raises(StudioError, match="Festfarben nach Skalierung"):
        RecipeBuildService(project).plan(asset.id)
    assert JobStore(project.catalog).rows() == []
    recipe = deepcopy(record.data["recipe"])
    append_step(recipe, "color", parameters={"mode": "fixed", "palette": "palette"})
    PipelineService(project).save(record.id, recipe, record.revision_no)
    _, artifacts = run(project, asset)
    with open_artifact(project, artifacts[0]) as image:
        assert {color[:3] for _, color in image.getcolors()} <= {(12, 24, 36), (100, 120, 140)}


def test_missing_sources_report_pose_and_direction(project):
    assets = AssetService(project)
    owner = next(r.id for r in project.cards() if r.kind == "global")
    data = default_definition("character").to_data()
    data["directions"] = ["SW"]
    data["poses"][0]["display_name"] = "Langsames Gehen"
    asset = assets.create("Figur", owner, data)
    recipe_for(project, asset, "graphics")
    with pytest.raises(StudioError, match="Langsames Gehen · SW"):
        RecipeBuildService(project).plan(asset.id)


def test_keep_duration_uses_actual_input_timing_and_ignores_inactive_fps(project, tmp_path):
    asset, _ = asset_source(project, tmp_path, count=16)
    assets = AssetService(project)
    current = assets.asset(asset.id)
    definition = assets.definition(asset.id).to_data()
    definition["poses"][0]["fps"] = 12.0
    assets.configure(asset.id, definition, current.revision_no)

    def configure(recipe):
        recipe["steps"][-1]["parameters"].update(timing="keep_duration", frames=8, fps=8)
        append_step(recipe, "frames", parameters={"timing": "keep_duration", "frames": 4})

    record = recipe_for(project, asset, "frames", configure)
    _, artifacts = run(project, asset)
    assert artifacts[0]["metadata"]["duration"] == 16 / 12
    assert artifacts[0]["metadata"]["fps"] == 3.0
    recipe = deepcopy(record.data["recipe"])
    recipe["steps"][-1]["parameters"]["fps"] = 60
    PipelineService(project).save(record.id, recipe, record.revision_no)
    report, _ = run(project, asset)
    assert all(row["actual"] == "reused" for row in report["actual"])
