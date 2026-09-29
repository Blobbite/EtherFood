"""Imported code, asset-owned files, transactional moves and honest publication failures."""

from copy import deepcopy
import json
from pathlib import Path

from PIL import Image
import pytest

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.build_planner import BuildPlanner
from etherfood_studio.application.commands import Commands
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.plugin_service import PluginService, read_manifest
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.recipe_builds import RecipeBuildService
from etherfood_studio.application.recipe_results import RecipeResultService
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


def import_scale(project, manifest=EXAMPLE, *, approve=True):
    service = PluginService(project)
    package = service.package(manifest)
    recipe = service.import_package(manifest, package["manifest"], package["code_hash"],
                                    "Skalierung")
    if approve:
        service.approve(package["manifest"]["id"], package["code_hash"])
    return recipe


def asset(project, tmp_path, owner, title="Wächter", *, animated=False):
    service = AssetService(project)
    definition = default_definition("effect" if animated else "texture").to_data()
    if animated:
        definition["poses"] = definition["poses"][:1]
        definition["poses"][0]["fps"] = 8.0
    record = service.create(title, owner, definition)
    source = tmp_path / (record.id + ".png")
    frames = 16 if animated else 1
    image = Image.new("RGBA", (512 * frames, 256), (20, 150, 30, 127))
    for i in range(frames):
        image.paste((i * 15, 150, 30, 127), (i * 512, 0, (i + 1) * 512, 256))
    image.save(source)
    imports = SourceImportService(service)
    key = expected_sources(service.definition(record.id))[0]
    imports.import_plan(imports.prepare(record.id, record.revision_no,
                                       [SourceSpec(source, key, frames, 1, frames)]))
    return record, source


def run(project, record):
    plan = RecipeBuildService(project).plan(record.id)
    result = BuildPlanner(project).execute(plan)
    assert result["status"] == "succeeded" and result["published"], result
    publication = RecipeResultService(project).latest(record.id)
    assert publication["state"] == "ready", publication
    return result, publication["artifacts"][0]


def test_import_scale_two_chapters_files_reload_and_cache(studio, tmp_path):
    act = studio.create_card("act", "Akt 1", studio.project().id)
    chapters = [studio.create_card("chapter", "Kapitel " + str(i), act.id) for i in (1, 2)]
    recipe = import_scale(studio)
    before_assets = []
    for chapter in chapters:
        package = studio.create_card("package", "Tempelpaket", chapter.id)
        record, original = asset(studio, tmp_path, package.id)
        before_assets.append(record.id)
        digest = file_hash(original)
        PipelineService(studio).assign(recipe.id, asset_id=record.id)
        report, artifact = run(studio, record)
        image_path = studio.catalog.path.parent / artifact["image_path"]
        assert image_path.is_relative_to(studio.files.path(record.id) / "Ergebnisse/scaled")
        assert str(image_path.relative_to(studio.catalog.path.parent)).startswith(
            f"Akt 1/{chapter.title}/Assets/Pakete/Tempelpaket/Textur/Wächter/Ergebnisse/scaled/")
        with Image.open(image_path) as image:
            assert image.size == (256, 128)
        assert artifact["metadata"]["logical_size"] == [512, 256]
        assert artifact["metadata"]["display_scale"] == [2.0, 2.0]
        assert "fps" not in artifact["metadata"]
        assert file_hash(original) == digest
        copies = list((studio.files.path(record.id) / "source").glob("*.png"))
        assert len(copies) == 1 and file_hash(copies[0]) == digest
        assert copies[0].stat().st_ino != original.stat().st_ino
        repeated, _ = run(studio, record)
        assert all(row["actual"] == "reused" for row in repeated["actual"])
        index = json.loads((studio.files.path(record.id) / "Ergebnisse/aktuell.json").read_text())
        assert index["asset_id"] == record.id and index["recipe_id"] == recipe.id
    assert sorted(r.id for r in studio.cards() if r.kind == "asset") == sorted(before_assets)
    assert not (studio.files.path(recipe.id) / "Ergebnisse").exists()
    assert (studio.files.path(recipe.id) / "Pakete/python-proportional-scale/scale.py").is_file()
    loaded = ProjectService.open(studio.catalog.path.parent)
    try:
        for identifier in before_assets:
            assert RecipeResultService(loaded).latest(identifier)["state"] == "ready"
    finally:
        loaded.catalog.close()
    other_root = tmp_path / "other"
    other_root.mkdir()
    other = ProjectService.new(other_root, "Anderes Projekt")
    try:
        assert PluginService(other).manifests() == {} and PipelineService(other).recipes() == []
    finally:
        other.catalog.close()


