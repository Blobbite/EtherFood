"""Inventory worker, explicit review and cancel using real Qt event processing."""

from threading import Event
import time

import pytest

pytest.importorskip("PySide6.QtWidgets", reason="Qt/GUI-Systembibliotheken fehlen")

from PIL import Image
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog, QMessageBox, QPlainTextEdit, QPushButton

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
    assert "1 gespeicherte Beobachtungen" in dialog.registered.toPlainText()
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


def test_html_reference_is_read_only_text(qt_app, inventory_dialog, tmp_path):
    dialog, _, _, _ = inventory_dialog
    root = tmp_path / "comparison"
    root.mkdir()
    page = root / "vergleich.html"
    html = '<script>window.invalid = true</script><img src="missing.png">'
    page.write_text(html)
    dialog.root.setText(str(root))
    QTest.mouseClick(dialog.scan_button, Qt.MouseButton.LeftButton)
    wait_for(qt_app, lambda: dialog.worker is None)
    assert dialog.pages.count() == 1
    assert "broken" in dialog.reports.toPlainText()
    visited = []

    def inspect():
        modal = qt_app.activeModalWidget()
        try:
            assert isinstance(modal, QDialog)
            text = modal.findChild(QPlainTextEdit)
            assert text.isReadOnly() and text.toPlainText() == html
            visited.append(True)
        finally:
            if modal:
                modal.accept()

    QTimer.singleShot(20, inspect)
    QTest.mouseClick(dialog.findChild(QPushButton, "inventory_read_page"),
                     Qt.MouseButton.LeftButton)
    assert visited and page.read_text() == html
