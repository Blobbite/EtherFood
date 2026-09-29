"""Integrated pose delivery, mirrored folders and real checked GIF publications."""

from PIL import Image
import pytest

from etherfood_studio.application.asset_deliveries import AssetDeliveries
from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.mask_service import MaskService
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.source_import import SourceImportService, SourceSpec
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.sources import SourceKey
from etherfood_studio.storage.blob_store import file_hash
from legacy_fixtures import asset_source
from test_pipeline_workspace import project

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
