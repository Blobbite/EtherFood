"""Canvas cards with native pointer-driven size grips and four connection ports."""

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFontMetricsF, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsEllipseItem, QGraphicsItem, QGraphicsPixmapItem, QGraphicsRectItem,
    QGraphicsSceneMouseEvent,
    QGraphicsSimpleTextItem, QStyleOptionGraphicsItem, QWidget,
)

from ..presentation import KIND_NAMES, kind_icon, status_icon
from ..theme import color as theme_color, content_color

if TYPE_CHECKING:
    from .view import Canvas

class Port(QGraphicsEllipseItem):
    def __init__(self, card: "CardItem", side: str) -> None:
        super().__init__(-6, -6, 12, 12, card)
        self.card, self.side = card, side
        self.setBrush(QColor("#d6eff8"))
        self.setPen(QPen(QColor("#187e93"), 1.5))
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setToolTip("Auf eine Karte ziehen: verbinden · "
                        "Auf freie Fläche ziehen: zugeordneten Inhalt anlegen")
        self.setZValue(3)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.card.view.begin_connection(self.card.identifier, self.scenePos())
        event.accept()

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.card.view.update_connection(event.scenePos())
        event.accept()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.card.view.finish_connection(event.scenePos())
        event.accept()


class SizeGrip(QGraphicsRectItem):
    def __init__(self, card: "CardItem") -> None:
        super().__init__(-18, -18, 18, 18, card)
        self.card = card
        self.origin = QPointF()
        self.before = QPointF()
        self.setBrush(QColor("#dce6ef"))
        self.setPen(QPen(QColor("#536d80")))
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setToolTip("Kartengröße ziehen (nur Ansicht) · Strg+Z: rückgängig")
        mark = QGraphicsSimpleTextItem("◢", self)
        mark.setPos(-16, -20)
        mark.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setZValue(4)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.origin = event.scenePos()
        self.before = QPointF(self.card.rect().width(), self.card.rect().height())
        event.accept()

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        size = self.before + event.scenePos() - self.origin
        self.card.resize(max(200, min(1000, size.x())), max(100, min(400, size.y())))
        event.accept()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        size = self.card.rect().size()
        if QPointF(size.width(), size.height()) != self.before:
            self.card.view.resized.emit(self.card.identifier, size.width(), size.height())
        event.accept()


class CardItem(QGraphicsRectItem):
    CORNER_RADIUS = 10.0

    def __init__(self, identifier: str, title: str, kind: str, summary: str,
                 view: "Canvas", width: float = 250, height: float = 100) -> None:
        super().__init__(0, 0, width, height)
        self.identifier, self.view = identifier, view
        self.kind = kind
        self.before = QPointF()
        self.drag_origins = {}
        self.setData(0, identifier)
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable
                      | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
                      | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setBrush(QColor("#e1eee7" if kind == "global" else "#ffffff"))
        self.setPen(QPen(QColor("#658076" if kind == "global" else "#b7c6d4"), 1.5))
        self.setToolTip(title + "\n" + summary)
        self.icon = QGraphicsPixmapItem(kind_icon(kind).pixmap(16, 16), self)
        self.icon.setPos(12, 9)
        self.icon.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.texts = []
        for text, y, color in ((KIND_NAMES[kind].upper(), 10, "#536d80"),
                               (title, 34, "#152a3d"), (summary, 65, "#765329")):
            child = QGraphicsSimpleTextItem(self)
            child.setBrush(QColor(color))
            child.setPos(34 if y == 10 else 12, y)
            child.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.texts.append((child, text))
        self.ports = {side: Port(self, side) for side in ("top", "right", "bottom", "left")}
        self.grip = SizeGrip(self)
        self.apply_appearance()
        self.resize(width, height)

    def apply_appearance(self) -> None:
        special = self.kind in {"global", "project"}
        fill = theme_color(self.kind + "_card" if special else "base")
        if hasattr(self, "content_color"):
            fill = content_color(self.content_color)
        self.setBrush(QColor(fill))
        self.setPen(QPen(QColor(theme_color(
            self.kind + "_border" if special else "border")),
            3 if self.kind == "project" else 1.5))
        for (child, text), name in zip(self.texts, ("muted", "text", "warning_text")):
            child.setBrush(QColor(theme_color(name)))
        for port in self.ports.values():
            port.setBrush(QColor(theme_color("port")))
            port.setPen(QPen(QColor(theme_color("port_border")), 1.5))
        self.grip.setBrush(QColor(theme_color("alternate")))
        self.grip.setPen(QPen(QColor(theme_color("border"))))
        for mark in self.grip.childItems():
            mark.setBrush(QColor(theme_color("text")))
        if hasattr(self, "status") and self.kind in {"task", "issue"}:
            self.icon.setPixmap(status_icon(self.status, issue=self.kind == "issue").pixmap(
                52 if self.kind == "issue" else 26, 26))
        elif hasattr(self, "icon"):
            size = getattr(self, "icon_size", 26 if hasattr(self, "content_color") else 16)
            self.icon.setPixmap(kind_icon(self.kind).pixmap(size, size))

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addRoundedRect(self.rect(), self.CORNER_RADIUS, self.CORNER_RADIUS)
        return path

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem,
              widget: QWidget | None = None) -> None:
        painter.save()
        pen = QPen(self.pen())
        if self.isSelected():
            pen.setColor(QColor(theme_color("accent")))
        painter.setPen(pen)
        painter.setBrush(self.brush())
        painter.drawPath(self.shape())
        painter.restore()

    def resize(self, width: float, height: float) -> None:
        self.setRect(0, 0, width, height)
        for child, text in self.texts:
            child.setText("\n".join(QFontMetricsF(child.font()).elidedText(
                line, Qt.TextElideMode.ElideRight, width - child.pos().x() - 16,
            ) for line in text.splitlines()))
        for side, point in {"top": QPointF(width / 2, 0), "right": QPointF(width, height / 2),
                            "bottom": QPointF(width / 2, height),
                            "left": QPointF(0, height / 2)}.items():
            self.ports[side].setPos(point)
        self.grip.setPos(width - 5, height - 5)
        self.view.update_edges()

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: object) -> object:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.view.update_edges()
        return super().itemChange(change, value)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.before = self.pos()
        super().mousePressEvent(event)
        self.drag_origins = {key: self.view.items_by_id[key].pos()
                             for key in self.view.selected_ids()}

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        positions = {key: {"x": item.x(), "y": item.y()}
                     for key, before in self.drag_origins.items()
                     if (item := self.view.items_by_id.get(key)) is not None
                     and item.pos() != before}
        if len(positions) > 1:
            self.view.moved_many.emit(positions)
        elif self.pos() != self.before:
            self.view.moved.emit(self.identifier, self.pos().x(), self.pos().y())

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self.kind == "pipeline":
            self.view.open_requested.emit(self.identifier)
        else:
            self.view.toggle_requested.emit(self.identifier)
        event.accept()


