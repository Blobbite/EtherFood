"""Failure-oriented catalog and import tests using disposable fixtures."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile

import pytest

from etherfood_studio.config import Configuration
from etherfood_studio.domain.models import StudioError
from etherfood_studio.storage import migrations
from etherfood_studio.storage.blob_store import BlobStore, file_hash
from etherfood_studio.storage.paths import safe_target, validate_roots
from etherfood_studio.storage.sqlite_repository import Catalog


@pytest.fixture
def catalog(tmp_path):
    value = Catalog(tmp_path / "Grün #1 100%.studio.sqlite", create=True)
    yield value
    value.close()


def test_cli_help_doctor_and_no_import_side_effects(tmp_path):
    script = Path(__file__).resolve().parents[1] / "studio.py"
    before = sorted(tmp_path.iterdir())
    result = subprocess.run([sys.executable, str(script), "--help"], cwd=tmp_path,
                            capture_output=True, text=True)
    assert result.returncode == 0
    result = subprocess.run([sys.executable, str(script), "doctor"], cwd=tmp_path,
                            capture_output=True, text=True)
    assert result.returncode == 1 and "Installation fehlt" in result.stdout
    assert sorted(tmp_path.iterdir()) == before
    result = subprocess.run([sys.executable, "-c", (
        f"import sys; sys.path.insert(0, {str(script.parent / 'src')!r}); "
        "import etherfood_studio; assert 'PySide6' not in sys.modules"
    )], cwd=tmp_path)
    assert result.returncode == 0


def test_transaction_foreign_keys_and_conflict(catalog):
    with pytest.raises(RuntimeError):
        with catalog.transaction():
            catalog.create("act", "Nicht behalten")
            raise RuntimeError("crash")
    assert catalog.records() == []
    record = catalog.create("project", "Projekt")
    newer = catalog.save(record, title="Neu")
    with pytest.raises(StudioError, match="Neuere"):
        catalog.save(record, title="Alt")
    assert catalog.get(record.id).title == "Neu"
    with pytest.raises(sqlite3.IntegrityError):
        catalog.add_relation(record.id, "missing", "uses")
    assert catalog.relations() == []
    archived = catalog.save(newer, archived=True)
    assert catalog.records() == []
    catalog.save(archived, archived=False)
    assert len(catalog.records()) == 1


def test_migration_backup_and_failed_migration(tmp_path, monkeypatch):
    path = tmp_path / "old.studio.sqlite"
    old = Catalog(path, create=True, target_version=1)
    record = old.create("document", "Text", data={"body": "Erhalten"})
    old.close()
    monkeypatch.setitem(migrations.MIGRATIONS, 2, ("INVALID SQL",))
    with pytest.raises(StudioError):
        Catalog(path)
    assert len(list(tmp_path.glob("*.studio-backup-*"))) == 1
    old = Catalog(path, target_version=1)
    assert old.get(record.id).data["body"] == "Erhalten"
    old.close()
    monkeypatch.undo()
    migrated = Catalog(path)
    assert migrated.get(record.id).id == record.id
    assert migrated.last_backup.is_file()
    migrated.close()


def test_snapshot_shared_ids_no_approvals(catalog, tmp_path):
    project = catalog.create("project", "Demo")
    hero = catalog.create("asset", "Hero", project.id)
    chapter = catalog.create("chapter", "Kapitel", project.id)
    catalog.add_relation(chapter.id, hero.id, "uses")
    catalog.create("approval", "Ungeprüfte Behauptung", hero.id)
    text = catalog.export_snapshot()
    assert text == catalog.export_snapshot()
    other = Catalog(tmp_path / "new.studio.sqlite", create=True)
    other.import_snapshot(text)
    assert other.get(hero.id).title == "Hero"
    assert other.relations() == catalog.relations()
    assert not any(row.kind == "approval" for row in other.records())
    with pytest.raises(StudioError):
        other.import_snapshot(text)
    other.close()


@pytest.mark.parametrize("name", ["../x", "/x", "NUL.png", "e\u0301.png", "a\\b", "a/../b"])
def test_unsafe_paths(tmp_path, name):
    with pytest.raises(StudioError):
        safe_target(tmp_path, name)


def test_symlink_overlap_and_case_collision(tmp_path):
    (tmp_path / "child").mkdir()
    (tmp_path / "link").symlink_to(tmp_path / "child", target_is_directory=True)
    with pytest.raises(StudioError):
        safe_target(tmp_path, "link/new")
    with pytest.raises(StudioError):
        validate_roots({"WORKSPACE_ROOT": tmp_path, "VERSIONS_ROOT": tmp_path / "child"})
    (tmp_path / "Art.png").touch()
    with pytest.raises(StudioError):
        safe_target(tmp_path, "art.png")


def test_blob_integrity_deduplication_and_crash(catalog, tiny_sheet, tmp_path):
    store = BlobStore(catalog, tmp_path)
    before = file_hash(tiny_sheet)

    def crash():
        raise RuntimeError("power loss")

    with pytest.raises(RuntimeError):
        store.import_file(tiny_sheet, after_copy=crash)
    assert catalog.db.execute("SELECT count(*) FROM blobs").fetchone()[0] == 0
    assert any("unvollständig" in item for item in store.integrity())
    assert store.journal.entries()[0]["state"] == "copied"
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: store.import_file(tiny_sheet), range(2)))
    assert results[0]["sha256"] == results[1]["sha256"] == before
    assert catalog.db.execute("SELECT count(*) FROM blobs").fetchone()[0] == 1
    assert file_hash(tiny_sheet) == before
    assert store.path_for(before).stat().st_ino != tiny_sheet.stat().st_ino


def test_disk_full_limits_cancel_and_cross_device(catalog, tiny_sheet, tmp_path, monkeypatch):
    store = BlobStore(catalog, tmp_path)
    before = file_hash(tiny_sheet)
    usage = shutil.disk_usage(tmp_path)
    monkeypatch.setattr(shutil, "disk_usage", lambda _: usage._replace(free=0))
    with pytest.raises(StudioError, match="Speicher"):
        store.import_file(tiny_sheet)
    assert file_hash(tiny_sheet) == before
    monkeypatch.undo()
    with pytest.raises(StudioError, match="abgebrochen"):
        store.import_file(tiny_sheet, cancelled=lambda: True)
    limited = BlobStore(catalog, tmp_path, Configuration(max_file_bytes=1))
    with pytest.raises(StudioError, match="Importgrenze"):
        limited.import_file(tiny_sheet)
    pixel_limited = BlobStore(catalog, tmp_path, Configuration(max_pixels=1))
    with pytest.raises(StudioError, match="Pixelgrenze"):
        pixel_limited.import_file(tiny_sheet)

    def exdev(*args, **kwargs):
        raise OSError(18, "Cross-device link")

    monkeypatch.setattr(Path, "rename", exdev)
    monkeypatch.setattr(Path, "replace", exdev)
    store.import_file(tiny_sheet)
    assert file_hash(tiny_sheet) == before
    assert store.integrity() == []


def test_bad_catalog_and_snapshot_do_not_replace_existing(tmp_path, catalog):
    bad = tmp_path / "bad.studio.sqlite"
    bad.write_text("not a database")
    with pytest.raises(StudioError):
        Catalog(bad)
    assert bad.read_text() == "not a database"
    with pytest.raises(StudioError):
        catalog.import_snapshot(json.dumps({"schema_version": 200}))
    assert catalog.records() == []


def test_actual_cross_device_import(catalog, tiny_sheet, tmp_path):
    shared = Path("/dev/shm")
    if not shared.is_dir() or shared.stat().st_dev == tmp_path.stat().st_dev:
        pytest.skip("Kein zweites Dateisystem verfügbar")
    with tempfile.TemporaryDirectory(prefix="studio-fixture-", dir=shared) as temporary:
        source = Path(temporary) / tiny_sheet.name
        shutil.copyfile(tiny_sheet, source)
        result = BlobStore(catalog, tmp_path).import_file(source)
        assert result["sha256"] == file_hash(source) == file_hash(tiny_sheet)


def test_mid_copy_enospc_and_immutable_revisions(catalog, tiny_sheet, tmp_path, monkeypatch):
    before = file_hash(tiny_sheet)
    store = BlobStore(catalog, tmp_path)

    def fail(incoming, output):
        output.write(b"partial")
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(shutil, "copyfileobj", fail)
    with pytest.raises(StudioError, match="unterbrochen"):
        store.import_file(tiny_sheet)
    assert file_hash(tiny_sheet) == before
    assert catalog.db.execute("SELECT count(*) FROM blobs").fetchone()[0] == 0
    assert store.journal.entries()[0]["state"] == "interrupted"
    assert store.integrity()
    record = catalog.create("source_revision", "Original")
    with pytest.raises(StudioError, match="unveränderlich"):
        catalog.save(record, title="Anders")


def test_unicode_root_collision_and_write_time_symlink(catalog, tiny_sheet, tmp_path):
    store = BlobStore(catalog, tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / ".asset-studio").symlink_to(outside, target_is_directory=True)
    with pytest.raises(StudioError, match="Symlink"):
        store.import_file(tiny_sheet)
    assert list(outside.iterdir()) == []
    first, second = tmp_path / "é", tmp_path / "e\u0301"
    first.mkdir()
    second.mkdir()
    with pytest.raises(StudioError):
        validate_roots({"WORKSPACE_ROOT": first, "VERSIONS_ROOT": second})


def test_invalid_layout_and_metadata_fail_explicitly(catalog):
    record = catalog.create("project", "Katalogprüfung")
    for value in ({"x": float("nan")}, {"w": -2}, {"manual": {"manual": {}}}):
        with pytest.raises(StudioError):
            catalog.save_layout(record.id, value)
    assert catalog.layout(record.id) == {}
    with catalog.transaction():
        catalog.db.execute("UPDATE objects SET data='[]' WHERE id=?", (record.id,))
    with pytest.raises(StudioError, match="Metadaten"):
        catalog.get(record.id)
