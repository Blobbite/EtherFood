"""Edit source-mapped Markdown blocks in one surface without rich-text round trips."""

import re

from markdown_it import MarkdownIt
from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QFrame, QInputDialog, QMenu, QPlainTextEdit, QScrollArea, QStackedLayout,
    QVBoxLayout, QWidget,
)

from .preview import HEADING_SIZES, SafePreview

MAX_BLOCK_WIDGETS = 200


def markdown_spans(text: str) -> tuple[list[tuple[int, int]], str]:
    """Preserve exact source slices, including blank lines and reference definitions."""
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    parser = MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])
    environment = {}
    tokens = parser.parse(text, environment)
    starts = sorted({offsets[token.map[0]] for token in tokens
                     if token.level == 0 and token.map and token.nesting >= 0})
    if not starts or len(starts) > MAX_BLOCK_WIDGETS:
        return [(0, len(text))], ""
    starts[0] = 0
    ends = starts[1:] + [len(text)]
    references = "\n".join("".join(lines[value["map"][0]:value["map"][1]])
                            for value in environment.get("references", {}).values())
    return list(zip(starts, ends)), references


class MarkdownBlock(QWidget):
    def __init__(self, host, start: int, end: int, references: str) -> None:
        super().__init__()
        self.host, self.start, self.end = host, start, end
        self.references = references
        self.stack = QStackedLayout(self)
        self.stack.setContentsMargins(0, 0, 0, 0)
        self.view = SafePreview()
        self.view.setFrameShape(QFrame.NoFrame)
        self.source = QPlainTextEdit()
        self.source.setObjectName("markdown_block_source")
        self.source.setFrameShape(QFrame.NoFrame)
        self.source.setStyleSheet("QPlainTextEdit { border: 1px solid #729ac1; "
                                  "border-radius: 4px; padding: 3px; }")
        self.source.setPlainText(host.toPlainText()[start:end])
        self.source.setReadOnly(host.isReadOnly())
        self.source.installEventFilter(self)
        self.focus_timer = QTimer(self)
        self.focus_timer.setSingleShot(True)
        self.focus_timer.timeout.connect(lambda: self.host.finish_if_unfocused(self))
        self.stack.addWidget(self.view)
        self.stack.addWidget(self.source)
        self.view.activated.connect(lambda: host.activate(self))
        self.source.textChanged.connect(self.changed)
        for widget in (self.view, self.source):
            widget.setContextMenuPolicy(Qt.CustomContextMenu)
            widget.customContextMenuRequested.connect(
                lambda point, field=widget: self.show_menu(field, point))
        self.render()

    def render(self) -> None:
        try:
            self.view.preview(self.source.toPlainText() + "\n\n" + self.references)
        except (RuntimeError, ValueError):
            self.view.setPlainText("Vorschau nicht verfügbar; anklicken und Quelltext bearbeiten.")
        self.stack.setCurrentWidget(self.view)
        self.fit()

    def changed(self) -> None:
        self.host.replace_block(self, self.source.toPlainText())
        self.style_source()
        self.fit()

    def style_source(self) -> None:
        match = re.match(r"\s*(#{1,6})\s", self.source.toPlainText())
        font = QFont(self.view.document().defaultFont())
        if match:
            font.setPointSizeF(HEADING_SIZES[len(match[1]) - 1])
            font.setBold(True)
        self.source.setFont(font)

    def fit(self) -> None:
        width = max(80, self.width() - 14)
        self.view.document().setTextWidth(width)
        if self.stack.currentWidget() is self.source:
            lines = self.source.document().size().height()
            height = lines * self.source.fontMetrics().lineSpacing()
        else:
            height = self.view.document().size().height()
        self.setFixedHeight(max(48, min(1200, int(height + 18))))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.fit()

    def eventFilter(self, watched, event) -> bool:
        if watched is self.source and event.type() == QEvent.FocusOut:
            self.focus_timer.start(0)
        return super().eventFilter(watched, event)

    def show_menu(self, widget, point) -> None:
        menu = self.host.context_menu(self, widget)
        menu.exec(widget.viewport().mapToGlobal(point))
        menu.deleteLater()


