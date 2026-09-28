"""Qt interaction with persisted references, mask previews and background profile generation."""

import time

import pytest

pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QPushButton

from etherfood_studio.application.mask_service import MaskService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.reference_service import ReferenceService
from etherfood_studio.ui.reference_materials import ReferenceMaterialsDialog
from test_color_references import mask_file, npc


def wait(qt_app, dialog):
    deadline = time.monotonic() + 15
    while dialog.worker is not None and time.monotonic() < deadline:
        qt_app.processEvents()
        time.sleep(0.01)
    qt_app.processEvents()
    assert dialog.worker is None


def click(dialog, name):
    widget = dialog.findChild(QPushButton, name)
    assert widget and widget.isEnabled()
    widget.click()


def test_select_generate_import_inspect_confirm_and_reopen(qt_app, tmp_path, monkeypatch):
    from etherfood_studio.ui import reference_materials as ui

    root = tmp_path / "project"
    root.mkdir()
    project = ProjectService.new(root, "Referenzdialog")
    asset, sources, _ = npc(project, tmp_path)
    errors = []
    monkeypatch.setattr(ui, "show_error", lambda parent, error: errors.append(str(error)))
    dialog = ReferenceMaterialsDialog(project, asset)
    dialog.show()
    try:
        click(dialog, "color_generate")
        wait(qt_app, dialog)
        assert "Masterreferenzen" in errors.pop()
        assert "fehlgeschlagen" in dialog.status.text()
        assert dialog.references.topLevelItemCount() == 2
        item = dialog.references.topLevelItem(0)
        source_id = item.data(0, Qt.ItemDataRole.UserRole)
        source = next(r for r in sources if r.id == source_id)
        item.setCheckState(0, Qt.CheckState.Checked)
        dialog.preview_reference.setCurrentIndex(dialog.preview_reference.findData(source_id))
        click(dialog, "color_save_references")
        wait(qt_app, dialog)
        assert not dialog.references_dirty
        assert len(ReferenceService(project).active(asset).data["selection"]["references"]) == 1
        dialog.mode.setCurrentIndex(dialog.mode.findData("fixed"))
        click(dialog, "color_generate")
        assert dialog.worker is not None  # Actual generation is off the GUI thread.
        wait(qt_app, dialog)
        profile = ReferenceService(project).profile(asset, "fixed")
        profile_export = tmp_path / "profile.json"
        monkeypatch.setattr(ui.QFileDialog, "getSaveFileName",
                            lambda *args: (str(profile_export), "JSON"))
        click(dialog, "color_export_profile")
        wait(qt_app, dialog)
        assert profile_export.read_bytes() == ReferenceService(project).blob(
            profile.data).read_bytes()
        click(dialog, "color_add_material")
        click(dialog, "color_save_materials")
        wait(qt_app, dialog)
        assert not dialog.materials_dirty
        dialog.mask_source.setCurrentIndex(dialog.mask_source.findData(source_id))
        click(dialog, "color_mask_template")
        wait(qt_app, dialog)
        click(dialog, "color_check_mask")
        wait(qt_app, dialog)
        assert "ohne Material" in dialog.findings.toPlainText()
        assert "Frame 2" in dialog.findings.toPlainText()
        assert not dialog.source_image.pixmap().isNull()
        mask = mask_file(tmp_path, source)
        monkeypatch.setattr(ui.QFileDialog, "getOpenFileName", lambda *args: (str(mask), "PNG"))
        click(dialog, "color_import_mask")
        wait(qt_app, dialog)
        identifier = dialog.mask_history.currentData()
        assert MaskService(project).status(identifier)["visual"] == "pending"
        mask_export = tmp_path / "mask-export.png"
        monkeypatch.setattr(ui.QFileDialog, "getSaveFileName",
                            lambda *args: (str(mask_export), "PNG"))
        click(dialog, "color_export_mask")
        wait(qt_app, dialog)
        assert mask_export.read_bytes() == mask.read_bytes()
        click(dialog, "color_confirm_mask")
        assert "visuell" in errors.pop()
        dialog.reviewed.setChecked(True)
        dialog.reviewer.setText("Explizite Testprüfung")
        click(dialog, "color_confirm_mask")
        wait(qt_app, dialog)
        click(dialog, "color_check_mask")
        wait(qt_app, dialog)
        assert "confirmed" in dialog.findings.toPlainText()
        assert source.data["sha256"] in dialog.findings.toPlainText()
        assert "1: Neues Material" in dialog.mask_legend.text()
        assert not dialog.mask_image.pixmap().isNull()
        assert not errors
        assert project.catalog.db.execute("SELECT count(*) FROM jobs").fetchone()[0] == 0
        dialog.reject()
        assert not dialog.isVisible()
        reopened = ReferenceMaterialsDialog(project, asset)
        assert reopened.references.topLevelItemCount() == 2
        assert reopened.mask_history.count() == 2
        assert reopened.reference_history.count() == 1
        reopened.deleteLater()
    finally:
        dialog.deleteLater()
        qt_app.processEvents()
        project.catalog.close()


def test_unsaved_selection_and_material_guard(qt_app, tmp_path, monkeypatch):
    root = tmp_path / "project"
    root.mkdir()
    project = ProjectService.new(root, "Entwurf")
    asset, _, _ = npc(project, tmp_path)
    dialog = ReferenceMaterialsDialog(project, asset)
    dialog.show()
    dialog.references.topLevelItem(0).setCheckState(0, Qt.CheckState.Checked)
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Cancel)
    dialog.reject()
    assert dialog.isVisible() and dialog.references_dirty
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Discard)
    dialog.reject()
    assert not dialog.isVisible()
    assert not project.catalog.get(asset).data.get("reference_selection_id")
    dialog.deleteLater()
    qt_app.processEvents()
    project.catalog.close()
