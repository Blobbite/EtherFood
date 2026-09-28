"""Reference/mask contracts exercise real PNGs, revisions and the existing image runner."""

from copy import deepcopy
import json
from pathlib import Path

from PIL import Image
import pytest

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.build_planner import BuildPlanner
from etherfood_studio.application.mask_service import MaskService
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.recipe_builds import RecipeBuildService
from etherfood_studio.application.reference_service import ReferenceService
from etherfood_studio.application.source_import import SourceImportService, SourceSpec
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.materials import MASK_CONTRACT
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.sources import expected_sources
from etherfood_studio.pipelines.image_processing import legacy_modules
from etherfood_studio.storage.blob_store import file_hash


@pytest.fixture
def color_project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    project = ProjectService.new(root, "Farbprojekt")
    yield project
    project.catalog.close()


def npc(project, tmp_path, *, directions=("O", "W"), frames=2):
    assets = AssetService(project)
    data = default_definition("npc").to_data()
    data["directions"] = list(directions)
    owner = next(r.id for r in project.cards() if r.kind == "global")
    asset = assets.create("NPC", owner, data)
    specs = []
    for index, key in enumerate(expected_sources(assets.definition(asset.id))):
        path = tmp_path / f"npc-{asset.id}-{key.direction}.png"
        with Image.new("RGBA", (4 * frames, 4), (80 + index * 70, 60, 30, 255)) as image:
            image.putpixel((0, 0), (10, 20, 30, 0))
            image.save(path)
        specs.append(SourceSpec(path, key, frames, 1, frames))
    sources = SourceImportService(assets)
    revisions = sources.import_plan(sources.prepare(asset.id, asset.revision_no, specs))
    return asset.id, revisions, [s.path for s in specs]


def rev(project, asset):
    return project.catalog.get(asset).revision_no


def select(project, asset, sources):
    return ReferenceService(project).select(asset, [r.id for r in sources], sources[0].id, rev(
        project, asset))


def definitions(project, asset, extra=False):
    rows = [{"id": 1, "name": "Stoff", "levels": 2}]
    if extra:
        rows.append({"id": 2, "name": "Metall", "levels": 2})
    return MaskService(project).save_definitions(asset, rows, rev(project, asset))


def mask_file(tmp_path, source, *, mode="L", label=1, wrong_hash=False):
    exact = legacy_modules()[-1]
    path = tmp_path / f"mask-{source.id}-{mode}-{label}.png"
    with Image.new(mode, (source.data["width"], source.data["height"]), label) as mask:
        mask.putpixel((0, 0), 0)
        if mode == "P":
            mask.putpalette([90, 90, 90] * 256)
        mask.save(path, pnginfo=exact.mask_metadata(source.data["grid"],
            "0" * 64 if wrong_hash else source.data["sha256"]))
    return path


@pytest.mark.parametrize("mode", ["soft", "fixed", "material"])
def test_two_directions_create_real_v2_and_run(color_project, tmp_path, mode):
    project = color_project
    asset, sources, originals = npc(project, tmp_path)
    before = [file_hash(p) for p in originals]
    selected = select(project, asset, sources[:1])
    service, masks = ReferenceService(project), MaskService(project)
    if mode == "material":
        definitions(project, asset)
        for source in sources:
            mask = masks.import_mask(asset, source.id, mask_file(tmp_path, source), rev(project,
                asset))
            assert masks.status(mask.id)["visual"] == "pending"
            masks.confirm(mask.id, "Testbestätigung", rev(project, asset))
    profile = service.generate(asset, mode, rev(project, asset))
    value = service.read_profile(profile, mode)
    assert value["version"] == 2 and len(value["references"]) == 1
    assert value["references"][0]["direction"] == "O"
    assert value["references"][0]["source_revision"] == sources[0].id
    assert value["preview_reference"] == selected.data["selection"]["preview_reference"]
    pipelines = PipelineService(project)
    recipe = pipelines.create("Farbe", "color")
    service.configure_step(asset, recipe.id, recipe.data["recipe"]["steps"][1]["id"], mode,
        recipe.revision_no)
    pipelines.assign(recipe.id, asset_id=asset)
    planner = BuildPlanner(project)
    plan = RecipeBuildService(project).plan(asset)
    assert profile.id in json.loads(plan.snapshot)["color_bindings"]
    report = planner.execute(plan)
    assert report["status"] == "succeeded", report
    jobs = project.catalog.db.execute("SELECT count(*) FROM jobs").fetchone()[0]
    assert planner.execute(RecipeBuildService(project).plan(asset))["status"] == "succeeded"
    assert project.catalog.db.execute("SELECT count(*) FROM jobs").fetchone()[0] == jobs
    assert [file_hash(p) for p in originals] == before


