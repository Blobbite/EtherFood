"""Render GFM without resource loading or automatic external navigation."""

from PySide6.QtCore import QByteArray, QPointF, QRectF, Qt, QUrl, Signal
from PySide6.QtGui import (
    QColor, QDesktopServices, QPainter, QPen, QPolygonF, QTextBlockFormat, QTextCharFormat,
    QTextCursor, QTextDocument, QTextFormat,
)
from PySide6.QtWidgets import QCheckBox, QMessageBox, QTextBrowser

from .markdown_source import checkbox_offsets
from .markdown_syntax import parser, render, visible
from ..appearance import appearance
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
        self.local_link = None
        self.local_resource = None
        self.media = None
        self.media_sources = []
        self.media_insets = {}
        self._press_position = None
        self.anchorClicked.connect(self._open_link)
        self.document().setUndoRedoEnabled(False)
        self.checkboxes = []
        self.checkbox_read_only = True
        self.verticalScrollBar().valueChanged.connect(self.position_checkboxes)
        self.horizontalScrollBar().valueChanged.connect(self.position_checkboxes)
        self.document().documentLayout().documentSizeChanged.connect(self.position_checkboxes)
        appearance().changed.connect(self.refresh_links)

    def refresh_links(self):
        block = self.document().begin()
        while block.isValid():
            iterator = block.begin()
            while not iterator.atEnd():
                fragment = iterator.fragment()
                if fragment.charFormat().anchorHref():
                    cursor = QTextCursor(self.document())
                    cursor.setPosition(fragment.position())
                    cursor.setPosition(fragment.position() + fragment.length(),
                                       QTextCursor.KeepAnchor)
                    style = QTextCharFormat()
                    style.setForeground(QColor(color("link")))
                    style.setFontUnderline(True)
                    cursor.mergeCharFormat(style)
                iterator += 1
            block = block.next()

    def loadResource(self, resource_type: int, name: QUrl) -> object:
        if name.scheme() == "studio-media" and self.media:
            return self.media.resource_image(name.path())
        if self.local_resource and not name.scheme() and not name.host():
            result = self.local_resource(resource_type, name)
            if result is not None:
                return result
        return QByteArray()

    def preview(self, text: str, *, references="") -> None:
        for checkbox, _ in self.checkboxes:
            checkbox.hide()
            checkbox.deleteLater()
        self.checkboxes = []
        # Keep exact source/checkbox offsets, but hide our own bookkeeping in rendered Markdown.
        from ...application.project_documents import START, END
        code_lines = {line for token in parser().parse(text) if token.type in {"fence",
            "code_block"}
                      for line in range(*token.map)}
        rendered = "\n".join("" if line.strip() in {START, END} and number not in code_lines
            else line
                             for number, line in enumerate(text.split("\n")))
        self.media_sources = []
        self.media_insets = {}

        def image_renderer(tokens, index, options, env):
            from html import escape
            token = tokens[index]
            source = token.attrGet("src") or ""
            alt = visible(token.children)
            self.media_sources.append((source, alt))
            if self.media:
                item = self.media.ensure(source)
                self.media_insets[item.key] = token.meta.get("inset", 0)
                return self.media.markup(source, alt, token.attrGet("title") or "",
                                         self.viewport().width() - 24 - token.meta.get("inset", 0))
            return '<img src="' + escape(source, quote=True) + '" alt="' + escape(alt,
                quote=True) + '" />'

        html, tasks = render(rendered, references=references, image_renderer=image_renderer)
        self.document().setHtml(html)
        self.refresh_links()
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
            iterator = block.begin()
            first = None if iterator.atEnd() else iterator.fragment()
            if first and first.isValid() and any(name.startswith("studio-task-")
                for name in first.charFormat().anchorNames()):
                checked = block.text().startswith("☑")
                cursor = QTextCursor(block)
                cursor.setPosition(block.position() + 2, QTextCursor.KeepAnchor)
                cursor.removeSelectedText()
                format_ = block.blockFormat()
                format_.setMarker(QTextBlockFormat.MarkerType.Checked if checked else
                                  QTextBlockFormat.MarkerType.Unchecked)
                cursor.setBlockFormat(format_)
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

    def update_media(self, key="") -> None:
        if not self.media:
            return
        block = self.document().begin()
        while block.isValid():
            fragments = []
            iterator = block.begin()
            while not iterator.atEnd():
                fragment = iterator.fragment()
                if fragment.charFormat().isImageFormat():
                    fragments.append(fragment)
                iterator += 1
            for fragment in fragments:
                format_ = fragment.charFormat().toImageFormat()
                name = QUrl(format_.name())
                if name.scheme() == "studio-media" and (not key or key == name.path()):
                    frame = self.media.resource_image(name.path())
                    size = self.media.display_size(name.path(), self.viewport().width() - 24 -
                                                     self.media_insets.get(name.path(), 0))
                    self.document().addResource(QTextDocument.ImageResource, name, frame)
                    if format_.width() != size.width() or format_.height() != size.height():
                        format_.setWidth(size.width())
                        format_.setHeight(size.height())
                        cursor = QTextCursor(self.document())
                        cursor.setPosition(fragment.position())
                        cursor.setPosition(fragment.position() + fragment.length(),
                            QTextCursor.KeepAnchor)
                        cursor.setCharFormat(format_)
            block = block.next()
        self.document().markContentsDirty(0, self.document().characterCount())
        self.viewport().update()

    def set_checkbox_read_only(self, value: bool) -> None:
        self.checkbox_read_only = value
        for checkbox, _ in self.checkboxes:
            checkbox.setEnabled(not value)

    def set_content_alignment(self, value: str) -> None:
        alignment = {"left": Qt.AlignLeft, "center": Qt.AlignHCenter,
                     "right": Qt.AlignRight}.get(value, Qt.AlignLeft)
        block = self.document().begin()
        while block.isValid():
            cursor = QTextCursor(block)
            format_ = block.blockFormat()
            if (not cursor.currentTable() and not format_.hasProperty(QTextFormat.BlockCodeLanguage)
                    and not format_.nonBreakableLines()):
                format_.setAlignment(alignment)
                cursor.setBlockFormat(format_)
            block = block.next()
        self.position_checkboxes()

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
        self.update_media()
        self.position_checkboxes()

    def mousePressEvent(self, event) -> None:
        self._press_position = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if (self._press_position is not None and
                (event.position().toPoint() - self._press_position).manhattanLength() > 4):
            event.accept()
            return
        super().mouseReleaseEvent(event)
        if (event.button() == Qt.LeftButton and not self.anchorAt(event.position().toPoint())
                and not self.textCursor().hasSelection()):
            self.activated.emit()

    def _open_link(self, url: QUrl) -> None:
        if (not url.scheme() and not url.host()
            or url.scheme() == "studio-wiki") and self.local_link:
            self.local_link(url)
            return
        if url.scheme() not in {"https", "http", "mailto"} or url.userName() or url.password():
            QMessageBox.information(self, "Link blockiert",
                "Dieses Linkprotokoll ist nicht freigegeben.")
            return
        answer = QMessageBox.question(self, "Externen Link öffnen?", url.toString(),
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer == QMessageBox.Yes:
            QDesktopServices.openUrl(url)
