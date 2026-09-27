"""Canvas creation at free endpoints, true multi-selection and reversible arrangements."""

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QPoint, QPointF, QSettings, Qt, QTimer
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication, QInputDialog

from etherfood_studio.ui.main_window import MainWindow


@pytest.fixture
def window(tmp_path, qt_app):
    value = MainWindow(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat))
    root = tmp_path / "project"
    root.mkdir()
    value.new_project(root, "Canvas-Werkzeuge")
    value.ids = value.project.demo()
    value.refresh()
    value.show()
    qt_app.processEvents()
    yield value
    value.documents.dirty = False
    for _, card in value.notes._cards():
        card.dirty = False
        card.timer.stop()
    value.close()
    qt_app.processEvents()


@pytest.mark.parametrize("scale", [0.3, 1.0, 2.5])
def test_real_port_drag_to_empty_emits_scene_position_and_reconnect_does_not_create(
        window, qt_app, scale):
    canvas = window.canvas
    canvas.create_requested.disconnect(window.canvas_actions.create_at)
    window.commands.layout(window.ids["one"], {"x": 2500, "y": 0})
    window.refresh()
    source = canvas.items_by_id[window.ids["one"]]
    canvas.zoom(scale / canvas.transform().m11())
    canvas.centerOn(source)
    qt_app.processEvents()
    start = canvas.mapFromScene(source.ports["left"].scenePos())
    end = start - QPoint(65, 45)
    expected = canvas.mapToScene(end)
    assert canvas.card_at(expected) is None
    created = QSignalSpy(canvas.create_requested)
    QTest.mousePress(canvas.viewport(), Qt.LeftButton, pos=start)
    QTest.mouseMove(canvas.viewport(), end, delay=10)
    QTest.mouseRelease(canvas.viewport(), Qt.LeftButton, pos=end)
    assert created.count() == 1
    assert created.at(0)[0] == source.identifier
    assert created.at(0)[1:] == pytest.approx([expected.x(), expected.y()], abs=1 / scale)
    canvas.begin_connection(source.identifier, source.pos(), "existing-edge")
    canvas.finish_connection(expected)
    assert created.count() == 1
    canvas.begin_connection(source.identifier, source.pos())
    QTest.keyClick(canvas, Qt.Key_Escape)
    canvas.finish_connection(expected)
    assert created.count() == 1


@pytest.mark.parametrize("cancel", ["menu", "title", None])
def test_endpoint_menu_creates_or_cancels_one_linked_note(window, qt_app, monkeypatch, cancel):
    source = window.project.catalog.get(window.ids["one"])
    before = window.project.catalog.export_snapshot()
    count = len(window.commands.done)

    def choose():
        menu = QApplication.activePopupWidget()
        names = {a.objectName() for a in menu.actions()}
        assert "canvas_create_asset" in names and "canvas_create_note" in names
        assert "canvas_create_act" not in names  # No invalid hierarchy offered.
        if cancel == "menu":
            QTest.keyClick(menu, Qt.Key_Escape)
        else:
            menu.setActiveAction(next(a for a in menu.actions()
                                      if a.objectName() == "canvas_create_note"))
            QTest.keyClick(menu, Qt.Key_Return)

    QTimer.singleShot(0, choose)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a: ("Direkt verbunden", cancel != "title"))
    window.canvas_actions.create_at(source.id, 4000, -230)
    if cancel:
        assert window.project.catalog.export_snapshot() == before
        assert len(window.commands.done) == count
        return
    record = next(r for r in window.project.catalog.records() if r.title == "Direkt verbunden")
    assert record.owner_id == source.id
    assert window.canvas.items_by_id[record.id].pos() == QPointF(4000, -230)
    assert "content:" + record.id in window.canvas.edges_by_id
    assert len(window.commands.done) == count + 1
    window.undo(False)
    assert record.id not in window.canvas.items_by_id
    window.undo(True)
    assert window.canvas.items_by_id[record.id].pos() == QPointF(4000, -230)


@pytest.mark.parametrize("scale", [0.3, 1.0, 2.5])
def test_ctrl_selection_and_group_drag_persist_all_positions_once(window, qt_app, scale):
    canvas = window.canvas
    identifiers = [window.ids["one"], window.ids["two"]]
    window.commands.layouts({identifiers[0]: {"x": 2000, "y": 0},
                             identifiers[1]: {"x": 2000, "y": 140}})
    window.refresh()
    canvas.zoom(scale / canvas.transform().m11())
    canvas.centerOn(QPointF(2125, 110))
    qt_app.processEvents()
    points = [canvas.mapFromScene(canvas.items_by_id[key].mapToScene(QPointF(50, 35)))
              for key in identifiers]
    QTest.mouseClick(canvas.viewport(), Qt.LeftButton, pos=points[0])
    qt_app.processEvents()
    QTest.mouseClick(canvas.viewport(), Qt.LeftButton, Qt.ControlModifier, points[1])
    qt_app.processEvents()
    assert canvas.selected_ids() == set(identifiers)
    before = window.project.catalog.export_snapshot()
    count = len(window.commands.done)
    records = window.project.catalog.records()
    start, delta = points[0], QPoint(17, 13)
    QTest.mousePress(canvas.viewport(), Qt.LeftButton, pos=start)
    qt_app.processEvents()
    QTest.mouseMove(canvas.viewport(), start + delta, delay=10)
    QTest.mouseRelease(canvas.viewport(), Qt.LeftButton, pos=start + delta)
    qt_app.processEvents()
    assert len(window.commands.done) == count + 1
    for key, y in zip(identifiers, [0, 140]):
        layout = window.project.catalog.layout(key)
        assert layout["x"] == pytest.approx(2000 + delta.x() / scale, abs=1 / scale)
        assert layout["y"] == pytest.approx(y + delta.y() / scale, abs=1 / scale)
    assert window.project.catalog.records() == records
    after = window.project.catalog.export_snapshot()
    window.undo(False)
    assert window.project.catalog.export_snapshot() == before
    window.undo(True)
    assert window.project.catalog.export_snapshot() == after


@pytest.mark.parametrize("mode", ["circle", "line"])
def test_arrangement_changes_only_selected_peers_preserves_anchor_zoom_and_undo(window, mode):
    canvas = window.canvas
    selected = {window.ids[key] for key in ("one", "two", "hero", "temple")}
    canvas.select_many(selected)
    canvas.zoom(0.8 / canvas.transform().m11())
    before = window.project.catalog.export_snapshot()
    positions = {key: item.pos() for key, item in canvas.items_by_id.items()}
    count = len(window.commands.done)
    anchor = window.ids["one"]
    menu = window.navigation.menu(anchor)
    submenu = next(action.menu() for action in menu.actions()
                   if action.text() == "Auswahl anordnen")
    next(a for a in submenu.actions() if a.objectName() == "canvas_arrange_" + mode).trigger()
    assert len(window.commands.done) == count + 1
    assert canvas.transform().m11() == 0.8 and canvas.selected_ids() == selected
    assert canvas.items_by_id[anchor].pos() == positions[anchor]
    assert all(canvas.items_by_id[key].pos() == point for key, point in positions.items()
               if key not in selected)
    boxes = [canvas.items_by_id[key].sceneBoundingRect() for key in selected]
    assert not any(a.intersects(b) for i, a in enumerate(boxes) for b in boxes[i + 1:])
    after = window.project.catalog.export_snapshot()
    window.undo(False)
    assert window.project.catalog.export_snapshot() == before
    window.undo(True)
    assert window.project.catalog.export_snapshot() == after
    menu.deleteLater()