def test_script_frames_keep_grid_timing_and_original_indices(studio, tmp_path):
    parent = next(r for r in studio.cards() if r.kind == "global")
    record, original = asset(studio, tmp_path, parent.id, animated=True)
    digest = file_hash(original)
    recipe = import_scale(studio)
    PipelineService(studio).assign(recipe.id, asset_id=record.id)
    _, artifact = run(studio, record)
    meta = artifact["metadata"]
    assert meta["grid"] == [16, 1] and meta["frames"] == 16
    assert meta["source_indices"] == list(range(16))
    assert meta["fps"] == 8.0 and meta["duration"] == 2.0
    with Image.open(studio.catalog.path.parent / artifact["image_path"]) as image:
        assert image.size == (4096, 128)
        for i in range(16):
            assert abs(image.getpixel((i * 256 + 128, 64))[0] - i * 15) <= 2
    assert file_hash(original) == digest


def test_owner_moves_rename_undo_and_layout_do_not_build(studio, tmp_path):
    act = studio.create_card("act", "Akt", studio.project().id)
    chapters = [studio.create_card("chapter", name, act.id) for name in ("Eins", "Zwei")]
    record, _ = asset(studio, tmp_path, chapters[0].id)
    recipe = import_scale(studio)
    PipelineService(studio).assign(recipe.id, asset_id=record.id)
    _, artifact = run(studio, record)
    original_path = studio.catalog.path.parent / artifact["image_path"]
    digest = file_hash(original_path)
    commands = Commands(studio)
    commands.move(record.id, chapters[1].id)
    assert not original_path.exists()
    _, moved = run(studio, record)
    assert file_hash(studio.catalog.path.parent / moved["image_path"]) == digest
    commands.undo()
    assert original_path.exists()
    # Rename an ancestor, including every nested source/result folder.
    current = studio.catalog.get(act.id)
    studio.rename(act.id, "Akt Neu", current.revision_no)
    latest = RecipeResultService(studio).latest(record.id)
    assert latest["state"] == "ready"
    assert latest["artifacts"][0]["image_path"].startswith("Akt Neu/Eins/Assets/Textur/Wächter/")
    before = len([r for r in studio.catalog.records() if r.kind == "build"])
    commands.layout(record.id, {"x": 321, "y": -20})
    assert len([r for r in studio.catalog.records() if r.kind == "build"]) == before
    assert all(row.state == "reused" for row in RecipeBuildService(studio).plan(record.id).nodes)


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


def test_missing_trust_removed_package_and_failed_outputs_never_publish(studio, tmp_path):
    parent = next(r for r in studio.cards() if r.kind == "global")
    record, source = asset(studio, tmp_path, parent.id)
    recipe = import_scale(studio, approve=False)
    PipelineService(studio).assign(recipe.id, asset_id=record.id)
    with pytest.raises(StudioError, match="freigegeben"):
        RecipeBuildService(studio).plan(record.id)
    plugins = PluginService(studio)
    registered = plugins.details("python:proportional-scale")
    plugins.approve(registered["identifier"], registered["code_hash"])
    _, good = run(studio, record)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(EXAMPLE.read_text())
    code = tmp_path / "scale.py"
    code.write_text('def apply(image, metadata, parameters):\n'
                    '    return image, {"source_sha256": "0" * 64}\n')
    changed = plugins.register(manifest, code)
    plugins.approve(changed["identifier"], changed["code_hash"])
    before = file_hash(source)
    failed = BuildPlanner(studio).execute(RecipeBuildService(studio).plan(record.id))
    assert not failed["published"] and failed["status"] == "incomplete"
    latest = RecipeResultService(studio).latest(record.id)
    assert latest["state"] == "stale" and latest["artifacts"][0] == good
    assert file_hash(source) == before
    plugins.remove(changed["identifier"])
    assert plugins.actions(changed["identifier"]) == []
    with pytest.raises(StudioError, match="Werkzeug fehlt"):
        RecipeBuildService(studio).plan(record.id)


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


