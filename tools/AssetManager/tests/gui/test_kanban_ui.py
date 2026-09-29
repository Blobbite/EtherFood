"""Real Qt navigation, Kanban drop events and revision/approval safeguards."""

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QMimeData, QPoint, QPointF, QSettings, Qt, QTimer
from PySide6.QtGui import QDrag, QDragEnterEvent, QDropEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication, QDialogButtonBox, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton,
)

from etherfood_studio.application.document_service import DocumentService
from etherfood_studio.application.issue_service import IssueService
from etherfood_studio.domain.models import new_id
from etherfood_studio.ui.main_window import MainWindow
from etherfood_studio.ui.tasks.column import MIME_TYPE
from etherfood_studio.ui.tasks.editor import TaskEditor


@pytest.fixture
def window(qt_app, tmp_path):
    value = MainWindow(QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat))
    root = tmp_path / "project"
    root.mkdir()
    assert value.new_project(root, "Kanban-Prüfung")
    value.show()
    value.tabs.setCurrentWidget(value.tasks)
    qt_app.processEvents()
    yield value
    value.documents.dirty = False
    value.close()
    qt_app.processEvents()


def seed(window):
    project = window.project
    ids = project.demo()
    ids["root"] = project.project().id
    service = IssueService(project)
    rows = {key: service.create(ids[key], "Prüfung " + key, "Beschreibung " + key,
                                issue=key == "hero")
            for key in ("root", "act", "one", "two", "hero")}
    window.refresh()
    return ids, rows


@pytest.mark.parametrize("issue", [False, True])
def test_empty_todo_button_opens_editor_focused_on_new_item(window, qt_app, issue):
    service = IssueService(window.project)
    record = service.create(window.project.project().id, "Leere Aufgabe", "Text", issue=issue)
    board = window.tasks
    board.refresh()
    board.show_record(record.id)
    entry = board.checklist.empty_button
    assert entry.isVisible() and not board.checklist.items.isVisible()
    observed = []

    def fill():
        popup = QApplication.activeModalWidget()
        assert isinstance(popup, TaskEditor)
        # A scheduled test click can run before native activation when widgets are created.
        QTest.qWait(10)
        observed.append(popup.checklist.text.hasFocus())
        QTest.keyClicks(popup.checklist.text, "Erster Testpunkt")
        assert popup.save()

    QTimer.singleShot(20, fill)
    QTest.mouseClick(entry, Qt.LeftButton)
    qt_app.processEvents()
    saved = window.project.catalog.get(record.id)
    assert observed == [True]
    assert saved.data["checklist"][0]["text"] == "Erster Testpunkt"
    assert saved.revision_no == record.revision_no + 1
    assert not board.checklist.empty_button.isVisible() and board.checklist.items.isVisible()


def send_drop(board, target, mime, qt_app):
    column = board.columns[target]
    enter = QDragEnterEvent(QPoint(20, 20), Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)
    QApplication.sendEvent(column.viewport(), enter)
    event = QDropEvent(QPointF(20, 20), Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)
    QApplication.sendEvent(column.viewport(), event)
    qt_app.processEvents()
    return event.isAccepted()


def drag_task(board, record, target, qt_app, monkeypatch):
    board.show_record(record.id)
    source = board.columns[record.data["status"]]

    def execute(drag, action):
        assert action == Qt.MoveAction
        assert board.dragged_record.id == record.id
        assert send_drop(board, target, drag.mimeData(), qt_app)
        return Qt.MoveAction

    # Exercise startDrag's actual payload and Qt drop events without a native mouse loop.
    monkeypatch.setattr(QDrag, "exec", execute)
    source.startDrag(Qt.MoveAction)
    assert board.dragged_record is None


def test_tabs_search_shortcut_and_filters_are_independent(window, qt_app):
    ids, rows = seed(window)
    doc = DocumentService(window.project).create(ids["two"], "Suchnotiz", "Dokumentinhalt")
    assert [window.tabs.tabText(i) for i in range(window.tabs.count())] == [
        "Projekt-Canvas", "Aufgaben-Kanban", "Notizen", "Dokumentation && Anhänge", "Suche",
        "Verarbeitung"]
    assert window.splitter.widget(2).isHidden()
    window.tabs.setCurrentIndex(0)
    assert not window.splitter.widget(2).isHidden()
    window.tabs.setCurrentWidget(window.tasks)
    window.tasks.kind.setCurrentIndex(window.tasks.kind.findData("issue"))
    assert set(window.tasks.records) == {rows["hero"].id}
    window.activateWindow()
    window.tasks.query.setFocus()
    qt_app.processEvents()
    QTest.keyClick(window, Qt.Key_F, Qt.ControlModifier)
    assert window.tabs.currentWidget() == window.search
    assert window.search.query.hasFocus()
    QTest.keyClicks(window.search.query, "Suchnotiz")
    assert window.search.results.count() == 1
    assert set(window.tasks.records) == {rows["hero"].id}
    window.search.show_record(doc.id)
    window.search.edit_current()
    assert window.notes.editor.current.id == doc.id
    assert window.tabs.currentWidget() == window.notes


