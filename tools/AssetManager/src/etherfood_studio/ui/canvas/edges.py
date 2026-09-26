"""Typed edges, draggable endpoints and labels isolated from all visible strokes."""

from math import atan2, cos, sin
from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPainterPathStroker, QPen, QPolygonF
from PySide6.QtWidgets import (
    QGraphicsEllipseItem, QGraphicsItem, QGraphicsPathItem, QGraphicsRectItem,
    QGraphicsSceneMouseEvent, QGraphicsSimpleTextItem, QStyleOptionGraphicsItem, QWidget,
)

if TYPE_CHECKING:
    from .view import Canvas

EDGE_LABELS = {"belongs_to": "gehört zu", "uses": "verwendet", "depends_on": "benötigt"}


def curve(start: QPointF, end: QPointF) -> QPainterPath:
    path = QPainterPath(start)
    middle = (start.y() + end.y()) / 2
    path.cubicTo(QPointF(start.x(), middle), QPointF(end.x(), middle), end)
    return path


class Endpoint(QGraphicsEllipseItem):
    def __init__(self, edge: "EdgeItem", end: str) -> None:
        super().__init__(-7, -7, 14, 14)
        self.edge, self.end = edge, end
        self.setBrush(QColor("#fff1be"))
        self.setPen(QPen(QColor("#9c6420"), 2))
        self.setZValue(10)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setToolTip("Verbindungsende auf eine andere Karte ziehen")
        self.setVisible(False)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        edge = self.edge
        fixed = edge.target if self.end == "source" else edge.source
        point = edge.path().pointAtPercent(1 if self.end == "source" else 0)
        edge.view.begin_connection(fixed, point, edge.identifier, self.end)
        event.accept()

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.edge.view.update_connection(event.scenePos())
        event.accept()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.edge.view.finish_connection(event.scenePos())
        event.accept()


class EdgeLabel(QGraphicsRectItem):
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.scene().clearSelection()
        self.parentItem().setSelected(True)
        event.accept()


