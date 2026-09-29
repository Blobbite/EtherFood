"""Integrated pose delivery, mirrored folders and real checked GIF publications."""

from PIL import Image
import pytest

from etherfood_studio.application.asset_deliveries import AssetDeliveries
from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.build_planner import BuildPlanner
from etherfood_studio.application.mask_service import MaskService
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.recipe_builds import RecipeBuildService
from etherfood_studio.application.recipe_results import RecipeResultService
from etherfood_studio.application.source_import import SourceImportService, SourceSpec
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.sources import SourceKey
from etherfood_studio.storage.blob_store import file_hash
from test_pipeline_processing import append_step, asset_source, project, recipe_for, run


def test_pose_requirements_mirror_sources_sheets_and_masks_and_follow_rename(project, tmp_path):
    assets = AssetService(project)
    definition = default_definition("npc").to_data()
    definition["directions"] = ["S"]
    owner = next(r.id for r in project.cards() if r.kind == "global")
    asset = assets.create("Greenhero", owner, definition)
    pose = definition["poses"][0]["id"]
    directory = project.files.path(asset.id)
    for branch in ("source", "spritesheets", "masks/source", "masks/spritesheets"):
        assert (directory / branch / "walk").is_dir()
    assert all((directory / "previews" / kind).is_dir() for kind in ("gif", "video"))
    deliveries = AssetDeliveries(project)
    assert len(deliveries.poses(asset.id)[0]["rows"]) == 2
    originals = []
    imports = SourceImportService(assets)
    for kind, frames in (("single_image", 1), ("spritesheet", 8)):
        path = tmp_path / (kind + ".png")
        Image.new("RGBA", (frames * 4, 4), "green").save(path)
        originals.append((path, file_hash(path)))
        imports.import_plan(imports.prepare(asset.id, assets.asset(asset.id).revision_no,
            [SourceSpec(path, SourceKey(pose, "S", kind), frames, 1, frames)]))
    masks = MaskService(project)
    masks.save_definitions(asset.id, [{"id": 1, "name": "Körper", "levels": 2}],
                           assets.asset(asset.id).revision_no)
    for source in imports.active(asset.id).values():
        masks.create_template(asset.id, source.id, assets.asset(asset.id).revision_no)
    rows = deliveries.poses(asset.id)[0]["rows"]
    assert all(row["state"] == "imported" and row["mask"] == "review" for row in rows)
    assert all(len(list((directory / branch / "walk").glob("*.png"))) == 1
               for branch in ("source", "spritesheets", "masks/source", "masks/spritesheets"))
    definition["poses"][0]["export_name"] = "run"
    assets.configure(asset.id, definition, assets.asset(asset.id).revision_no)
    assert all(len(list((directory / branch / "run").glob("*.png"))) == 1
               for branch in ("source", "spritesheets", "masks/source", "masks/spritesheets"))
    assert all(file_hash(path) == digest for path, digest in originals)
    assert len(imports.revisions(asset.id)) == 2


def test_gif_pipeline_publishes_real_timed_preview_and_reuses_cache(project, tmp_path):
    asset, original = asset_source(project, tmp_path, count=8)
    assets = AssetService(project)
    definition = assets.definition(asset.id).to_data()
    definition["poses"][0].update(fps=7.5, loop=False)
    assets.configure(asset.id, definition, assets.asset(asset.id).revision_no)
    digest = file_hash(original)
    recipe = recipe_for(project, asset, "gif")
    _, artifacts = run(project, asset)
    preview = artifacts[0]["preview"]
    path = project.catalog.path.parent / preview["path"]
    assert path.parent == project.files.path(asset.id) / "previews/gif"
    assert artifacts[0]["metadata"]["grid"] == [8, 1]
    with Image.open(path) as gif:
        assert gif.format == "GIF" and gif.size == (8, 4)
        assert gif.n_frames == 8 and "loop" not in gif.info
        duration = 0
        for index in range(gif.n_frames):
            gif.seek(index)
            duration += gif.info["duration"]
        assert duration == 1070
    assert file_hash(original) == digest
    assert AssetDeliveries(project).poses(asset.id)[0]["gifs"] == 1
    assert "![" in (path.parent / "index.md").read_text()
    again, _ = run(project, asset)
    assert all(row["actual"] == "reused" for row in again["actual"])
    reopened = ProjectService.open(project.catalog.path.parent)
    try:
        assert RecipeResultService(reopened).latest(asset.id)["state"] == "ready"
        assert PipelineService(reopened).recipe(recipe.id).id == recipe.id
    finally:
        reopened.catalog.close()
    definition["poses"][0]["fps"] = 12
    assets.configure(asset.id, definition, assets.asset(asset.id).revision_no)
    assert AssetDeliveries(project).poses(asset.id)[0]["gifs"] == 0
    path.write_bytes(b"broken GIF")
    assert RecipeResultService(project).latest(asset.id)["state"] == "invalid"
    assert AssetDeliveries(project).poses(asset.id)[0]["gifs"] == 0