def test_scope_groups_card_click_and_explicit_navigation(window, qt_app):
    ids, rows = seed(window)
    board = window.tasks
    assert len(board.records) == 5
    column = board.columns["open"]
    item = column.items_by_id[rows["one"].id]
    QTest.mouseClick(column.viewport(), Qt.LeftButton, pos=column.visualItemRect(item).center())
    assert board.selected_record.id == rows["one"].id
    assert window.selected_id == ids["root"] and len(board.records) == 5
    assert "Beschreibung one" in board.details.toPlainText()
    QTest.mouseClick(board.owner_button, Qt.LeftButton)
    assert window.selected_id == ids["one"]
    assert set(board.records) == {rows["one"].id, rows["hero"].id}
    assert any(key[0] == "shared" for key in column.groups)
    window.select_card(ids["act"])
    assert set(board.records) == {rows[key].id for key in ("act", "one", "two", "hero")}
    QTest.mouseClick(board.findChild(QPushButton, "kanban_project"), Qt.LeftButton)
    assert window.selected_id == ids["root"] and len(board.records) == 5
    key = (ids["act"],)
    column.groups[key].setExpanded(False)
    board.refresh()
    assert not column.groups[key].isExpanded()
    board.show_record(rows["one"].id)
    assert column.groups[key].isExpanded()


def test_double_click_and_enter_open_one_editor_each(window, qt_app, monkeypatch):
    ids, rows = seed(window)
    board = window.tasks
    board.show_record(rows["one"].id)
    column = board.columns["open"]
    opened = []
    monkeypatch.setattr(board, "edit_current", lambda: opened.append(board.selected_record.id))
    point = column.visualItemRect(column.currentItem()).center()
    QTest.mouseClick(column.viewport(), Qt.LeftButton, pos=point)
    QTest.mouseDClick(column.viewport(), Qt.LeftButton, pos=point)
    assert opened == [rows["one"].id]
    QTest.keyClick(column, Qt.Key_Return)
    assert opened == [rows["one"].id, rows["one"].id]


def test_drag_status_preserves_id_owner_links_details_and_survives_restart(
        window, qt_app, monkeypatch):
    ids, rows = seed(window)
    record = rows["hero"]
    board = window.tasks
    edges = window.project.catalog.relations()
    for target in ("in_progress", "blocked", "done", "open"):
        drag_task(board, record, target, qt_app, monkeypatch)
        saved = window.project.catalog.get(record.id)
        assert saved.revision_no == record.revision_no + 1
        assert saved.data["status"] == target
        assert saved.owner_id == ids["hero"] and saved.id == record.id
        assert saved.data["body"] == record.data["body"]
        assert saved.id in board.columns[target].items_by_id
        assert sum(saved.id in col.items_by_id for col in board.columns.values()) == 1
        assert window.project.catalog.relations() == edges
        record = saved
    root = window.project.catalog.path.parent
    window.open_project(root)
    assert window.project.catalog.get(record.id) == record
    assert record.id in window.tasks.columns["open"].items_by_id


def test_drop_and_button_respect_checklists_and_explicit_approval(window, qt_app, monkeypatch):
    service = IssueService(window.project)
    task = service.create(window.selected_id, "Abnahme", approval_needed=True, checklist=[
        {"id": new_id(), "text": "Testen", "done": False}])
    window.refresh()
    errors = []
    monkeypatch.setattr("etherfood_studio.ui.tasks.base.show_error",
                        lambda parent, error: errors.append(str(error)))
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Yes)
    drag_task(window.tasks, task, "done", qt_app, monkeypatch)
    assert "To-do" in errors[-1] and window.project.catalog.get(task.id) == task
    assert task.id in window.tasks.columns["open"].items_by_id
    window.tasks.checklist.items.item(0).setCheckState(Qt.Checked)
    checked = window.project.catalog.get(task.id)
    assert checked.data["status"] == "open"  # A checked list is not a status/asset approval.
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.No)
    drag_task(window.tasks, checked, "done", qt_app, monkeypatch)
    assert window.project.catalog.get(task.id) == checked
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Yes)
    window.tasks.new_status.setCurrentIndex(window.tasks.new_status.findData("done"))
    QTest.mouseClick(window.tasks.status_button, Qt.LeftButton)
    saved = window.project.catalog.get(task.id)
    assert saved.data["status"] == "done" and saved.data["approval_confirmed"]
    window.tasks.checklist.items.item(0).setCheckState(Qt.Unchecked)
    reopened = window.project.catalog.get(task.id)
    assert reopened.data["status"] == "open" and not reopened.data["approval_confirmed"]
    assert task.id in window.tasks.columns["open"].items_by_id


