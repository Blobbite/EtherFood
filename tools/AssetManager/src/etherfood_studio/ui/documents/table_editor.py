"""Editable Markdown tables with native row/column selection and drag handles."""

from PySide6.QtCore import QByteArray, QEvent, QSignalBlocker, Qt, Signal
from PySide6.QtGui import (
    QAbstractTextDocumentLayout, QKeySequence, QPalette, QPen, QTextCursor, QTextDocument,
)
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QStyle, QStyledItemDelegate,
    QStyleOptionViewItem, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ..common import button
from .markdown_source import MarkdownTable


class CellDocument(QTextDocument):
    def loadResource(self, resource_type, name) -> object:
        return QByteArray()


class MarkdownCellDelegate(QStyledItemDelegate):
    def __init__(self, references: str, parent=None) -> None:
        super().__init__(parent)
        self.references = references

    def paint(self, painter, option, index) -> None:
        option = QStyleOptionViewItem(option)
        self.initStyleOption(option, index)
        text, option.text = option.text, ""
        option.widget.style().drawControl(QStyle.CE_ItemViewItem, option, painter, option.widget)
        document = CellDocument()
        document.setDefaultFont(option.font)
        document.setDocumentMargin(0)
        document.setMarkdown(text + "\n\n" + self.references, QTextDocument.MarkdownDialectGitHub
                              | QTextDocument.MarkdownNoHTML)
        cursor = QTextCursor(document)
        cursor.select(QTextCursor.Document)
        format_ = cursor.blockFormat()
        format_.setAlignment(option.displayAlignment)
        cursor.mergeBlockFormat(format_)
        document.setTextWidth(max(1, option.rect.width() - 8))
        context = QAbstractTextDocumentLayout.PaintContext()
        context.palette = option.palette
        if option.state & QStyle.State_Selected:
            context.palette.setColor(QPalette.Text, option.palette.highlightedText().color())
        painter.save()
        painter.setClipRect(option.rect)
        painter.translate(option.rect.left() + 4, option.rect.top() + 4)
        document.documentLayout().draw(painter, context)
        painter.restore()


class InsertHeader(QHeaderView):
    insert_after = Signal(int)

    def __init__(self, orientation, parent=None) -> None:
        super().__init__(orientation, parent)
        self.setSectionsMovable(True)
        self.setSectionsClickable(True)
        self.setFirstSectionMovable(orientation == Qt.Horizontal)
        self.setMinimumSectionSize(40)
        self.setToolTip("Klicken: auswählen · Ziehen: umordnen · +: danach einfügen")

    def paintSection(self, painter, rect, logical_index) -> None:
        super().paintSection(painter, rect, logical_index)
        painter.save()
        painter.setPen(QPen(self.palette().buttonText().color(), 1.6))
        center = rect.topRight() + rect.bottomRight()
        x, y = rect.right() - 11, center.y() // 2
        painter.drawLine(x - 4, y, x + 4, y)
        painter.drawLine(x, y - 4, x, y + 4)
        painter.restore()

    def mousePressEvent(self, event) -> None:
        point = event.position().toPoint()
        index = self.logicalIndexAt(point)
        if index >= 0 and event.button() == Qt.LeftButton:
            edge = (self.sectionViewportPosition(index) + self.sectionSize(index)
                    if self.orientation() == Qt.Horizontal else self.width())
            if edge - 22 <= point.x() <= edge:
                self.insert_after.emit(index)
                event.accept()
                return
        super().mousePressEvent(event)