def test_drafts_findings_p_indices_and_review_binding(color_project, tmp_path):
    project = color_project
    asset, sources, _ = npc(project, tmp_path)
    defs = definitions(project, asset, extra=True)
    service = MaskService(project)
    draft = service.create_template(asset, sources[0].id, rev(project, asset))
    status = service.status(draft.id)
    assert status["technical"] == "failed" and status["visual"] == "pending"
    assert {f["frame"] for f in status["findings"]} == {1, 2}
    assert all(f["bounds"] and f["direction"] == "O" for f in status["findings"])
    with pytest.raises(StudioError, match="technisch"):
        service.confirm(draft.id, "Tester", rev(project, asset))
    path = mask_file(tmp_path, sources[0], mode="P")
    with Image.open(path) as image:
        image.putpixel((1, 0), 2)
        image.save(path, pnginfo=legacy_modules()[-1].mask_metadata(sources[0].data["grid"],
            sources[0].data["sha256"]))
    current = service.import_mask(asset, sources[0].id, path, rev(project, asset),
        method="legacy_import")
    assert current.data["previous"] == draft.id and current.data["material_revision"] == defs.id
    assert service.status(current.id) == {"technical": "passed", "visual": "pending",
        "findings": []}
    with pytest.raises(StudioError, match="visuell"):
        service.for_source(asset, sources[0].id)
    service.confirm(current.id, "Tester", rev(project, asset))
    assert service.for_source(asset, sources[0].id).id == current.id
    newer = service.import_mask(asset, sources[0].id, path, rev(project, asset))
    assert service.status(newer.id)["visual"] == "pending"
    assert service.status(current.id)["visual"] == "confirmed"
    assert len(service.records(asset, MASK_CONTRACT)) == 3
    with pytest.raises(StudioError, match="unveränderlich"):
        project.catalog.save(current, title="ändern")


def test_source_change_stales_selection_mask_and_profile(color_project, tmp_path):
    project = color_project
    asset, sources, paths = npc(project, tmp_path)
    refs, masks = ReferenceService(project), MaskService(project)
    select(project, asset, sources[:1])
    profile = refs.generate(asset, "fixed", rev(project, asset))
    definitions(project, asset)
    mask = masks.import_mask(asset, sources[0].id, mask_file(tmp_path, sources[0]), rev(project,
        asset))
    masks.confirm(mask.id, "Tester", rev(project, asset))
    imports = SourceImportService(AssetService(project))
    spec = SourceSpec(paths[0], expected_sources(AssetService(project).definition(asset))[0], 2,
        1, 2)
    imports.import_plan(imports.prepare(asset, rev(project, asset), [spec]), replace_active=True)
    with pytest.raises(StudioError, match="veraltet"):
        refs.profile(asset, "fixed")
    assert masks.status(mask.id)["technical"] == "stale"
    assert project.catalog.get(profile.id) == profile


def test_even_fully_transparent_templates_remain_drafts(color_project, tmp_path):
    project = color_project
    asset, _, paths = npc(project, tmp_path)
    definitions(project, asset)
    with Image.new("RGBA", (8, 4)) as image:
        image.save(paths[0])
    imports = SourceImportService(AssetService(project))
    key = expected_sources(AssetService(project).definition(asset))[0]
    sources = imports.import_plan(
        imports.prepare(asset, rev(project, asset), [SourceSpec(paths[0], key, 2, 1, 2)]),
        replace_active=True)
    service = MaskService(project)
    draft = service.create_template(asset, sources[0].id, rev(project, asset))
    assert draft.data["technical"] == "failed"
    assert service.status(draft.id)["technical"] == "failed"
    with pytest.raises(StudioError, match="technisch"):
        service.confirm(draft.id, "Tester", rev(project, asset))


def test_missing_material_rejects_profile_and_wrong_hash_is_draft(color_project, tmp_path):
    project = color_project
    asset, sources, _ = npc(project, tmp_path)
    select(project, asset, sources[:1])
    definitions(project, asset, extra=True)
    service = MaskService(project)
    invalid = service.import_mask(asset, sources[0].id,
        mask_file(tmp_path, sources[0], wrong_hash=True), rev(project, asset))
    assert service.status(invalid.id)["technical"] == "failed"
    valid = service.import_mask(asset, sources[0].id, mask_file(tmp_path, sources[0]), rev(
        project, asset))
    service.confirm(valid.id, "Tester", rev(project, asset))
    with pytest.raises(StudioError, match="Metall"):
        ReferenceService(project).generate(asset, "material", rev(project, asset))