@pytest.mark.parametrize("action", ["drop", "button"])
def test_stale_status_changes_report_conflict_without_losing_parallel_text(
        window, qt_app, monkeypatch, action):
    ids, rows = seed(window)
    record = rows["one"]
    board = window.tasks
    board.show_record(record.id)
    updated = IssueService(window.project).update(record.id, record.title,
                                                  "Parallel gespeichert", record.revision_no)
    errors = []
    monkeypatch.setattr("etherfood_studio.ui.tasks.base.show_error",
                        lambda parent, error: errors.append(error.code))
    if action == "drop":
        board.dragged_record = board.records[record.id]
        mime = board.columns["open"].drag_mime(record.id)
        assert send_drop(board, "blocked", mime, qt_app)
        board.dragged_record = None
    else:
        board.new_status.setCurrentIndex(board.new_status.findData("blocked"))
        QTest.mouseClick(board.status_button, Qt.LeftButton)
    assert errors == ["conflict"] and window.project.catalog.get(record.id) == updated
    assert "Parallel gespeichert" in board.details.toPlainText()
    assert record.id in board.columns["open"].items_by_id


def test_external_drop_is_rejected_and_same_column_drop_is_noop(window, qt_app, monkeypatch):
    ids, rows = seed(window)
    board = window.tasks
    task = rows["one"]
    before = window.project.catalog.export_snapshot()
    mime = QMimeData()
    mime.setData(MIME_TYPE, ("other-board:" + task.id).encode())
    board.dragged_record = task
    assert not send_drop(board, "done", mime, qt_app)
    board.dragged_record = None
    drag_task(board, task, "open", qt_app, monkeypatch)
    assert window.project.catalog.export_snapshot() == before


def test_creation_uses_selected_scope_and_existing_search_sees_same_record(
        window, qt_app, monkeypatch):
    ids, rows = seed(window)
    window.select_card(ids["two"])

    def fill_dialog():
        dialog = QApplication.activeModalWidget()
        dialog.findChild(QLineEdit, "new_task_title").setText("Neue Bereichsaufgabe")
        dialog.findChild(QPlainTextEdit, "new_task_body").setPlainText("Ein gemeinsamer Datensatz")
        QTest.mouseClick(dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.Ok),
                         Qt.LeftButton)

    for issue in (False, True):
        QTimer.singleShot(0, fill_dialog)
        window.tasks.new_item(issue)
        task = window.tasks.selected_record
        assert task.owner_id == ids["two"] and task.kind == ("issue" if issue else "task")
        window.search.show_record(task.id)
        assert window.search.selected_record == task
    window.tasks.query.setText("Keine passenden Aufgaben")
    assert not window.tasks.records and not window.tasks.edit_button.isEnabled()
    assert not window.tasks.status_button.isEnabled() and not window.tasks.owner_button.isEnabled()
    window.tasks.show_record(task.id)
    assert window.tasks.selected_record.id == task.id


def test_cancelled_scope_navigation_and_task_changes_preserve_unsaved_notes(
        window, qt_app, monkeypatch):
    ids, rows = seed(window)
    window.select_card(ids["one"])
    window.documents.create_document("Entwurf")
    window.documents.editor.setPlainText("Ungespeichert behalten")
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Cancel)
    QTest.mouseClick(window.tasks.findChild(QPushButton, "kanban_project"), Qt.LeftButton)
    assert window.selected_id == ids["one"] and window.tasks.current_card == ids["one"]
    task = rows["one"]
    window.tasks.show_record(task.id)
    window.tasks.new_status.setCurrentIndex(window.tasks.new_status.findData("in_progress"))
    window.tasks.change_status()
    assert window.documents.dirty
    assert window.documents.editor.toPlainText() == "Ungespeichert behalten"
