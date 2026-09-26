"""Real Qt interactions for the dashboard review corrections."""

import pytest

QtWidgets = pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialogButtonBox, QMessageBox

from etherfood_studio.application.document_service import DocumentService
from etherfood_studio.application.issue_service import Finding, IssueService
from etherfood_studio.ui.main_window import MainWindow
from etherfood_studio.ui.tasks.editor import TaskEditor


@pytest.fixture
def window(qt_app, tmp_path):
    settings = QSettings(str(tmp_path / "preferences.ini"), QSettings.Format.IniFormat)
    result = MainWindow(settings)
    root = tmp_path / "project"
    root.mkdir()
    assert result.new_project(root, "Review")
    result.show()
    qt_app.processEvents()
    yield result
    result.documents.dirty = False
    result.close()


def test_task_details_edit_conflict_cancel_and_save(window, qt_app, monkeypatch):
    service = IssueService(window.project)
    item = service.create(window.selected_id, "Issue", "Gespeicherte Beschreibung", issue=True,
                          finding=Finding(direction="SW", frame_index=0))
    window.tasks.show_record(item.id)
    window.tabs.setCurrentWidget(window.tasks)
    result = window.tasks.results.currentItem()
    QTest.mouseClick(window.tasks.results.viewport(), Qt.LeftButton,
                     pos=window.tasks.results.visualItemRect(result).center())
    assert "Gespeicherte Beschreibung" in window.tasks.details.toPlainText()
    assert "direction: SW" in window.tasks.details.toPlainText()
    editor = TaskEditor(service, item, window)
    editor.show()
    editor.body.setPlainText("Lokaler neuer Inhalt")
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Cancel)
    editor.reject()
    assert editor.isVisible() and editor.body.toPlainText() == "Lokaler neuer Inhalt"
    updated = service.update(item.id, item.title, "Anderer Bearbeiter", item.revision_no)
    errors = []
    monkeypatch.setattr("etherfood_studio.ui.tasks.editor.show_error",
                        lambda parent, error: errors.append(error))
    QTest.mouseClick(editor.buttons.button(QDialogButtonBox.Save), Qt.LeftButton)
    assert errors and editor.isVisible() and editor.body.toPlainText() == "Lokaler neuer Inhalt"
    assert service.catalog.get(item.id).data["body"] == "Anderer Bearbeiter"
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Discard)
    editor.reject()
    editor = TaskEditor(service, updated, window)
    editor.show()
    editor.body.setPlainText("Korrekt gespeichert")
    QTest.mouseClick(editor.buttons.button(QDialogButtonBox.Save), Qt.LeftButton)
    window.tasks.refresh()
    assert "Korrekt gespeichert" in window.tasks.details.toPlainText()
    assert window.tasks.results.currentItem().data(Qt.UserRole) == item.id


def test_search_document_open_preserves_unsaved_content(window, monkeypatch):
    service = DocumentService(window.project)
    first = window.documents.create_document("Erste Notiz")
    second = service.create(window.selected_id, "Zweite Notiz", "Zweiter Text")
    window.documents.editor.setPlainText("Ungespeichert")
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Cancel)
    window.open_document(second.id)
    assert window.documents.current.id == first.id
    assert window.documents.editor.toPlainText() == "Ungespeichert"
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Save)
    window.tasks.show_record(second.id)
    window.tasks.edit_current()
    assert service.catalog.get(first.id).data["body"] == "Ungespeichert"
    assert window.documents.current.id == second.id
    assert window.tabs.currentWidget() == window.documents
