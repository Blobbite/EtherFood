"""Actual Qt tree drops, post-it editing and compact canvas content navigation."""

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QMimeData, QPointF, QSettings, Qt, QTimer
from PySide6.QtGui import QDrag, QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QMessageBox, QPushButton

from etherfood_studio.application.document_service import DocumentService
from etherfood_studio.application.issue_service import IssueService
from etherfood_studio.application.note_service import NoteService
from etherfood_studio.application.tree_service import TreeService
from etherfood_studio.ui.main_window import MainWindow
from etherfood_studio.ui.notes import NoteEditor, NOTE_ROLE
from etherfood_studio.ui.presentation import kind_icon
from etherfood_studio.ui.project_tree import EDGE_ROLE, ID_ROLE, KIND_ROLE, TREE_MIME


@pytest.fixture
def window(qt_app, tmp_path):
    value = MainWindow(QSettings(str(tmp_path / "preferences.ini"), QSettings.IniFormat))
    root = tmp_path / "project"
    root.mkdir()
    value.new_project(root, "Notizprüfung")
    value.ids = value.project.demo()
    value.refresh()
    value.show()
    qt_app.processEvents()
    yield value
    value.documents.dirty = False
    value.notes.editor.dirty = False
    value.close()
    qt_app.processEvents()


def tree_item(window, identifier, *, reference=False):
    return next(item for item in window.tree.findItems("", Qt.MatchContains | Qt.MatchRecursive)
                if item.data(0, ID_ROLE) == identifier
                and (item.data(0, KIND_ROLE) == "reference") == reference)


def send_tree_drop(window, target, qt_app, *, control=False, mime=None):
    tree = window.tree
    item = tree_item(window, target)
    tree.scrollToItem(item)
    qt_app.processEvents()
    point = tree.visualItemRect(item).center()
    data = mime or tree.drag_mime()
    mods = Qt.ControlModifier if control else Qt.NoModifier
    actions = Qt.CopyAction | Qt.MoveAction
    for event in (QDragEnterEvent(point, actions, data, Qt.LeftButton, mods),
                  QDragMoveEvent(point, actions, data, Qt.LeftButton, mods)):
        QApplication.sendEvent(tree.viewport(), event)
    drop = QDropEvent(QPointF(point), actions, data, Qt.LeftButton, mods)
    QApplication.sendEvent(tree.viewport(), drop)
    qt_app.processEvents()
    return drop.isAccepted()


@pytest.mark.parametrize("kind", ["task", "document", "asset"])
def test_tree_drop_moves_real_records_with_undo_and_no_parent_dropdown(window, qt_app, kind):
    ids, project = window.ids, window.project
    if kind == "task":
        record = IssueService(project).create(ids["one"], "Aufgabe", "Inhalt")
    elif kind == "document":
        record = DocumentService(project).create(ids["one"], "Notiz", "Inhalt")
    else:
        record = project.catalog.get(ids["hero"])
    window.refresh()
    window.tree.dragged = TreeService(window.commands).capture(record.id)
    assert send_tree_drop(window, ids["two"], qt_app)
    window.tree.dragged = None
    saved = project.catalog.get(record.id)
    assert saved.owner_id == ids["two"] and saved.data == record.data
    assert tree_item(window, record.id).parent().data(0, ID_ROLE) == ids["two"]
    assert window.findChild(QPushButton, "reparent_card") is None
    menu = window.navigation.menu(ids["hero"])
    assert not any(action.objectName() == "context_reparent" for action in menu.actions())
    menu.deleteLater()
    window.tabs.setCurrentIndex(0)
    window.undo(False)
    assert project.catalog.get(record.id).owner_id == record.owner_id
    window.undo(True)
    assert project.catalog.get(record.id).owner_id == ids["two"]


