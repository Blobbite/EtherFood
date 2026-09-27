"""Rounded cards and bounded, viewport-sized panning using actual Qt events."""

import math

import pytest

pytest.importorskip("PySide6.QtWidgets", reason="GUI-Abhängigkeiten fehlen")

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QStyleOptionGraphicsItem

from etherfood_studio.ui.canvas.items import CardItem
from etherfood_studio.ui.canvas.view import Canvas


@pytest.fixture
def canvas(qt_app):
    view = Canvas()
    view.resize(900, 650)
    view.show()
    card = CardItem("card", "Testkarte", "asset", "Nicht abgenommen", view, 250, 130)
    view.scene().addItem(card)
    view.items_by_id[card.identifier] = card
    card.setPos(-120, 80)
    view.update_edges()
    qt_app.processEvents()
    view.focus_card(card.identifier)
    yield view
    view.close()
    view.deleteLater()
    qt_app.processEvents()


def visible_rect(canvas):
    return canvas.mapToScene(canvas.viewport().rect()).boundingRect()


def assert_edge_limits(canvas):
    content = canvas.content_rect()
    scale = canvas.transform().m11()
    peek = canvas.EDGE_PEEK_PIXELS / scale
    tolerance = 3 / scale
    horizontal, vertical = canvas.horizontalScrollBar(), canvas.verticalScrollBar()
    assert horizontal.maximum() > horizontal.minimum()
    assert vertical.maximum() > vertical.minimum()
    horizontal.setValue(horizontal.minimum())
    assert visible_rect(canvas).right() - content.left() == pytest.approx(peek, abs=tolerance)
    horizontal.setValue(horizontal.maximum())
    assert content.right() - visible_rect(canvas).left() == pytest.approx(peek, abs=tolerance)
    vertical.setValue(vertical.minimum())
    assert visible_rect(canvas).bottom() - content.top() == pytest.approx(peek, abs=tolerance)
    vertical.setValue(vertical.maximum())
    assert content.bottom() - visible_rect(canvas).top() == pytest.approx(peek, abs=tolerance)


def test_rounded_paint_shape_selection_and_inset_grip(canvas):
    card = canvas.items_by_id["card"]
    rect = card.rect()
    for point in (rect.topLeft() + QPointF(1, 1), rect.topRight() + QPointF(-1, 1),
                  rect.bottomLeft() + QPointF(1, -1), rect.bottomRight() + QPointF(-1, -1)):
        assert not card.shape().contains(point)
    assert card.shape().contains(rect.center())
    assert card.shape().contains(QPointF(rect.center().x(), 1))

    def paint(selected):
        card.setSelected(selected)
        image = QImage(254, 134, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.translate(2, 2)
        card.paint(painter, QStyleOptionGraphicsItem())
        painter.end()
        return image

    normal, selected = paint(False), paint(True)
    assert normal.pixelColor(2, 2).alpha() == 0
    assert normal.pixelColor(40, 40).name() == "#ffffff"
    assert selected.pixelColor(40, 2) != normal.pixelColor(40, 2)
    card.resize(400, 180)
    assert card.grip.pos() == QPointF(395, 175)
    assert card.ports["right"].pos() == QPointF(400, 90)
    assert not card.shape().contains(QPointF(399, 179))


@pytest.mark.parametrize("scale", [0.25, 0.8, 1.0, 2.5])
def test_pan_to_all_edges_after_zoom_and_window_resize(canvas, qt_app, scale):
    canvas.zoom(scale)
    qt_app.processEvents()
    assert_edge_limits(canvas)
    canvas.resize(1100, 780)
    qt_app.processEvents()
    assert_edge_limits(canvas)
    assert all(math.isfinite(v) for v in canvas.sceneRect().getRect())


def test_middle_drag_over_card_moves_only_view_and_is_bounded(canvas, qt_app):
    card = canvas.items_by_id["card"]
    original_position = card.pos()
    moved, selected = QSignalSpy(canvas.moved), QSignalSpy(canvas.selected)
    scene_rect = canvas.sceneRect()
    before = visible_rect(canvas).center()
    start = canvas.mapFromScene(card.mapToScene(card.rect().center()))
    end = start + QPoint(130, 90)
    QTest.mousePress(canvas.viewport(), Qt.MouseButton.MiddleButton, pos=start)
    QTest.mouseMove(canvas.viewport(), end, delay=10)
    QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.MiddleButton, pos=end)
    qt_app.processEvents()
    offset = visible_rect(canvas).center() - before
    assert offset.x() == pytest.approx(-130, abs=2)
    assert offset.y() == pytest.approx(-90, abs=2)
    assert card.pos() == original_position and moved.count() == selected.count() == 0
    assert canvas._pan_anchor is None
    for _ in range(5):
        assert_edge_limits(canvas)
        assert canvas.sceneRect() == scene_rect
    horizontal = canvas.horizontalScrollBar()
    horizontal.setValue(horizontal.maximum())
    start = canvas.viewport().rect().center()
    QTest.mousePress(canvas.viewport(), Qt.MouseButton.MiddleButton, pos=start)
    QTest.mouseMove(canvas.viewport(), start - QPoint(100, 0), delay=10)
    QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.MiddleButton,
                       pos=start - QPoint(100, 0))
    assert horizontal.value() == horizontal.maximum()
    assert canvas.sceneRect() == scene_rect


def test_card_changes_update_limits_but_preview_and_pan_do_not(canvas, qt_app):
    card = canvas.items_by_id["card"]
    original = canvas.sceneRect()
    card.setPos(2200, -1600)
    qt_app.processEvents()
    assert canvas.sceneRect() != original
    card.resize(500, 250)
    assert_edge_limits(canvas)
    before = canvas.sceneRect()
    canvas.begin_connection(card.identifier, card.scenePos())
    canvas.update_connection(QPointF(1000000, 1000000))
    canvas.update_scene_rect()
    assert canvas.sceneRect() == before
    canvas.cancel_connection()
    second = CardItem("second", "Zweite Karte", "asset", "Offen", canvas)
    canvas.scene().addItem(second)
    canvas.items_by_id[second.identifier] = second
    second.setPos(-5000, 4000)
    canvas.update_edges()
    assert canvas.content_rect().contains(card.sceneBoundingRect().center())
    assert canvas.content_rect().contains(second.sceneBoundingRect().center())
    assert_edge_limits(canvas)
    canvas.items_by_id.pop(second.identifier)
    canvas.scene().removeItem(second)
    canvas.update_edges()
    assert canvas.sceneRect() == before


def test_empty_board_and_escape_end_panning(qt_app):
    canvas = Canvas()
    canvas.resize(800, 600)
    canvas.show()
    qt_app.processEvents()
    canvas.update_scene_rect()
    before = canvas.sceneRect()
    assert not before.isEmpty()
    assert_edge_limits(canvas)
    point = canvas.viewport().rect().center()
    QTest.mousePress(canvas.viewport(), Qt.MouseButton.MiddleButton, pos=point)
    QTest.keyClick(canvas, Qt.Key.Key_Escape)
    assert canvas._pan_anchor is None
    QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.MiddleButton, pos=point)
    assert canvas.sceneRect() == before
    canvas.close()
    canvas.deleteLater()
