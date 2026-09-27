"""Actual file selection, worker completion, partial delivery and safe closing."""

from time import monotonic

from PIL import Image
import pytest

pytest.importorskip("PySide6.QtWidgets", reason="Qt/GUI-Systembibliotheken fehlen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QFileDialog, QMessageBox

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.source_import import SourceImportService
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.models import StudioError
from etherfood_studio.ui.source_import_dialog import SourceImportDialog


@pytest.fixture
def delivery(tmp_path, qt_app):
    root = tmp_path / "project"
    root.mkdir()
    project = ProjectService.new(root, "Quellen")
    assets = AssetService(project)
    asset = project.create_card("asset", "Testfigur", next(c.id for c in project.cards()
                                                           if c.kind == "global"))
    data = default_definition().to_data()
    data["directions"] = ["SW", "SO"]
    assets.configure(asset.id, data, asset.revision_no)
    dialog = SourceImportDialog(assets, asset.id)
    dialog.show()
    qt_app.processEvents()
    yield project, dialog
    dialog.close()
    wait_finished(dialog, qt_app)
    dialog.deleteLater()
    qt_app.processEvents()
    project.catalog.close()


def wait_finished(dialog, qt_app):
    deadline = monotonic() + 10
    while dialog.worker is not None and monotonic() < deadline:
        QTest.qWait(10)
        qt_app.processEvents()
    assert dialog.worker is None


def test_choose_horizontal_sheet_import_partial_and_reopen(delivery, tmp_path, qt_app, monkeypatch):
    project, dialog = delivery
    source = tmp_path / "hero_walk_SW_16x1.png"
    Image.new("RGBA", (64, 4), (30, 170, 60, 255)).save(source)
    monkeypatch.setattr(QFileDialog, "getOpenFileNames", lambda *args: ([str(source)], ""))
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    QTest.mouseClick(dialog.choose, Qt.MouseButton.LeftButton)
    assert dialog.table.cellWidget(0, 4).currentText() == "16x1"
    assert dialog.table.cellWidget(0, 2).currentData() == "SW"
    QTest.mouseClick(dialog.check_button, Qt.MouseButton.LeftButton)
    wait_finished(dialog, qt_app)
    assert dialog.plan and dialog.import_button.isEnabled()
    QTest.mouseClick(dialog.import_button, Qt.MouseButton.LeftButton)
    wait_finished(dialog, qt_app)
    assert dialog.changed and "1/2" in dialog.deliveries.summary.text()
    service = SourceImportService(AssetService(project))
    revision, = service.revisions(dialog.identifier)
    assert revision.data["grid"] == [16, 1]
    assert "nicht erzeugt" not in dialog.status.text()
    reopened = SourceImportDialog(AssetService(project), dialog.identifier)
    assert "1/2" in reopened.deliveries.summary.text()
    assert reopened.deliveries.revisions.count() == 1
    reopened.close()
    reopened.deleteLater()


def test_grid_change_invalidates_preview_and_conflict_requires_consent(
        delivery, tmp_path, qt_app, monkeypatch):
    project, dialog = delivery
    source = tmp_path / "hero_SW.png"
    Image.new("RGBA", (64, 16), (30, 170, 60, 255)).save(source)
    dialog.add_files([source])
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    errors = []
    monkeypatch.setattr("etherfood_studio.ui.source_import_dialog.show_error",
                        lambda parent, error: errors.append(error))
    dialog.prepare()
    wait_finished(dialog, qt_app)
    dialog.table.cellWidget(0, 4).setCurrentText("1x16")
    assert dialog.plan is None and not dialog.import_button.isEnabled()
    dialog.prepare()
    wait_finished(dialog, qt_app)
    dialog.import_plan()
    wait_finished(dialog, qt_app)
    service = SourceImportService(AssetService(project))
    original, = service.revisions(dialog.identifier)
    assert original.data["grid"] == [1, 16]
    dialog.prepare()
    wait_finished(dialog, qt_app)
    dialog.import_plan()
    wait_finished(dialog, qt_app)
    assert errors[-1].code == "conflict"
    assert len(service.revisions(dialog.identifier)) == 1
    dialog.replace_active.setChecked(True)
    dialog.prepare()
    wait_finished(dialog, qt_app)
    dialog.import_plan()
    wait_finished(dialog, qt_app)
    assert len(service.revisions(dialog.identifier)) == 2
    panel = dialog.deliveries
    panel.revisions.setCurrentIndex(panel.revisions.findData(original.id))
    QTest.mouseClick(panel.activate_button, Qt.MouseButton.LeftButton)
    assert next(iter(service.active(dialog.identifier).values())).id == original.id


def test_closing_running_import_waits_for_safe_cancel(delivery, tmp_path, qt_app, monkeypatch):
    project, dialog = delivery
    before = project.catalog.export_snapshot()
    source = tmp_path / "hero_SW.png"
    Image.new("RGBA", (64, 4)).save(source)
    dialog.add_files([source])

    def slow_prepare(self, *args, cancelled, **kwargs):
        deadline = monotonic() + 5
        while not cancelled() and monotonic() < deadline:
            QTest.qSleep(5)
        raise StudioError("cancelled", "Testabbruch")

    monkeypatch.setattr(SourceImportService, "prepare", slow_prepare)
    dialog.prepare()
    dialog.close()
    wait_finished(dialog, qt_app)
    assert not dialog.isVisible()
    assert not dialog.changed
    assert project.catalog.export_snapshot() == before