def test_script_maximum_edge_and_no_upscale(studio, tmp_path):
    parent = next(r for r in studio.cards() if r.kind == "global")
    record, _ = asset(studio, tmp_path, parent.id)
    recipe = import_scale(studio)
    data = deepcopy(recipe.data["recipe"])
    data["steps"][1]["parameters"].update(size_mode="max_edge", max_edge=128)
    recipe = PipelineService(studio).save(recipe.id, data, recipe.revision_no)
    PipelineService(studio).assign(recipe.id, asset_id=record.id)
    _, result = run(studio, record)
    assert result["metadata"]["frame_size"] == [128, 64]
    data["steps"][1]["parameters"]["max_edge"] = 1024
    PipelineService(studio).save(recipe.id, data, recipe.revision_no)
    _, result = run(studio, record)
    assert result["metadata"]["frame_size"] == [512, 256]


def test_modified_asset_output_is_not_overwritten_or_reported_success(studio, tmp_path):
    parent = next(r for r in studio.cards() if r.kind == "global")
    record, _ = asset(studio, tmp_path, parent.id)
    recipe = import_scale(studio)
    PipelineService(studio).assign(recipe.id, asset_id=record.id)
    _, result = run(studio, record)
    path = studio.catalog.path.parent / result["image_path"]
    path.write_bytes(b"foreign edit")
    failed = BuildPlanner(studio).execute(RecipeBuildService(studio).plan(record.id))
    assert not failed["published"] and failed["status"] == "incomplete"
    assert "extern verändert" in failed["publication_error"]
    assert path.read_bytes() == b"foreign edit"
    reopened = ProjectService.open(studio.catalog.path.parent)
    try:
        assert RecipeResultService(reopened).latest(record.id)["state"] == "invalid"
    finally:
        reopened.catalog.close()


def test_cancelled_run_keeps_complete_asset_publication(studio, tmp_path):
    parent = next(r for r in studio.cards() if r.kind == "global")
    record, _ = asset(studio, tmp_path, parent.id)
    recipe = import_scale(studio)
    PipelineService(studio).assign(recipe.id, asset_id=record.id)
    _, good = run(studio, record)
    cancelled = BuildPlanner(studio).execute(RecipeBuildService(studio).plan(record.id),
                                            cancelled=lambda: True)
    assert not cancelled["published"]
    assert RecipeResultService(studio).latest(record.id)["artifacts"][0] == good


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


def test_second_imported_script_changes_frames_without_runner_or_ui_special_case(studio, tmp_path):
    from etherfood_studio.domain.pipeline_recipes import BUILTINS, step

    parent = next(r for r in studio.cards() if r.kind == "global")
    record, _ = asset(studio, tmp_path, parent.id, animated=True)
    declaration = json.loads(EXAMPLE.read_text())
    declaration.update(id="python:select-frames", actions=[], parameters={},
                       capabilities=["animated"])
    descriptor = tmp_path / "manifest.json"
    descriptor.write_text(json.dumps(declaration))
    (tmp_path / "scale.py").write_text(
        'from etherfood_studio.pipelines.image_processing import split_frames, legacy_modules\n'
        'def apply(image, metadata, parameters):\n'
        '    frames = split_frames(image, metadata["grid"])[::2]\n'
        '    grid = legacy_modules()[0]\n'
        '    return grid.pack_frames(frames, (4, 2), optimize=False), {\n'
        '        "grid": [4, 2], "source_indices": metadata["source_indices"][::2],\n'
        '        "fps": 4.0, "timing_mode": "keep_duration"}\n')
    recipe = import_scale(studio, descriptor)
    data = deepcopy(recipe.data["recipe"])
    downstream = step("frames", BUILTINS["frames"])
    downstream["parameters"].update(frames=8, timing="keep_duration")
    data["steps"].append(downstream)
    data["connections"].append({"from": data["steps"][1]["id"], "out": "image",
                                "to": downstream["id"], "in": "image"})
    PipelineService(studio).save(recipe.id, data, recipe.revision_no)
    PipelineService(studio).assign(recipe.id, asset_id=record.id)
    _, output = run(studio, record)
    assert output["metadata"]["source_indices"] == list(range(0, 16, 2))
    assert output["metadata"]["frames"] == 8 and output["metadata"]["duration"] == 2.0


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
