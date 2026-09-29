"""Python text editing with line numbers, highlighting and error navigation."""

import keyword
import re

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import (
    QColor,
    QFontDatabase,
    QPainter,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QWidget


class PythonHighlighter(QSyntaxHighlighter):
    def highlightBlock(self, text):
        light = QApplication.palette().base().color().lightness() > 128
        for pattern, color in (
            (r"\b(?:" + "|".join(keyword.kwlist) + r")\b", "#d695e8"),
            (r"\b[0-9]+(?:\.[0-9]+)?\b", "#e4bb7b"),
            (r"\b(?:def|class)\s+([A-Za-z_]\w*)", "#83c7f4"),
            (r"(?:'[^'\\]*(?:\\.[^'\\]*)*'|\"[^\"\\]*(?:\\.[^\"\\]*)*\")", "#a2d995"),
            (r"#.*$", "#899499"),
        ):
            style = QTextCharFormat()
            if light:
                color = {
                    "#d695e8": "#75419b",
                    "#e4bb7b": "#895218",
                    "#83c7f4": "#075c8c",
                    "#a2d995": "#276c34",
                    "#899499": "#647078",
                }[color]
            style.setForeground(QColor(color))
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), style)


class LineNumbers(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def paintEvent(self, event):
        editor = self.editor
        painter = QPainter(self)
        painter.fillRect(event.rect(), editor.palette().alternateBase())
        painter.setPen(editor.palette().text().color())
        block = editor.firstVisibleBlock()
        while block.isValid():
            top = int(editor.blockBoundingGeometry(block).translated(editor.contentOffset()).top())
            height = int(editor.blockBoundingRect(block).height())
            if top > event.rect().bottom():
                break
            if block.isVisible():
                painter.drawText(
                    0, top, self.width() - 7, height, Qt.AlignRight, str(block.blockNumber() + 1)
                )
            block = block.next()


class PythonEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("workflow_python_editor")
        self.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.numbers = LineNumbers(self)
        self.highlighter = PythonHighlighter(self.document())
        self.blockCountChanged.connect(self.update_margin)
        self.updateRequest.connect(lambda rect, dy: self.numbers.update())
        self.update_margin()

    def update_margin(self):
        self.setViewportMargins(
            15 + self.fontMetrics().horizontalAdvance("9") * len(str(max(1, self.blockCount()))),
            0,
            0,
            0,
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        area = self.contentsRect()
        self.numbers.setGeometry(
            QRect(area.left(), area.top(), self.viewportMargins().left(), area.height())
        )

    def goto_line(self, number):
        block = self.document().findBlockByNumber(max(0, number - 1))
        if block.isValid():
            self.setTextCursor(QTextCursor(block))
            self.centerCursor()
            self.setFocus()
