"""Documentation creation, compact canvas handles and unambiguous shared type icons."""

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QPointF, QSettings, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox, QPushButton

from etherfood_studio.application.document_service import DocumentService
from etherfood_studio.application.issue_service import IssueService
from etherfood_studio.application.note_service import NoteService
from etherfood_studio.domain.notes import is_note
from etherfood_studio.ui.main_window import MainWindow
from etherfood_studio.ui.presentation import DOCUMENT_COLOR, kind_icon


@pytest.fixture
def window(qt_app, tmp_path):
    value = MainWindow(QSettings(str(tmp_path / "preferences.ini"), QSettings.IniFormat))
    root = tmp_path / "project"
    root.mkdir()
    value.new_project(root, "Dokumente im Canvas")
    value.ids = value.project.demo()
    value.refresh()
    value.select_card(value.ids["one"])
    value.show()
    qt_app.processEvents()
    yield value
    value.documents.dirty = False
    value.notes.editor.dirty = False
    value.close()
    qt_app.processEvents()


@pytest.mark.parametrize("template", ["Dokumentation", "Asset-Briefing"])
def test_documentation_button_creates_document_not_post_it(window, qt_app, monkeypatch, template):
    window.tabs.setCurrentWidget(window.documents)
    button = window.documents.findChild(QPushButton, "new_document")
    assert button.text() == "+ Dokumentation"
    assert "+ Dokumentation" in window.documents.state.text()
    assert "+ Dokumentation" in window.documents.editor.placeholderText()
    dialogs = []

    def title(parent, caption, label):
        dialogs.append(caption)
        return "Dokument aus Button", True

    def choose(parent, caption, label, choices, index, editable):
        assert choices[0] == "Dokumentation" and not editable
        assert "Freie Notiz" not in choices and "Testnotiz" not in choices
        return template, True

    monkeypatch.setattr(QInputDialog, "getText", title)
    monkeypatch.setattr(QInputDialog, "getItem", choose)
    QTest.mouseClick(button, Qt.LeftButton)
    record = window.documents.current
    assert dialogs == ["Neue Dokumentation"]
    assert not is_note(record) and record.data["template"] == template
    assert record.owner_id == window.ids["one"]
    assert record.id in window.canvas.items_by_id
    assert window.notes.notes.count() == 0
    assert window.notes.findChild(QPushButton, "new_note").text() == "+ Notiz"


def test_context_note_opens_notes_dashboard(window):
    def fill():
        editor = QApplication.activeModalWidget()
        editor.title.setText("Kontextnotiz")
        editor.body.setPlainText("Notiztext")
        editor.save()
    QTimer.singleShot(0, fill)
    window.navigation.new_note()
    assert window.tabs.currentWidget() == window.notes
    assert is_note(window.notes.editor.current)
    assert window.documents.current is None
    assert window.notes.notes.count() == 1


def test_markdown_button_kept_and_import_appears_on_canvas(window, tmp_path, qt_app, monkeypatch):
    path = tmp_path / "Dokument.md"
    path.write_text("# Anleitung\n\nEin eigener Absatz.", encoding="utf-8")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a: (str(path), ""))
    window.tabs.setCurrentWidget(window.documents)
    button = window.documents.findChild(QPushButton, "import_markdown")
    assert button.text() == "Markdown importieren"
    QTest.mouseClick(button, Qt.LeftButton)
    record = window.documents.current
    assert not is_note(record)
    assert record.data["body"] == path.read_text(encoding="utf-8")
    assert record.id in window.canvas.items_by_id and window.notes.notes.count() == 0


@pytest.mark.parametrize("scale", [0.3, 1.0, 2.5])
def test_document_icon_color_and_click_preserve_canvas_positions(window, qt_app, scale):
    record = window.documents.create_document("Anleitung")
    note = NoteService(window.project).write(window.ids["one"], "Post-it", "Kurznotiz")
    task = IssueService(window.project).create(window.ids["one"], "Aufgabe")
    window.refresh()
    canvas = window.canvas
    item = canvas.items_by_id[record.id]
    assert item.rect().width() == 144 and not item.grip.isVisible()
    assert item.brush().color().name() == DOCUMENT_COLOR
    for other in (note, task):
        assert item.brush() != canvas.items_by_id[other.id].brush()
        assert item.icon.pixmap().toImage() != canvas.items_by_id[other.id].icon.pixmap().toImage()
    canvas.zoom(scale / canvas.transform().m11())
    canvas.centerOn(item)
    qt_app.processEvents()
    positions = {key: value.pos() for key, value in canvas.items_by_id.items()}
    transform = canvas.viewportTransform()
    snapshot = window.project.catalog.export_snapshot()
    QTest.mouseClick(canvas.viewport(), Qt.LeftButton,
                     pos=canvas.mapFromScene(item.mapToScene(item.rect().center())))
    qt_app.processEvents()
    assert window.selected_content_id == record.id
    assert canvas.viewportTransform() == transform
    assert {key: value.pos() for key, value in canvas.items_by_id.items()} == positions
    assert window.project.catalog.export_snapshot() == snapshot