def test_selection_conflicts_boundaries_and_mixed_grid(color_project, tmp_path):
    project = color_project
    asset, sources, paths = npc(project, tmp_path)
    service = ReferenceService(project)
    with pytest.raises(StudioError, match="inzwischen"):
        service.select(asset, [sources[0].id], sources[0].id, 1)
    other, other_sources, _ = npc(project, tmp_path)
    with pytest.raises(StudioError, match="gehört"):
        select(project, asset, other_sources)
    imports = SourceImportService(AssetService(project))
    spec = SourceSpec(paths[1], expected_sources(AssetService(project).definition(asset))[1], 1,
        1, 1)
    newer = imports.import_plan(imports.prepare(asset, rev(project, asset), [spec]),
        replace_active=True)
    with pytest.raises(StudioError, match="Gemischte"):
        select(project, asset, sources[:1] + newer)


def test_v1_output_and_unknown_versions(tmp_path):
    soft, exact = legacy_modules()[-2:]
    refs = []
    for direction in soft.DIRECTIONS:
        path = tmp_path / f"stand_{direction}.png"
        Image.new("RGBA", (2, 2), (80, 100, 120, 255)).save(path)
        refs.append((path, direction, (1, 1)))
    value = soft.make_profile(refs)
    assert value["version"] == 1 and value["pixel_palette"] == [[80, 100, 120]]
    path = tmp_path / "v1.json"
    path.write_text(json.dumps(value))
    assert soft.load_profile(path) == value
    fixed = exact.make_palette(value)
    assert fixed["version"] == 1 and "preview_reference" not in fixed
    with Image.new("RGBA", (2, 2), (90, 110, 130, 255)) as image:
        with exact.FixedMatcher(fixed).apply(image) as output:
            assert output.getpixel((0, 0)) == (80, 100, 120, 255)
    with pytest.raises(ValueError, match="Referenz"):
        soft.make_profile(refs[:2])
    for version in (0, 3, True):
        value["version"] = version
        path.write_text(json.dumps(value))
        with pytest.raises(ValueError, match="unterstütztes"):
            soft.load_profile(path)


def test_static_reference_has_no_invented_pose_or_direction(color_project, tmp_path):
    project = color_project
    assets = AssetService(project)
    owner = next(r.id for r in project.cards() if r.kind == "global")
    asset = assets.create("Textur", owner, default_definition("texture").to_data())
    path = tmp_path / "texture.png"
    with Image.new("RGBA", (8, 4), (80, 100, 120, 255)) as image:
        image.save(path)
    source_service = SourceImportService(assets)
    key = expected_sources(assets.definition(asset.id))[0]
    spec = SourceSpec(path, key, 1, 1, 1)
    sources = source_service.import_plan(
        source_service.prepare(asset.id, asset.revision_no, [spec]))
    selected = select(project, asset.id, sources)
    reference = selected.data["selection"]["references"][0]
    assert reference["pose"] is None and reference["direction"] is None
    assert reference["grid"] == [1, 1] and reference["frames"] == 1
    service = ReferenceService(project)
    profile = service.generate(asset.id, "fixed", rev(project, asset.id))
    assert service.read_profile(profile, "fixed")["references"] == [reference]


@pytest.mark.parametrize("kind", ["profile", "mask"])
def test_exports_copy_bytes_without_overwriting_or_linking_sources(color_project, tmp_path, kind):
    project = color_project
    asset, sources, originals = npc(project, tmp_path)
    original_hashes = [file_hash(p) for p in originals]
    if kind == "profile":
        service = ReferenceService(project)
        select(project, asset, sources[:1])
        record = service.generate(asset, "fixed", rev(project, asset))
        suffix = ".json"
    else:
        service = MaskService(project)
        definitions(project, asset)
        record = service.import_mask(
            asset, sources[0].id, mask_file(tmp_path, sources[0], mode="P"), rev(project, asset))
        suffix = ".png"
    target = tmp_path / ("export" + suffix)
    stored = service.blob(record.data)
    service.export_file(record.data, target, suffix)
    assert target.read_bytes() == stored.read_bytes()
    assert not target.samefile(stored)
    assert [file_hash(p) for p in originals] == original_hashes
    with pytest.raises(StudioError, match="existiert bereits"):
        service.export_file(record.data, target, suffix)
    target.write_bytes(b"changed externally")
    assert file_hash(stored) == record.data["sha256"]
    assert not list(tmp_path.glob(".studio-export-*"))