class IconCardItem(CardItem):
    """Small content handle, not another workflow/asset card."""

    def __init__(self, identifier: str, title: str, kind: str, summary: str,
                 view: "Canvas", color: str = "#e3effb", status: str = "open") -> None:
        super().__init__(identifier, title, kind, summary, view, 144, 62)
        self.kind = kind
        self.content_color = color
        self.status = status
        self.grip.hide()
        self.setBrush(QColor(color))
        icon = status_icon(status, issue=kind == "issue") if kind in {"task", "issue"} \
            else kind_icon(kind)
        self.icon.setPixmap(icon.pixmap(52 if kind == "issue" else 26, 26))
        self.icon.setPos(10, 17)
        self.texts[0][0].setPos(69 if kind == "issue" else 45, 9)
        self.texts[1][0].setPos(69 if kind == "issue" else 45, 30)
        self.texts[2][0].hide()
        self.resize(144, 62)
        self.apply_appearance()
        self.setToolTip(title + "\n" + summary + "\nDoppelklick: öffnen · Port ziehen: zuordnen")

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.view.open_requested.emit(self.identifier)
        event.accept()

    def resize(self, width, height):
        super().resize(144, 62)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        clicked = self.pos() == self.before
        super().mouseReleaseEvent(event)
        if clicked and event.button() == Qt.LeftButton and self.kind == "note" \
                and len(self.view.selected_ids()) == 1 \
                and not event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.view.open_requested.emit(self.identifier)


class ProjectItem(CardItem):
    """Stable visual root, independent of historic user-resized card dimensions."""

    WIDTH, HEIGHT = 520, 140

    def __init__(self, identifier, title, summary, view):
        super().__init__(identifier, title, "project", summary, view, self.WIDTH, self.HEIGHT)
        self.grip.hide()
        font = self.texts[1][0].font()
        font.setPointSizeF(font.pointSizeF() + 4)
        font.setBold(True)
        self.texts[1][0].setFont(font)
        self.texts[2][0].setPos(12, 92)
        self.resize(self.WIDTH, self.HEIGHT)

    def resize(self, width, height):
        super().resize(self.WIDTH, self.HEIGHT)


class WorkflowIconItem(CardItem):
    """Large asset or output symbol with four usable connection points."""

    WIDTH, HEIGHT = 200, 140

    def __init__(self, identifier, title, kind, summary, view):
        self.icon_size = 48
        super().__init__(identifier, title, kind, summary, view, self.WIDTH, self.HEIGHT)
        self.grip.hide()
        self.icon.setPos(76, 12)
        self.texts[0][0].hide()
        self.texts[1][0].setPos(12, 72)
        self.texts[2][0].setPos(12, 105)
        self.resize(self.WIDTH, self.HEIGHT)

    def resize(self, width, height):
        super().resize(self.WIDTH, self.HEIGHT)

    def mouseDoubleClickEvent(self, event):
        self.view.open_requested.emit(self.identifier)
        event.accept()