@pytest.mark.parametrize("generated", [False, True])
def test_document_double_click_and_ownership_respect_report_protection(
        window, qt_app, monkeypatch, generated):
    record = DocumentService(window.project).create(window.ids["one"], "Dokument", "Inhalt",
                                                     template="Dokumentation", generated=generated)
    window.refresh()
    canvas = window.canvas
    item = canvas.items_by_id[record.id]
    canvas.centerOn(item)
    qt_app.processEvents()
    calls = []
    open_document = window.documents.open_document

    def opened(identifier):
        calls.append(identifier)
        return open_document(identifier)

    monkeypatch.setattr(window.documents, "open_document", opened)
    point = canvas.mapFromScene(item.mapToScene(item.rect().center()))
    QTest.mouseClick(canvas.viewport(), Qt.LeftButton, pos=point)
    QTest.mouseDClick(canvas.viewport(), Qt.LeftButton, pos=point)
    QTest.qWait(20)
    assert calls == [record.id]
    assert window.tabs.currentWidget() == window.documents
    assert window.documents.current.id == record.id
    assert window.documents.editor.isReadOnly() == generated
    assert window.documents.save_button.isEnabled() != generated
    window.tabs.setCurrentWidget(canvas)
    errors = []
    monkeypatch.setattr("etherfood_studio.ui.main_window.show_error",
                        lambda parent, error: errors.append(error))
    before = window.project.catalog.export_snapshot()
    window.reconnect_cards("content:" + record.id, record.id, window.ids["two"])
    if generated:
        assert errors and window.project.catalog.export_snapshot() == before
    else:
        assert not errors
        assert window.project.catalog.get(record.id).owner_id == window.ids["two"]
        window.undo(False)
        assert window.project.catalog.get(record.id).owner_id == window.ids["one"]
        window.undo(True)
        assert window.project.catalog.get(record.id).owner_id == window.ids["two"]
    assert window.project.catalog.get(record.id).data == record.data


def test_document_draft_layout_and_attachment_survive_switch_and_restart(
        window, tmp_path, qt_app, monkeypatch):
    record = window.documents.create_document("Bleibt erhalten")
    source = tmp_path / "Anhang.txt"
    source.write_text("Anhang bleibt", encoding="utf-8")
    service = window.documents.service
    service.attach(record.id, source, record.revision_no)
    window.documents.refresh_documents(record.id)
    window.documents.editor.setPlainText("Noch ungespeicherte Dokumentation")
    other = service.create(window.ids["two"], "Anderes Dokument", template="Dokumentation")
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Cancel)
    window.open_canvas_content(other.id)
    assert window.documents.current.id == record.id and window.documents.dirty
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Save)
    window.open_canvas_content(other.id)
    assert window.documents.current.id == other.id
    window.move_card(record.id, 2300, 600)
    root = window.project.catalog.path.parent
    window.open_project(root)
    saved = window.project.catalog.get(record.id)
    assert saved.data["body"] == "Noch ungespeicherte Dokumentation"
    assert saved.owner_id == window.ids["one"] and not is_note(saved)
    assert window.documents.service.attachment_text(record.id, 0) == "Anhang bleibt"
    assert window.canvas.items_by_id[record.id].pos() == QPointF(2300, 600)
    window.toggle_card(window.ids["one"])
    assert record.id not in window.canvas.items_by_id
    window.toggle_card(window.ids["one"])
    assert record.id in window.canvas.items_by_id
    window.project.archive(window.ids["act"], True,
                            window.project.catalog.get(window.ids["act"]).revision_no)
    window.refresh()
    assert record.id not in window.canvas.items_by_id


@pytest.mark.parametrize("size", [16, 32])
def test_task_icon_is_a_thick_green_check_with_transparent_background(qt_app, size):
    image = kind_icon("task").pixmap(size, size).toImage()
    assert image.width() == size and image.pixelColor(0, 0).alpha() == 0
    assert image.pixelColor(size - 1, size - 1).alpha() == 0
    painted = [image.pixelColor(x, y) for x in range(size) for y in range(size)
               if image.pixelColor(x, y).alpha() > 32]
    assert len(painted) > size * size * 0.17
    assert all(pixel.green() > pixel.red() and pixel.green() > pixel.blue() for pixel in painted)
    assert kind_icon("document").pixmap(size).toImage() != kind_icon("note").pixmap(size).toImage()