def test_only_dependent_color_branch_rebuilds_and_frozen_plan_survives(color_project, tmp_path):
    from etherfood_studio.domain.pipeline_recipes import BUILTINS, step

    project = color_project
    asset, sources, _ = npc(project, tmp_path)
    refs = ReferenceService(project)
    select(project, asset, sources[:1])
    refs.generate(asset, "fixed", rev(project, asset))
    pipelines = PipelineService(project)
    recipe = pipelines.create("Unabhängige Zweige", "graphics")
    data = deepcopy(recipe.data["recipe"])
    data["profiles"] = ["comic_high"]
    color = step("color", BUILTINS["color"])
    color["parameters"].update(mode="fixed", palette="@asset")
    data["steps"].append(color)
    data["connections"].append({"from": data["steps"][0]["id"], "out": "image",
                                 "to": color["id"], "in": "image"})
    pipelines.save(recipe.id, data, recipe.revision_no)
    pipelines.assign(recipe.id, asset_id=asset)
    old_plan = RecipeBuildService(project).plan(asset)
    select(project, asset, sources[1:])
    refs.generate(asset, "fixed", rev(project, asset))
    # Already planned jobs continue with exactly their old resource copies/hashes.
    assert BuildPlanner(project).execute(old_plan)["status"] == "succeeded"
    new_plan = RecipeBuildService(project).plan(asset)
    colors = [r for r in new_plan.nodes if r.node.stage == "color"]
    graphics = [r for r in new_plan.nodes if r.node.stage == "scale"]
    assert all(r.state != "reused" for r in colors)
    assert all(r.state == "reused" for r in graphics)
    assert BuildPlanner(project).execute(new_plan)["status"] == "succeeded"


def test_material_revisions_stale_masks_but_keep_history(color_project, tmp_path):
    project = color_project
    asset, sources, _ = npc(project, tmp_path)
    original = definitions(project, asset)
    service = MaskService(project)
    mask = service.import_mask(asset, sources[0].id, mask_file(tmp_path, sources[0]), rev(
        project, asset))
    review = service.confirm(mask.id, "Tester", rev(project, asset))
    definitions(project, asset, extra=True)
    assert service.status(mask.id)["technical"] == "stale"
    assert project.catalog.get(mask.id) == mask and project.catalog.get(review.id) == review
    assert project.catalog.get(original.id) == original


def test_metadata_import_drops_mask_reviews_and_reopen_preserves_local_state(color_project,
    tmp_path):
    from etherfood_studio.application.project_service import CATALOG_NAME
    from etherfood_studio.storage.sqlite_repository import Catalog

    project = color_project
    asset, sources, _ = npc(project, tmp_path)
    select(project, asset, sources[:1])
    ReferenceService(project).generate(asset, "soft", rev(project, asset))
    definitions(project, asset)
    masks = MaskService(project)
    mask = masks.import_mask(asset, sources[0].id, mask_file(tmp_path, sources[0]), rev(project,
        asset))
    masks.confirm(mask.id, "Tester", rev(project, asset))
    reopened = ProjectService.open(project.catalog.path.parent)
    try:
        assert ReferenceService(reopened).profile(asset, "soft")
        assert MaskService(reopened).status(mask.id)["visual"] == "confirmed"
    finally:
        reopened.catalog.close()
    root = tmp_path / "copy"
    root.mkdir()
    catalog = Catalog(root / CATALOG_NAME, create=True)
    imported = ProjectService(catalog)
    try:
        imported.import_snapshot(project.catalog.export_snapshot())
        assert MaskService(imported).status(mask.id)["visual"] == "pending"
        assert not any(r.kind == "review" for r in catalog.records())
        with pytest.raises(StudioError):
            ReferenceService(imported).profile(asset, "soft")
    finally:
        catalog.close()


def test_greenhero_preset_keeps_all_stand_directions_and_frames(color_project, tmp_path):
    from etherfood_studio.domain.assets import DIRECTIONS

    project = color_project
    asset, sources, _ = npc(project, tmp_path, directions=DIRECTIONS, frames=16)
    assets = AssetService(project)
    data = assets.definition(asset).to_data()
    data["poses"][0].update(export_name="stand", display_name="Stand")
    assets.configure(asset, data, rev(project, asset))
    value = ReferenceService(project).greenhero_selection(asset, rev(project, asset)).data[
        "selection"]
    assert [r["direction"] for r in value["references"]] == list(DIRECTIONS)
    assert all(r["frames"] == 16 for r in value["references"])
    assert {r["source_revision"] for r in value["references"]} == {s.id for s in sources}
