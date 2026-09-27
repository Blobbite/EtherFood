"""Render GFM without resource loading or automatic external navigation."""

from PySide6.QtCore import QByteArray, QPointF, QRectF, Qt, QUrl, Signal
from PySide6.QtGui import (
    QColor, QDesktopServices, QPainter, QPen, QPolygonF, QTextBlockFormat, QTextCharFormat,
    QTextCursor, QTextDocument,
)
from PySide6.QtWidgets import QCheckBox, QMessageBox, QTextBrowser

from .markdown_source import checkbox_offsets
from ..theme import color

HEADING_SIZES = (24, 20, 17, 15, 13, 11)


class MarkdownCheckBox(QCheckBox):
    """A real keyboard-accessible checkbox with a legible outline in either theme."""

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(color("base")))
        painter.setPen(QPen(QColor(color("muted")), 1.4))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(2, 2, -2, -2), 2, 2)
        if self.isChecked():
            painter.setPen(QPen(QColor(color("text")), 2.2, Qt.SolidLine, Qt.RoundCap,
                                Qt.RoundJoin))
            painter.drawPolyline(QPolygonF([QPointF(5, self.height() * 0.52),
                                           QPointF(self.width() * 0.43, self.height() - 5),
                                           QPointF(self.width() - 5, 5)]))
        if self.hasFocus():
            painter.setPen(QPen(QColor(color("accent")), 1, Qt.DotLine))
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        painter.end()


class SafePreview(QTextBrowser):
    activated = Signal()
    checkbox_toggled = Signal(int, bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("markdown_preview")
        self.setAccessibleName("Markdown – anklicken zum Bearbeiten")
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.anchorClicked.connect(self._open_link)
        self.checkboxes = []
        self.checkbox_read_only = True
        self.verticalScrollBar().valueChanged.connect(self.position_checkboxes)
        self.horizontalScrollBar().valueChanged.connect(self.position_checkboxes)
        self.document().documentLayout().documentSizeChanged.connect(self.position_checkboxes)

    def loadResource(self, resource_type: int, name: QUrl) -> object:
        return QByteArray()

    def preview(self, text: str) -> None:
        for checkbox, _ in self.checkboxes:
            checkbox.hide()
            checkbox.deleteLater()
        self.checkboxes = []
        self.document().setMarkdown(text, QTextDocument.MarkdownFeature.MarkdownDialectGitHub
                                    | QTextDocument.MarkdownFeature.MarkdownNoHTML)
        block = self.document().begin()
        task_blocks = []
        while block.isValid():
            level = block.blockFormat().headingLevel()
            if level:
                cursor = QTextCursor(block)
                cursor.select(QTextCursor.BlockUnderCursor)
                style = QTextCharFormat()
                style.setFontPointSize(HEADING_SIZES[level - 1])
                cursor.mergeCharFormat(style)
                format_ = block.blockFormat()
                format_.setTopMargin(0)
                format_.setBottomMargin(0)
                cursor.setBlockFormat(format_)
            if block.blockFormat().marker() != QTextBlockFormat.MarkerType.NoMarker:
                task_blocks.append(block)
            block = block.next()
        offsets = checkbox_offsets(text)
        # Qt and the source parser must agree before exposing any source-changing action.
        if len(offsets) == len(task_blocks):
            for offset, task in zip(offsets, task_blocks):
                checkbox = MarkdownCheckBox(self.viewport())
                checkbox.setObjectName("markdown_checkbox")
                checkbox.setAccessibleName(task.text())
                checkbox.setToolTip(task.text())
                checkbox.setChecked(text[offset].lower() == "x")
                checkbox.setEnabled(not self.checkbox_read_only)
                checkbox.toggled.connect(lambda value, start=offset:
                                         self.checkbox_toggled.emit(start, value))
                self.checkboxes.append((checkbox, task.position()))
                checkbox.show()
        self.position_checkboxes()

    def set_checkbox_read_only(self, value: bool) -> None:
        self.checkbox_read_only = value
        for checkbox, _ in self.checkboxes:
            checkbox.setEnabled(not value)

    def position_checkboxes(self, *args: object) -> None:
        for checkbox, position in self.checkboxes:
            cursor = QTextCursor(self.document())
            cursor.setPosition(position)
            rect = self.cursorRect(cursor)
            size = max(18, checkbox.sizeHint().height())
            checkbox.setGeometry(max(0, rect.left() - size - 3),
                                 rect.top() + (rect.height() - size) // 2, size, size)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.position_checkboxes()

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        if (event.button() == Qt.LeftButton and not self.anchorAt(event.position().toPoint())
                and not self.textCursor().hasSelection()):
            self.activated.emit()

    def _open_link(self, url: QUrl) -> None:
        if url.scheme() not in {"https", "http"}:
            return
        answer = QMessageBox.question(self, "Externen Link öffnen?", url.toString(),
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer == QMessageBox.Yes:
            QDesktopServices.openUrl(url)
