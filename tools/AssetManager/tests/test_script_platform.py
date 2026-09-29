"""Imported code, asset-owned files, transactional moves and honest publication failures."""

from copy import deepcopy
import json
from pathlib import Path

from PIL import Image
import pytest

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.commands import Commands
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.plugin_service import PluginService, read_manifest
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.source_import import SourceImportService, SourceSpec
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.sources import expected_sources
from etherfood_studio.storage.blob_store import file_hash
from etherfood_studio.storage.file_changes import FileChanges

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/pipeline_scale/manifest.json"


@pytest.fixture
def studio(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    project = ProjectService.new(root, "Skriptplattform")
    yield project
    project.catalog.close()


def test_file_conflict_rolls_back_catalog_and_preserves_foreign_file(studio):
    act = studio.create_card("act", "Akt", studio.project().id)
    foreign = studio.catalog.path.parent / "Anderer Akt"
    foreign.mkdir()
    (foreign / "privat.txt").write_text("erhalten")
    with pytest.raises(StudioError, match="existiert"):
        studio.rename(act.id, "Anderer Akt", act.revision_no)
    assert studio.catalog.get(act.id) == act
    assert studio.files.path(act.id).name == "Akt"
    assert (foreign / "privat.txt").read_text() == "erhalten"


def test_file_rollback_after_failure_and_crash_recovery(studio, monkeypatch):
    act = studio.create_card("act", "Akt", studio.project().id)
    previous = studio.files.path(act.id)
    original = studio.files.json
    def fail(*args, **kwargs):
        raise OSError("synthetic failure after directory rename")
    monkeypatch.setattr(studio.files, "json", fail)
    with pytest.raises(OSError, match="synthetic"):
        studio.rename(act.id, "Neu", act.revision_no)
    assert previous.is_dir() and studio.catalog.get(act.id).title == "Akt"
    monkeypatch.setattr(studio.files, "json", original)
    change = FileChanges(studio.catalog)
    change.move(previous, previous.with_name("Unterbrochen"))
    loaded = ProjectService.open(studio.catalog.path.parent)
    try:
        assert previous.is_dir() and not previous.with_name("Unterbrochen").exists()
        assert loaded.files.path(act.id) == previous
    finally:
        loaded.catalog.close()


@pytest.mark.parametrize("field,value", [("source", "../escape.py"), ("source", "/tmp/code.py"),
                                        ("actions", [{"id": "bad"}])])
def test_package_paths_and_actions_validate(field, value):
    data = json.loads(EXAMPLE.read_text())
    data[field] = value
    with pytest.raises(StudioError):
        read_manifest(json.dumps(data).encode())


def test_package_import_never_executes_and_detects_preview_change(studio, tmp_path):
    descriptor = tmp_path / "manifest.json"
    descriptor.write_text(EXAMPLE.read_text())
    marker = tmp_path / "unexpected"
    code = tmp_path / "scale.py"
    code.write_text(f"from pathlib import Path\nPath({str(marker)!r}).touch()\n")
    service = PluginService(studio)
    preview = service.package(descriptor)
    code.write_text(code.read_text() + "# modified\n")
    with pytest.raises(StudioError, match="Vorschau geändert"):
        service.import_package(descriptor, preview["manifest"], preview["code_hash"], "Skalierung")
    import_scale(studio, descriptor, approve=False)
    assert not marker.exists()
    reopened = ProjectService.open(studio.catalog.path.parent)
    reopened.catalog.close()
    assert not marker.exists()


@pytest.mark.parametrize("factor", [0, -1, float("nan"), float("inf")])
def test_script_parameters_reject_invalid_scale_before_execution(studio, factor):
    recipe = import_scale(studio)
    data = deepcopy(recipe.data["recipe"])
    data["steps"][1]["parameters"]["factor"] = factor
    with pytest.raises(StudioError, match="Zahl"):
        PipelineService(studio).save(recipe.id, data, recipe.revision_no)
    assert not any(r.kind == "build" for r in studio.catalog.records())


def test_visible_script_copy_can_be_explicitly_reregistered(studio):
    recipe = import_scale(studio)
    directory = studio.files.path(recipe.id) / "Pakete/python-proportional-scale"
    source = directory / "scale.py"
    source.write_text(source.read_text() + "\n# Explicit new version\n")
    service = PluginService(studio)
    changed = service.register(directory / "manifest.json", source)
    assert changed["approved_hash"] is None and file_hash(source) == changed["code_hash"]
    with pytest.raises(StudioError, match="freigegeben"):
        service.trusted(changed["identifier"])


def test_committed_journal_cleanup_never_undoes_a_later_edit(studio, monkeypatch):
    original = FileChanges.finish
    def fail(self):
        raise OSError("cleanup interrupted")
    monkeypatch.setattr(FileChanges, "finish", fail)
    act = studio.create_card("act", "Akt", studio.project().id)
    changed = studio.rename(act.id, "Neuer Akt", act.revision_no)
    monkeypatch.setattr(FileChanges, "finish", original)
    reopened = ProjectService.open(studio.catalog.path.parent)
    try:
        assert reopened.catalog.get(act.id) == changed
        assert reopened.files.path(act.id).name == "Neuer Akt"
    finally:
        reopened.catalog.close()


def test_manifest_schema_matches_example():
    import jsonschema
    schema = EXAMPLE.parents[4] / "schemas/asset-studio/pipeline-manifest-v2.json"
    jsonschema.Draft202012Validator(json.loads(schema.read_text())).validate(
        json.loads(EXAMPLE.read_text()))


def test_migration_collision_keeps_foreign_folder_separate(studio):
    root = studio.catalog.path.parent
    foreign = root / "Fremdes Paket"
    foreign.mkdir()
    (foreign / "original.png").write_bytes(b"foreign original")
    parent = next(r for r in studio.cards() if r.kind == "global")
    # This foreign folder lives at the same prospective project level as the new act.
    act = studio.create_card("act", "Fremdes Paket", studio.project().id)
    assert studio.files.path(act.id).name == "Fremdes Paket--" + act.id[:8]
    assert (foreign / "original.png").read_bytes() == b"foreign original"
    studio.create_card("asset", "Anderes Asset", parent.id)
    assert studio.files.path(act.id).name == "Fremdes Paket--" + act.id[:8]

from legacy_fixtures import EXAMPLE, import_scale
