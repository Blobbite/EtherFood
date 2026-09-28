"""Migration, declarative typed graphs, project profile keys and independent layouts."""

from copy import deepcopy
import json

import pytest

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.commands import Commands
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.profile_service import ProfileService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.domain.assets import GRAPHICS, AssetDefinition, VariantKey, default_definition
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.pipeline_recipes import (
    BUILTINS, blockers, step, template, validate_recipe,
)
from etherfood_studio.storage.sqlite_repository import Catalog


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    value = ProjectService.new(root, "Projekt")
    yield value
    value.catalog.close()


def test_old_project_profile_migration_is_idempotent_and_keeps_timing(tmp_path):
    root = tmp_path / "legacy"
    root.mkdir()
    catalog = Catalog(root / "project.studio.sqlite", create=True, target_version=5)
    project = ProjectService(catalog)
    top = catalog.create("project", "Bestand")
    global_card = project.create_card("global", "Bestehender globaler Rahmen", top.id)
    data = default_definition().to_data()
    data["poses"][0]["fps"] = 11.5
    asset = AssetService(project).create("Bestehender Held", global_card.id, data)
    catalog.close()
    (root / "project.studio-local.json").write_text(json.dumps({"schema_version": 1,
        "roots": {"WORKSPACE_ROOT": str(root)}}), encoding="utf-8")
    migrated = ProjectService.open(root)
    assert tuple(ProfileService(migrated).profiles()) == GRAPHICS
    assert AssetService(migrated).definition(asset.id).poses[0].fps == 11.5
    assert migrated.catalog.get(global_card.id).title == global_card.title
    assert migrated.catalog.last_backup.is_file()
    snapshot = migrated.catalog.export_snapshot()
    migrated.catalog.close()
    reopened = ProjectService.open(root)
    assert reopened.catalog.export_snapshot() == snapshot
    reopened.catalog.close()


def test_custom_keys_disabled_requirements_and_no_fallback(project):
    profiles = ProfileService(project)
    values = list(profiles.profiles().values())
    values[1]["enabled"] = False
    custom = {**values[0], "key": "comic_tiny", "name": "Eigene kleine Grafik", "value": 0.125}
    values.append(custom)
    profiles.save(values, project.project().revision_no)
    definition = default_definition("texture").to_data()
    definition["graphics"] = ["comic_high", "comic_mid", "comic_tiny"]
    parsed = AssetService(project).parse_definition(definition)
    assert {v.graphics for v in parsed.expected()} == {"comic_high", "comic_tiny"}
    observed = VariantKey(None, None, "comic_mid", None)
    assert parsed.matrix({observed})[observed] == "not_required"
    definition["graphics"] = ["unknown"]
    with pytest.raises(StudioError):
        AssetService(project).parse_definition(definition)
    with pytest.raises(StudioError, match="Profilidentitäten"):
        profiles.save(values[:-1], project.project().revision_no)


def test_recipe_types_cycles_no_implicit_project_dataflow(project):
    service = PipelineService(project)
    recipe = service.create("Technisch", "frames")
    other = service.create("Organisatorisch", "graphics")
    project.relate(recipe.id, other.id, "depends_on")
    assert service.recipe(recipe.id).data["recipe"]["connections"] == \
        recipe.data["recipe"]["connections"]
    data = deepcopy(recipe.data["recipe"])
    second = step("frames", BUILTINS["frames"])
    data["steps"].append(second)
    first = data["steps"][1]
    data["connections"] = [
        {"from": first["id"], "out": "image", "to": second["id"], "in": "image"},
        {"from": second["id"], "out": "image", "to": first["id"], "in": "image"}]
    with pytest.raises(StudioError, match="Zyklus"):
        validate_recipe(data)
    data = deepcopy(recipe.data["recipe"])
    data["connections"][0]["out"] = "palette"
    with pytest.raises(StudioError, match="Ein-/Ausgabetypen"):
        validate_recipe(data)
    data = template("empty")
    assert blockers(data, BUILTINS)
    data["steps"][0]["enabled"] = False
    assert any("durchreichen" in reason for reason in blockers(data, BUILTINS))


def test_pipeline_ownership_archive_undo_and_layout_revision(project):
    service = PipelineService(project)
    commands = Commands(project)
    identifier = commands.create_card("pipeline", "Vorlage", service.project_id,
        {"project_id": service.project_id, "recipe": template("graphics")})
    record = service.recipe(identifier)
    assert record.owner_id == project.project().id
    commands.layout(identifier, {"x": 250, "y": -140})
    assert service.recipe(identifier).revision_no == record.revision_no
    commands.undo()
    assert project.catalog.layout(identifier) == {}
    commands.undo()
    assert project.catalog.get(identifier).archived
    commands.redo()
    assert not service.recipe(identifier).archived
    act = project.create_card("act", "Akt", project.project().id)
    with pytest.raises(StudioError):
        project.move(identifier, act.id, service.recipe(identifier).revision_no)
    with pytest.raises(StudioError):
        project.move(identifier, service.global_id, service.recipe(identifier).revision_no)
    project.validate_structure()


def test_recipe_change_keeps_override_conflict_visible_not_unopenable(project):
    service = PipelineService(project)
    record = service.create("Frames", "frames")
    data = deepcopy(record.data["recipe"])
    token = data["steps"][1]["id"] + ".fps"
    data["overridable"] = [token]
    record = service.save(record.id, data, record.revision_no)
    asset = AssetService(project).create("Held", service.global_id, default_definition().to_data())
    service.assign(record.id, asset_id=asset.id, overrides={token: 9.0})
    data["overridable"] = []
    service.save(record.id, data, record.revision_no)
    project.validate_structure()
    with pytest.raises(StudioError, match="Abweichung"):
        service.resolve(asset.id)
