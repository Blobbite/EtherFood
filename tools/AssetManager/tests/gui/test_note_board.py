"""Real pointer events preserve editable post-its and saved free-board coordinates."""

import sqlite3

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPalette
from PySide6.QtTest import QTest

from etherfood_studio.application.note_service import NoteService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.ui.notes import NotesPanel


@pytest.fixture
def panel(qt_app, tmp_path):
    project = ProjectService.new(tmp_path, "Pinnwand")
    value = NotesPanel(lambda: True)
    value.bind(project)
    value.changed.connect(value.refresh)
    value.resize(1100, 760)
    value.show()
    qt_app.processEvents()
    yield value
    for _, card in value._cards():
        card.timer.stop()
        card.dirty = False
    value.close()
    value.deleteLater()
    qt_app.processEvents()
    project.catalog.close()


def drag(card, delta, qt_app):
    grip = card.grip
    start = QPoint(40, 10)
    end = grip.mapToGlobal(start) + delta
    QTest.mousePress(grip, Qt.LeftButton, pos=start)
    QTest.mouseMove(grip, grip.mapFromGlobal(end))
    QTest.mouseRelease(grip, Qt.LeftButton, pos=grip.mapFromGlobal(end))
    qt_app.processEvents()


def assert_visible_position(panel, item, point):
    board = panel.notes
    offset = QPoint(board.horizontalScrollBar().value(), board.verticalScrollBar().value())
    assert board.position(item) == point
    assert board.visualItemRect(item).topLeft() + offset == point
    assert board.itemWidget(item).pos() + offset == point


def test_blank_draft_moves_without_creating_record_then_saves_position_with_text(panel, qt_app):
    card = panel.editor
    item = panel.notes.currentItem()
    before = panel.project.catalog.export_snapshot()
    start = panel.notes.position(item)
    drag(card, QPoint(123, 84), qt_app)
    point = start + QPoint(123, 84)
    assert_visible_position(panel, item, point)
    assert panel.project.catalog.export_snapshot() == before and card.current is None
    assert card.board_position == {"x": point.x(), "y": point.y()}
    QTest.mouseClick(card.editor.viewport(), Qt.LeftButton)
    QTest.keyClicks(card.editor, "Notiz direkt schreiben")
    assert card.save()
    assert NoteService(panel.project).position(card.current.id) == card.board_position
    assert_visible_position(panel, item, point)


def test_move_filter_resize_refresh_and_reopen_keep_exact_positions(panel, qt_app):
    service = NoteService(panel.project)
    owner = panel.project.project().id
    first = service.write(owner, "A", "Erste Notiz", color="pink")
    second = service.write(owner, "B", "Zweite Notiz")
    panel.refresh()
    assert panel.notes.count() == 2  # The old empty placeholder is no extra blank post-it.
    panel.select_note(first.id)
    card = panel.editor
    item = panel.notes.currentItem()
    point = panel.notes.position(item) + QPoint(101, 69)
    drag(card, QPoint(101, 69), qt_app)
    assert_visible_position(panel, item, point)
    assert service.catalog.get(first.id) == first  # No content revision created by a move.
    panel.query.setText("Zweite")
    panel.query.clear()
    panel.color.setCurrentIndex(panel.color.findData("pink"))
    panel.color.setCurrentIndex(0)
    panel.resize(720, 500)
    panel.refresh()
    qt_app.processEvents()
    panel.select_note(first.id)
    assert_visible_position(panel, panel.notes.currentItem(), point)
    reopened = ProjectService.open(panel.project.catalog.path.parent)
    other = NotesPanel(lambda: True)
    try:
        other.bind(reopened)
        other.resize(900, 700)
        other.show()
        other.select_note(first.id)
        qt_app.processEvents()
        assert_visible_position(other, other.notes.currentItem(), point)
        assert service.catalog.get(second.id) == second
    finally:
        other.close()
        other.deleteLater()
        qt_app.processEvents()
        reopened.catalog.close()


def test_typing_selecting_text_and_changing_color_do_not_move_postit(panel, qt_app):
    card, item = panel.editor, panel.notes.currentItem()
    point = panel.notes.position(item)
    card.editor.setPlainText("Text auswählen statt die Karte zu ziehen")
    QTest.mousePress(card.editor.viewport(), Qt.LeftButton, pos=QPoint(10, 12))
    QTest.mouseMove(card.editor.viewport(), QPoint(150, 12))
    QTest.mouseRelease(card.editor.viewport(), Qt.LeftButton, pos=QPoint(150, 12))
    assert card.editor.textCursor().hasSelection()
    card.color.setCurrentIndex(card.color.findData("blue"))
    assert card.save()
    qt_app.processEvents()
    assert_visible_position(panel, item, point)
    assert card.editor.viewport().palette().color(QPalette.Base).name() == "#cfe6ff"
    # A rendered background pixel, not just a stylesheet assertion.
    picture = card.editor.viewport().grab().toImage()
    assert picture.pixelColor(picture.width() - 20, picture.height() - 20).name() == "#cfe6ff"
    background = panel.notes.viewport().grab().toImage()
    assert background.pixelColor(600, 400).name() == "#c5b493"


