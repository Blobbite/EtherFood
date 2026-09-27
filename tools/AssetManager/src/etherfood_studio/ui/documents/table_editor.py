"""Source-preserving tables with hover handles, native selection and no action bar."""

from PySide6.QtCore import QEvent, QSignalBlocker, Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QFrame, QGridLayout, QHBoxLayout, QMenu, QTableWidget,
    QTableWidgetItem, QToolButton, QVBoxLayout, QWidget,
)

from .markdown_source import MarkdownTable
from .table_widgets import InsertHeader, MarkdownCellDelegate


class MarkdownTableEditor(QWidget):
    source_changed = Signal(str)
    geometry_changed = Signal()
    undo_requested = Signal()
    redo_requested = Signal()

    def __init__(self, model: MarkdownTable, read_only: bool, parent=None,
                 *, references: str = "") -> None:
        super().__init__(parent)
        self.setObjectName("markdown_table_editor")
        self.model = model
        self.read_only = read_only
        self.selection_axis = None
        self.layout_timer = QTimer(self)
        self.layout_timer.setSingleShot(True)
        self.layout_timer.timeout.connect(self.fit_rows)
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.table = QTableWidget()
        self.table.setObjectName("markdown_table_cells")
        self.table.setAccessibleName("Markdown-Tabelle – Kopfzeile und Zellen bearbeiten")
        self.table.setFrameShape(QFrame.NoFrame)
        self.table.setCornerButtonEnabled(False)
        self.table.setStyleSheet("QTableView { gridline-color: palette(mid); } "
                                "QTableCornerButton::section { "
                                "background: palette(base); border: none; }")
        self.table.setHorizontalHeader(InsertHeader(Qt.Horizontal, self.table))
        self.table.setVerticalHeader(InsertHeader(Qt.Vertical, self.table))
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setWordWrap(True)
        self.table.setItemDelegate(MarkdownCellDelegate(references, self.table))
        self.table.installEventFilter(self)
        self.table.viewport().installEventFilter(self)
        self.table.cellPressed.connect(self.clear_selection_axis)
        self.table.horizontalHeader().sectionPressed.connect(lambda _: self.select_axis("column"))
        self.table.verticalHeader().sectionPressed.connect(lambda _: self.select_axis("row"))
        layout.addWidget(self.table, 0, 0)
        self.add_column = self.edge_button("markdown_add_column", "Spalte rechts hinzufügen",
                                           lambda: self.insert_column())
        self.add_row = self.edge_button("markdown_add_row", "Zeile unten hinzufügen",
                                        lambda: self.insert_row())
        right, bottom = QWidget(), QWidget()
        right.setFixedWidth(24)
        bottom.setFixedHeight(24)
        right_layout, bottom_layout = QVBoxLayout(right), QHBoxLayout(bottom)
        for box, widget in ((right_layout, self.add_column), (bottom_layout, self.add_row)):
            box.setContentsMargins(0, 0, 0, 0)
            box.addStretch(1)
            box.addWidget(widget)
            box.addStretch(1)
        layout.addWidget(right, 0, 1)
        layout.addWidget(bottom, 1, 0)
        layout.setColumnStretch(0, 1)
        self.table.itemChanged.connect(self.edit_cell)
        self.table.itemSelectionChanged.connect(self.update_controls)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context)
        for axis, header, callback, insert in (
            ("column", self.table.horizontalHeader(), self.move_column, self.insert_column),
            ("row", self.table.verticalHeader(), self.move_row, self.insert_row),
        ):
            header.sectionMoved.connect(callback)
            header.insert_after.connect(lambda index, action=insert: action(index + 1))
            header.setContextMenuPolicy(Qt.CustomContextMenu)
            header.customContextMenuRequested.connect(
                lambda point, field=header, value=axis: self.header_context(field, value, point))
        self.table.horizontalHeader().sectionResized.connect(lambda *_: self.layout_timer.start(0))
        QApplication.instance().focusChanged.connect(self.update_controls)
        self.reload()
        self.set_read_only(read_only)

    def edge_button(self, name: str, title: str, callback) -> QToolButton:
        widget = QToolButton()
        widget.setObjectName(name)
        widget.setText("+")
        widget.setToolTip(title)
        widget.setAccessibleName(title)
        widget.setAutoRaise(True)
        widget.setFixedSize(22, 22)
        widget.clicked.connect(callback)
        return widget

    def select_axis(self, axis: str) -> None:
        self.selection_axis = axis

    def clear_selection_axis(self, *args: object) -> None:
        self.selection_axis = None

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self.update_controls()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self.update_controls()

    def eventFilter(self, watched, event) -> bool:
        if watched is self.table.viewport() and event.type() == QEvent.Resize:
            self.layout_timer.start(0)
        if (watched is self.table
                and event.type() in {QEvent.ShortcutOverride, QEvent.KeyPress}):
            undo, redo = event.matches(QKeySequence.Undo), event.matches(QKeySequence.Redo)
            delete = event.key() in {Qt.Key_Delete, Qt.Key_Backspace}
            if undo or redo or delete:
                if event.type() == QEvent.KeyPress and not self.read_only:
                    if undo or redo:
                        (self.undo_requested if undo else self.redo_requested).emit()
                    elif self.selection_axis == "column":
                        self.remove_columns()
                    elif self.selection_axis == "row":
                        self.remove_rows()
                event.accept()
                return True
        return super().eventFilter(watched, event)

    def set_read_only(self, value: bool) -> None:
        self.read_only = value
        self.table.setEditTriggers(
            QAbstractItemView.NoEditTriggers if value else
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed
            | QAbstractItemView.AnyKeyPressed)
        self.table.horizontalHeader().setSectionsMovable(not value)
        self.table.verticalHeader().setSectionsMovable(not value)
        self.table.setToolTip("Schreibgeschützte Tabelle" if value else
                              "Zelle doppelt anklicken: bearbeiten · "
                              "Randgriff: auswählen/ziehen · Entf: ganze Auswahl entfernen")
        self.update_controls()

    def reload(self) -> None:
        self.selection_axis = None
        with QSignalBlocker(self.table):
            self.table.clear()
            self.table.setRowCount(len(self.model.rows))
            self.table.setColumnCount(len(self.model.separators))
            self.table.setHorizontalHeaderLabels([""] * self.table.columnCount())
            self.table.setVerticalHeaderLabels([""] * self.table.rowCount())
            for row, values in enumerate(self.model.rows):
                for column, value in enumerate(values):
                    item = QTableWidgetItem(value.strip())
                    if row == 0:
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                    separator = self.model.separators[column].strip()
                    align = (Qt.AlignCenter if separator.startswith(":") else Qt.AlignRight
                             ) if separator.endswith(":") else Qt.AlignLeft
                    item.setTextAlignment(align | Qt.AlignVCenter)
                    self.table.setItem(row, column, item)
            for header in (self.table.horizontalHeader(), self.table.verticalHeader()):
                with QSignalBlocker(header):
                    for index in range(header.count()):
                        header.moveSection(header.visualIndex(index), index)
                        title = ("Spalte " if header.orientation() == Qt.Horizontal else "Zeile ")
                        self.table.model().setHeaderData(index, header.orientation(), "")
                        self.table.model().setHeaderData(
                            index, header.orientation(), title + str(index + 1),
                            Qt.AccessibleTextRole)
        self.layout_timer.start(0)
        self.update_controls()

    def fit_rows(self) -> None:
        self.table.resizeRowsToContents()
        height = self.table.horizontalHeader().height() + sum(
            self.table.rowHeight(row) for row in range(self.table.rowCount())) + 2
        if self.table.horizontalScrollBar().maximum():
            height += self.table.horizontalScrollBar().sizeHint().height()
        self.table.setFixedHeight(min(480, max(54, height)))
        self.geometry_changed.emit()

    def update_controls(self, *args: object) -> None:
        focus = QApplication.focusWidget()
        visible = not self.read_only and (self.underMouse()
                                         or bool(focus and self.isAncestorOf(focus)))
        for header in (self.table.horizontalHeader(), self.table.verticalHeader()):
            header.show_controls(visible)
        for button in (self.add_row, self.add_column):
            button.setEnabled(not self.read_only)
            button.setVisible(visible)

    def removal_allowed(self, axis: str) -> bool:
        selection = self.table.selectionModel()
        if self.read_only:
            return False
        if axis == "row":
            return any(index.row() > 0 for index in selection.selectedRows())
        return 0 < len(selection.selectedColumns()) < self.table.columnCount()

    def context_menu(self) -> QMenu:
        menu = QMenu(self)
        for title, axis, callback in (("Zeilen entfernen", "row", self.remove_rows),
                                      ("Spalten entfernen", "column", self.remove_columns)):
            action = menu.addAction(title, callback)
            action.setEnabled(self.removal_allowed(axis))
            action.setObjectName("markdown_delete_" + axis)
        return menu

    def header_context(self, header, axis: str, point) -> None:
        index = header.logicalIndexAt(point)
        if index < 0:
            return
        selected = (self.table.selectionModel().selectedColumns() if axis == "column" else
                    self.table.selectionModel().selectedRows())
        if not any((value.column() if axis == "column" else value.row()) == index
                   for value in selected):
            self.table.selectColumn(index) if axis == "column" else self.table.selectRow(index)
        self.selection_axis = axis
        menu = self.context_menu()
        menu.exec(header.viewport().mapToGlobal(point))
        menu.deleteLater()

    def show_context(self, point) -> None:
        menu = self.context_menu()
        menu.exec(self.table.viewport().mapToGlobal(point))
        menu.deleteLater()

    def commit(self, *, reload: bool = True) -> None:
        if reload:
            self.reload()
        else:
            self.layout_timer.start(0)
        self.source_changed.emit(self.model.text())

    def edit_cell(self, item: QTableWidgetItem) -> None:
        if not self.read_only:
            self.model.edit(item.row(), item.column(), item.text())
            self.commit(reload=False)

    def insert_column(self, index: int | None = None) -> None:
        if not self.read_only:
            self.model.insert_column(len(self.model.separators) if index is None else index)
            self.commit()

    def insert_row(self, index: int | None = None) -> None:
        if not self.read_only:
            self.model.insert_row(len(self.model.rows) if index is None else index)
            self.commit()

    def move_column(self, logical: int, before: int, after: int) -> None:
        if not self.read_only:
            self.model.move_column(before, after)
            self.commit()

    def move_row(self, logical: int, before: int, after: int) -> None:
        if not self.read_only:
            self.model.move_row(before, after)
            self.commit()

    def remove_rows(self) -> None:
        if self.removal_allowed("row"):
            self.model.remove_rows([index.row() for index in
                                    self.table.selectionModel().selectedRows()])
            self.commit()

    def remove_columns(self) -> None:
        if self.removal_allowed("column"):
            self.model.remove_columns([index.column() for index in
                                       self.table.selectionModel().selectedColumns()])
            self.commit()
