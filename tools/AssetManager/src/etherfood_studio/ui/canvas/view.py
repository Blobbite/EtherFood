"""Lazy-detail card canvas, independent from asset and workflow revisions."""

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QFontMetricsF, QPainter, QPen, QWheelEvent
from PySide6.QtWidgets import (
    QGraphicsItem, QGraphicsRectItem, QGraphicsScene, QGraphicsSceneMouseEvent,
    QGraphicsSimpleTextItem, QGraphicsView,
)

from ...application.project_service import ProjectService
from ...application.status_service import StatusService
from .edges import edge_item

KIND_NAMES = {"project": "Projekt", "global": "Projektweit", "act": "Akt", "chapter": "Kapitel",
              "asset": "Asset", "package": "Paket", "note": "Notiz"}


class CardItem(QGraphicsRectItem):
    def __init__(self, identifier: str, title: str, kind: str, summary: str,
                 view: "Canvas", width: float = 250, height: float = 100) -> None:
        super().__init__(0, 0, width, height)
        self.identifier = identifier
        self.view = view
        self.before = QPointF()
        self.setData(0, identifier)
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable
                      | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setBrush(QColor("#e1eee7" if kind == "global" else "#ffffff"))
        self.setPen(QPen(QColor("#658076" if kind == "global" else "#b7c6d4"), 1.5))
        self.setToolTip(title + "\n" + summary)
        for text, y, color in ((KIND_NAMES[kind].upper(), 10, "#536d80"),
                               (title, 34, "#152a3d"), (summary, 65, "#765329")):
            child = QGraphicsSimpleTextItem(self)
            clipped = QFontMetricsF(child.font()).elidedText(
                text, Qt.TextElideMode.ElideRight, width - 24,
            )
            child.setText(clipped)
            child.setBrush(QColor(color))
            child.setPos(12, y)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.before = self.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        if self.pos() != self.before:
            self.view.moved.emit(self.identifier, self.pos().x(), self.pos().y())

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.view.toggle_requested.emit(self.identifier)
        event.accept()


class Canvas(QGraphicsView):
    selected = Signal(str)
    moved = Signal(str, float, float)
    toggle_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("project_canvas")
        self.setAccessibleName("Projektkarten; Doppelklick klappt Gruppen ein oder aus")
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QColor("#f0f4f7"))
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.items_by_id: dict[str, CardItem] = {}
        self.scene().selectionChanged.connect(self._selection)
        self.setMinimumWidth(300)

    def _selection(self) -> None:
        selected = self.scene().selectedItems()
        if selected:
            self.selected.emit(str(selected[0].data(0)))

    @staticmethod
    def default_positions(project: ProjectService) -> dict[str, dict]:
        cards = project.cards()
        positions = {}
        cursor = 0

        def arrange(identifier: str, depth: int) -> None:
            nonlocal cursor
            card = project.catalog.get(identifier)
            width = 650 if card.kind in {"global", "project"} else 250
            positions[identifier] = {"x": depth * 295, "y": cursor * 125, "w": width, "h": 100}
            cursor += 1
            children = [row for row in cards if row.owner_id == identifier]
            children.sort(key=lambda row: (
                row.kind != "global", row.data.get("order", 0), row.title,
            ))
            for child in children:
                arrange(child.id, depth + (0 if child.kind in {"global", "act"} else 1))

        arrange(project.project().id, 0)
        return positions

    def render(self, project: ProjectService, selected_id: str | None = None) -> None:
        self.scene().blockSignals(True)
        self.scene().clear()
        self.items_by_id.clear()
        defaults = self.default_positions(project)
        statuses = StatusService(project)
        cards = project.cards()
        hidden = set()
        for card in project.cards(include_archived=True):
            layout = project.catalog.layout(card.id)
            if card.archived or layout.get("collapsed"):
                keep = {card.id} if not card.archived else set()
                hidden.update(project.descendants(card.id) - keep)
        for card in cards:
            if card.id in hidden:
                continue
            layout = defaults.get(card.id, {"x": 0, "y": 0}) | project.catalog.layout(card.id)
            item = CardItem(card.id, card.title, card.kind, statuses.summary(card.id), self,
                            layout.get("w", 250), layout.get("h", 100))
            item.setPos(layout["x"], layout["y"])
            self.scene().addItem(item)
            self.items_by_id[card.id] = item
            if card.id == selected_id:
                item.setSelected(True)
        for edge in project.catalog.relations():
            source = self.items_by_id.get(edge["source_id"])
            target = self.items_by_id.get(edge["target_id"])
            if source is not None and target is not None:
                start = source.sceneBoundingRect().center()
                end = target.sceneBoundingRect().center()
                self.scene().addItem(edge_item(start, end, edge["kind"]))
        self.scene().setSceneRect(self.scene().itemsBoundingRect().adjusted(-60, -60, 100, 100))
        self.scene().blockSignals(False)

    def focus_card(self, identifier: str) -> None:
        item = self.items_by_id.get(identifier)
        if item is not None:
            self.scene().blockSignals(True)
            self.scene().clearSelection()
            item.setSelected(True)
            self.scene().blockSignals(False)
            self.centerOn(item)

    def zoom(self, factor: float) -> None:
        if 0.25 <= self.transform().m11() * factor <= 2.5:
            self.scale(factor, factor)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom(1.15 if event.angleDelta().y() > 0 else 1 / 1.15)
            event.accept()
        else:
            super().wheelEvent(event)
