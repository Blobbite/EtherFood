"""Actual task/issue dialogs and checklist interactions on one shared asset identity."""

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication, QDialogButtonBox, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton,
)

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.issue_service import IssueService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.models import new_id
from etherfood_studio.ui.asset_workspace import AssetWorkspace
from etherfood_studio.ui.main_window import MainWindow
from etherfood_studio.ui.tasks.checklist import ChecklistEditor
from etherfood_studio.ui.tasks.editor import TaskEditor


@pytest.fixture
def workspace(qt_app, tmp_path):
    window = MainWindow(QSettings(str(tmp_path / "preferences.ini"), QSettings.Format.IniFormat))
    root = tmp_path / "project"
    root.mkdir()
    assert window.new_project(root, "Aufgaben am Asset")
    assets = AssetService(window.project)
    owner = next(c.id for c in window.project.cards() if c.kind == "global")
    asset = assets.create("Held", owner, default_definition().to_data())
    other = assets.create("Anderes Asset", owner, default_definition().to_data())
    IssueService(window.project).create(other.id, "Nicht hier anzeigen")
    value = AssetWorkspace(assets, asset.id, window)
    value.show()
    value.tabs.setCurrentWidget(value.documentation)
    value.documentation.setCurrentWidget(value.tasks)
    qt_app.processEvents()
    yield window, value
    value.documents.dirty = False
    value.close()
    value.deleteLater()
    window.documents.dirty = False
    window.close()
    qt_app.processEvents()


def test_create_check_search_and_reopen_shared_asset_task(workspace, qt_app, monkeypatch):
    window, workspace = workspace
    panel = workspace.tasks
    assert panel.results.count() == 0 and not panel.scope.isVisible()
    errors = []
    monkeypatch.setattr("etherfood_studio.ui.tasks.panel.show_error",
                        lambda parent, error: errors.append(str(error)))

    def create_task():
        dialog = QApplication.activeModalWidget()
        assert dialog.objectName() == "task_create_dialog"
        body = dialog.findChild(QPlainTextEdit, "new_task_body")
        body.setPlainText("Beschreibung bleibt erhalten")
        checklist = dialog.findChild(ChecklistEditor)
        checklist.text.setText("SW vergleichen")
        QTest.mouseClick(checklist.findChild(QPushButton, "checklist_add"), Qt.LeftButton)
        checklist.text.setText("Raster kontrollieren")  # Pending input also saved explicitly.
        ok = dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.Ok)
        QTest.mouseClick(ok, Qt.LeftButton)
        assert dialog.isVisible() and errors  # Empty title: keep all input in the dialog.
        assert body.toPlainText() == "Beschreibung bleibt erhalten"
        assert checklist.items.count() == 2
        dialog.findChild(QLineEdit, "new_task_title").setText("Quellen prüfen")
        QTest.mouseClick(ok, Qt.LeftButton)

    QTimer.singleShot(0, create_task)
    QTest.mouseClick(panel.findChild(QPushButton, "new_task"), Qt.LeftButton)
    assert panel.results.count() == 1 and panel.selected_record.owner_id == workspace.identifier
    record = panel.selected_record
    assert record.data["finding"]["asset_id"] == workspace.identifier
    assert len(record.data["checklist"]) == 2
    assert "0/2" in panel.checklist.summary.text()
    note = workspace.documents.create_document("Lokale Notiz")
    workspace.documents.editor.setPlainText("Nicht durch Aufgaben-Refresh verlieren")
    panel.checklist.items.setCurrentRow(0)
    panel.checklist.items.setFocus()
    QTest.keyClick(panel.checklist.items, Qt.Key_Space)
    qt_app.processEvents()
    saved = window.project.catalog.get(record.id)
    assert saved.data["checklist"][0]["done"] is True
    assert "1/2" in panel.checklist.summary.text()
    assert workspace.documents.dirty
    assert workspace.documents.editor.toPlainText() == "Nicht durch Aufgaben-Refresh verlieren"
    panel.new_status.setCurrentIndex(panel.new_status.findData("done"))
    panel.change_status()
    assert "To-do" in errors[-1] and window.project.catalog.get(record.id).data["status"] == "open"
    panel.query.setText("Raster kontrollieren")
    assert panel.results.count() == 1
    panel.query.setText("Nicht hier anzeigen")
    assert panel.results.count() == 0
    panel.show_record(record.id)
    panel.checklist.items.setCurrentRow(1)
    QTest.keyClick(panel.checklist.items, Qt.Key_Space)
    panel.change_status()
    assert window.project.catalog.get(record.id).data["status"] == "done"
    workspace.documents.save()
    window.tasks.refresh()
    window.tasks.show_record(record.id)
    assert window.tasks.selected_record.id == record.id
    assert "2/2" in window.tasks.checklist.summary.text()
    loaded = ProjectService.open(window.project.catalog.path.parent)
    try:
        assert loaded.catalog.get(record.id).data["checklist"] == window.tasks.checklist.value()
        assert loaded.catalog.get(note.id).data["body"] == "Nicht durch Aufgaben-Refresh verlieren"
    finally:
        loaded.catalog.close()


def test_asset_issue_creation_and_cancel_make_no_second_task_store(workspace, qt_app):
    window, workspace = workspace
    panel = workspace.tasks
    before = window.project.catalog.export_snapshot()
    QTimer.singleShot(0, lambda: QApplication.activeModalWidget().reject())
    panel.new_item(True)
    assert window.project.catalog.export_snapshot() == before

    def create_issue():
        dialog = QApplication.activeModalWidget()
        dialog.findChild(QLineEdit, "new_task_title").setText("SW-Befund")
        dialog.findChild(QPlainTextEdit, "new_task_body").setPlainText("Konkreter Testbefund")
        QTest.mouseClick(dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.Ok),
                         Qt.LeftButton)

    QTimer.singleShot(0, create_issue)
    panel.new_item(True)
    issue = panel.selected_record
    assert issue.kind == "issue" and issue.owner_id == workspace.identifier
    panel.kind.setCurrentIndex(panel.kind.findData("task"))
    assert panel.results.count() == 0
    panel.kind.setCurrentIndex(panel.kind.findData("issue"))
    assert panel.results.count() == 1
    window.tasks.show_record(issue.id)
    assert window.tasks.selected_record.id == issue.id


def test_checklist_edit_conflict_cancel_and_preserved_pending_input(workspace, monkeypatch):
    window, workspace = workspace
    service = IssueService(window.project)
    record = service.create(workspace.identifier, "Konflikttest", checklist=[
        {"id": new_id(), "text": "Alt", "done": False}])
    editor = TaskEditor(service, record, workspace)
    editor.show()
    editor.checklist.text.setText("Neue Eingabe")
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Cancel)
    editor.reject()
    assert editor.isVisible() and editor.checklist.text.text() == "Neue Eingabe"
    service.update(record.id, record.title, "Anderer Stand", record.revision_no)
    errors = []
    monkeypatch.setattr("etherfood_studio.ui.tasks.editor.show_error",
                        lambda parent, error: errors.append(str(error)))
    assert not editor.save() and errors
    assert editor.isVisible() and len(editor.checklist.value()) == 2
    assert service.catalog.get(record.id).data["body"] == "Anderer Stand"
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Discard)
    editor.reject()
    editor.deleteLater()
