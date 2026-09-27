"""Grouped Kanban column; dragging requests a status change, never a tree move."""

from PySide6.QtCore import QMimeData, QSize, Qt, QTimer
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QAbstractItemView, QToolButton, QTreeWidget, QTreeWidgetItem

from ...application.kanban_service import TaskGroup
from ..appearance import appearance
from ..presentation import KIND_NAMES, kind_icon, record_icon, status_icon

TASK_ROLE = Qt.ItemDataRole.UserRole
GROUP_ROLE = Qt.ItemDataRole.UserRole + 1
MIME_TYPE = "application/x-etherfood-kanban-task"
PRIORITY_NAMES = {"low": "Niedrig", "normal": "Normal", "high": "Hoch", "critical": "Kritisch"}


class StatusHeader(QToolButton):
    """Allow dropping onto a collapsed status group as well as its task list."""

    def __init__(self, board, status: str) -> None:
        super().__init__()
        self.board, self.status = board, status
        self.setCheckable(True)
        self.setAcceptDrops(True)
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.setArrowType(Qt.DownArrow)

    def dragEnterEvent(self, event) -> None:
        self.board.columns[self.status].dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        self.dragEnterEvent(event)

    def dropEvent(self, event) -> None:
        if self.board.columns[self.status].accepts_drag(event):
            self.setChecked(True)
        self.board.columns[self.status].dropEvent(event)


class KanbanColumn(QTreeWidget):
    def __init__(self, board, status: str) -> None:
        super().__init__()
        self.board = board
        self.status = status
        self.items_by_id = {}
        self.groups = {}
        self.setObjectName("kanban_" + status)
        self.setHeaderHidden(True)
        self.setIndentation(12)
        self.setWordWrap(False)
        self.setMinimumWidth(140)
        self.setIconSize(QSize(40, 20))
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(False)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setStyleSheet(
            "QTreeWidget { border: 1px solid palette(mid); border-radius: 6px; }"
            "QTreeWidget::item { padding: 5px 2px; margin: 2px; border-radius: 4px; }"
            "QTreeWidget::item:selected { background: palette(highlight); "
            "color: palette(highlighted-text); }"
        )
        self.itemSelectionChanged.connect(lambda: board.select_item(self))
        self.itemDoubleClicked.connect(self._open)
        appearance().changed.connect(self.refresh_icons)

    def refresh_icons(self) -> None:
        for identifier, item in self.items_by_id.items():
            record = self.board.records.get(identifier)
            if record:
                item.setIcon(0, record_icon(record))
        for key, item in self.groups.items():
            if key[-1].startswith("kind:"):
                item.setIcon(0, status_icon(self.status, issue=key[-1] == "kind:issue"))

    def keyPressEvent(self, event) -> None:
        item = self.currentItem()
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter} \
                and item and item.data(0, TASK_ROLE):
            self.board.edit_current()
            event.accept()
            return
        super().keyPressEvent(event)

    def _open(self, item: QTreeWidgetItem, column: int = 0) -> None:
        if item.data(0, TASK_ROLE):
            self.board.edit_current()

    def fill(self, entries, selected: str | None) -> None:
        collapsed = {key for key, item in self.groups.items() if not item.isExpanded()}
        scroll = self.verticalScrollBar().value()
        self.blockSignals(True)
        self.clear()
        self.items_by_id.clear()
        self.groups.clear()
        for entry in entries:
            if entry.record.data["status"] != self.status:
                continue
            parent = self.invisibleRootItem()
            key = ()
            groups = (TaskGroup("kind:" + entry.record.kind,
                                "Issues" if entry.record.kind == "issue" else "Aufgaben",
                                entry.record.kind),) if self.board.compact else entry.groups
            for group in groups:
                key += (group.id,)
                if key not in self.groups:
                    title = (group.title if group.kind == "global" or group.id == "shared"
                             or group.id.startswith("kind:")
                             else KIND_NAMES[group.kind] + " · " + group.title)
                    item = QTreeWidgetItem(parent, [title])
                    item.setData(0, GROUP_ROLE, key)
                    item.setIcon(0, status_icon(self.status, issue=group.kind == "issue")
                                 if group.id.startswith("kind:") else kind_icon(group.kind))
                    item.setToolTip(0, title)
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    font = item.font(0)
                    font.setBold(True)
                    item.setFont(0, font)
                    item.setExpanded(key not in collapsed)
                    self.groups[key] = item
                parent = self.groups[key]
            record = entry.record
            todos = record.data.get("checklist", [])
            done = sum(todo["done"] for todo in todos)
            info = PRIORITY_NAMES[record.data["priority"]]
            if todos:
                info += f" · To-dos {done}/{len(todos)}"
            if record.data.get("approval_needed"):
                info += " · Abnahme"
            item = QTreeWidgetItem(parent, [f"{KIND_NAMES[record.kind]} · {record.title}\n{info}"])
            item.setIcon(0, record_icon(record))
            item.setData(0, TASK_ROLE, record.id)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                          | Qt.ItemFlag.ItemIsDragEnabled)
            item.setToolTip(0, record.title + "\n" + entry.location + "\n"
                            + (record.data.get("body", "")[:600] or "Keine Beschreibung."))
            self.items_by_id[record.id] = item
            if record.id == selected:
                self.setCurrentItem(item)
        # Qt may expand ancestors when restoring the selected child.
        for key in collapsed:
            if key in self.groups:
                self.groups[key].setExpanded(False)
        self.blockSignals(False)
        self.verticalScrollBar().setValue(scroll)

    def drag_mime(self, identifier: str) -> QMimeData:
        mime = QMimeData()
        mime.setData(MIME_TYPE, (self.board.drag_token + ":" + identifier).encode())
        return mime

    def startDrag(self, supported_actions) -> None:
        item = self.currentItem()
        identifier = item.data(0, TASK_ROLE) if item else None
        if identifier not in self.board.records:
            return
        # Keep the displayed revision: a parallel edit must reject this move.
        self.board.dragged_record = self.board.records[identifier]
        drag = QDrag(self)
        drag.setMimeData(self.drag_mime(identifier))
        try:
            drag.exec(Qt.DropAction.MoveAction)
        finally:
            self.board.dragged_record = None

    def accepts_drag(self, event) -> bool:
        record = self.board.dragged_record
        return bool(record and event.mimeData().hasFormat(MIME_TYPE)
                    and bytes(event.mimeData().data(MIME_TYPE))
                    == (self.board.drag_token + ":" + record.id).encode())

    def dragEnterEvent(self, event) -> None:
        if self.accepts_drag(event):
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        self.dragEnterEvent(event)

    def dropEvent(self, event) -> None:
        if not self.accepts_drag(event):
            event.ignore()
            return
        record = self.board.dragged_record
        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()
        # No QTreeWidget default move/removal: rebuild only from persisted data.
        QTimer.singleShot(0, lambda: self.board.apply_status(record, self.status))
