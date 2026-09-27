"""Lazy-detail card canvas, independent from asset and workflow revisions."""

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor, QFocusEvent, QKeyEvent, QMouseEvent, QPainter, QPen, QResizeEvent, QWheelEvent,
)
from PySide6.QtWidgets import (
    QGraphicsPathItem, QGraphicsScene, QGraphicsView,
)

from ...application.project_service import ProjectService
from ...application.status_service import StatusService
from .edges import EdgeItem, curve, place_labels
from .items import CardItem, KIND_NAMES


class Canvas(QGraphicsView):
    EDGE_PEEK_PIXELS = 48.0

    selected = Signal(str)
    moved = Signal(str, float, float)
    toggle_requested = Signal(str)
    resized = Signal(str, float, float)
    connection_requested = Signal(str, str)
    reconnect_requested = Signal(str, str, str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("project_canvas")
        self.setAccessibleName("Projektkarten; Doppelklick klappt Gruppen ein oder aus")
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QColor("#f0f4f7"))
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.items_by_id: dict[str, CardItem] = {}
        self.edges_by_id: dict[str, EdgeItem] = {}
        self.label_rects = []
        self.rendering = False
        self._updating_bounds = False
        self._pan_anchor: QPointF | None = None
        self._pan_cursor = self.viewport().cursor()
        self.connection: tuple | None = None
        self.preview: QGraphicsPathItem | None = None
        self.scene().selectionChanged.connect(self._selection)
        self.setMinimumWidth(300)

    def _selection(self) -> None:
        self.update_edges()
        selected = [item for item in self.scene().selectedItems() if isinstance(item, CardItem)]
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
        self.rendering = True
        self.cancel_connection()
        self.scene().blockSignals(True)
        self.edges_by_id.clear()
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
                item = EdgeItem(edge, self)
                self.scene().addItem(item)
                self.edges_by_id[edge["id"]] = item
        self.rendering = False
        self.update_edges()
        self.scene().blockSignals(False)

    def content_rect(self) -> QRectF:
        """Only cards define the board; a dragged connection preview cannot grow it."""
        bounds = QRectF()
        for item in self.items_by_id.values():
            bounds = bounds.united(item.mapRectToScene(item.rect()))
        return bounds if not bounds.isEmpty() else QRectF(0, 0, 1, 1)

    def update_scene_rect(self) -> None:
        if self.rendering or self._updating_bounds:
            return
        self._updating_bounds = True
        try:
            inverse, invertible = self.transform().inverted()
            if not invertible:
                return
            viewport = inverse.mapRect(QRectF(self.viewport().rect()))
            peek = inverse.mapRect(QRectF(0, 0, self.EDGE_PEEK_PIXELS, self.EDGE_PEEK_PIXELS))
            horizontal = max(0.0, viewport.width() - peek.width())
            vertical = max(0.0, viewport.height() - peek.height())
            self.scene().setSceneRect(self.content_rect().adjusted(
                -horizontal, -vertical, horizontal, vertical,
            ))
        finally:
            self._updating_bounds = False

    def update_edges(self) -> None:
        if self.rendering:
            return
        for edge in self.edges_by_id.values():
            edge.update_geometry()
        self.label_rects = place_labels(list(self.edges_by_id.values()), [
            item.mapRectToScene(item.rect()).adjusted(-10, -10, 10, 10)
            for item in self.items_by_id.values()
        ])
        self.update_scene_rect()
        self.scene().update()

    def begin_connection(self, fixed_id: str, start: QPointF,
                         edge_id: str | None = None, moving: str = "target") -> None:
        self.cancel_connection()
        self.connection = (fixed_id, start, edge_id, moving)
        self.preview = QGraphicsPathItem()
        self.preview.setPen(QPen(QColor("#147fb0"), 2, Qt.PenStyle.DashLine))
        self.preview.setZValue(20)
        self.preview.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.scene().addItem(self.preview)
        self.update_connection(start)

    def update_connection(self, end: QPointF) -> None:
        if self.preview and self.connection:
            self.preview.setPath(curve(self.connection[1], end))

    def card_at(self, point: QPointF) -> CardItem | None:
        for item in self.scene().items(point):
            while item and not isinstance(item, CardItem):
                item = item.parentItem()
            if isinstance(item, CardItem):
                return item
        return None

    def finish_connection(self, point: QPointF) -> None:
        connection = self.connection
        card = self.card_at(point)
        self.cancel_connection()
        if not connection or not card:
            return
        fixed, _, edge_id, moving = connection
        source, target = ((card.identifier, fixed) if moving == "source"
                          else (fixed, card.identifier))
        if edge_id:
            self.reconnect_requested.emit(edge_id, source, target)
        else:
            self.connection_requested.emit(source, target)

    def cancel_connection(self) -> None:
        if self.preview:
            self.scene().removeItem(self.preview)
            self.preview = None
        self.connection = None

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape and self._pan_anchor is not None:
            self._stop_panning()
            event.accept()
        elif event.key() == Qt.Key.Key_Escape and self.connection:
            self.cancel_connection()
            event.accept()
        else:
            super().keyPressEvent(event)

    def focus_card(self, identifier: str, *, center: bool = True) -> None:
        item = self.items_by_id.get(identifier)
        if item is not None:
            self.scene().blockSignals(True)
            self.scene().clearSelection()
            item.setSelected(True)
            self.scene().blockSignals(False)
            self.update_edges()
            if center:
                self.centerOn(item)

    def zoom(self, factor: float) -> None:
        if 0.25 <= self.transform().m11() * factor <= 2.5:
            self.scale(factor, factor)
            self.update_scene_rect()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if hasattr(self, "items_by_id"):
            self.update_scene_rect()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_anchor = event.position()
            self._pan_cursor = self.viewport().cursor()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._pan_anchor is not None:
            if event.buttons() & Qt.MouseButton.MiddleButton:
                delta = event.position() - self._pan_anchor
                self._pan_anchor = event.position()
                horizontal, vertical = self.horizontalScrollBar(), self.verticalScrollBar()
                horizontal.setValue(horizontal.value() - round(delta.x()))
                vertical.setValue(vertical.value() - round(delta.y()))
                event.accept()
                return
            self._stop_panning()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton and self._pan_anchor is not None:
            self._stop_panning()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _stop_panning(self) -> None:
        if self._pan_anchor is not None:
            self._pan_anchor = None
            self.viewport().setCursor(self._pan_cursor)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        self._stop_panning()
        super().focusOutEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom(1.15 if event.angleDelta().y() > 0 else 1 / 1.15)
            event.accept()
        else:
            super().wheelEvent(event)
