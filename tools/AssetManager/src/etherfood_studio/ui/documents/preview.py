"""Render GFM without resource loading or automatic external navigation."""

from PySide6.QtCore import QByteArray, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QTextCharFormat, QTextCursor, QTextDocument
from PySide6.QtWidgets import QMessageBox, QTextBrowser

HEADING_SIZES = (24, 20, 17, 15, 13, 11)


class SafePreview(QTextBrowser):
    activated = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("markdown_preview")
        self.setAccessibleName("Markdown – anklicken zum Bearbeiten")
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.anchorClicked.connect(self._open_link)

    def loadResource(self, resource_type: int, name: QUrl) -> object:
        return QByteArray()

    def preview(self, text: str) -> None:
        self.document().setMarkdown(text, QTextDocument.MarkdownFeature.MarkdownDialectGitHub
                                    | QTextDocument.MarkdownFeature.MarkdownNoHTML)
        block = self.document().begin()
        while block.isValid():
            level = block.blockFormat().headingLevel()
            if level:
                cursor = QTextCursor(block)
                cursor.select(QTextCursor.BlockUnderCursor)
                style = QTextCharFormat()
                style.setFontPointSize(HEADING_SIZES[level - 1])
                cursor.mergeCharFormat(style)
            block = block.next()

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton and not self.anchorAt(event.position().toPoint()) \
                and not self.textCursor().hasSelection():
            self.activated.emit()

    def _open_link(self, url: QUrl) -> None:
        if url.scheme() not in {"https", "http"}:
            return
        answer = QMessageBox.question(self, "Externen Link öffnen?", url.toString(),
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer == QMessageBox.Yes:
            QDesktopServices.openUrl(url)