def test_control_drag_and_reference_drag_do_not_move_asset(window, qt_app):
    ids = window.ids
    project = window.project
    third = project.create_card("chapter", "Drei", ids["act"])
    window.refresh()
    hero = project.catalog.get(ids["hero"])
    tree = TreeService(window.commands)
    window.tree.dragged = tree.capture(hero.id)
    assert send_tree_drop(window, third.id, qt_app, control=True)
    window.tree.dragged = None
    assert project.catalog.get(hero.id) == hero
    edge = next(row for row in project.catalog.relations()
                if row["kind"] == "uses" and row["source_id"] == third.id
                and row["target_id"] == hero.id)
    assert tree_item(window, hero.id, reference=True).data(0, EDGE_ROLE)
    window.tree.dragged = tree.capture(hero.id, edge["id"])
    assert send_tree_drop(window, ids["act"], qt_app)
    window.tree.dragged = None
    assert project.catalog.get(hero.id) == hero
    moved = next(row for row in project.catalog.relations() if row["id"] == edge["id"])
    assert moved["source_id"] == ids["act"]


def test_invalid_and_foreign_drops_and_hover_expansion_do_not_write(window, qt_app):
    ids = window.ids
    before = window.project.catalog.export_snapshot()
    window.tree.dragged = TreeService(window.commands).capture(ids["act"])
    assert not send_tree_drop(window, ids["one"], qt_app)
    tree_item(window, ids["two"]).setExpanded(False)
    tree_item(window, ids["two"]).setExpanded(True)
    assert window.project.catalog.export_snapshot() == before
    mime = QMimeData()
    mime.setData(TREE_MIME, b"foreign-tree")
    assert not send_tree_drop(window, ids["two"], qt_app, mime=mime)
    window.tree.dragged = None
    assert window.project.catalog.export_snapshot() == before


def test_drag_hover_opens_collapsed_target_without_saving_layout(window, qt_app):
    task = IssueService(window.project).create(window.project.project().id, "Ziehen")
    window.refresh()
    item = tree_item(window, window.ids["act"])
    item.setExpanded(False)
    before = window.project.catalog.export_snapshot()
    window.tree.dragged = TreeService(window.commands).capture(task.id)
    point = window.tree.visualItemRect(item).center()
    mime = window.tree.drag_mime()
    enter = QDragEnterEvent(point, Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)
    move = QDragMoveEvent(point, Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)
    QApplication.sendEvent(window.tree.viewport(), enter)
    QApplication.sendEvent(window.tree.viewport(), move)
    QTest.qWait(850)
    assert item.isExpanded()
    assert window.project.catalog.export_snapshot() == before
    window.tree.dragged = None


def test_drag_autoscroll_reaches_large_tree_without_reparenting(window, qt_app):
    for index in range(35):
        window.project.create_card("act", f"Weiterer Akt {index}", window.project.project().id)
    task = IssueService(window.project).create(window.project.project().id, "Ziehen")
    window.refresh()
    tree = window.tree
    tree.verticalScrollBar().setValue(0)
    before = window.project.catalog.export_snapshot()
    tree.dragged = TreeService(window.commands).capture(task.id)
    point = tree.viewport().rect().bottomLeft()
    point.setX(60)
    point.setY(point.y() - 5)
    mime = tree.drag_mime()
    QApplication.sendEvent(tree.viewport(), QDragEnterEvent(
        point, Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier))
    QApplication.sendEvent(tree.viewport(), QDragMoveEvent(
        point, Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier))
    QTest.qWait(350)
    assert tree.verticalScrollBar().value() > 0
    assert window.project.catalog.export_snapshot() == before
    tree.clear_hover()
    tree.dragged = None


def test_drag_start_saves_dirty_document_before_capturing_revision(window, qt_app, monkeypatch):
    ids = window.ids
    window.select_card(ids["one"])
    note = window.documents.create_document("Entwurf ziehen")
    window.tree.setCurrentItem(tree_item(window, note.id))
    window.documents.editor.setPlainText("Gespeicherter Entwurf")
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Cancel)
    calls = []
    monkeypatch.setattr(QDrag, "exec", lambda *args: calls.append(True))
    window.tree.startDrag(Qt.MoveAction)
    assert not calls and window.documents.dirty
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Save)

    def drag(*args):
        assert not window.documents.dirty
        assert window.tree.dragged.record.data["body"] == "Gespeicherter Entwurf"
        assert send_tree_drop(window, ids["two"], qt_app)
        return Qt.MoveAction

    monkeypatch.setattr(QDrag, "exec", drag)
    window.tree.startDrag(Qt.MoveAction)
    saved = window.project.catalog.get(note.id)
    assert saved.owner_id == ids["two"] and saved.data["body"] == "Gespeicherter Entwurf"
    assert window.documents.current.id == note.id and window.documents.owner_id == ids["two"]
    window.tabs.setCurrentIndex(0)
    window.undo(False)
    assert window.documents.owner_id == ids["one"]


