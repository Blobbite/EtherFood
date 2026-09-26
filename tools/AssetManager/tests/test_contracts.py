"""Validate versioned contracts with synthetic, non-approved examples."""

from copy import deepcopy
import json
from pathlib import Path
from uuid import uuid4

import pytest

jsonschema = pytest.importorskip("jsonschema", reason="Schema-Testabhängigkeit fehlt")
ROOT = Path(__file__).resolve().parents[3]
SCHEMA = json.loads((ROOT / "schemas/asset-studio/contracts-v1.json").read_text())


def validate(value, definition=None):
    schema = SCHEMA if definition is None else {
        "$defs": SCHEMA["$defs"], "$ref": f"#/$defs/{definition}",
    }
    jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker(),
    ).validate(value)


def test_schema_is_valid():
    jsonschema.Draft202012Validator.check_schema(SCHEMA)


def test_static_variant_and_shared_identity():
    asset_id = str(uuid4())
    variant = {
        "asset_id": asset_id, "pose_id": None, "direction_id": None,
        "graphics_profile_id": "comic_high", "frame_profile_id": None,
        "source_revision_id": str(uuid4()),
    }
    validate(variant, "VariantKey")
    uses = [(str(uuid4()), asset_id), (str(uuid4()), asset_id)]
    assert len({target for _, target in uses}) == 1


def test_review_cannot_refer_to_latest():
    value = {
        "schema_version": 1, "kind": "Review", "id": str(uuid4()),
        "build_id": str(uuid4()), "scope": "synthetic schema test only",
        "decision": "rejected", "created_at": "2026-09-26T12:00:00Z",
    }
    validate(value)
    value["build_id"] = "latest"
    with pytest.raises(jsonschema.ValidationError):
        validate(value)


def test_build_request_excludes_view_data_and_future_versions():
    value = {
        "schema_version": 1, "kind": "BuildRequest", "id": str(uuid4()),
        "asset_id": str(uuid4()), "input_fingerprint": "a" * 64,
        "source_revision_ids": [str(uuid4())], "profile_revision_ids": [],
        "mask_revision_ids": [], "recipe_revision": "synthetic-1",
        "algorithm_version": "test-1", "output_root": "WORKSPACE_ROOT",
        "variants": [{
            "asset_id": str(uuid4()), "pose_id": None, "direction_id": None,
            "graphics_profile_id": "pixel_low", "frame_profile_id": None,
            "source_revision_id": str(uuid4()),
        }],
    }
    validate(value)
    for change in ({"layout": {"x": 4}}, {"schema_version": 2}):
        invalid = deepcopy(value)
        invalid.update(change)
        with pytest.raises(jsonschema.ValidationError):
            validate(invalid)


@pytest.mark.parametrize("path", ["../source.png", "/tmp/a", "a/../../b", "C:\\x"])
def test_artifact_rejects_escape(path):
    with pytest.raises(jsonschema.ValidationError):
        validate({"path": path, "sha256": "a" * 64, "length": 8}, "Artifact")


def test_path_map_preserves_display_names_and_actual_roots():
    path_map = json.loads((ROOT / (
        "docs/system/development/asset-studio/PATH_MAP.json"
    )).read_text())
    assert path_map["path_name_examples"] == ["Kapitel 1", "Grüne Höhle", "Test #1", "100%"]
    for path in path_map["roots"].values():
        if path is not None:
            assert (ROOT / path).is_dir()
