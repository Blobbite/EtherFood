"""Asset-specific rules and real profile folders share the runner's output convention."""

import pytest

from etherfood_studio.application.asset_pipelines import AssetPipelines
from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.profile_service import ProfileService
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.models import StudioError
from test_pipeline_processing import append_step, asset_source, project, recipe_for, run


def profiles_enabled(project, enabled):
    service = ProfileService(project)
    values = list(service.profiles().values())
    for value in values:
        value["enabled"] = value["key"] in enabled
    service.save(values, project.project().revision_no)


def configured_asset(project, title="Greenhero"):
    definition = default_definition("npc").to_data()
    definition["directions"] = ["S"]
    owner = next(row.id for row in project.cards() if row.kind == "global")
    return AssetService(project).create(title, owner, definition)


def test_profile_folders_exist_before_sources_without_publishing_internal_parent(project):
    profiles_enabled(project, {"comic_high", "comic_low", "pixel_low"})
    asset = configured_asset(project)
    service = PipelineService(project)
    recipe = service.create("Grafikvarianten", "graphics")
    data = recipe.data["recipe"]
    data["profiles"] = ["comic_high", "comic_mid", "pixel_low"]
    service.save(recipe.id, data, recipe.revision_no)
    service.assign(recipe.id, type_id="npc")
    root = project.files.path(asset.id) / "spritesheets/walk"
    assert (root / "comic_high").is_dir() and (root / "pixel_low").is_dir()
    assert not any((root / key).exists() for key in ("comic_mid", "comic_low", "pixel_high"))
    rows = AssetPipelines(project).rows(asset.id)
    outputs = {row["profile"]: row for row in rows[0]["outputs"]}
    assert outputs["pixel_high"]["state"] == "internal"
    assert outputs["pixel_high"]["paths"] == []
    assert outputs["comic_mid"]["state"] == "disabled"
    assert outputs["comic_low"]["state"] == "unselected"
    assert not any(row.kind in {"source_revision", "job", "build"}
                   for row in project.catalog.records())
    profiles_enabled(project, {"comic_high", "comic_mid", "pixel_low"})
    assert (root / "comic_mid").is_dir()
    historical = root / "comic_mid" / "Eigene Notiz.txt"
    historical.write_text("Erhalten", encoding="utf-8")
    profiles_enabled(project, {"pixel_low"})
    assert historical.read_text(encoding="utf-8") == "Erhalten"
    assert not (root / "pixel_high").exists()


def test_rules_show_overridden_and_conflicting_assignments_without_cross_asset_leaks(project):
    first, second = configured_asset(project), configured_asset(project, "Andere Figur")
    service = PipelineService(project)
    standard, typed, explicit = (service.create(name, "gif")
                                for name in ("Standard", "Spreadsheet-Animation", "Test"))
    service.assign(standard.id)
    service.assign(typed.id, type_id="npc")
    service.assign(explicit.id, asset_id=first.id)
    rows = {row["recipe"].id: row for row in AssetPipelines(project).rows(first.id)}
    assert rows[explicit.id]["state"] == "active"
    assert rows[typed.id]["state"] == rows[standard.id]["state"] == "superseded"
    other = {row["recipe"].id: row for row in AssetPipelines(project).rows(second.id)}
    assert explicit.id not in other and other[typed.id]["state"] == "active"
    service.assign(typed.id, asset_id=first.id)
    assert sum(row["state"] == "active" for row in AssetPipelines(project).rows(first.id)) == 2
    service.assign(explicit.id, asset_id=first.id)
    rows = {row["recipe"].id: row for row in AssetPipelines(project).rows(first.id)}
    assert rows[explicit.id]["state"] == "blocked"
    assert rows[typed.id]["state"] == "active"


def test_saved_custom_gif_folder_follows_activation_and_preserves_old_folders(project):
    asset = configured_asset(project)
    service = PipelineService(project)
    recipe = service.create("Vorschau", "gif")
    data = recipe.data["recipe"]
    data["enabled"] = False
    data["steps"][1]["parameters"]["directory"] = "previews/gif/animation"
    service.save(recipe.id, data, recipe.revision_no)
    service.assign(recipe.id, asset_id=asset.id)
    root = project.files.path(asset.id)
    assert not (root / "previews/gif/animation").exists()
    data["enabled"] = True
    service.save(recipe.id, data, service.recipe(recipe.id).revision_no)
    assert (root / "previews/gif/animation").is_dir()
    data["steps"][1]["parameters"]["directory"] = "previews/gif/neues-ziel"
    service.save(recipe.id, data, service.recipe(recipe.id).revision_no)
    assert (root / "previews/gif/neues-ziel").is_dir()
    assert (root / "previews/gif/animation").is_dir()


def test_folder_conflict_rolls_back_assignment_without_touching_foreign_file(project):
    asset = configured_asset(project)
    service = PipelineService(project)
    recipe = service.create("Grafikvarianten", "graphics")
    path = project.files.path(asset.id) / "spritesheets/walk/comic_high"
    path.write_bytes(b"foreign file")
    before = project.catalog.export_snapshot()
    with pytest.raises(StudioError, match="kein Ordner"):
        service.assign(recipe.id, asset_id=asset.id)
    assert project.catalog.export_snapshot() == before
    assert path.read_bytes() == b"foreign file"


def test_asset_requirements_and_disabled_graphics_step_control_static_folders(project):
    assets = AssetService(project)
    definition = default_definition("texture").to_data()
    definition["graphics"] = ["comic_high"]
    owner = next(row.id for row in project.cards() if row.kind == "global")
    asset = assets.create("Boden", owner, definition)
    service = PipelineService(project)
    recipe = service.create("Grafikvarianten", "graphics")
    data = recipe.data["recipe"]
    data["steps"][1]["enabled"] = False
    service.save(recipe.id, data, recipe.revision_no)
    service.assign(recipe.id, asset_id=asset.id)
    root = project.files.path(asset.id) / "Ergebnisse"
    assert not (root / "comic_high").exists()
    data["steps"][1]["enabled"] = True
    service.save(recipe.id, data, service.recipe(recipe.id).revision_no)
    assert (root / "comic_high").is_dir() and not (root / "comic_mid").exists()
    definition["graphics"].append("comic_mid")
    assets.configure(asset.id, definition, assets.asset(asset.id).revision_no)
    assert (root / "comic_mid").is_dir()


def test_real_graphics_and_gif_publish_into_the_folders_shown_by_asset_board(project, tmp_path):
    profiles_enabled(project, {"comic_high", "pixel_low"})
    asset, _ = asset_source(project, tmp_path, count=8)
    def edit(recipe):
        recipe["profiles"] = ["comic_high", "pixel_low"]
        append_step(recipe, "gif", parameters={"directory": "previews/gif/animation"})
    recipe_for(project, asset, "graphics", edit)
    root = project.files.path(asset.id)
    directories = AssetPipelines(project).directories(asset.id)
    assert set(directories) == {"spritesheets/walk/comic_high", "spritesheets/walk/pixel_low",
                                "previews/gif/animation"}
    assert all((root / path).is_dir() for path in directories)
    _, artifacts = run(project, asset)
    assert {row["metadata"]["profile"] for row in artifacts} == {"comic_high", "pixel_low"}
    for row in artifacts:
        image = project.catalog.path.parent / row["image_path"]
        assert image.parent == root / "spritesheets/walk" / row["metadata"]["profile"]
        assert (project.catalog.path.parent / row["preview"]["path"]).parent == \
            root / "previews/gif/animation"
    assert not (root / "spritesheets/walk/pixel_high").exists()