def test_postit_create_edit_filter_pin_and_restart_use_existing_documents(window, qt_app):
    ids = window.ids
    window.select_card(ids["one"])
    window.tabs.setCurrentWidget(window.notes)

    QTest.mouseClick(window.notes.findChild(QPushButton, "new_note"), Qt.LeftButton)
    editor = window.notes.editor
    editor.title.setText("Raster besprechen")
    editor.editor.setPlainText("Walk und Stand prüfen")
    editor.color.setCurrentIndex(editor.color.findData("blue"))
    editor.pinned.setChecked(True)
    assert editor.save()
    assert window.notes.notes.count() == 1
    record = window.notes.selected()
    assert record.kind == "document" and record.owner_id == ids["one"]
    assert record.data["note_color"] == "blue" and record.data["note_pinned"]
    assert record in DocumentService(window.project).documents(ids["one"])
    window.notes.color.setCurrentIndex(window.notes.color.findData("pink"))
    assert window.notes.notes.count() == 0
    window.notes.color.setCurrentIndex(0)
    window.notes.query.setText("STAND")
    assert window.notes.notes.count() == 1
    window.notes.select_note(record.id)
    window.notes.edit_note()
    assert window.tabs.currentWidget() == window.notes
    assert window.notes.editor.current == record
    window.open_project(window.project.catalog.path.parent)
    window.notes.query.clear()
    window.notes.select_note(record.id)
    assert window.notes.selected() == record


def test_note_editor_conflict_cancel_and_document_draft_guard(window, qt_app, monkeypatch):
    service = NoteService(window.project)
    note = service.write(window.ids["one"], "Notiz", "Alt")
    editor = NoteEditor(service, note.owner_id, note, window)
    editor.show()
    editor.body.setPlainText("Mein Entwurf")
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Cancel)
    editor.reject()
    assert editor.isVisible() and editor.body.toPlainText() == "Mein Entwurf"
    service.save(note.id, "Parallel gespeichert", note.revision_no)
    errors = []
    monkeypatch.setattr("etherfood_studio.ui.notes.show_error",
                        lambda parent, error: errors.append(error.code))
    assert not editor.save() and errors == ["conflict"]
    assert editor.body.toPlainText() == "Mein Entwurf" and editor.isVisible()
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Discard)
    editor.reject()
    editor.deleteLater()
    window.open_document(note.id)
    window.notes.editor.editor.setPlainText("Nicht verlieren")
    window.notes.refresh()
    window.notes.select_note(note.id)
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Cancel)
    window.notes.edit_note()
    assert window.notes.editor.dirty
    assert window.notes.editor.editor.toPlainText() == "Nicht verlieren"


