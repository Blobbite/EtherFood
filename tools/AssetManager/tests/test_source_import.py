"""Source deliveries never alter originals, old revisions or approvals."""

from dataclasses import asdict, replace

from PIL import Image
import pytest

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.source_import import SourceImportService, SourceSpec
from etherfood_studio.application.status_service import StatusService
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.sources import SourceKey
from etherfood_studio.domain.workflows import Evidence, input_fingerprint
from etherfood_studio.storage.blob_store import file_hash
from etherfood_studio.storage.sqlite_repository import Catalog


@pytest.fixture
def sources(tmp_path):
    root = tmp_path / "Projekt Grün #1 100%"
    root.mkdir()
    project = ProjectService.new(root, "Import")
    assets = AssetService(project)
    asset = project.create_card("asset", "Held", next(c.id for c in project.cards()
                                                      if c.kind == "global"))
    data = default_definition().to_data()
    data["directions"] = ["SW", "SO"]
    assets.configure(asset.id, data, asset.revision_no)
    yield SourceImportService(assets), asset.id
    project.catalog.close()


def spec_for(service, identifier, path, direction="SW", *, grid=(16, 1), single=False):
    pose = service.assets.definition(identifier).poses[0]
    return SourceSpec(path, SourceKey(pose.id, direction,
                      "single_image" if single else "spritesheet"),
                      grid[0], grid[1], grid[0] * grid[1], "Externes Werkzeug")


def sheet(path, size=(64, 4), color=(45, 170, 30, 255)):
    Image.new("RGBA", size, color).save(path)
    return path


def plan(service, identifier, specs):
    return service.prepare(identifier, service.assets.asset(identifier).revision_no, specs)


@pytest.mark.parametrize("grid,size", [((16, 1), (64, 4)), ((1, 16), (4, 64)),
                                      ((4, 4), (16, 16)), ((4, 2), (16, 8))])
def test_explicit_grids_immutable_bytes_and_snapshot(sources, tmp_path, grid, size):
    service, identifier = sources
    original = sheet(tmp_path / "Original Grün #1.png", size)
    before = file_hash(original)
    revision, = service.import_plan(plan(service, identifier, [
        spec_for(service, identifier, original, grid=grid)]))
    assert revision.data["grid"] == list(grid)
    assert revision.data["frames"] == grid[0] * grid[1]
    assert revision.data["external_tool"] == "Externes Werkzeug"
    assert file_hash(service.store.path_for(before)) == file_hash(original) == before
    with pytest.raises(StudioError, match="unveränderlich"):
        service.catalog.save(revision, title="Überschreiben")
    exported = service.catalog.export_snapshot()
    assert str(tmp_path) not in exported
    catalog = Catalog(tmp_path / "snapshot.sqlite", create=True)
    try:
        copied = ProjectService(catalog)
        copied.import_snapshot(exported)
        assert catalog.get(revision.id).data["verification"] == "not_run"
        assert SourceImportService(AssetService(copied)).fingerprint(identifier) is None
    finally:
        catalog.close()


def test_duplicates_conflict_and_independent_design_original(sources, tmp_path):
    service, identifier = sources
    first = spec_for(service, identifier, sheet(tmp_path / "first.png"))
    with pytest.raises(StudioError, match="Doppelte"):
        plan(service, identifier, [first, first])
    original, = service.import_plan(plan(service, identifier, [first]))
    with pytest.raises(StudioError, match="bereits aktiv"):
        service.import_plan(plan(service, identifier, [first]))
    design = spec_for(service, identifier, sheet(tmp_path / "design.png", (4, 4)),
                      grid=(1, 1), single=True)
    service.import_plan(plan(service, identifier, [design]))
    assert len(service.active(identifier)) == 2
    assert service.catalog.get(original.id) == original
    assert StatusService(service.project).status(identifier)["source"].state == "waiting_external"


@pytest.mark.parametrize("failure", ["truncated", "file_limit", "pixel_limit", "grid", "frames",
                                     "wrong_direction", "fake_png"])
