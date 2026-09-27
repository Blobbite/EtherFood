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
from ...domain.notes import NOTE_COLORS, is_note
from ..presentation import DOCUMENT_COLOR
from .edges import EdgeItem, curve, place_labels
from .items import CardItem, IconCardItem, KIND_NAMES


class Canvas(QGraphicsView):
    EDGE_PEEK_PIXELS = 48.0

    selected = Signal(str)
    open_requested = Signal(str)
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
        contents = [row for row in project.catalog.records()
                    if row.kind in {"task", "issue", "document"}]
        positions = {}
        cursor = 0

        def arrange(identifier: str, depth: int) -> None:
            nonlocal cursor
            card = project.catalog.get(identifier)
            width = 650 if card.kind in {"global", "project"} else 250
            positions[identifier] = {"x": depth * 295, "y": cursor, "w": width, "h": 100}
            if card.kind == "note":
                positions[identifier] |= {"w": 144, "h": 62}
            cursor += 125
            children = [row for row in cards if row.owner_id == identifier]
            children.sort(key=lambda row: (
                row.kind != "global", row.data.get("order", 0), row.title,
            ))
            for child in children:
                arrange(child.id, depth + (0 if child.kind in {"global", "act"} else 1))

        arrange(project.project().id, 0)
        occupied = []
        for card in cards:
            if card.id not in positions:
                continue
            value = positions[card.id] | project.catalog.layout(card.id)
            occupied.append(QRectF(value["x"], value["y"], value["w"], value["h"]))
        for record in contents:
            saved = project.catalog.layout(record.id)
            if "x" in saved and "y" in saved:
                occupied.append(QRectF(saved["x"], saved["y"], 144, 62))
        # Add small handles into free space without moving or covering existing cards.
        ordered = sorted(contents, key=lambda row: (row.owner_id, row.title.casefold(), row.id))
        for record in ordered:
            if record.owner_id not in positions:
                continue
            owner = positions[record.owner_id] | project.catalog.layout(record.owner_id)
            offset = 0
            while True:
                box = QRectF(owner["x"] + owner["w"] + 35 + offset % 4 * 170,
                             owner["y"] + offset // 4 * 80, 144, 62)
                if not any(box.adjusted(-10, -10, 10, 10).intersects(other)
                           for other in occupied):
                    break
                offset += 1
            positions[record.id] = {"x": box.x(), "y": box.y(), "w": 144, "h": 62}
            saved = positions[record.id] | project.catalog.layout(record.id)
            occupied.append(QRectF(saved["x"], saved["y"], 144, 62))
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
            if card.kind == "note":
                item = IconCardItem(card.id, card.title, "note", "Notizbereich öffnen", self,
                                    NOTE_COLORS["yellow"][1])
            else:
                item = CardItem(card.id, card.title, card.kind, statuses.summary(card.id), self,
                                layout.get("w", 250), layout.get("h", 100))
            item.setPos(layout["x"], layout["y"])
            self.scene().addItem(item)
            self.items_by_id[card.id] = item
            if card.id == selected_id:
                item.setSelected(True)
        content_edges = []
        for record in project.catalog.records():
            if record.kind not in {"task", "issue", "document"}:
                continue
            if record.owner_id not in self.items_by_id \
                    or project.catalog.layout(record.owner_id).get("collapsed"):
                continue
            note = is_note(record)
            color = DOCUMENT_COLOR if record.kind == "document" else "#e3effb"
            if note:
                color = NOTE_COLORS[record.data.get("note_color", "yellow")][1]
            summary = project.breadcrumb(record.owner_id)
            if record.kind in {"task", "issue"}:
                summary += "\nStatus: " + {"open": "Offen", "in_progress": "In Arbeit",
                    "blocked": "Blockiert", "done": "Erledigt"}[record.data["status"]]
            elif record.data.get("document_type") == "generated":
                summary += "\nBericht (nur lesen)"
            item = IconCardItem(record.id, record.title, "note" if note else record.kind,
                                summary, self, color)
            layout = defaults[record.id] | project.catalog.layout(record.id)
            item.setPos(layout["x"], layout["y"])
            self.scene().addItem(item)
            self.items_by_id[record.id] = item
            content_edges.append({"id": "content:" + record.id, "kind": "belongs_to",
                                  "source_id": record.id, "target_id": record.owner_id})
            if record.id == selected_id:
                item.setSelected(True)
        for edge in project.catalog.relations() + content_edges:
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
