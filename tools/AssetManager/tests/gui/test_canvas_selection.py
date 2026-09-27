"""Mouse selection must not move the camera or corrupt a zoomed card drag."""

import pytest

pytest.importorskip("PySide6.QtWidgets", reason="GUI-Abhängigkeiten fehlen")

from PySide6.QtCore import QPoint, QPointF, QSettings, Qt
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QMessageBox

from etherfood_studio.ui.main_window import MainWindow


@pytest.fixture
def window(qt_app, tmp_path):
    settings = QSettings(str(tmp_path / "preferences.ini"), QSettings.Format.IniFormat)
    result = MainWindow(settings)
    root = tmp_path / "project"
    root.mkdir()
    assert result.new_project(root, "Zoom-Auswahl")
    result.project.demo()
    result.refresh()
    result.show()
    qt_app.processEvents()
    yield result
    result.documents.dirty = False
    result.close()
    qt_app.processEvents()


def prepare_target(window, qt_app, scale):
    canvas = window.canvas
    identifier = next(card.id for card in window.project.cards() if card.kind == "asset")
    canvas.zoom(scale / canvas.transform().m11())
    card = canvas.items_by_id[identifier]
    canvas.centerOn(card.sceneBoundingRect().center() + QPointF(65 / scale, 45 / scale))
    qt_app.processEvents()
    point = canvas.mapFromScene(card.mapToScene(card.rect().center()))
    assert canvas.viewport().rect().contains(point)
    assert window.selected_id != identifier
    return identifier, point


@pytest.mark.parametrize("scale", [0.25, 0.8, 1.0, 2.5])
def test_click_after_zoom_keeps_camera_positions_and_catalog(window, qt_app, scale):
    identifier, point = prepare_target(window, qt_app, scale)
    canvas = window.canvas
    positions = {key: item.pos() for key, item in canvas.items_by_id.items()}
    before = window.project.catalog.export_snapshot()
    undo_count = len(window.commands.done)
    transform = canvas.viewportTransform()
    moved = QSignalSpy(canvas.moved)
    QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=point)
    qt_app.processEvents()
    QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=point)
    qt_app.processEvents()
    assert window.selected_id == identifier
    assert canvas.viewportTransform() == transform
    assert {key: item.pos() for key, item in canvas.items_by_id.items()} == positions
    assert window.project.catalog.export_snapshot() == before
    assert moved.count() == 0
    assert len(window.commands.done) == undo_count
    window.open_project(window.project.catalog.path.parent)
    assert window.project.catalog.export_snapshot() == before
    assert {key: item.pos() for key, item in canvas.items_by_id.items()} == positions


@pytest.mark.parametrize("scale", [0.25, 0.8, 1.0, 2.5])
@pytest.mark.parametrize("delta", [QPoint(1, 1), QPoint(40, 25)])
def test_drag_new_selection_moves_only_by_pointer_delta_with_undo(window, qt_app, scale, delta):
    identifier, point = prepare_target(window, qt_app, scale)
    canvas = window.canvas
    positions = {key: item.pos() for key, item in canvas.items_by_id.items()}
    before = window.project.catalog.export_snapshot()
    records = window.project.catalog.records(include_archived=True)
    undo_count = len(window.commands.done)
    original = positions[identifier]
    QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=point)
    qt_app.processEvents()
    QTest.mouseMove(canvas.viewport(), point + delta, delay=10)
    qt_app.processEvents()
    QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=point + delta)
    qt_app.processEvents()
    layout = window.project.catalog.layout(identifier)
    assert layout["x"] == pytest.approx(original.x() + delta.x() / scale, abs=1 / scale)
    assert layout["y"] == pytest.approx(original.y() + delta.y() / scale, abs=1 / scale)
    assert {key: item.pos() for key, item in canvas.items_by_id.items() if key != identifier} \
        == {key: pos for key, pos in positions.items() if key != identifier}
    assert window.project.catalog.records(include_archived=True) == records
    assert len(window.commands.done) == undo_count + 1
    after = window.project.catalog.export_snapshot()
    window.undo(False)
    assert window.project.catalog.export_snapshot() == before
    window.undo(True)
    assert window.project.catalog.export_snapshot() == after
    window.open_project(window.project.catalog.path.parent)
    assert window.project.catalog.export_snapshot() == after


@pytest.mark.parametrize("source", ["tree", "search"])
def test_explicit_navigation_still_centers_the_target(window, qt_app, source):
    identifier, _ = prepare_target(window, qt_app, 1.0)
    canvas = window.canvas
    transform = canvas.viewportTransform()
    before = window.project.catalog.export_snapshot()
    if source == "tree":
        item = next(row for row in window.tree.findItems(
            "", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchRecursive,
        ) if row.data(0, Qt.ItemDataRole.UserRole) == identifier)
        window.tree.setCurrentItem(item)
    else:
        window.tasks.focus_requested.emit(identifier)
    qt_app.processEvents()
    assert window.selected_id == identifier
    assert canvas.viewportTransform() != transform
    item = canvas.items_by_id[identifier]
    center = canvas.mapFromScene(item.sceneBoundingRect().center())
    assert (center - canvas.viewport().rect().center()).manhattanLength() <= 2
    assert window.project.catalog.export_snapshot() == before


@pytest.mark.parametrize("answer", [QMessageBox.StandardButton.Cancel,
                                   QMessageBox.StandardButton.Save])
def test_dirty_note_guard_does_not_recenter_canvas_click(window, qt_app, monkeypatch, answer):
    previous = window.selected_id
    document = window.documents.create_document("Offener Entwurf")
    window.documents.editor.setPlainText("Nicht verlieren")
    window.tabs.setCurrentIndex(0)
    identifier, point = prepare_target(window, qt_app, 0.8)
    canvas = window.canvas
    positions = {key: item.pos() for key, item in canvas.items_by_id.items()}
    transform = canvas.viewportTransform()
    layouts = {key: window.project.catalog.layout(key) for key in positions}
    monkeypatch.setattr(QMessageBox, "question", lambda *args: answer)
    QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=point)
    qt_app.processEvents()
    QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=point)
    qt_app.processEvents()
    expected = previous if answer == QMessageBox.StandardButton.Cancel else identifier
    assert window.selected_id == expected
    assert canvas.items_by_id[expected].isSelected()
    assert canvas.viewportTransform() == transform
    assert {key: item.pos() for key, item in canvas.items_by_id.items()} == positions
    assert {key: window.project.catalog.layout(key) for key in positions} == layouts
    if answer == QMessageBox.StandardButton.Cancel:
        assert window.documents.dirty
        assert window.documents.editor.toPlainText() == "Nicht verlieren"
    else:
        assert window.project.catalog.get(document.id).data["body"] == "Nicht verlieren"
