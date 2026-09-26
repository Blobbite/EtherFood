"""Inventory worker, explicit review and cancel using real Qt event processing."""

from pathlib import Path
from threading import Event
import time

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox, QPushButton
import pytest

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.storage.inventory_files import check_cancel
from etherfood_studio.ui.inventory import InventoryDialog


def wait_for(qt_app, predicate):
    until = time.monotonic() + 5
    while not predicate() and time.monotonic() < until:
        qt_app.processEvents()
        QTest.qWait(10)
    assert predicate(), "Qt worker did not finish"


@pytest.fixture
def inventory_dialog(qt_app, tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    project = ProjectService.new(root, "Test")
    identifier = project.demo()["hero"]
    assets = AssetService(project)
    assets.configure(identifier, default_definition().to_data(), 1)
    dialog = InventoryDialog(assets, identifier)
    dialog.show()
    yield dialog, project, assets, identifier
    dialog.reject()
    wait_for(qt_app, lambda: dialog.worker is None)
    dialog.deleteLater()
    project.catalog.close()


def test_scan_review_and_explicit_adoption(qt_app, inventory_dialog, tmp_path, monkeypatch):
    dialog, project, assets, identifier = inventory_dialog
    root = tmp_path / "Bestand Grün #1 100%"
    path = root / "walk/comic_high/spritesheet-fram8/test_walk_spritesheet_SW_4x2_o.png"
    path.parent.mkdir(parents=True)
    Image.new("RGBA", (16, 8), (12, 23, 34, 255)).save(path)
    before = path.read_bytes()
    dialog.root.setText(str(root))
    QTest.mouseClick(dialog.findChild(QPushButton, "inventory_scan"), Qt.MouseButton.LeftButton)
    wait_for(qt_app, lambda: dialog.worker is None)
    assert dialog.table.rowCount() == 1 and "199 fehlen" in dialog.status.text()
    assert dialog.table.item(0, 4).text() == "SW"
    assert "Fehlt" in dialog.matrix.toPlainText()
    assert not assets.observations(identifier)
    QTest.mouseClick(dialog.adopt_button, Qt.MouseButton.LeftButton)
    assert "ankreuzen" in dialog.status.text()
    dialog.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.StandardButton.Yes)
    QTest.mouseClick(dialog.adopt_button, Qt.MouseButton.LeftButton)
    wait_for(qt_app, lambda: dialog.worker is None)
    assert "Übernommen: 1" in dialog.status.text()
    assert dialog.changed and assets.observations(identifier)[0]["provenance"]["kind"] == "unknown"
    assert path.read_bytes() == before
    QTest.mouseClick(dialog.adopt_button, Qt.MouseButton.LeftButton)
    wait_for(qt_app, lambda: dialog.worker is None)
    assert "Schon vorhanden: 1" in dialog.status.text()
    assert len(assets.observations(identifier)) == 1
    assert any(r.kind == "document" and r.data["document_type"] == "generated"
               for r in project.catalog.records())


def test_cancel_button_and_close_wait_for_reader(qt_app, inventory_dialog, monkeypatch, tmp_path):
    dialog, project, assets, identifier = inventory_dialog
    started = Event()

    def slow_scan(*args, cancel, **kwargs):
        started.set()
        assert cancel.wait(3), "cancel was not forwarded to worker"
        check_cancel(cancel)

    monkeypatch.setattr("etherfood_studio.ui.inventory.scan_inventory", slow_scan)
    before = project.catalog.export_snapshot()
    dialog.root.setText(str(tmp_path))
    QTest.mouseClick(dialog.scan_button, Qt.MouseButton.LeftButton)
    wait_for(qt_app, started.is_set)
    QTest.mouseClick(dialog.findChild(QPushButton, "inventory_cancel"), Qt.MouseButton.LeftButton)
    wait_for(qt_app, lambda: dialog.worker is None)
    assert "abgebrochen" in dialog.status.text()
    started.clear()
    QTest.mouseClick(dialog.scan_button, Qt.MouseButton.LeftButton)
    wait_for(qt_app, started.is_set)
    dialog.close()
    wait_for(qt_app, lambda: dialog.worker is None)
    assert not dialog.isVisible()
    assert project.catalog.export_snapshot() == before
