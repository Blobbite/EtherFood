"""Quiet table handles and safely rendered, wrapping Markdown cells."""

from collections import OrderedDict

from PySide6.QtCore import QByteArray, QEvent, QSize, Qt, QUrl, Signal
from PySide6.QtGui import (
    QAbstractTextDocumentLayout, QPalette, QPen, QTextCursor, QTextDocument, QTextOption,
)
from PySide6.QtWidgets import (
    QAbstractItemDelegate, QHeaderView, QPlainTextEdit, QStyle, QStyledItemDelegate,
    QStyleOptionViewItem,
)

from .markdown_syntax import render
from ..appearance import appearance
from ..theme import color


class CellDocument(QTextDocument):
    def __init__(self, media=None, width=200):
        super().__init__()
        self.media, self.width = media, width
        self.sources = set()

    def loadResource(self, resource_type, name) -> object:
        if self.media and name.scheme() == "studio-media":
            return self.media.resource_image(name.path())
        return QByteArray()


class MarkdownCellDelegate(QStyledItemDelegate):
    def __init__(self, references: str, parent=None, *, media=None, open_link=None) -> None:
        super().__init__(parent)
        self.references = references
        self.media, self.open_link = media, open_link
        self.cache = OrderedDict()
        self.press = None
        if media:
            media.changed.connect(self.media_changed)
        appearance().changed.connect(self.refresh_appearance)

    def refresh_appearance(self):
        self.cache.clear()
        self.parent().viewport().update()

    def media_changed(self, key):
        resized = False
        for document in self.cache.values():
            if key not in document.sources:
                continue
            frame = self.media.resource_image(key)
            size = self.media.display_size(key, document.width)
            document.addResource(QTextDocument.ImageResource, QUrl("studio-media:" + key), frame)
            block = document.begin()
            while block.isValid():
                iterator = block.begin()
                while not iterator.atEnd():
                    fragment = iterator.fragment()
                    if fragment.charFormat().isImageFormat():
                        format_ = fragment.charFormat().toImageFormat()
                        if format_.name() == "studio-media:" + key and (
                                format_.width() != size.width()
                                    or format_.height() != size.height()):
                            format_.setWidth(size.width())
                            format_.setHeight(size.height())
                            cursor = QTextCursor(document)
                            cursor.setPosition(fragment.position())
                            cursor.setPosition(fragment.position() + fragment.length(),
                                QTextCursor.KeepAnchor)
                            cursor.setCharFormat(format_)
                            resized = True
                    iterator += 1
                block = block.next()
            document.markContentsDirty(0, document.characterCount())
        self.parent().viewport().update()
        if resized:
            self.parent().parent().layout_timer.start(0)

    def document(self, option, index) -> QTextDocument:
        width = max(20, self.parent().columnWidth(index.column()) - 18)
        cache_key = (index.data(), width, option.font.toString(), option.displayAlignment)
        if cache_key in self.cache:
            self.cache.move_to_end(cache_key)
            return self.cache[cache_key]
        document = CellDocument(self.media, width)
        document.setDefaultStyleSheet("a { color: " + color("link") +
                                      "; text-decoration: underline; }")
        document.setDefaultFont(option.font)
        document.setDocumentMargin(0)
        def image_renderer(tokens, index, options, env):
            token = tokens[index]
            if self.media:
                document.sources.add(self.media.ensure(token.attrGet("src") or "").key)
            return (self.media.markup(token.attrGet("src") or "", token.content,
                                      token.attrGet("title") or "", width) if self.media else
                    token.content)
        html, _ = render(str(index.data() or "").replace("\\|", "|"), references=self.references,
                         image_renderer=image_renderer)
        document.setHtml(html)
        cursor = QTextCursor(document)
        cursor.select(QTextCursor.Document)
        format_ = cursor.blockFormat()
        format_.setAlignment(option.displayAlignment)
        cursor.mergeBlockFormat(format_)
        text_option = document.defaultTextOption()
        text_option.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        document.setDefaultTextOption(text_option)
        document.setTextWidth(max(20, self.parent().columnWidth(index.column()) - 18))
        self.cache[cache_key] = document
        while len(self.cache) > 128:
            self.cache.popitem(last=False)
        return document

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonPress:
            self.press = event.position().toPoint()
        if (event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton
                and self.press is not None and
                (event.position().toPoint() - self.press).manhattanLength() < 4):
            document = self.document(option, index)
            from PySide6.QtCore import QPointF
            point = event.position() - QPointF(option.rect.topLeft()) - QPointF(8, 6)
            target = document.documentLayout().anchorAt(point)
            if target and self.open_link:
                self.open_link(QUrl(target))
                return True
        return super().editorEvent(event, model, option, index)

    def createEditor(self, parent, option, index):
        editor = QPlainTextEdit(parent)
        editor.setAccessibleName("Tabellenzelle bearbeiten")
        return editor

    def setEditorData(self, editor, index):
        import re
        editor.setPlainText(re.sub(r"<br(?:/| /)?>", "\n", str(index.data() or "")))
        editor.selectAll()

    def setModelData(self, editor, model, index):
        model.setData(index, editor.toPlainText(), Qt.EditRole)

    def eventFilter(self, editor, event):
        if isinstance(editor, QPlainTextEdit) and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Escape:
                self.closeEditor.emit(editor, QAbstractItemDelegate.RevertModelCache)
                return True
            if event.key() in {Qt.Key_Return, Qt.Key_Enter}:
                if event.modifiers() & Qt.ShiftModifier:
                    editor.insertPlainText("\n")
                else:
                    self.commitData.emit(editor)
                    self.closeEditor.emit(editor, QAbstractItemDelegate.NoHint)
                return True
            if event.key() in {Qt.Key_Tab, Qt.Key_Backtab}:
                backwards = event.key() == Qt.Key_Backtab or event.modifiers() & Qt.ShiftModifier
                self.commitData.emit(editor)
                self.closeEditor.emit(editor, QAbstractItemDelegate.NoHint)
                self.parent().parent().next_cell(bool(backwards))
                return True
        return super().eventFilter(editor, event)

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