class EdgeItem(QGraphicsPathItem):
    def __init__(self, edge: dict, view: "Canvas") -> None:
        super().__init__()
        self.view = view
        self.identifier, self.kind = edge["id"], edge["kind"]
        self.source, self.target = edge["source_id"], edge["target_id"]
        color, style = {
            "belongs_to": ("#6b849c", Qt.PenStyle.SolidLine),
            "uses": ("#187e93", Qt.PenStyle.DashLine),
            "depends_on": ("#af5427", Qt.PenStyle.DotLine),
        }[self.kind]
        self.setPen(QPen(QColor(color), 2, style))
        self.setZValue(-1)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setToolTip(EDGE_LABELS[self.kind] + " · Anklicken, dann Endpunkt ziehen")
        self.caption = EdgeLabel(self)
        self.caption.setBrush(QColor("#ffffff"))
        self.caption.setPen(QPen(QColor(color), 0.6))
        self.caption.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.caption.setToolTip(self.set_edge_tooltip())
        text = QGraphicsSimpleTextItem(EDGE_LABELS[self.kind], self.caption)
        text.setBrush(QColor(color))
        text.setPos(5, 3)
        text.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.caption.setRect(text.boundingRect().adjusted(0, 0, 10, 6))
        self.handles = {end: Endpoint(self, end) for end in ("source", "target")}
        for handle in self.handles.values():
            view.scene().addItem(handle)

    def set_edge_tooltip(self) -> str:
        source = self.view.items_by_id[self.source].toolTip().split("\n")[0]
        target = self.view.items_by_id[self.target].toolTip().split("\n")[0]
        return f"{source} → {target}: {EDGE_LABELS[self.kind]}"

    def update_geometry(self) -> None:
        source, target = self.view.items_by_id[self.source], self.view.items_by_id[self.target]
        start_rect = source.mapRectToScene(source.rect())
        end_rect = target.mapRectToScene(target.rect())
        start = self.anchor(start_rect, end_rect.center())
        end = self.anchor(end_rect, start_rect.center())
        self.setPath(curve(start, end))
        self.handles["source"].setPos(self.anchor(start_rect, end_rect.center(), 18))
        self.handles["target"].setPos(self.anchor(end_rect, start_rect.center(), 18))
        self.caption.setBrush(QColor("#fff1be" if self.isSelected() else "#ffffff"))
        for side, handle in self.handles.items():
            handle.setVisible(self.isSelected() and not (
                self.kind == "belongs_to" and side == "source"))

    @staticmethod
    def anchor(rect: QRectF, toward: QPointF, offset: float = 0) -> QPointF:
        center = rect.center()
        dx, dy = toward.x() - center.x(), toward.y() - center.y()
        if abs(dx) / rect.width() > abs(dy) / rect.height():
            return QPointF(rect.right() + offset if dx >= 0 else rect.left() - offset, center.y())
        return QPointF(center.x(), rect.bottom() + offset if dy >= 0 else rect.top() - offset)

    def shape(self) -> QPainterPath:
        stroker = QPainterPathStroker()
        stroker.setWidth(12)
        return stroker.createStroke(self.path())

    def boundingRect(self) -> QRectF:
        return super().boundingRect().adjusted(-10, -10, 10, 10)

    def visible_stroke(self) -> QPainterPath:
        stroker = QPainterPathStroker()
        stroker.setWidth(4)
        path = stroker.createStroke(self.path())
        for rect in self.view.label_rects:
            mask = QPainterPath()
            mask.addRect(rect)
            path = path.subtracted(mask)
        return path

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem,
              widget: QWidget | None = None) -> None:
        painter.save()
        clip = QPainterPath()
        clip.addRect(self.boundingRect())
        for rect in self.view.label_rects:
            mask = QPainterPath()
            mask.addRect(rect)
            clip = clip.subtracted(mask)
        painter.setClipPath(clip, Qt.ClipOperation.IntersectClip)
        pen = QPen(self.pen())
        if self.isSelected():
            pen.setWidthF(3.5)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self.path())
        end, near = self.path().pointAtPercent(1), self.path().pointAtPercent(0.95)
        angle = atan2(end.y() - near.y(), end.x() - near.x())
        arrow = QPolygonF([end, end - QPointF(10 * cos(angle - .5), 10 * sin(angle - .5)),
                           end - QPointF(10 * cos(angle + .5), 10 * sin(angle + .5))])
        painter.setBrush(pen.color())
        painter.drawPolygon(arrow)
        painter.restore()


def place_labels(edges: list[EdgeItem], cards: list[QRectF]) -> list[QRectF]:
    """Prefer nearby clear space; mask every line as a final readability safeguard."""
    occupied = []
    strokes = [edge.shape() for edge in edges]
    right = max((rect.right() for rect in cards), default=0) + 30
    for edge in edges:
        size = edge.caption.rect().size()
        candidates = []
        for fraction in (.5, .35, .65, .2, .8):
            point = edge.path().pointAtPercent(fraction)
            for gap in (12, 32, 64):
                candidates.extend([
                    QPointF(point.x() - size.width() / 2, point.y() - size.height() - gap),
                    QPointF(point.x() - size.width() / 2, point.y() + gap),
                    QPointF(point.x() + gap, point.y() - size.height() / 2),
                    QPointF(point.x() - size.width() - gap, point.y() - size.height() / 2),
                ])
        position = None
        for avoid_lines in (True, False):
            for candidate in candidates:
                rect = QRectF(candidate, size).adjusted(-4, -4, 4, 4)
                if not any(rect.intersects(other) for other in cards + occupied) \
                        and (not avoid_lines or not any(path.intersects(rect) for path in strokes)):
                    position = candidate
                    break
            if position is not None:
                break
        if position is None:
            position = QPointF(right, 0)
            while any(QRectF(position, size).adjusted(-4, -4, 4, 4).intersects(other)
                      for other in occupied):
                position += QPointF(0, size.height() + 16)
        edge.caption.setPos(position)
        occupied.append(QRectF(position, size).adjusted(-4, -4, 4, 4))
    return occupied