def test_storage_error_restores_position_without_losing_unsaved_text(panel, qt_app, monkeypatch):
    card, item = panel.editor, panel.notes.currentItem()
    card.editor.setPlainText("Gespeichert")
    assert card.save()
    card.editor.setPlainText("Ungespeichert")
    card.timer.stop()
    position = panel.notes.position(item)
    before = panel.project.catalog.export_snapshot()
    errors = []

    def locked(*args):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(card.service, "place", locked)
    monkeypatch.setattr("etherfood_studio.ui.notes.show_error",
                        lambda parent, error: errors.append(str(error)))
    drag(card, QPoint(70, 45), qt_app)
    assert errors == ["database is locked"]
    assert_visible_position(panel, item, position)
    assert panel.project.catalog.export_snapshot() == before
    assert card.dirty and card.editor.toPlainText() == "Ungespeichert"


def test_stacked_asset_notes_keep_board_positions_and_have_no_drag_handle(panel, qt_app):
    service = NoteService(panel.project)
    record = service.write(panel.current_card, "Idee", "Text", position={"x": 755, "y": 322})
    stacked = NotesPanel(lambda: True, stacked=True)
    try:
        stacked.bind(panel.project)
        stacked.show()
        stacked.select_note(record.id)
        assert not stacked.editor.grip.isVisible()
        stacked.editor.editor.setPlainText("Aus dem Asset-Menü")
        assert stacked.editor.save()
        assert service.position(record.id) == {"x": 755, "y": 322}
    finally:
        stacked.close()
        stacked.deleteLater()
        qt_app.processEvents()


def test_drag_after_scrolling_and_scope_change_keeps_content_coordinates(panel, qt_app):
    card = panel.editor
    card.editor.setPlainText("Weit rechts unten")
    assert card.save()
    record = card.current
    service = NoteService(panel.project)
    service.place(record.id, {"x": 1400, "y": 900})
    panel.refresh()
    panel.select_note(record.id)
    qt_app.processEvents()
    assert panel.notes.horizontalScrollBar().value() > 0
    assert panel.notes.verticalScrollBar().value() > 0
    drag(panel.editor, QPoint(-45, -33), qt_app)
    target = QPoint(1355, 867)
    assert_visible_position(panel, panel.notes.currentItem(), target)
    assert service.position(record.id) == {"x": target.x(), "y": target.y()}
    other = next(row.id for row in panel.project.cards() if row.kind == "global")
    assert panel.set_scope(other)
    assert panel.set_scope(record.owner_id)
    panel.select_note(record.id)
    qt_app.processEvents()
    assert_visible_position(panel, panel.notes.currentItem(), target)


def test_cancel_drag_and_text_save_do_not_overwrite_other_position_change(panel, qt_app):
    card, item = panel.editor, panel.notes.currentItem()
    card.editor.setPlainText("Eine Idee")
    assert card.save()
    old = panel.notes.position(item)
    before = panel.project.catalog.export_snapshot()
    grip = card.grip
    start = QPoint(40, 10)
    end = grip.mapToGlobal(start) + QPoint(90, 50)
    QTest.mousePress(grip, Qt.LeftButton, pos=start)
    QTest.mouseMove(grip, grip.mapFromGlobal(end))
    QTest.keyClick(grip, Qt.Key_Escape)
    QTest.mouseRelease(grip, Qt.LeftButton, pos=start)
    assert_visible_position(panel, item, old)
    assert panel.project.catalog.export_snapshot() == before
    service = NoteService(panel.project)
    service.place(card.current.id, {"x": 700, "y": 440})
    card.editor.setPlainText("Neuer Text nach anderem Positionswechsel")
    assert card.save()
    qt_app.processEvents()
    assert service.position(card.current.id) == {"x": 700, "y": 440}
    assert_visible_position(panel, item, QPoint(700, 440))


def test_explicit_new_note_draft_survives_refresh_beside_existing_notes(panel):
    panel.editor.editor.setPlainText("Gespeicherte Notiz")
    assert panel.editor.save()
    panel.new_note()
    draft = panel.editor
    assert draft.current is None and not draft.dirty
    panel.refresh()
    assert panel.notes.count() == 2
    assert draft in [card for _, card in panel._cards()]


def test_drag_to_origin_is_not_treated_as_missing_position(panel, qt_app):
    card, item = panel.editor, panel.notes.currentItem()
    card.editor.setPlainText("Linke obere Ecke")
    assert card.save()
    drag(card, QPoint(-150, -150), qt_app)
    assert_visible_position(panel, item, QPoint(0, 0))
    service = NoteService(panel.project)
    assert service.position(card.current.id) == {"x": 0, "y": 0}
    panel.refresh()
    panel.resize(900, 640)
    qt_app.processEvents()
    assert_visible_position(panel, item, QPoint(0, 0))