class MarkdownTableEditor(QWidget):
    source_changed = Signal(str)
    undo_requested = Signal()
    redo_requested = Signal()

    def __init__(self, model: MarkdownTable, read_only: bool, parent=None,
                 *, references: str = "") -> None:
        super().__init__(parent)
        self.setObjectName("markdown_table_editor")
        self.model = model
        self.read_only = read_only
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(3)
        self.hint = QLabel("Kopf/Rand: auswählen · ziehen zum Umordnen · + zum Einfügen")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        body = QHBoxLayout()
        self.table = QTableWidget()
        self.table.setObjectName("markdown_table_cells")
        self.table.setAccessibleName("Markdown-Tabelle – Kopfzeile und Zellen bearbeiten")
        self.table.setHorizontalHeader(InsertHeader(Qt.Horizontal, self.table))
        self.table.setVerticalHeader(InsertHeader(Qt.Vertical, self.table))
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setItemDelegate(MarkdownCellDelegate(references, self.table))
        self.table.installEventFilter(self)
        self.table.horizontalHeader().setDefaultSectionSize(150)
        self.table.verticalHeader().setDefaultSectionSize(30)
        body.addWidget(self.table, 1)
        self.add_column = button("+", "markdown_add_column", lambda: self.insert_column())
        self.add_column.setToolTip("Spalte rechts hinzufügen")
        self.add_column.setAccessibleName("Spalte rechts hinzufügen")
        self.add_column.setFixedWidth(38)
        body.addWidget(self.add_column)
        layout.addLayout(body)
        actions = QHBoxLayout()
        self.add_row = button("+ Zeile", "markdown_add_row", lambda: self.insert_row())
        self.delete_rows = button("Zeilen entfernen", "markdown_delete_rows", self.remove_rows)
        self.delete_columns = button("Spalten entfernen", "markdown_delete_columns",
                                     self.remove_columns)
        for widget in (self.add_row, self.delete_rows, self.delete_columns):
            actions.addWidget(widget)
        actions.addStretch(1)
        layout.addLayout(actions)
        self.table.itemChanged.connect(self.edit_cell)
        self.table.itemSelectionChanged.connect(self.update_actions)
        for header, callback, insert in (
            (self.table.horizontalHeader(), self.move_column, self.insert_column),
            (self.table.verticalHeader(), self.move_row, self.insert_row),
        ):
            header.sectionMoved.connect(callback)
            header.insert_after.connect(lambda index, action=insert: action(index + 1))
        self.reload()
        self.set_read_only(read_only)

    def eventFilter(self, watched, event) -> bool:
        if (watched is self.table
                and event.type() in {QEvent.ShortcutOverride, QEvent.KeyPress}):
            undo, redo = event.matches(QKeySequence.Undo), event.matches(QKeySequence.Redo)
            if undo or redo:
                if event.type() == QEvent.KeyPress and not self.read_only:
                    (self.undo_requested if undo else self.redo_requested).emit()
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
        self.hint.setText("Schreibgeschützte Tabelle" if value else
                          "Kopf/Rand: auswählen · ziehen zum Umordnen · + zum Einfügen")
        self.update_actions()

    def reload(self) -> None:
        with QSignalBlocker(self.table):
            self.table.clear()
            self.table.setRowCount(len(self.model.rows))
            self.table.setColumnCount(len(self.model.separators))
            self.table.setHorizontalHeaderLabels(
                [f"Spalte {i + 1}    " for i in range(self.table.columnCount())])
            self.table.setVerticalHeaderLabels(
                ["Kopf    "] + [f"{i}    " for i in range(1, self.table.rowCount())])
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
        self.table.setMinimumHeight(min(480, 38 + 30 * len(self.model.rows)))
        self.update_actions()

    def update_actions(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        columns = self.table.selectionModel().selectedColumns()
        self.delete_rows.setEnabled(not self.read_only and any(i.row() > 0 for i in rows))
        self.delete_columns.setEnabled(not self.read_only and
                                       0 < len(columns) < self.table.columnCount())
        self.add_row.setEnabled(not self.read_only)
        self.add_column.setEnabled(not self.read_only)

    def commit(self, *, reload: bool = True) -> None:
        if reload:
            self.reload()
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
        if not self.read_only:
            self.model.remove_rows([index.row() for index in
                                    self.table.selectionModel().selectedRows()])
            self.commit()

    def remove_columns(self) -> None:
        if not self.read_only:
            self.model.remove_columns([index.column() for index in
                                       self.table.selectionModel().selectedColumns()])
            self.commit()
