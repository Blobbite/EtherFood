"""Move legacy pipeline ownership atomically without losing recipes, history or bindings."""

from dataclasses import asdict
import json

import pytest

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.graphics import default_profiles
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.pipeline_recipes import template
from etherfood_studio.storage import migrations
from etherfood_studio.storage.sqlite_repository import Catalog


@pytest.fixture
def legacy(tmp_path):
    root = tmp_path / "legacy"
    root.mkdir()
    catalog = Catalog(root / "project.studio.sqlite", create=True, target_version=6)
    top = catalog.create("project", "Projekt", data={"graphics_profiles": default_profiles()})
    service = ProjectService(catalog)
    scope = service.create_card("global", "Projektweit", top.id)
    asset = AssetService(service).create("Bild", scope.id, default_definition("texture").to_data())
    recipe = catalog.create("pipeline", "Bestand", scope.id,
                            {"project_id": top.id, "recipe": template("graphics")})
    edge = catalog.add_relation(recipe.id, scope.id, "belongs_to")
    archived = catalog.create("pipeline", "Archiv", scope.id, recipe.data)
    catalog.add_relation(archived.id, scope.id, "belongs_to")
    archived = catalog.save(archived, archived=True)
    assignment = {"project_id": top.id, "recipe_id": recipe.id, "asset_id": None,
                  "type_id": "texture", "capabilities": [], "overrides": {}}
    rule = catalog.create("pipeline_assignment", "Typregel", scope.id, assignment)
    explicit = catalog.create("pipeline_assignment", "Asset", asset.id,
                               {**assignment, "asset_id": asset.id, "type_id": None})
    layout = {"x": 310, "y": -25, "pipeline_nodes": {
        recipe.data["recipe"]["steps"][0]["id"]: {"x": -15, "y": 40}}}
    catalog.save_layout(recipe.id, layout)
    build = catalog.create("build", "Unveränderlicher Snapshot", asset.id,
                            {"recipe": recipe.data, "recipe_revision": recipe.revision_no})
    snapshot = catalog.export_snapshot()
    histories = {r.id: catalog.history(r.id) for r in (recipe, archived, rule, explicit)}
    catalog.close()
    (root / "project.studio-local.json").write_text(json.dumps({"schema_version": 1,
        "roots": {"WORKSPACE_ROOT": str(root)}}), encoding="utf-8")
    return {"root": root, "project": top, "scope": scope, "asset": asset, "recipe": recipe,
            "archived": archived, "rule": rule, "explicit": explicit, "layout": layout,
            "build": build, "edge": edge, "snapshot": snapshot, "histories": histories}


def assert_migrated(project, legacy):
    from etherfood_studio.application.pipeline_workspace import PipelineWorkspace

    catalog = project.catalog
    workspace = PipelineWorkspace(project)
    for key in ("recipe", "archived"):
        before = legacy[key]
        current = catalog.get(before.id)
        assert current.owner_id == legacy["project"].id
        assert current.kind == "pipeline_definition" and current.archived == before.archived
        assert current.revision_no > before.revision_no
        assert workspace.files.path(current).is_file()
        assert catalog.history(before.id)[-1] == asdict(current)
    assert catalog.get(legacy["scope"].id) == legacy["scope"]
    asset = catalog.get(legacy["asset"].id)
    assert asset.id == legacy["asset"].id and asset.owner_id == legacy["asset"].owner_id
    assert asset.data["asset_definition"]["schema_version"] == 2
    assert not catalog.db.execute(
        "SELECT 1 FROM objects WHERE id=?", (legacy["build"].id,)
    ).fetchone()
    assert catalog.layout(legacy["recipe"].id) == legacy["layout"]
    explicit = catalog.get(legacy["explicit"].id)
    rule = catalog.get(legacy["rule"].id)
    assert explicit.kind == rule.kind == "pipeline_usage"
    assert explicit.data["targets"] == [asset.id]
    assert rule.data["targets"] == []
    assert explicit.data["definition_id"] == legacy["recipe"].id
    assert not catalog.db.execute("SELECT 1 FROM sqlite_master WHERE name='jobs'").fetchone()
    project.validate_structure()


def test_version_six_migration_preserves_history_bindings_and_is_idempotent(legacy):
    project = ProjectService.open(legacy["root"])
    assert_migrated(project, legacy)
    backup = project.catalog.last_backup
    assert backup.is_file()
    for identifier, history in legacy["histories"].items():
        assert project.catalog.history(identifier)[:len(history)] == history
    old = Catalog(backup, target_version=6, read_only=True)
    assert old.export_snapshot() == legacy["snapshot"]
    old.close()
    snapshot = project.catalog.export_snapshot()
    project.catalog.close()
    reopened = ProjectService.open(legacy["root"])
    assert reopened.catalog.last_backup is None
    assert reopened.catalog.export_snapshot() == snapshot
    reopened.catalog.close()


def test_ownership_migration_failure_rolls_back_every_change(legacy, monkeypatch):
    monkeypatch.setitem(migrations.MIGRATIONS, 7,
                        migrations.MIGRATIONS[7] + ("INVALID SQL",))
    with pytest.raises(StudioError):
        ProjectService.open(legacy["root"])
    old = Catalog(legacy["root"] / "project.studio.sqlite", target_version=6, read_only=True)
    assert old.export_snapshot() == legacy["snapshot"]
    for identifier, history in legacy["histories"].items():
        assert old.history(identifier) == history
    assert old.db.execute("SELECT version FROM schema_version").fetchone()[0] == 6
    old.close()


def test_legacy_metadata_snapshot_import_normalizes_ownership(legacy, tmp_path):
    catalog = Catalog(tmp_path / "copy.sqlite", create=True)
    project = ProjectService(catalog)
    # Metadata imports intentionally reset immutable build verification.
    value = json.loads(legacy["snapshot"])
    value["objects"] = [row for row in value["objects"] if row["id"] != legacy["build"].id]
    value["layouts"].pop(legacy["build"].id)
    project.import_snapshot(json.dumps(value))
    assert catalog.get(legacy["recipe"].id).owner_id == legacy["project"].id
    assert catalog.get(legacy["rule"].id).owner_id == legacy["project"].id
    assert catalog.get(legacy["explicit"].id) == legacy["explicit"]
    assert catalog.layout(legacy["recipe"].id) == legacy["layout"]
    assert PipelineService(project).resolve(legacy["asset"].id)["recipe"].id == legacy["recipe"].id
    catalog.close()


def test_new_recipes_and_type_rules_belong_to_project(tmp_path):
    project = ProjectService.new(tmp_path, "Neu")
    service = PipelineService(project)
    recipe = service.create("Rezept", "graphics")
    assert recipe.owner_id == project.project().id
    assert service.assign(recipe.id, type_id="npc").owner_id == project.project().id
    assert service.assign(recipe.id).owner_id == project.project().id
    with pytest.raises(StudioError):
        project.create_card("pipeline", "Falsche Ebene", service.global_id, recipe.data)
    project.validate_structure()
    project.catalog.close()
