"""T013 requirements, stable identity and independent-source protection."""

import json
from pathlib import Path

import pytest

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.status_service import StatusService
from etherfood_studio.domain.assets import AssetDefinition, VariantKey, default_definition, new_pose
from etherfood_studio.domain.models import StudioError


@pytest.fixture
def asset_project(tmp_path):
    root = tmp_path / "Projekt"
    root.mkdir()
    project = ProjectService.new(root, "Test")
    identifier = project.demo()["hero"]
    yield project, AssetService(project), identifier
    project.catalog.close()


def test_matrix_and_override_and_separate_fps():
    data = default_definition().to_data()
    definition = AssetDefinition.from_data(data)
    assert len(definition.expected()) == 200
    data["poses"][0]["directions"] = ["O", "W"]
    data["poses"][0]["fps"] = 12
    npc = AssetDefinition.from_data(data)
    assert len(npc.expected()) == 50
    assert {key.frames for key in npc.expected()} == {8, 10, 12, 14, 16}
    unused = VariantKey(npc.poses[0].id, "SW", "comic_high", 8)
    assert npc.matrix({unused})[unused] == "not_required"
    data["poses"].append(new_pose("jump", single=True).to_data())
    assert len(AssetDefinition.from_data(data).expected()) == 90


def test_static_no_fake_pose_frame_or_direction():
    static = default_definition("texture")
    assert len(static.expected()) == 5
    assert all(k.pose_id is None and k.direction is None and k.frames is None
               for k in static.expected())


@pytest.mark.parametrize("change", [
    {"schema_version": 2}, {"schema_version": True}, {"frames": [True]}, {"directions": ["S", "S"]},
    {"extra": "no"}, {"poses": []}, {"frames": [0]}, {"graphics": ["unknown"]},
])
def test_invalid_definition(change):
    with pytest.raises(StudioError):
        AssetDefinition.from_data({**default_definition().to_data(), **change})


@pytest.mark.parametrize("change", [{"fps": float("nan")}, {"fps": 0}, {"loop": "yes"},
                                    {"anchor": [3, 1]}, {"id": "walk"}, {"export_name": "../bad"}])
def test_invalid_pose(change):
    data = default_definition().to_data()
    data["poses"][0].update(change)
    with pytest.raises(StudioError):
        AssetDefinition.from_data(data)


def test_stable_pose_and_shared_asset_and_independent_original(asset_project):
    project, service, identifier = asset_project
    record = service.configure(identifier, default_definition().to_data(), 1)
    definition = service.definition(identifier)
    key = next(k for k in definition.expected() if k.frames == 8)
    original = {"root_id": "local-root", "path": "eight.png", "sha256": "a" * 64,
                "variant": key.to_data(), "provenance": {"kind": "original"}}
    assert service.append_observations(record, [original]) == (1, 0)
    derived = {**original, "path": "reduced.png", "sha256": "b" * 64,
               "provenance": {"kind": "derived", "source_sha256": "c" * 64}}
    record = service.asset(identifier)
    assert service.append_observations(record, [derived, original]) == (1, 1)
    relations = project.catalog.relations()
    data = definition.to_data()
    data["poses"][0]["display_name"] = "Gehen"
    record = service.asset(identifier)
    service.configure(identifier, data, record.revision_no)
    assert service.definition(identifier).poses[0].id == definition.poses[0].id
    assert project.catalog.relations() == relations
    assert service.observations(identifier)[0] == original
    assert service.matrix(identifier)[key] == "conflict"
    with pytest.raises(StudioError, match="inzwischen"):
        service.configure(identifier, data, record.revision_no)


def test_texture_workflow_and_reopen(asset_project):
    project, service, identifier = asset_project
    service.configure(identifier, default_definition("texture").to_data(), 1)
    statuses = StatusService(project).status(identifier)
    assert all(statuses[s].state == "not_required" for s in ("mask", "color", "frames"))
    assert statuses["source"].state == "waiting_external"
    reopened = ProjectService.open(project.catalog.path.parent)
    try:
        assert len(AssetService(reopened).definition(identifier).expected()) == 5
    finally:
        reopened.catalog.close()


def test_versioned_json_schema():
    jsonschema = pytest.importorskip("jsonschema")
    path = Path(__file__).resolve().parents[3] / "schemas/asset-studio/asset-definition-v1.json"
    schema = json.loads(path.read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    for kind in ("character", "effect", "texture", "prop"):
        validator.validate(default_definition(kind).to_data())