def test_gif_can_feed_another_script_and_publish_both_outputs(project, tmp_path):
    asset, _ = asset_source(project, tmp_path, count=8)
    recipe_for(project, asset, "gif", lambda r: append_step(r, "frames", parameters={"frames": 4}))
    _, artifacts = run(project, asset)
    assert len(artifacts) == 2
    assert sum("preview" in row for row in artifacts) == 1
    assert sorted(row["metadata"]["frames"] for row in artifacts) == [4, 8]


@pytest.mark.parametrize("directory", ["../escape", "/tmp/gifs", "previews/../source",
                                         "previews/gif/../../escape", "previews//gif"])
def test_gif_output_cannot_escape_asset_preview_area(project, tmp_path, directory):
    asset, _ = asset_source(project, tmp_path, count=8)
    recipe_for(project, asset, "gif", lambda r: r["steps"][1]["parameters"].update(
        directory=directory))
    with pytest.raises(StudioError, match="Ausgabeordner"):
        RecipeBuildService(project).plan(asset.id)
    assert not any(r.kind == "build" for r in project.catalog.records())


def test_one_asset_can_run_two_explicit_dashboard_pipelines(project, tmp_path):
    asset, _ = asset_source(project, tmp_path, count=8)
    gif = recipe_for(project, asset, "gif")
    frames = recipe_for(project, asset, "frames")
    service = RecipeBuildService(project)
    for recipe in (gif, frames):
        rows = service.dry_run(recipe.id)
        assert rows[0]["state"] == "affected"
        report = BuildPlanner(project).execute(rows[0]["plan"])
        assert report["status"] == "succeeded" and report["published"]
    assert AssetDeliveries(project).poses(asset.id)[0]["gifs"] == 1


def test_dashboard_selection_preserves_explicit_over_type_and_project_precedence(project, tmp_path):
    asset, _ = asset_source(project, tmp_path, count=8)
    service = PipelineService(project)
    default = service.create("Projektstandard", "gif")
    typed = service.create("Typregel", "frames")
    explicit = service.create("Explizit", "gif")
    service.assign(default.id)
    service.assign(typed.id, type_id="effect")
    service.assign(explicit.id, asset_id=asset.id)
    assert service.resolve(asset.id, default.id) is None
    assert service.resolve(asset.id, typed.id) is None
    assert service.resolve(asset.id, explicit.id)["recipe"].id == explicit.id
    service.assign(typed.id, asset_id=asset.id)
    assert service.resolve(asset.id, typed.id)["recipe"].id == typed.id
    assert service.resolve(asset.id, explicit.id)["recipe"].id == explicit.id


def test_old_managed_source_folder_is_moved_without_a_second_copy(project, tmp_path):
    asset, _ = asset_source(project, tmp_path, count=8)
    root = project.files.path(asset.id)
    files = list((root / "spritesheets/walk").glob("*.*"))
    (root / "Quellen").mkdir()
    for path in files:
        old = root / "Quellen" / path.name
        path.rename(old)
        project.catalog.db.execute("UPDATE managed_files SET path=? WHERE owner_id=? AND path=?",
                                  ("Quellen/" + path.name, asset.id, str(path.relative_to(root))))
    reopened = ProjectService.open(project.catalog.path.parent)
    try:
        assert len(list((root / "spritesheets/walk").glob("*.png"))) == 1
        assert not list((root / "Quellen").iterdir())
        assert len(SourceImportService(AssetService(reopened)).revisions(asset.id)) == 1
    finally:
        reopened.catalog.close()
