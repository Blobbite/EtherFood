"""Real Qt profile/assignment editing and image builds through the shared planner."""

from copy import deepcopy
import json
import time

from PIL import Image
import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QCoreApplication, QEvent, QTimer, Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.profile_service import ProfileService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.source_import import SourceImportService, SourceSpec
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.sources import expected_sources
from etherfood_studio.storage.blob_store import file_hash
from etherfood_studio.ui import profile_settings as ui

def wait_for(predicate, timeout=30):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(0.005)
    assert predicate()


@pytest.fixture
def project(qt_app, tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    value = ProjectService.new(root, "Pipeline-Dialoge")
    yield value
    for widget in QApplication.topLevelWidgets():
        if not isinstance(widget, ui.ProfileDialog):
            continue
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qt_app.processEvents()
    value.catalog.close()


def test_profiles_show_proportions_and_preserve_keys(project):
    dialog = ui.ProfileDialog(project)
    assert dialog.table.rowCount() == 5
    assert dialog.table.item(1, 8).text() == "256 × 128 px"
    assert dialog.table.item(3, 8).text() == "128 × 64 px"
    assert dialog.table.item(4, 8).text() == "115 × 58 px"
    assert not dialog.table.item(0, 0).flags() & Qt.ItemFlag.ItemIsEditable
    assert dialog.table.cellWidget(4, 7).currentData() == "pixel_high"
    assert not dialog.table.cellWidget(4, 6).isEnabled()
    dialog.table.cellWidget(0, 5).setValue(0.5)
    assert dialog.table.item(0, 8).text() == "256 × 128 px"
    select(dialog.table.cellWidget(0, 4), "max_edge")
    dialog.table.cellWidget(0, 5).setValue(128)
    assert dialog.table.item(0, 8).text() == "128 × 64 px"
    for row in (1, 2):
        dialog.table.cellWidget(row, 2).setChecked(False)
    dialog.add_profile()
    dialog.table.item(5, 0).setText("menu_preview")
    dialog.table.item(5, 1).setText("Menüvorschau")
    dialog.save()
    assert dialog.result() == ui.QDialog.DialogCode.Accepted
    profiles = ProfileService(project).profiles()
    assert set(profiles) == {"comic_high", "comic_mid", "comic_low", "pixel_high",
                             "pixel_low", "menu_preview"}
    assert sum(p["enabled"] for p in profiles.values()) == 4
    assert profiles["menu_preview"]["name"] == "Menüvorschau"
    loaded = ProjectService.open(project.catalog.path.parent, read_only=True)
    assert ProfileService(loaded).profiles() == profiles
    loaded.catalog.close()


def test_profiles_invalid_edit_stale_save_and_unsaved_guard(project, monkeypatch):
    errors = []
    monkeypatch.setattr(ui, "show_error", lambda _parent, error: errors.append(str(error)))
    dialog = ui.ProfileDialog(project)
    dialog.show()
    revision = project.project().revision_no
    dialog.table.item(0, 1).setText("")
    dialog.save()
    assert errors and project.project().revision_no == revision
    assert dialog.isVisible()
    dialog.table.item(0, 1).setText("Anderer Anzeigename")
    project.catalog.save(project.project(), title="Parallel geändert")
    dialog.save()
    assert len(errors) == 2
    assert ProfileService(project).profiles()["comic_high"]["name"] == "Comic High"
    confirm(monkeypatch, QMessageBox.StandardButton.No)
    dialog.reject()
    assert dialog.isVisible()
    confirm(monkeypatch)
    dialog.reject()
    assert not dialog.isVisible()


def test_profile_draft_undo_redo_does_not_write_or_remove_existing_keys(project):
    dialog = ui.ProfileDialog(project)
    original = ProfileService(project).profiles()
    revision = project.project().revision_no
    dialog.table.cellWidget(0, 5).setValue(0.25)
    assert dialog.undo_button.isEnabled()
    dialog.history(False)
    assert dialog.table.cellWidget(0, 5).value() == 1
    dialog.history(True)
    assert dialog.table.cellWidget(0, 5).value() == 0.25
    dialog.add_profile()
    assert dialog.table.rowCount() == 6
    dialog.history(False)
    assert dialog.table.rowCount() == 5
    dialog.history(True)
    assert dialog.table.rowCount() == 6
    assert not dialog.table.item(0, 0).flags() & Qt.ItemFlag.ItemIsEditable
    assert project.project().revision_no == revision
    assert ProfileService(project).profiles() == original


def test_profile_parent_later_in_table_is_preserved(project):
    service = ProfileService(project)
    profiles = list(service.profiles().values())
    custom = {**profiles[3], "key": "custom_pixel", "name": "Andere Pixelbasis", "value": 64}
    profiles.append(custom)
    profiles[4]["parent"] = custom["key"]
    service.save(profiles, project.project().revision_no)
    dialog = ui.ProfileDialog(project)
    assert dialog.values() == profiles
    assert dialog.table.item(4, 8).text() == "58 × 29 px"
    assert not dialog.commands.done


def test_profile_precision_and_invalid_sizes_are_not_silently_changed(project, monkeypatch):
    errors = []
    monkeypatch.setattr(ui, "show_error", lambda _parent, error: errors.append(str(error)))
    profiles = list(ProfileService(project).profiles().values())
    profiles[0]["value"] = 0.123456789
    profiles[1]["value"] = 1e-12
    ProfileService(project).save(profiles, project.project().revision_no)
    dialog = ui.ProfileDialog(project)
    assert dialog.values() == profiles
    assert not dialog.commands.done
    for value in (0, -1, float("inf"), float("nan"), "invalid"):
        dialog.table.cellWidget(0, 5).setValue(value)
        dialog.save()
        assert errors
        errors.clear()
    dialog.table.cellWidget(0, 5).setValue(0.5)
    select(dialog.table.cellWidget(0, 4), "max_edge")
    dialog.table.cellWidget(0, 5).setValue(128.5)
    dialog.save()
    assert errors and ProfileService(project).profiles()["comic_high"]["value"] == 0.123456789


def select(widget, value):
    index = widget.findData(value)
    assert index >= 0
    widget.setCurrentIndex(index)


def confirm(monkeypatch, answer=QMessageBox.Yes):
    monkeypatch.setattr(QMessageBox, "question", lambda *args: answer)
