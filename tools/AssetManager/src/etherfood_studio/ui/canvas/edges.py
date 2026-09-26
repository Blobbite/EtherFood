"""Typed connection rendering; crossings have no model semantics."""

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsSimpleTextItem

EDGE_LABELS = {
    "belongs_to": "gehört zu", "uses": "verwendet", "depends_on": "benötigt",
}


def edge_item(start: QPointF, end: QPointF, kind: str) -> QGraphicsPathItem:
    path = QPainterPath(start)
    middle = (start.y() + end.y()) / 2
    path.cubicTo(QPointF(start.x(), middle), QPointF(end.x(), middle), end)
    item = QGraphicsPathItem(path)
    color, style = {
        "belongs_to": ("#6b849c", Qt.PenStyle.SolidLine),
        "uses": ("#187e93", Qt.PenStyle.DashLine),
        "depends_on": ("#af5427", Qt.PenStyle.DotLine),
    }[kind]
    item.setPen(QPen(QColor(color), 2, style))
    item.setZValue(-1)
    item.setToolTip(EDGE_LABELS[kind])
    caption = QGraphicsSimpleTextItem(EDGE_LABELS[kind], item)
    caption.setBrush(QColor(color))
    caption.setPos((start + end) / 2)
    return item
