"""A free-positioned post-it board; dragging its handles never edits note contents."""

from PySide6.QtCore import QEvent, QPoint, QSize, Qt, Signal
from PySide6.QtWidgets import QApplication, QListView, QListWidget

from ..domain.notes import NOTE_POSITION_LIMIT
from .appearance import appearance
from .theme import color

POSITION_ROLE = Qt.UserRole + 2
BOARD_COLOR = "#c5b493"


class NoteBoard(QListWidget):
    moved = Signal(object, object, object)

    def __init__(self, *, stacked: bool = False) -> None:
        super().__init__()
        self.free = not stacked
        self._handles = {}
        self._drag = None
        self._extent = QSize(800, 600)
        self.setObjectName("notes_board")
        self.setViewMode(QListView.IconMode)
        self.setResizeMode(QListView.Fixed if self.free else QListView.Adjust)
        self.setMovement(QListView.Free if self.free else QListView.Static)
        self.setDragEnabled(False)
        self.setAcceptDrops(False)
        self.setFlow(QListView.TopToBottom if stacked else QListView.LeftToRight)
        self.setWrapping(not stacked)
        self.setGridSize(QSize(334, 284))
        self.setSpacing(4)
        appearance().changed.connect(self.apply_appearance)
        self.apply_appearance()
        self.setHorizontalScrollMode(QListView.ScrollPerPixel)
        self.setVerticalScrollMode(QListView.ScrollPerPixel)

    def apply_appearance(self) -> None:
        self.setStyleSheet(f"QListWidget#notes_board {{ background: {color('board')}; "
                           f"border: 1px solid {color('board_border')}; border-radius: 8px; }}"
                           "QListWidget::item:selected { background: transparent; }")

    def attach_handle(self, item, handle) -> None:
        handle.setVisible(self.free)
        if self.free:
            self._handles[handle] = item
            handle.setFocusPolicy(Qt.StrongFocus)
            handle.installEventFilter(self)

    def detach_handle(self, handle) -> None:
        handle.removeEventFilter(self)
        self._handles.pop(handle, None)
        if self._drag and self._drag[0] is handle:
            self._drag = None

    def reset_extent(self) -> None:
        self._extent = QSize(800, 600)
        self.horizontalScrollBar().setValue(0)
        self.verticalScrollBar().setValue(0)

    def position(self, item) -> QPoint:
        point = item.data(POSITION_ROLE)
        return point if point is not None else QPoint(16, 16)

    def place_item(self, item, point: QPoint) -> None:
        point = QPoint(max(0, min(NOTE_POSITION_LIMIT, point.x())),
                       max(0, min(NOTE_POSITION_LIMIT, point.y())))
        if item.data(POSITION_ROLE) != point:
            item.setData(POSITION_ROLE, point)
        self.setPositionForIndex(point, self.indexFromItem(item))
        self.updateEditorGeometries()
        self.updateGeometries()

    def doItemsLayout(self) -> None:
        super().doItemsLayout()
        self.restore_positions()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.restore_positions()

    def restore_positions(self) -> None:
        if not self.free:
            return
        for index in range(self.count()):
            item = self.item(index)
            self.setPositionForIndex(self.position(item), self.indexFromItem(item))
        self.updateEditorGeometries()
        self.updateGeometries()

    def updateGeometries(self) -> None:
        free = getattr(self, "free", False)
        offset = self._offset() if free else QPoint()
        super().updateGeometries()
        if not free:
            return
        points = [self.position(self.item(i)) for i in range(self.count())]
        # Leave working room beyond the last card; no forced repacking on resize.
        width = max((point.x() + 534 for point in points), default=800)
        height = max((point.y() + 484 for point in points), default=600)
        self._extent = self._extent.expandedTo(QSize(width, height))
        for bar, length, visible in (
            (self.horizontalScrollBar(), self._extent.width(), self.viewport().width()),
            (self.verticalScrollBar(), self._extent.height(), self.viewport().height()),
        ):
            bar.setRange(0, max(0, length - visible))
        self.horizontalScrollBar().setValue(offset.x())
        self.verticalScrollBar().setValue(offset.y())

    def _offset(self) -> QPoint:
        return QPoint(self.horizontalScrollBar().value(), self.verticalScrollBar().value())

    def _drag_to(self, global_point: QPoint) -> None:
        handle, item, start, original, offset = self._drag
        if (global_point - start).manhattanLength() < QApplication.startDragDistance():
            return
        point = self.viewport().mapFromGlobal(global_point)
        for coordinate, length, bar in (
            (point.x(), self.viewport().width(), self.horizontalScrollBar()),
            (point.y(), self.viewport().height(), self.verticalScrollBar()),
        ):
            if coordinate < 24:
                bar.setValue(bar.value() - 24)
            elif coordinate > length - 24:
                bar.setValue(bar.value() + 24)
        self.place_item(item, original + global_point - start + self._offset() - offset)

    def eventFilter(self, watched, event) -> bool:
        if watched not in self._handles:
            return super().eventFilter(watched, event)
        item = self._handles[watched]
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self.setCurrentItem(item)
            if self.currentItem() is not item:
                return True  # A draft guard rejected selecting this note.
            watched.setFocus()
            self.itemWidget(item).raise_()
            self._drag = (watched, item, event.globalPosition().toPoint(),
                          self.position(item), self._offset())
            watched.setCursor(Qt.ClosedHandCursor)
            return True
        if self._drag and self._drag[0] is watched:
            if event.type() == QEvent.MouseMove:
                self._drag_to(event.globalPosition().toPoint())
                return True
            if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                self._drag_to(event.globalPosition().toPoint())
                original = self._drag[3]
                self._drag = None
                watched.setCursor(Qt.OpenHandCursor)
                if self.position(item) != original:
                    self.moved.emit(item, self.position(item), original)
                return True
            if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
                self.place_item(item, self._drag[3])
                self._drag = None
                watched.setCursor(Qt.OpenHandCursor)
                return True
        return super().eventFilter(watched, event)
