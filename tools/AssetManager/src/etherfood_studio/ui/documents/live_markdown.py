"""Edit source-mapped Markdown blocks in one surface without rich-text round trips."""

import re

from markdown_it import MarkdownIt
from PySide6.QtCore import QEvent, QSignalBlocker, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QFontDatabase, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QFrame, QHBoxLayout, QInputDialog, QMenu, QPlainTextEdit,
    QScrollArea, QStackedLayout, QVBoxLayout, QWidget,
)

from ..appearance import ActionButton, appearance
from .markdown_source import MarkdownTable
from .preview import HEADING_SIZES, SafePreview
from .table_editor import MarkdownTableEditor

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
        self.table_editor = None
        self.view.activated.connect(lambda: host.activate(self))
        self.view.checkbox_toggled.connect(self.toggle_checkbox)
        self.view.set_checkbox_read_only(host.isReadOnly())
        self.source.textChanged.connect(self.changed)
        for widget in (self.view, self.source):
            widget.setContextMenuPolicy(Qt.CustomContextMenu)
            widget.customContextMenuRequested.connect(
                lambda point, field=widget: self.show_menu(field, point))
        self.render()

    def render(self) -> None:
        try:
            self.view.preview(self.host.toPlainText()[self.start:self.end]
                              + "\n\n" + self.references)
        except (RuntimeError, ValueError):
            self.view.setPlainText("Vorschau nicht verfügbar; anklicken und Quelltext bearbeiten.")
        self.stack.setCurrentWidget(self.view)
        model = MarkdownTable.parse(self.host.toPlainText()[self.start:self.end])
        if self.table_editor:
            self.stack.removeWidget(self.table_editor)
            self.table_editor.deleteLater()
            self.table_editor = None
        if model is not None:
            self.table_editor = MarkdownTableEditor(model, self.host.isReadOnly(),
                                                     references=self.references)
            self.table_editor.source_changed.connect(self.edit_structured)
            self.table_editor.undo_requested.connect(self.host.undo)
            self.table_editor.redo_requested.connect(self.host.redo)
            self.stack.addWidget(self.table_editor)
            self.stack.setCurrentWidget(self.table_editor)
        self.fit()

    def edit_structured(self, value: str) -> None:
        if self.host.isReadOnly():
            return
        with QSignalBlocker(self.source):
            self.source.setPlainText(value)
        self.host.replace_block(self, value)
        self.fit()

    def toggle_checkbox(self, offset: int, checked: bool) -> None:
        value = self.host.toPlainText()[self.start:self.end]
        if not self.host.isReadOnly() and 0 <= offset < len(value):
            self.edit_structured(value[:offset] + ("x" if checked else " ") + value[offset + 1:])

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
        if self.table_editor and self.stack.currentWidget() is self.table_editor:
            self.setFixedHeight(self.table_editor.sizeHint().height())
            return
        if self.stack.currentWidget() is self.source:
            document = self.source.document()
            last = max(len(self.source.toPlainText().rstrip().splitlines()) - 1,
                       self.source.textCursor().blockNumber(), 0)
            lines = sum(max(1, document.findBlockByNumber(i).layout().lineCount())
                        for i in range(last + 1))
            height = lines * self.source.fontMetrics().lineSpacing()
        else:
            height = self.view.document().size().height()
        self.setFixedHeight(max(48, min(1200, int(height + 18))))
        self.view.position_checkboxes()

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
    modeChanged = Signal(str)

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
        self.mode = "md"
        self.setFocusPolicy(Qt.StrongFocus)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        modes = QHBoxLayout()
        self.mode_buttons = QButtonGroup(self)
        for title, mode, hint in (("MD", "md", "Gerendertes Markdown; Blöcke direkt bearbeiten"),
                                  ("Code", "code", "Vollständigen Markdown-Quelltext bearbeiten")):
            button = ActionButton(title, "markdown_mode_" + mode)
            button.setAccessibleName(hint)
            button.setToolTip(hint)
            button.setCheckable(True)
            button.setChecked(mode == self.mode)
            button.clicked.connect(lambda checked=False, value=mode: self.set_mode(value))
            self.mode_buttons.addButton(button)
            modes.addWidget(button)
        modes.addStretch(1)
        self.alignment_buttons = QButtonGroup(self)
        for title, key in (("Links", "left"), ("Mittig", "center"), ("Rechts", "right"),
                           ("Volle Breite", "full")):
            button = ActionButton(title, "document_align_" + key)
            button.setCheckable(True)
            button.setToolTip("Dokumentationsfläche: " + title)
            button.clicked.connect(lambda checked=False, value=key: self.set_alignment(value))
            self.alignment_buttons.addButton(button)
            modes.addWidget(button)
        layout.addLayout(modes)
        self.surface_row = QHBoxLayout()
        self.surface_widget = QWidget()
        self.surface = QStackedLayout(self.surface_widget)
        self.surface.setContentsMargins(0, 0, 0, 0)
        self.surface_row.addWidget(self.surface_widget)
        layout.addLayout(self.surface_row, 1)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.page = QWidget()
        self.page_layout = QVBoxLayout(self.page)
        self.page_layout.setContentsMargins(8, 8, 8, 8)
        self.page_layout.setSpacing(0)
        self.scroll.setWidget(self.page)
        self.surface.addWidget(self.scroll)
        self.code_source = QPlainTextEdit()
        self.code_source.setObjectName("markdown_code_source")
        self.code_source.setAccessibleName("Vollständiger Markdown-Quelltext")
        self.code_source.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        self.code_source.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.code_source.installEventFilter(self)
        self.code_source.textChanged.connect(self._code_changed)
        self.code_source.setContextMenuPolicy(Qt.CustomContextMenu)
        self.code_source.customContextMenuRequested.connect(self.show_code_context)
        self.surface.addWidget(self.code_source)
        self.scroll.setContextMenuPolicy(Qt.CustomContextMenu)
        self.scroll.customContextMenuRequested.connect(self.show_context)
        settings = appearance().settings
        self.set_alignment(str(settings.value("appearance/document_alignment", "full"))
                           if settings is not None else "full", persist=False)
        self.rebuild()

    def set_alignment(self, alignment: str, *, persist: bool = True) -> None:
        self.alignment = alignment if alignment in {"left", "center", "right", "full"} else "full"
        self.surface_widget.setMaximumWidth(16777215 if self.alignment == "full" else 820)
        self.surface_row.setAlignment(self.surface_widget, {
            "left": Qt.AlignLeft, "center": Qt.AlignHCenter, "right": Qt.AlignRight,
            "full": Qt.AlignmentFlag(0),
        }[self.alignment])
        for button in self.alignment_buttons.buttons():
            button.setChecked(button.objectName() == "document_align_" + self.alignment)
        settings = appearance().settings
        if persist and settings is not None:
            settings.setValue("appearance/document_alignment", self.alignment)
            settings.sync()

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
        self.code_source.setReadOnly(value)
        for block in self.blocks:
            block.source.setReadOnly(value)
            block.view.set_checkbox_read_only(value)
            if block.table_editor:
                block.table_editor.set_read_only(value)
        if value and self.active:
            self.active.render()
            self.active = None

    def isReadOnly(self) -> bool:
        return self._read_only

    def setPlaceholderText(self, text: str) -> None:
        self._placeholder = text
        self.code_source.setPlaceholderText(text)
        for block in self.blocks:
            block.source.setPlaceholderText(text)

    def placeholderText(self) -> str:
        return self._placeholder

    def set_mode(self, mode: str) -> None:
        if mode not in {"md", "code"}:
            raise ValueError("Unknown Markdown editor mode")
        if self.mode == mode:
            return
        self.mode = mode
        self.active = None
        for button in self.mode_buttons.buttons():
            button.setChecked(button.objectName() == "markdown_mode_" + mode)
        self.rebuild()
        self.surface.setCurrentWidget(self.code_source if mode == "code" else self.scroll)
        if mode == "code":
            self.code_source.setFocus()
        self.modeChanged.emit(mode)

    def _sync_code(self) -> None:
        # Loading an unchanged source must not normalize line endings or mark it dirty.
        if self.code_source.toPlainText() == self._text:
            return
        cursor = self.code_source.textCursor().position()
        scroll = self.code_source.verticalScrollBar().value()
        with QSignalBlocker(self.code_source):
            self.code_source.setPlainText(self._text)
        selection = self.code_source.textCursor()
        selection.setPosition(min(cursor, self.code_source.document().characterCount() - 1))
        self.code_source.setTextCursor(selection)
        self.code_source.verticalScrollBar().setValue(scroll)

    def _code_changed(self) -> None:
        if self.mode != "code" or self._read_only:
            return
        value, previous = self.code_source.toPlainText(), self._text
        if value == previous:
            return
        start = 0
        limit = min(len(value), len(previous))
        while start < limit and value[start] == previous[start]:
            start += 1
        tail = 0
        while tail < limit - start and value[-tail - 1] == previous[-tail - 1]:
            tail += 1
        self._undo.append((start, previous[start:len(previous) - tail],
                           value[start:len(value) - tail]))
        self._undo = self._undo[-100:]
        self._redo.clear()
        self._text = value
        self.textChanged.emit()

    def eventFilter(self, watched, event) -> bool:
        if (watched is self.code_source
                and event.type() in {QEvent.ShortcutOverride, QEvent.KeyPress}):
            undo = event.matches(QKeySequence.Undo)
            redo = event.matches(QKeySequence.Redo)
            if undo or redo:
                if event.type() == QEvent.KeyPress:
                    self.undo() if undo else self.redo()
                event.accept()
                return True
        return super().eventFilter(watched, event)

    def rebuild(self) -> None:
        if self.mode == "code":
            self._sync_code()
            return
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
        if self.mode != "md" or self._read_only or block not in self.blocks:
            return
        if self.active and self.active is not block:
            self.active.render()
        if block.table_editor:
            block.stack.setCurrentWidget(block.table_editor)
            block.table_editor.table.setFocus()
            return
        self.active = block
        block.style_source()
        block.stack.setCurrentWidget(block.source)
        block.fit()
        block.source.setFocus()

    def finish_if_unfocused(self, block: MarkdownBlock) -> None:
        if (not self._rebuilding and self.active is block and not block.source.hasFocus()
                and QApplication.activePopupWidget() is None):
            focus = QApplication.focusWidget()
            if focus and any(other is not block and other.isAncestorOf(focus)
                             for other in self.blocks):
                # Do not destroy the table cell/checkbox which just received focus.
                self.active = None
                block.render()
                return
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
        focus = QApplication.focusWidget()
        return super().hasFocus() or bool(focus and self.isAncestorOf(focus))

    def setFocus(self, reason=Qt.OtherFocusReason) -> None:
        if self.mode == "code":
            self.code_source.setFocus(reason)
        elif not self._read_only:
            self.activate(self.active or self.blocks[0])
        else:
            super().setFocus(reason)

    def keyPressEvent(self, event) -> None:
        if event.matches(QKeySequence.Undo):
            self.undo()
            event.accept()
        elif event.matches(QKeySequence.Redo):
            self.redo()
            event.accept()
        elif self.mode == "code":
            self.code_source.keyPressEvent(event)
            event.accept()
        elif not self._read_only:
            focus = QApplication.focusWidget()
            block = next((block for block in self.blocks
                          if focus and block.isAncestorOf(focus)), self.active or self.blocks[0])
            if block.table_editor or (focus and focus.objectName() == "markdown_checkbox"):
                super().keyPressEvent(event)
                return
            self.activate(block)
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
        if self.mode == "code":
            self.code_source.setFocus()
            return
        block = next((b for b in self.blocks if b.start <= position < b.end), self.blocks[-1])
        self.activate(block)

    def context_menu(self, block=None, field=None) -> QMenu:
        if field is self.code_source:
            menu = QMenu(self)
            for title, callback, enabled in (
                ("Rückgängig", self.undo, bool(self._undo) and not self._read_only),
                ("Wiederholen", self.redo, bool(self._redo) and not self._read_only),
                ("Ausschneiden", field.cut,
                 field.textCursor().hasSelection() and not self._read_only),
                ("Kopieren", field.copy, field.textCursor().hasSelection()),
                ("Einfügen", field.paste, field.canPaste()),
                ("Alles auswählen", field.selectAll, True),
            ):
                menu.addAction(title, callback).setEnabled(enabled)
        else:
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
        source.triggered.connect(self.edit_whole_source)
        if self.mode == "code":
            menu.addAction("Gerendertes Markdown anzeigen", lambda: self.set_mode("md"))
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
        self.set_mode("code")

    def show_code_context(self, point) -> None:
        menu = self.context_menu(field=self.code_source)
        menu.exec(self.code_source.viewport().mapToGlobal(point))
        menu.deleteLater()

    def show_context(self, point) -> None:
        menu = self.context_menu()
        menu.exec(self.scroll.viewport().mapToGlobal(point))
        menu.deleteLater()