def test_bad_sources_never_register(sources, tmp_path, failure):
    service, identifier = sources
    path = sheet(tmp_path / "source.png")
    spec = spec_for(service, identifier, path)
    if failure == "truncated":
        path.write_bytes(path.read_bytes()[:40])
    elif failure == "file_limit":
        service.project.config = replace(service.project.config, max_file_bytes=4)
    elif failure == "pixel_limit":
        service.project.config = replace(service.project.config, max_pixels=4)
    elif failure == "grid":
        spec = replace(spec, columns=3, rows=1, frames=3)
    elif failure == "frames":
        spec = replace(spec, frames=12)
    elif failure == "wrong_direction":
        spec = replace(spec, key=replace(spec.key, direction="N"))
    else:
        path.write_text("not a PNG")
    before = service.catalog.export_snapshot()
    with pytest.raises(StudioError):
        plan(service, identifier, [spec])
    assert service.catalog.export_snapshot() == before
    assert service.revisions(identifier) == []


@pytest.mark.parametrize("moment", ["before", "during", "cancel", "asset_changed"])
def test_changed_or_cancelled_batch_keeps_all_previous_bindings(sources, tmp_path, moment):
    service, identifier = sources
    first = spec_for(service, identifier, sheet(tmp_path / "first.png"))
    second = spec_for(service, identifier, sheet(tmp_path / "second.png"), "SO")
    previous = service.import_plan(plan(service, identifier, [first]))
    prepared = plan(service, identifier, [first, second])
    before = service.catalog.export_snapshot()
    if moment == "before":
        sheet(first.path, color=(250, 0, 0, 255))
    if moment == "asset_changed":
        service.catalog.save(service.assets.asset(identifier), title="Neu")
        before = service.catalog.export_snapshot()
    cancelled = []

    def progress(count):
        if count == 1 and moment == "during":
            sheet(first.path, color=(250, 0, 0, 255))
        if count == 1 and moment == "cancel":
            cancelled.append(True)

    with pytest.raises(StudioError):
        service.import_plan(prepared, replace_active=True, progress=progress,
                            cancelled=lambda: bool(cancelled))
    assert service.catalog.export_snapshot() == before
    assert service.revisions(identifier) == previous


def test_active_revision_switch_invalidates_evidence_without_rewriting_it(sources, tmp_path):
    service, identifier = sources
    first = spec_for(service, identifier, sheet(tmp_path / "first.png"))
    second = spec_for(service, identifier, sheet(tmp_path / "second.png"), "SO")
    original = service.import_plan(plan(service, identifier, [first, second]))
    inputs = {"source": service.fingerprint(identifier)}
    proof = Evidence("passed", input_fingerprint("frames", inputs), "synthetic-build")
    record = service.assets.asset(identifier)
    service.catalog.save(record, data={**record.data, "evidence": {"frames": asdict(proof)}})
    sheet(first.path, color=(250, 0, 0, 255))
    newer, = service.import_plan(plan(service, identifier, [first]), replace_active=True)
    assert service.fingerprint(identifier) != inputs["source"]
    assert StatusService(service.project).status(identifier)["frames"].state == "stale"
    assert service.assets.asset(identifier).data["evidence"]["frames"] == asdict(proof)
    assert all(service.catalog.get(r.id) == r for r in original)
    service.activate(identifier, original[0].id, service.assets.asset(identifier).revision_no)
    assert service.fingerprint(identifier) == inputs["source"]
    assert service.catalog.get(newer.id) == newer


def test_partial_matrix_reopen_and_static_source(sources, tmp_path):
    service, identifier = sources
    first = spec_for(service, identifier, sheet(tmp_path / "first.png"))
    service.import_plan(plan(service, identifier, [first]))
    rows = service.matrix(identifier)
    assert sum(r["required"] for r in rows) == 2
    assert sum(r["state"] == "missing" for r in rows) == 1
    assert sum(r["state"] == "not_required" for r in rows) == 6
    reopened = ProjectService.open(service.catalog.path.parent)
    try:
        assert "1/2" in StatusService(reopened).status(identifier)["source"].reason
        assert SourceImportService(AssetService(reopened)).matrix(identifier) == rows
    finally:
        reopened.catalog.close()
    asset = service.assets.asset(identifier)
    service.assets.configure(identifier, default_definition("texture").to_data(), asset.revision_no)
    static = SourceSpec(sheet(tmp_path / "static.png", (8, 8)),
                        SourceKey(None, None, "single_image"), 1, 1, 1)
    service.import_plan(plan(service, identifier, [static]))
    assert StatusService(service.project).status(identifier)["source"].state == "passed"
