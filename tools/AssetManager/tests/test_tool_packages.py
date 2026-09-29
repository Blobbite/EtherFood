"""Real generic jobs, immutable code, complete package transfer and diagnostics."""

from copy import deepcopy
from importlib.metadata import distribution
import json
import sys
import zipfile

from PIL import Image
import pytest

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.source_import import SourceImportService, SourceSpec
from etherfood_studio.application.tool_environments import ToolEnvironments
from etherfood_studio.application.tool_packages import ToolPackageService
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.sources import expected_sources
from etherfood_studio.storage.blob_store import file_hash


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

from legacy_fixtures import studio, source_asset, example
