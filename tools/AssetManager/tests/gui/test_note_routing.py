"""All note entry points remain in the dashboard with editable, protected drafts."""

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox, QPushButton

from etherfood_studio.application.note_service import NoteService
from etherfood_studio.ui.main_window import MainWindow
from etherfood_studio.ui.notes import NOTE_ROLE


@pytest.fixture
def window(qt_app, tmp_path):
    value = MainWindow(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat))
    root = tmp_path / "project"
    root.mkdir()
    value.new_project(root, "Notizen")
    value.ids = value.project.demo()
    value.note = NoteService(value.project).write(value.ids["one"], "Notiz", "Vorhandener Text")
    value.refresh()
    value.show()
    qt_app.processEvents()
    yield value
    value.notes.editor.dirty = False
    value.documents.dirty = False
    value.close()


@pytest.mark.parametrize("entry", ["tree", "canvas", "search", "context"])
def test_all_note_entry_points_open_inline_dashboard(window, qt_app, entry):
    identifier = window.note.id
    if entry == "tree":
        item = next(item for item in window.tree.findItems("", Qt.MatchContains | Qt.MatchRecursive)
                    if item.data(0, Qt.UserRole) == identifier)
        window.tree.setCurrentItem(item)
    elif entry == "canvas":
        item = window.canvas.items_by_id[identifier]
        window.canvas.centerOn(item)
        qt_app.processEvents()
        QTest.mouseClick(window.canvas.viewport(), Qt.LeftButton,
                         pos=window.canvas.mapFromScene(item.mapToScene(item.rect().center())))
        QTest.qWait(20)
    elif entry == "search":
        window.search.show_record(identifier)
        window.search.edit_current()
    else:
        menu = window.navigation.menu(identifier)
        next(a for a in menu.actions() if a.objectName() == "context_edit").trigger()
        menu.deleteLater()
    assert window.tabs.currentWidget() == window.notes
    assert window.notes.selected().id == identifier
    assert window.notes.editor.current.id == identifier
    assert window.notes.editor.editor.toPlainText() == "Vorhandener Text"
    assert window.documents.current is None and window.documents.documents.count() == 0


def test_inline_note_save_colors_attachment_conflict_and_restart(window, qt_app,
                                                              tmp_path, monkeypatch):
    path = tmp_path / "Anhang.txt"
    path.write_text("Sicherer Altanhang", encoding="utf-8")
    service = NoteService(window.project)
    service.attach(window.note.id, path, window.note.revision_no)
    window.open_content(window.note.id)
    editor = window.notes.editor
    editor.title.setText("Umbenannte Notiz")
    editor.editor.setPlainText("Im Dashboard bearbeitet")
    editor.color.setCurrentIndex(editor.color.findData("pink"))
    editor.pinned.setChecked(True)
    editor.editor.setFocus()
    QTest.keyClick(editor.editor, Qt.Key_S, Qt.ControlModifier)
    assert not editor.dirty
    record = window.project.catalog.get(window.note.id)
    assert record.title == "Umbenannte Notiz" and record.data["note_color"] == "pink"
    assert record.data["note_pinned"] and record.data["body"] == "Im Dashboard bearbeitet"
    assert editor.findChild(QPushButton, "note_inline_add_attachment") is None
    assert not hasattr(editor, "attachments")
    assert service.attachment_text(record.id, 0) == "Sicherer Altanhang"
    editor.editor.setPlainText("Lokaler Entwurf")
    record = editor.service.save(record.id, "Parallel", editor.current.revision_no)
    errors = []
    monkeypatch.setattr("etherfood_studio.ui.note_details.show_error",
                        lambda parent, error: errors.append(error.code))
    assert not editor.save() and errors == ["conflict"]
    assert editor.dirty and editor.editor.toPlainText() == "Lokaler Entwurf"
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Cancel)
    assert not window.select_card(window.ids["two"])
    assert window.notes.current_card == window.ids["one"]
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Discard)
    assert window.open_project(window.project.catalog.path.parent)
    window.open_content(record.id)
    assert window.notes.editor.editor.toPlainText() == "Parallel"
    assert NoteService(window.project).attachment_text(record.id, 0) == "Sicherer Altanhang"


def test_selecting_another_postit_guards_inline_draft(window, monkeypatch):
    other = NoteService(window.project).write(window.ids["one"], "Zweite", "Anderer Text")
    window.open_content(window.note.id)
    window.notes.editor.editor.setPlainText("Nicht verlieren")
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Cancel)
    item = next(window.notes.notes.item(i) for i in range(window.notes.notes.count())
                if window.notes.notes.item(i).data(NOTE_ROLE).id == other.id)
    window.notes.notes.setCurrentItem(item)
    assert window.notes.selected().id == window.note.id
    assert window.notes.editor.current.id == window.note.id and window.notes.editor.dirty
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Save)
    window.notes.notes.setCurrentItem(item)
    assert window.notes.editor.current.id == other.id
    assert window.notes.selected().id == other.id
    assert window.project.catalog.get(window.note.id).data["body"] == "Nicht verlieren"
