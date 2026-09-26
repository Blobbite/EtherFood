"""T014 safety and review with synthetic assets; originals must remain byte-identical."""

import hashlib
import json
import struct
from threading import Event
import zlib

from PIL import Image
import pytest

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.document_service import DocumentService
from etherfood_studio.application.inventory_scan import scan_inventory
from etherfood_studio.application.inventory_service import InventoryService, prepare_adoption
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.status_service import StatusService
from etherfood_studio.domain.assets import default_definition, new_pose
from etherfood_studio.domain.models import StudioError
from etherfood_studio.storage.inventory_files import ScanLimits
from etherfood_studio.storage.sqlite_repository import Catalog


def sheet(root, *, pose="walk", direction="SW", graphic="comic_high", frames=8, name=None):
    grid = "4x2" if frames == 8 else "4x4"
    path = root / pose / graphic / f"spritesheet-fram{frames}" / (
        name or f"test_hd_{pose}_spritesheet_{direction}_{grid}_o.png")
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (16, 8 if frames == 8 else 16), (20, 100, 40, 255)).save(path)
    return path


def hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file() and not p.is_symlink()}


@pytest.fixture
def configured(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    project = ProjectService.new(root, "Test")
    identifier = project.demo()["hero"]
    assets = AssetService(project)
    assets.configure(identifier, default_definition().to_data(), 1)
    yield project, assets, identifier
    project.catalog.close()


def test_partial_inventory_is_not_complete_and_direction_pose_exact(tmp_path):
    sheet(tmp_path)
    sheet(tmp_path, direction="SO")
    sheet(tmp_path, pose="slowwalk")
    before = hashes(tmp_path)
    result = scan_inventory(tmp_path, default_definition())
    assert hashes(tmp_path) == before
    assert len(result.candidates) == 3
    assert [c.state for c in result.candidates].count("proposal") == 2
    assert {c.variant.direction for c in result.candidates
            if c.state == "proposal"} == {"SO", "SW"}
    assert list(result.matrix().values()).count("missing") == 198
    unknown = next(c for c in result.candidates if "slowwalk" in c.path)
    assert unknown.state == "needs_review"
    data = result.definition.to_data()
    data["poses"].append(new_pose("slowwalk").to_data())
    from etherfood_studio.domain.assets import AssetDefinition
    result = scan_inventory(tmp_path, AssetDefinition.from_data(data))
    assert all(c.state == "proposal" for c in result.candidates)
    assert len(result.matrix()) == 400


def test_wrong_pose_in_walk_folder_never_assigned_as_walk(tmp_path):
    sheet(tmp_path, name="test_hd_slowwalk_spritesheet_SW_4x2_o.png")
    result = scan_inventory(tmp_path, default_definition())
    assert result.candidates[0].state == "needs_review"
    assert any("Posen" in note for note in result.candidates[0].notes)


def test_unknown_pixeleng_origin_and_grid_conflicts(tmp_path):
    path = tmp_path / "PixelEng" / "unbekannt.png"
    path.parent.mkdir()
    Image.new("RGBA", (16, 8)).save(path)
    sheet(tmp_path, frames=16, name="test_hd_walk_spritesheet_SW_4x2_o.png")
    result = scan_inventory(tmp_path, default_definition())
    assert all(c.state == "needs_review" for c in result.candidates)
    assert all(any("Herkunft unbekannt" in note for note in c.notes) for c in result.candidates)


def test_duplicate_requires_explicit_choice_and_repeat_is_idempotent(configured, tmp_path):
    project, assets, identifier = configured
    root = tmp_path / "Quellen Grün #1 100%"
    a = sheet(root)
    b = sheet(root, name="copy_hd_walk_spritesheet_SW_4x2_o.png")
    before = hashes(root)
    scan = scan_inventory(root, assets.definition(identifier))
    assert all(c.state == "duplicate" for c in scan.candidates)
    with pytest.raises(StudioError, match="Auswahlkonflikt"):
        prepare_adoption(scan, [c.path for c in scan.candidates])
    prepared = prepare_adoption(scan, [a.relative_to(root).as_posix()],
                                 provenance={"kind": "original"})
    service = InventoryService(assets)
    assert service.adopt(identifier, 2, prepared)["adopted"] == 1
    snapshot = project.catalog.export_snapshot()
    revision = assets.asset(identifier).revision_no
    assert service.adopt(identifier, revision, prepared)["already_present"] == 1
    assert project.catalog.export_snapshot() == snapshot
    assert len(assets.observations(identifier)) == 1
    assert str(root) not in snapshot
    row = assets.observations(identifier)[0]
    assert project.catalog.inventory_path(row["root_id"]) == root
    assert row["provenance"]["kind"] == "original"
    assert hashes(root) == before and b.exists()
    assert StatusService(project).status(identifier)["source"].state == "waiting_external"
    reopened = ProjectService.open(project.catalog.path.parent)
    try:
        assert len(AssetService(reopened).observations(identifier)) == 1
    finally:
        reopened.catalog.close()


def test_changed_source_and_stale_asset_and_cancel_never_partial(configured, tmp_path):
    project, assets, identifier = configured
    root = tmp_path / "source"
    a = sheet(root)
    scan = scan_inventory(root, assets.definition(identifier))
    before = project.catalog.export_snapshot()
    Image.new("RGBA", (16, 8), (255, 0, 0)).save(a)
    with pytest.raises(StudioError, match="geändert"):
        prepare_adoption(scan, [scan.candidates[0].path])
    assert project.catalog.export_snapshot() == before
    scan = scan_inventory(root, assets.definition(identifier))
    prepared = prepare_adoption(scan, [scan.candidates[0].path])
    service = InventoryService(assets)
    with pytest.raises(StudioError, match="Asset seit Scan"):
        service.adopt(identifier, 1, prepared)
    cancel = Event()
    cancel.set()
    with pytest.raises(StudioError, match="abgebrochen"):
        service.adopt(identifier, 2, prepared, cancel=cancel)
    assert project.catalog.export_snapshot() == before
    assert project.catalog.db.execute("SELECT count(*) FROM inventory_roots").fetchone()[0] == 0
    a.touch()
    with pytest.raises(StudioError, match="geändert"):
        service.adopt(identifier, 2, prepared)


def test_symlinks_limits_broken_png_and_cancel(tmp_path):
    a = sheet(tmp_path)
    (tmp_path / "loop").symlink_to(tmp_path, target_is_directory=True)
    (tmp_path / "alias.png").symlink_to(a)
    (tmp_path / "bad.png").write_bytes(b"not an image")
    result = scan_inventory(tmp_path, default_definition())
    assert len(result.candidates) == 1 and len(result.problems) == 3
    with pytest.raises(StudioError, match="kleineren"):
        scan_inventory(tmp_path, default_definition(), limits=ScanLimits(max_files=1))
    result = scan_inventory(tmp_path, default_definition(), limits=ScanLimits(max_pixels=2))
    assert len(result.candidates) == 0 and any("zu groß" in p for p in result.problems)
    result = scan_inventory(tmp_path, default_definition(), limits=ScanLimits(max_depth=0))
    assert any("Ordnertiefe" in p for p in result.problems)
    cancel = Event()
    cancel.set()
    with pytest.raises(StudioError, match="abgebrochen"):
        scan_inventory(tmp_path, default_definition(), cancel=cancel)


def test_old_report_hash_binding_and_safe_comparison_links(tmp_path):
    source = sheet(tmp_path)
    relative = source.relative_to(tmp_path).as_posix()
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    report = tmp_path / "pruefung.json"
    claim = {"passed": True, "files": [{"source": relative, "source_sha256": "0" * 64,
                                       "outputs": [{"png": relative, "png_sha256": digest}]}]}
    report.write_text(json.dumps(claim))
    page = tmp_path / "Vergleich #1 100%.html"
    page.write_text(f'<script>throw Error()</script><img src="{relative}">'
                    '<a href="../../outside">broken</a><img src="absent.png">'
                    '<img src="https://example.invalid/x.png">')
    before = hashes(tmp_path)
    result = scan_inventory(tmp_path, default_definition())
    assert result.reports[0]["state"] == "historical_unverified"
    assert result.reports[0]["sources"][0]["state"] == "mismatch"
    assert result.reports[0]["approval"] == "not_granted"
    assert [v["state"] for v in result.pages[0]["links"]] == [
        "found", "broken", "broken", "blocked_external",
    ]
    assert hashes(tmp_path) == before
    claim["files"][0]["source_sha256"] = digest
    report.write_text(json.dumps(claim))
    result = scan_inventory(tmp_path, default_definition())
    assert result.reports[0]["state"] == "historical_bound"
    assert result.reports[0]["approval"] == "not_granted"
    del claim["files"][0]["outputs"][0]["png_sha256"]
    report.write_text(json.dumps(claim))
    result = scan_inventory(tmp_path, default_definition())
    assert result.reports[0]["state"] == "historical_unverified"


def test_static_image_and_png_metadata(tmp_path):
    from PIL.PngImagePlugin import PngInfo
    meta = PngInfo()
    meta.add_text("etherfood_variant", json.dumps({"graphics": "pixel_low"}))
    Image.new("RGBA", (3, 5)).save(tmp_path / "Wand.png", pnginfo=meta)
    result = scan_inventory(tmp_path, default_definition("texture"))
    assert result.candidates[0].state == "proposal"
    assert result.candidates[0].variant.frames is None
    assert list(result.matrix().values()).count("missing") == 4


def test_schema_two_upgrade_keeps_data_and_excludes_local_roots(tmp_path):
    path = tmp_path / "old.sqlite"
    catalog = Catalog(path, create=True, target_version=2)
    record = catalog.create("project", "Preserve")
    catalog.close()
    catalog = Catalog(path)
    try:
        assert catalog.last_backup.is_file() and catalog.get(record.id).title == "Preserve"
        catalog.inventory_root(tmp_path)
        assert str(tmp_path) not in catalog.export_snapshot()
    finally:
        catalog.close()


def test_original_eight_survives_derived_inventory(configured, tmp_path):
    _, assets, identifier = configured
    root = tmp_path / "originals"
    sheet(root)
    scan = scan_inventory(root, assets.definition(identifier))
    service = InventoryService(assets)
    prepared = prepare_adoption(scan, [scan.candidates[0].path], provenance={"kind": "original"})
    service.adopt(identifier, 2, prepared)
    original = assets.observations(identifier)[0]
    derived_root = tmp_path / "derived"
    derived = sheet(derived_root)
    Image.new("RGBA", (16, 8), (100, 0, 0)).save(derived)
    scan = scan_inventory(derived_root, assets.definition(identifier))
    prepared = prepare_adoption(scan, [scan.candidates[0].path],
                                provenance={"kind": "derived", "source_sha256": "f" * 64})
    service.adopt(identifier, assets.asset(identifier).revision_no, prepared)
    assert assets.observations(identifier)[0] == original
    assert len(assets.observations(identifier)) == 2
    assert "conflict" in assets.matrix(identifier).values()


def test_transaction_rollback_when_report_fails_or_final_cancel(configured, tmp_path, monkeypatch):
    project, assets, identifier = configured
    root = tmp_path / "source"
    sheet(root)
    scan = scan_inventory(root, assets.definition(identifier))
    prepared = prepare_adoption(scan, [scan.candidates[0].path])
    before = project.catalog.export_snapshot()
    original_create = DocumentService.create

    def fail_report(*args, **kwargs):
        raise StudioError("storage", "Test: Bericht kann nicht gespeichert werden")

    monkeypatch.setattr(DocumentService, "create", fail_report)
    with pytest.raises(StudioError, match="Test: Bericht"):
        InventoryService(assets).adopt(identifier, 2, prepared)
    assert project.catalog.export_snapshot() == before
    assert project.catalog.db.execute("SELECT count(*) FROM inventory_roots").fetchone()[0] == 0
    cancel = Event()

    def cancel_after_report(*args, **kwargs):
        result = original_create(*args, **kwargs)
        cancel.set()
        return result

    monkeypatch.setattr(DocumentService, "create", cancel_after_report)
    with pytest.raises(StudioError, match="abgebrochen"):
        InventoryService(assets).adopt(identifier, 2, prepared, cancel=cancel)
    assert project.catalog.export_snapshot() == before
    assert project.catalog.db.execute("SELECT count(*) FROM inventory_roots").fetchone()[0] == 0


def test_crc_header_and_metadata_conflicts(tmp_path):
    from PIL.PngImagePlugin import PngInfo
    path = sheet(tmp_path)
    raw = bytearray(path.read_bytes())
    raw[24] = 3  # invalid bit depth for RGBA; checksum remains valid after recomputing
    raw[29:33] = struct.pack(">I", zlib.crc32(raw[12:29]) & 0xffffffff)
    path.write_bytes(raw)
    result = scan_inventory(tmp_path, default_definition())
    assert not result.candidates and any("Headerformat" in p for p in result.problems)
    raw[25] = 2  # deliberately corrupt IHDR CRC
    path.write_bytes(raw)
    result = scan_inventory(tmp_path, default_definition())
    assert any("Prüfsumme" in p for p in result.problems)
    meta = PngInfo()
    meta.add_text("etherfood_variant", json.dumps({"direction": "SO"}))
    Image.new("RGBA", (16, 8)).save(path, pnginfo=meta)
    result = scan_inventory(tmp_path, default_definition())
    assert result.candidates[0].state == "needs_review"
    assert any("Richtungen" in n for n in result.candidates[0].notes)


def test_bound_report_cannot_survive_changed_unselected_source(configured, tmp_path):
    _, assets, identifier = configured
    root = tmp_path / "source"
    selected = sheet(root)
    unselected = sheet(root, direction="SO")
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    report = {"files": [{"source": unselected.relative_to(root).as_posix(),
                         "source_sha256": digest(unselected), "outputs": [{
                             "png": selected.relative_to(root).as_posix(),
                             "sha256": digest(selected)}]}]}
    (root / "build-info.json").write_text(json.dumps(report))
    scan = scan_inventory(root, assets.definition(identifier))
    assert scan.reports[0]["state"] == "historical_bound"
    prepared = prepare_adoption(scan, [selected.relative_to(root).as_posix()])
    assert prepared.selected[0].path == selected.relative_to(root).as_posix()
    Image.new("RGBA", (16, 8), (255, 0, 0)).save(unselected)
    with pytest.raises(StudioError, match="veraltet"):
        prepare_adoption(scan, [selected.relative_to(root).as_posix()])


def test_report_reference_outside_root_and_report_limits(tmp_path):
    root = tmp_path / "root"
    path = sheet(root)
    report = {"files": [{"source": "../../secret", "source_sha256": "a" * 64,
                         "outputs": [{"png": path.relative_to(root).as_posix()}]}]}
    (root / "pruefung.json").write_text(json.dumps(report))
    result = scan_inventory(root, default_definition())
    assert result.reports[0]["sources"][0]["state"] == "unavailable"
    assert "außerhalb" in result.reports[0]["sources"][0]["reason"]
    result = scan_inventory(root, default_definition(), limits=ScanLimits(max_report_bytes=2))
    assert not result.reports and any("zu groß" in p for p in result.problems)