@pytest.mark.parametrize("scale", [0.25, 1.0, 2.5])
def test_compact_canvas_icons_selection_and_positions_survive_zoom(window, qt_app, scale):
    ids = window.ids
    task = IssueService(window.project).create(ids["one"], "Aufgabe", "Text")
    note = NoteService(window.project).write(ids["two"], "Notiz", "Text", color="pink")
    # Deliberately crowded manual positions: automatic content handles must not cover cards.
    for index, card in enumerate(window.project.cards()):
        window.project.catalog.save_layout(card.id, {
            "x": index % 3 * 310, "y": index // 3 * 170, "w": 220, "h": 100})
    window.refresh()
    canvas = window.canvas
    for record in (task, note):
        icon = canvas.items_by_id[record.id]
        assert icon.rect().width() < 200 and icon.rect().height() < 100
        assert not icon.grip.isVisible()
        for card in window.project.cards():
            other = canvas.items_by_id[card.id]
            assert not icon.sceneBoundingRect().intersects(other.sceneBoundingRect())
    assert canvas.items_by_id[note.id].brush().color().name() == "#f9d2e1"
    canvas.zoom(scale / canvas.transform().m11())
    target = canvas.items_by_id[task.id]
    canvas.centerOn(target)
    qt_app.processEvents()
    positions = {key: value.pos() for key, value in canvas.items_by_id.items()}
    transform = canvas.viewportTransform()
    snapshot = window.project.catalog.export_snapshot()
    point = canvas.mapFromScene(target.mapToScene(target.rect().center()))
    QTest.mouseClick(canvas.viewport(), Qt.LeftButton, pos=point)
    qt_app.processEvents()
    assert window.selected_content_id == task.id
    assert canvas.viewportTransform() == transform
    assert {key: value.pos() for key, value in canvas.items_by_id.items()} == positions
    assert window.project.catalog.export_snapshot() == snapshot


def test_canvas_note_double_click_and_content_arrow_reassign(window, qt_app):
    ids = window.ids
    note = NoteService(window.project).write(ids["one"], "Notiz", "Text")
    window.refresh()
    canvas = window.canvas
    canvas.centerOn(canvas.items_by_id[note.id])
    qt_app.processEvents()
    icon = canvas.items_by_id[note.id]
    point = canvas.mapFromScene(icon.mapToScene(icon.rect().center()))
    QTest.mouseClick(canvas.viewport(), Qt.LeftButton, pos=point)
    QTest.qWait(50)
    assert window.notes.editor.current.id == note.id
    assert window.tabs.currentWidget() == window.notes
    window.reconnect_cards("content:" + note.id, note.id, ids["two"])
    assert window.project.catalog.get(note.id).owner_id == ids["two"]
    assert window.canvas.edges_by_id["content:" + note.id].target == ids["two"]
    window.select_card(ids["two"])
    assert window.notes.notes.item(0).data(NOTE_ROLE).id == note.id


def test_legacy_note_card_is_compact_and_opens_its_note_dashboard(window, qt_app):
    record = window.project.create_card("note", "Bestehender Notizbereich", window.ids["one"])
    note = DocumentService(window.project).create(record.id, "Vorhandene Notiz", "Inhalt")
    window.refresh()
    icon = window.canvas.items_by_id[record.id]
    assert icon.rect().width() == 144
    window.open_canvas_content(record.id)
    assert window.tabs.currentWidget() == window.notes
    assert window.notes.current_card == record.id
    assert window.notes.notes.item(0).data(NOTE_ROLE).id == note.id


def test_task_icon_opens_same_kanban_task_editor(window, qt_app):
    from etherfood_studio.ui.tasks.editor import TaskEditor

    task = IssueService(window.project).create(window.ids["one"], "Kleine Aufgabe", "Inhalt")
    window.refresh()
    canvas = window.canvas
    icon = canvas.items_by_id[task.id]
    canvas.centerOn(icon)
    qt_app.processEvents()
    opened = []

    def close_editor():
        editor = QApplication.activeModalWidget()
        assert isinstance(editor, TaskEditor)
        opened.append(True)
        editor.reject()

    point = canvas.mapFromScene(icon.mapToScene(icon.rect().center()))
    QTimer.singleShot(20, close_editor)
    QTest.mouseClick(canvas.viewport(), Qt.LeftButton, pos=point)
    QTest.mouseDClick(canvas.viewport(), Qt.LeftButton, pos=point)
    QTest.qWait(50)
    assert opened == [True] and window.tabs.currentWidget() == window.tasks
    assert window.tasks.selected_record.id == task.id


def test_asset_icon_is_not_a_document_icon_and_archived_contents_hide(window, qt_app):
    assert kind_icon("asset").pixmap(32).toImage() != kind_icon("document").pixmap(32).toImage()
    assert kind_icon("note").pixmap(32).toImage() != kind_icon("asset").pixmap(32).toImage()
    note = NoteService(window.project).write(window.ids["one"], "Archivnotiz", "Text")
    window.project.archive(window.ids["act"], True,
                            window.project.catalog.get(window.ids["act"]).revision_no)
    window.refresh()
    assert note.id not in window.canvas.items_by_id
    assert NoteService(window.project).notes(window.notes.current_card) == []
    assert window.notes.editor.current is None
