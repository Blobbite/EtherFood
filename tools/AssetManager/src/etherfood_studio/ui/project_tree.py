"""Internal, validated tree drag/drop with autoscroll and hover expansion."""

from PySide6.QtCore import QMimeData, QModelIndex, QPersistentModelIndex, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QPainter, QPen
from PySide6.QtWidgets import QAbstractItemView, QTreeWidget

from ..application.tree_service import TreeService
from ..domain.models import StudioError, new_id

ID_ROLE = Qt.ItemDataRole.UserRole
KIND_ROLE = Qt.ItemDataRole.UserRole + 1
EDGE_ROLE = Qt.ItemDataRole.UserRole + 2
TREE_MIME = "application/x-etherfood-project-tree"


class ProjectTree(QTreeWidget):
    drop_requested = Signal(object, str, bool)

    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        self.dragged = None
        self.token = new_id()
        self.hover_index = QPersistentModelIndex()
        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.setInterval(650)
        self.hover_timer.timeout.connect(self.expand_hover)
        self.scroll_direction = 0
        self.scroll_timer = QTimer(self)
        self.scroll_timer.setInterval(70)
        self.scroll_timer.timeout.connect(self.scroll_drag)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        # Qt's default model rejects our private MIME before its convenience timers run.
        self.setAutoScroll(False)
        self.setAutoExpandDelay(-1)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setToolTip("Auf Zielkarte ziehen: zuordnen · Strg+Ziehen: Asset verwenden · "
                        "Verweis ziehen: nur Verwendung verschieben · Strg+Z: rückgängig")

    def drag_mime(self) -> QMimeData:
        mime = QMimeData()
        mime.setData(TREE_MIME, self.token.encode())
        return mime

    def startDrag(self, supported_actions) -> None:
        item = self.currentItem()
        if not item or not self.window.project:
            return
        identifier, edge_id = item.data(0, ID_ROLE), item.data(0, EDGE_ROLE)
        if not identifier or not self.window.prepare_content_change():
            return
        try:
            self.dragged = TreeService(self.window.commands).capture(identifier, edge_id)
            drag = QDrag(self)
            drag.setMimeData(self.drag_mime())
            drag.exec(Qt.DropAction.MoveAction | Qt.DropAction.CopyAction,
                      Qt.DropAction.MoveAction)
        except StudioError as error:
            self.window.statusBar().showMessage(str(error), 7000)
        finally:
            self.clear_hover()
            self.dragged = None

    def clear_hover(self) -> None:
        self.hover_timer.stop()
        self.scroll_timer.stop()
        self.hover_index = QPersistentModelIndex()
        self.viewport().update()

    def expand_hover(self) -> None:
        if self.dragged and self.hover_index.isValid():
            item = self.itemFromIndex(QModelIndex(self.hover_index))
            item.setExpanded(True)

    def scroll_drag(self) -> None:
        if self.dragged:
            bar = self.verticalScrollBar()
            before = bar.value()
            bar.setValue(bar.value() + self.scroll_direction * max(1, bar.singleStep()))
            if bar.value() != before:
                self.hover_timer.stop()
                self.hover_index = QPersistentModelIndex()
                self.viewport().update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self.dragged and self.hover_index.isValid():
            painter = QPainter(self.viewport())
            painter.setPen(QPen(QColor("#2472ab"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.visualRect(QModelIndex(self.hover_index)).adjusted(1, 1, -2, -2))
            painter.end()

    def target(self, event):
        if not self.dragged or not event.mimeData().hasFormat(TREE_MIME) \
                or bytes(event.mimeData().data(TREE_MIME)) != self.token.encode():
            raise StudioError("validation", "Nur Inhalte aus diesem Projektbaum hier zuordnen.")
        item = self.itemAt(event.position().toPoint())
        if not item:
            raise StudioError("validation", "Direkt auf die gewünschte Zielkarte ziehen.")
        target_id = item.data(0, ID_ROLE)
        copy = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        TreeService(self.window.commands).validate(self.dragged, target_id, copy)
        return target_id, copy

    def dragEnterEvent(self, event) -> None:
        if self.dragged and event.mimeData().hasFormat(TREE_MIME) \
                and bytes(event.mimeData().data(TREE_MIME)) == self.token.encode():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        y = event.position().y()
        self.scroll_direction = -1 if y < 24 else (1 if y > self.viewport().height() - 24 else 0)
        if self.scroll_direction and self.dragged:
            if not self.scroll_timer.isActive():
                self.scroll_timer.start()
        else:
            self.scroll_timer.stop()
        try:
            target, copy = self.target(event)
            index = QPersistentModelIndex(self.indexAt(event.position().toPoint()))
            if index != self.hover_index:
                self.hover_index = index
                self.hover_timer.start()
            self.viewport().update()
            event.setDropAction(Qt.DropAction.CopyAction if copy else Qt.DropAction.MoveAction)
            event.accept()
        except StudioError as error:
            self.hover_timer.stop()
            self.hover_index = QPersistentModelIndex()
            self.viewport().update()
            event.ignore()
            self.window.statusBar().showMessage(str(error), 3000)

    def dragLeaveEvent(self, event) -> None:
        self.clear_hover()
        event.accept()

    def dropEvent(self, event) -> None:
        self.clear_hover()
        try:
            target, copy = self.target(event)
            event.setDropAction(Qt.DropAction.CopyAction if copy else Qt.DropAction.MoveAction)
            event.accept()
            self.drop_requested.emit(self.dragged, target, copy)
        except StudioError as error:
            event.ignore()
            self.window.statusBar().showMessage(str(error), 7000)


def populate_project_tree(window):
    """One ownership tree plus explicit references; inactive roots occur only once."""
    from datetime import datetime
    from PySide6.QtWidgets import QTreeWidgetItem
    from ..application.lifecycle_service import LifecycleService
    from ..application.search_service import SearchService
    from ..domain.relations import CARD_KINDS
    from .presentation import KIND_NAMES, record_icon

    tree, project = window.tree, window.project
    tree.clear()
    states = SearchService(project)
    life = LifecycleService(project)
    records = {r.id: r for r in project.catalog.records(include_archived=True)}
    originals = QTreeWidgetItem(tree, ["Projektinhalte"])
    references = QTreeWidgetItem(tree, ["Verwendungen"])
    storage = QTreeWidgetItem(
        tree,
        [
            (
                "Archiv"
                if window.project_archive_view.currentData() == "archived"
                else "Papierkorb · 30 Tage"
            )
        ],
    )
    items = {}

    def item(parent, record, *, edge=None):
        node = QTreeWidgetItem(parent, [record.title])
        node.setData(0, ID_ROLE, record.id)
        node.setData(0, KIND_ROLE, record.kind)
        node.setData(0, EDGE_ROLE, edge)
        node.setIcon(0, record_icon(record))
        node.setToolTip(0, KIND_NAMES.get(record.kind, record.kind))
        if edge:
            relation = next(
                e for e in project.catalog.relations(include_inactive=True) if e["id"] == edge
            )
            node.setText(0, record.title + " · " + records[relation["source_id"]].title)
        return node

    def add(identifier):
        if identifier in items:
            return items[identifier]
        record = records[identifier]
        if states.state(record) != "active":
            return None
        if record.kind == "pipeline_usage":
            parent = references
        elif record.owner_id in records and records[record.owner_id].kind in CARD_KINDS:
            parent = add(record.owner_id)
        else:
            parent = originals
        if parent is None:
            return None
        node = item(parent, record)
        items[identifier] = node
        node.setExpanded(not project.catalog.layout(identifier).get("collapsed", False))
        return node

    for record in records.values():
        if record.kind in CARD_KINDS | {"document", "task", "issue"}:
            # Migrated definition documents remain available in the documentation view.
            if (
                record.owner_id in records
                and records[record.owner_id].kind == "pipeline_definition"
            ):
                continue
            add(record.id)
    for edge in project.catalog.relations():
        if edge["kind"] == "uses" and all(
            states.state(records[edge[key]]) == "active" for key in ("source_id", "target_id")
        ):
            item(references, records[edge["target_id"]], edge=edge["id"])
    original_storage = QTreeWidgetItem(storage, ["Projektinhalte"])
    reference_storage = QTreeWidgetItem(storage, ["Verwendungen"])
    state = window.project_archive_view.currentData()
    for entry in life.entries(state):
        key = entry["id"]
        if entry["entity_kind"] == "reference":
            edge = life._edge(key)
            node = item(reference_storage, records[edge["target_id"]], edge=key)
        elif key in records and records[key].kind not in {"script", "pipeline_definition"}:
            row = records[key]
            ancestor = row.owner_id
            while ancestor and ancestor in records and not life.state(ancestor):
                ancestor = records[ancestor].owner_id
            if ancestor and life.state(ancestor):
                continue
            node = item(
                reference_storage if row.kind == "pipeline_usage" else original_storage, row
            )
        else:
            continue
        if entry["purge_at"]:
            deadline = (
                datetime.fromisoformat(entry["purge_at"]).astimezone().strftime("%d.%m.%Y %H:%M %Z")
            )
            node.setToolTip(0, "Endgültige Bereinigung ab " + deadline)
    originals.setExpanded(True)
    references.setExpanded(True)
    storage.setExpanded(True)
    original_storage.setExpanded(True)
    reference_storage.setExpanded(True)
    for key, node in items.items():
        if key == (window.selected_content_id or window.selected_id):
            tree.setCurrentItem(node)
