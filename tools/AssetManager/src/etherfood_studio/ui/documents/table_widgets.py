"""Quiet table handles and safely rendered, wrapping Markdown cells."""

from PySide6.QtCore import QByteArray, QSize, Qt, Signal
from PySide6.QtGui import (
    QAbstractTextDocumentLayout, QPalette, QPen, QTextCursor, QTextDocument, QTextOption,
)
from PySide6.QtWidgets import QHeaderView, QStyle, QStyledItemDelegate, QStyleOptionViewItem


class CellDocument(QTextDocument):
    def loadResource(self, resource_type, name) -> object:
        return QByteArray()


class MarkdownCellDelegate(QStyledItemDelegate):
    def __init__(self, references: str, parent=None) -> None:
        super().__init__(parent)
        self.references = references

    def document(self, option, index) -> QTextDocument:
        document = CellDocument()
        document.setDefaultFont(option.font)
        document.setDocumentMargin(0)
        document.setMarkdown(str(index.data() or "") + "\n\n" + self.references,
                              QTextDocument.MarkdownDialectGitHub | QTextDocument.MarkdownNoHTML)
        cursor = QTextCursor(document)
        cursor.select(QTextCursor.Document)
        format_ = cursor.blockFormat()
        format_.setAlignment(option.displayAlignment)
        cursor.mergeBlockFormat(format_)
        text_option = document.defaultTextOption()
        text_option.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        document.setDefaultTextOption(text_option)
        document.setTextWidth(max(20, self.parent().columnWidth(index.column()) - 18))
        return document

    def paint(self, painter, option, index) -> None:
        option = QStyleOptionViewItem(option)
        self.initStyleOption(option, index)
        option.text = ""
        option.widget.style().drawControl(QStyle.CE_ItemViewItem, option, painter, option.widget)
        document = self.document(option, index)
        context = QAbstractTextDocumentLayout.PaintContext()
        context.palette = option.palette
        if option.state & QStyle.State_Selected:
            context.palette.setColor(QPalette.Text, option.palette.highlightedText().color())
        painter.save()
        painter.setClipRect(option.rect)
        painter.translate(option.rect.left() + 8, option.rect.top() + 6)
        document.documentLayout().draw(painter, context)
        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        option = QStyleOptionViewItem(option)
        self.initStyleOption(option, index)
        document = self.document(option, index)
        return QSize(120, max(30, int(document.size().height() + 14)))


class InsertHeader(QHeaderView):
    insert_after = Signal(int)

    def __init__(self, orientation, parent=None) -> None:
        super().__init__(orientation, parent)
        self.controls_visible = False
        self.setSectionsMovable(True)
        self.setSectionsClickable(True)
        self.setFirstSectionMovable(orientation == Qt.Horizontal)
        self.setMinimumSectionSize(120 if orientation == Qt.Horizontal else 30)
        if orientation == Qt.Horizontal:
            self.setFixedHeight(20)
            self.setSectionResizeMode(QHeaderView.Stretch)
        else:
            self.setFixedWidth(30)
        self.setToolTip("Klicken: auswählen · Ziehen: umordnen · +: danach einfügen · "
                        "Entf oder Rechtsklick: Auswahl entfernen")

    def show_controls(self, visible: bool) -> None:
        if visible != self.controls_visible:
            self.controls_visible = visible
            self.viewport().update()

    def paintSection(self, painter, rect, logical_index) -> None:
        painter.save()
        painter.fillRect(rect, self.palette().base())
        if self.controls_visible:
            painter.setPen(QPen(self.palette().text().color(), 1.5))
            x = rect.center().x() if self.orientation() == Qt.Horizontal else rect.left() + 6
            for y in (-3, 0, 3):
                painter.drawPoint(x, rect.center().y() + y)
            x, y = rect.right() - 10, rect.center().y()
            painter.drawLine(x - 3, y, x + 3, y)
            painter.drawLine(x, y - 3, x, y + 3)
        painter.restore()

    def mousePressEvent(self, event) -> None:
        point = event.position().toPoint()
        index = self.logicalIndexAt(point)
        if self.controls_visible and index >= 0 and event.button() == Qt.LeftButton:
            edge = (self.sectionViewportPosition(index) + self.sectionSize(index)
                    if self.orientation() == Qt.Horizontal else self.width())
            if edge - 20 <= point.x() <= edge:
                self.insert_after.emit(index)
                event.accept()
                return
        super().mousePressEvent(event)