class LiveMarkdownEditor(QWidget):
    textChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._text = ""
        self._read_only = False
        self._placeholder = ""
        self._undo = []
        self._redo = []
        self.blocks = []
        self.active = None
        self._rebuilding = False
        self.setFocusPolicy(Qt.StrongFocus)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.page = QWidget()
        self.page_layout = QVBoxLayout(self.page)
        self.page_layout.setContentsMargins(8, 8, 8, 8)
        self.page_layout.setSpacing(0)
        self.scroll.setWidget(self.page)
        layout.addWidget(self.scroll)
        self.scroll.setContextMenuPolicy(Qt.CustomContextMenu)
        self.scroll.customContextMenuRequested.connect(self.show_context)
        self.rebuild()

    def toPlainText(self) -> str:
        return self._text

    def setPlainText(self, text: str) -> None:
        self._text = text
        self._undo.clear()
        self._redo.clear()
        self.rebuild()
        self.textChanged.emit()

    def setReadOnly(self, value: bool) -> None:
        self._read_only = value
        for block in self.blocks:
            block.source.setReadOnly(value)
        if value and self.active:
            self.active.render()
            self.active = None

    def isReadOnly(self) -> bool:
        return self._read_only

    def setPlaceholderText(self, text: str) -> None:
        self._placeholder = text
        for block in self.blocks:
            block.source.setPlaceholderText(text)

    def placeholderText(self) -> str:
        return self._placeholder

    def rebuild(self, *, whole_source: bool = False) -> None:
        self._rebuilding = True
        self.active = None
        scroll = self.scroll.verticalScrollBar().value()
        while self.page_layout.count():
            item = self.page_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        self.blocks = []
        spans, references = markdown_spans(self._text)
        if whole_source:
            spans = [(0, len(self._text))]
        for start, end in spans:
            block = MarkdownBlock(self, start, end, references)
            block.source.setPlaceholderText(self._placeholder)
            if not self._text:
                block.view.setPlainText(self._placeholder or "Hier klicken und schreiben …")
            self.blocks.append(block)
            self.page_layout.addWidget(block)
        self.page_layout.addStretch(1)
        self.scroll.verticalScrollBar().setValue(scroll)
        self._rebuilding = False

    def activate(self, block: MarkdownBlock) -> None:
        if self._read_only or block not in self.blocks:
            return
        if self.active and self.active is not block:
            self.active.render()
        self.active = block
        block.style_source()
        block.stack.setCurrentWidget(block.source)
        block.fit()
        block.source.setFocus()

    def finish_if_unfocused(self, block: MarkdownBlock) -> None:
        if (not self._rebuilding and self.active is block and not block.source.hasFocus()
                and QApplication.activePopupWidget() is None):
            self.rebuild()

    def replace_block(self, block: MarkdownBlock, value: str) -> None:
        if self._rebuilding or self._read_only:
            return
        start, end = block.start, block.end
        previous = self._text[start:end]
        if previous == value:
            return
        self._undo.append((start, previous, value))
        self._undo = self._undo[-100:]
        self._redo.clear()
        self._text = self._text[:start] + value + self._text[end:]
        delta = len(value) - len(previous)
        for other in self.blocks:
            if other.start > start:
                other.start += delta
                other.end += delta
        block.end = start + len(value)
        self.textChanged.emit()

    def undo(self) -> None:
        if self._undo and not self._read_only:
            start, previous, value = self._undo.pop()
            self._redo.append((start, previous, value))
            self._text = self._text[:start] + previous + self._text[start + len(value):]
            self.rebuild()
            self.textChanged.emit()

    def redo(self) -> None:
        if self._redo and not self._read_only:
            start, previous, value = self._redo.pop()
            self._undo.append((start, previous, value))
            self._text = self._text[:start] + value + self._text[start + len(previous):]
            self.rebuild()
            self.textChanged.emit()

    def hasFocus(self) -> bool:
        return super().hasFocus() or bool(self.active and self.active.source.hasFocus())

    def setFocus(self, reason=Qt.OtherFocusReason) -> None:
        if not self._read_only:
            self.activate(self.active or self.blocks[0])
        else:
            super().setFocus(reason)

    def keyPressEvent(self, event) -> None:
        if not self._read_only:
            self.activate(self.active or self.blocks[0])
            # Calling sendEvent here would propagate ignored modifier keys back
            # through this parent and recurse indefinitely.
            self.active.source.keyPressEvent(event)
            event.accept()
        else:
            super().keyPressEvent(event)

    def insert_template(self, kind: str, *, position: int | None = None,
                        columns: int = 2, rows: int = 2) -> None:
        if self._read_only:
            return
        fence = chr(96) * 3
        templates = {"heading": "## Überschrift\n", "code": fence + "text\nCode\n" + fence + "\n",
                     "list": "- Stichpunkt\n", "todo": "- [ ] Aufgabe\n",
                     "quote": "> Zitat\n", "link": "[Linktext](https://example.org)\n"}
        if kind == "table":
            columns, rows = max(1, min(12, columns)), max(1, min(50, rows))
            header = "| " + " | ".join(f"Spalte {i + 1}" for i in range(columns)) + " |\n"
            value = header + "| " + " | ".join(["---"] * columns) + " |\n"
            value += ("| " + " | ".join(["Text"] * columns) + " |\n") * rows
        else:
            value = templates[kind]
        position = len(self._text) if position is None else position
        value = ("\n\n" if position and not self._text[:position].endswith("\n\n") else "") + value
        value += "\n"
        self._undo.append((position, "", value))
        self._undo = self._undo[-100:]
        self._redo.clear()
        self._text = self._text[:position] + value + self._text[position:]
        self.rebuild()
        self.textChanged.emit()
        block = next((b for b in self.blocks if b.start <= position < b.end), self.blocks[-1])
        self.activate(block)

    def context_menu(self, block=None, field=None) -> QMenu:
        menu = field.createStandardContextMenu() if field else QMenu(self)
        menu.addSeparator()
        position = block.end if block else len(self._text)
        for title, kind in (("Überschrift einfügen", "heading"), ("Tabelle einfügen …", "table"),
                            ("Codeblock einfügen", "code"), ("Liste einfügen", "list"),
                            ("Aufgabenliste einfügen", "todo"), ("Zitat einfügen", "quote"),
                            ("Link einfügen", "link")):
            action = menu.addAction(title)
            action.setObjectName("markdown_insert_" + kind)
            action.setEnabled(not self._read_only)
            action.triggered.connect(lambda checked=False, value=kind:
                                     self.insert_dialog(value, position))
        source = menu.addAction("Gesamten Markdown-Quelltext bearbeiten")
        source.setObjectName("markdown_full_source")
        source.setEnabled(not self._read_only)
        source.triggered.connect(self.edit_whole_source)
        return menu

    def insert_dialog(self, kind: str, position: int) -> None:
        columns, rows = 2, 2
        if kind == "table":
            columns, accepted = QInputDialog.getInt(self, "Tabelle", "Spalten", 2, 1, 12)
            if not accepted:
                return
            rows, accepted = QInputDialog.getInt(self, "Tabelle", "Datenzeilen", 2, 1, 50)
            if not accepted:
                return
        self.insert_template(kind, position=position, columns=columns, rows=rows)

    def edit_whole_source(self) -> None:
        if not self._read_only:
            self.rebuild(whole_source=True)
            self.activate(self.blocks[0])

    def show_context(self, point) -> None:
        menu = self.context_menu()
        menu.exec(self.scroll.viewport().mapToGlobal(point))
        menu.deleteLater()
