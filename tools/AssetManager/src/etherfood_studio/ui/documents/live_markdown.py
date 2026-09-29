"""Edit source-mapped Markdown blocks in one surface without rich-text round trips."""

import re

from PySide6.QtCore import QEvent, QSignalBlocker, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QFontDatabase, QKeySequence, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog, QFrame, QGridLayout,
        QHBoxLayout, QInputDialog,
    QLabel, QMenu, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QStackedLayout,
    QVBoxLayout, QWidget,
)

from ..appearance import ActionButton, appearance
from .markdown_source import MarkdownTable
from .preview import HEADING_SIZES, SafePreview
from .table_editor import MarkdownTableEditor
from .markdown_syntax import (
    code_content, headings, link_spans, parser, preserved_edit, python_position,
    source_position, utf16_position,
)
from .media import MediaControls, MediaSession

MAX_BLOCK_WIDGETS = 200


def image_mime(mime):
    from pathlib import Path
    return mime.hasImage() or any(
        url.isLocalFile() and Path(url.toLocalFile()).suffix.lower()
        in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
        for url in mime.urls())


def markdown_spans(text: str) -> tuple[list[tuple[int, int]], str]:
    """Preserve exact source slices, including blank lines and reference definitions."""
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    syntax = parser()
    environment = {}
    tokens = syntax.parse(text, environment)
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
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedLayout()
        self.outer.addLayout(self.stack)
        self.controls = None
        self.code_controls = None
        self.stack.setContentsMargins(0, 0, 0, 0)
        self.view = SafePreview()
        self.view.local_link = host.local_link
        self.view.local_resource = host.local_resource
        self.view.media = host.media
        host.media.changed.connect(self.media_changed)
        self.view.setFrameShape(QFrame.NoFrame)
        self.source = QPlainTextEdit()
        self.source.setObjectName("markdown_block_source")
        self.source.setFrameShape(QFrame.NoFrame)
        self.source.setStyleSheet("QPlainTextEdit { border: 1px solid #729ac1; "
                                  "border-radius: 4px; padding: 3px; }")
        self.source.setPlainText(host.toPlainText()[start:end])
        self.source.setReadOnly(host.isReadOnly())
        self.source.installEventFilter(self)
        self.source.installEventFilter(host)
        self.source.viewport().installEventFilter(host)
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
        value = self.host.toPlainText()[self.start:self.end]
        roots = [t for t in parser().parse(value) if t.level == 0 and t.map and t.nesting >= 0]
        try:
            if len(roots) > MAX_BLOCK_WIDGETS:
                self.view.setPlainText("Großes Dokument: verlustfreie Quelltextansicht. "
                                       "Zum Bearbeiten Code wählen.\n\n" + value)
            else:
                self.view.preview(value, references=self.references)
            self.view.set_content_alignment(self.host.alignment)
        except (RuntimeError, ValueError):
            self.view.setPlainText("Vorschau nicht verfügbar; anklicken und Quelltext bearbeiten.")
        self.stack.setCurrentWidget(self.view)
        model = MarkdownTable.parse(value)
        if self.table_editor:
            self.stack.removeWidget(self.table_editor)
            self.table_editor.deleteLater()
            self.table_editor = None
        if model is not None:
            self.table_editor = MarkdownTableEditor(model, self.host.isReadOnly(),
                                                     references=self.references,
                                                         media=self.host.media,
                                                     open_link=self.view._open_link,
                                                     reference_handler=self.table_reference)
            self.table_editor.source_changed.connect(self.edit_structured)
            self.table_editor.geometry_changed.connect(self.fit)
            self.table_editor.undo_requested.connect(self.host.undo)
            self.table_editor.redo_requested.connect(self.host.redo)
            self.stack.addWidget(self.table_editor)
            self.stack.setCurrentWidget(self.table_editor)
        if any(t.type == "table_open" for t in roots) and model is None:
            self.view.setPlainText("Tabelle prüfbedürftig; vollständiger Quelltext:\n\n" + value)
        for widget in (self.controls, self.code_controls):
            if widget:
                self.outer.removeWidget(widget)
                widget.deleteLater()
        self.controls = self.code_controls = None
        if len(roots) == 1 and roots[0].type in {"fence", "code_block"}:
            token = roots[0]
            self.view.setLineWrapMode(self.view.LineWrapMode.NoWrap)
            self.code_controls = QWidget()
            bar = QHBoxLayout(self.code_controls)
            bar.setContentsMargins(0, 0, 0, 0)
            language = QLabel(token.info or "Text")
            language.setTextFormat(Qt.PlainText)
            bar.addWidget(language)
            copy = QPushButton("Code kopieren")
            content = code_content(value, token)
            copy.clicked.connect(lambda: QApplication.clipboard().setText(content))
            bar.addWidget(copy)
            if token.type == "fence" and token.info.strip().lower() == "svg":
                from urllib.parse import quote
                source = "studio-svg:" + quote(token.content, safe="")
                toggle = QPushButton("SVG-Vorschau")
                toggle.setCheckable(True)
                toggle.toggled.connect(lambda checked, s=source, v=value:
                                       self.svg_preview(checked, s, v))
                bar.addWidget(toggle)
            self.outer.addWidget(self.code_controls)
        if self.view.media_sources:
            self.controls = MediaControls(self.host.media, self.view.media_sources)
            self.controls.source_change.connect(self.change_image)
            for _, buttons, _ in self.controls.rows.values():
                buttons["source"].setEnabled(not self.host.isReadOnly())
            self.outer.addWidget(self.controls)
        self.fit()

    def change_image(self, source):
        span = next((item for item in link_spans(self.host.toPlainText())
                     if self.start <= item[0] < self.end and item[2].type == "image"
                     and item[2].attrGet("src") == source), None)
        if span:
            self.host.reference_dialog(image=True, span=span)

    def table_reference(self, row, column, action, token):
        if self.host.isReadOnly() or not self.table_editor:
            return
        cell = self.table_editor.model.cell_range(row, column)
        if cell is None:
            return
        start, end = (self.start + offset for offset in cell)
        if action in {"image", "link"}:
            self.host.reference_dialog(image=action == "image", selection_override=(start,
                end), table_cell=True)
        else:
            span = next((s for s in link_spans(self.host.toPlainText()) if start <= s[0] < end
                         and s[2].type == token.type and s[2].attrs == token.attrs), None)
            if span and action == "remove":
                self.host.apply_edit(span[0], span[1], self.host.link_label(*span[:2]))
            elif span:
                self.host.reference_dialog(image=token.type == "image", span=span, table_cell=True)
        for block in self.host.blocks:
            if block.start <= start < block.end and block.table_editor:
                block.table_editor.table.setCurrentCell(row, column)
                block.table_editor.table.setFocus()

    def svg_preview(self, checked, source, value):
        if checked:
            self.view.preview("![SVG-Vorschau](" + source + ")")
            if not self.controls:
                self.controls = MediaControls(self.host.media, [(source, "SVG-Vorschau")])
                self.outer.addWidget(self.controls)
        else:
            self.view.preview(value)
        self.fit()

    def media_changed(self, key):
        if key not in self.view.media_insets:
            return
        scrollbar = self.host.scroll.verticalScrollBar()
        position, height = scrollbar.value(), self.height()
        above = self.y() + height <= position
        self.view.update_media(key)
        self.fit()
        if above and self.height() != height and not self.host._rebuilding:
            scrollbar.setValue(position + self.height() - height)

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
        original = self.host.toPlainText()[self.start:self.end]
        start, end, value = preserved_edit(original, self.source.toPlainText())
        self.host.replace_block(self, original[:start] + value + original[end:])
        self.style_source()
        self.fit()

    def style_source(self) -> None:
        match = re.match(r"\s*(#{1,6})\s", self.source.toPlainText())
        font = QFont(self.view.document().defaultFont())
        level = len(match[1]) if match else 0
        if not level:
            tokens = parser().parse(self.source.toPlainText())
            if tokens and tokens[0].type == "heading_open":
                level = int(tokens[0].tag[1:])
        if level:
            font.setPointSizeF(HEADING_SIZES[level - 1])
            font.setBold(True)
        self.source.setFont(font)

    def fit(self) -> None:
        extra = sum(w.sizeHint().height() for w in (self.controls, self.code_controls) if w)
        width = max(80, self.width() - 14)
        self.view.document().setTextWidth(width)
        if self.table_editor and self.stack.currentWidget() is self.table_editor:
            self.setFixedHeight(self.table_editor.sizeHint().height() + extra)
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
        self.setFixedHeight(max(48, min(1200, int(height + 18))) + extra)
        self.view.position_checkboxes()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.fit()

    def eventFilter(self, watched, event) -> bool:
        if watched is self.source and event.type() == QEvent.FocusOut:
            self.focus_timer.start(0)
        return super().eventFilter(watched, event)

    def show_menu(self, widget, point) -> None:
        menu = self.host.context_menu(self, widget, point)
        menu.exec(widget.viewport().mapToGlobal(point))
        menu.deleteLater()


class LiveMarkdownEditor(QWidget):
    textChanged = Signal()
    modeChanged = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._text = ""
        self.local_link = None
        self.local_resource = None
        self.media = MediaSession(self)
        self.restore_media_settings()
        self.document_service = None
        self.document_id = None
        self.import_image = None
        self._read_only = False
        self._placeholder = ""
        self._undo = []
        self._redo = []
        self.blocks = []
        self.active = None
        self._rebuilding = False
        self._dialog_active = False
        self._code_press = None
        self._selection = (0, 0)
        self.mode = "md"
        self.alignment = "left"
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
        for title, key in (("Links", "left"), ("Mittig", "center"), ("Rechts", "right")):
            button = ActionButton(title, "document_align_" + key)
            button.setCheckable(True)
            button.setToolTip("Inhalt bei voller Dokumentbreite: " + title)
            button.clicked.connect(lambda checked=False, value=key: self.set_alignment(value))
            self.alignment_buttons.addButton(button)
            modes.addWidget(button)
        layout.addLayout(modes)
        media_settings = QGridLayout()
        self.media_policy = QComboBox()
        self.media_policy.setAccessibleName("Richtlinie für externe Bilder")
        for title, value in (("Nachfragen", "ask"), ("HTTPS-Bilder automatisch laden", "https"),
                              ("Externe Bilder blockieren", "block")):
            self.media_policy.addItem(title, value)
        self.media_policy.setCurrentIndex(self.media_policy.findData(self.media.policy))
        self.media_policy.currentIndexChanged.connect(self.change_media_policy)
        media_settings.addWidget(self.media_policy, 0, 0)
        for column, (title, field) in enumerate((("Animationen automatisch abspielen", "autoplay"),
                                                ("Reduzierte Bewegung", "reduced_motion"))):
            checkbox = QCheckBox(title)
            checkbox.setChecked(getattr(self.media, field))
            checkbox.toggled.connect(lambda value, name=field: self.motion_setting(name, value))
            media_settings.addWidget(checkbox, 1, column)
        limits = QPushButton("Mediengrenzen …")
        limits.clicked.connect(self.media_limits_dialog)
        media_settings.addWidget(limits, 0, 1)
        layout.addLayout(media_settings)
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
        self.code_source.viewport().installEventFilter(self)
        self.code_source.setAcceptDrops(True)
        self.setAcceptDrops(True)
        self.code_source.textChanged.connect(self._code_changed)
        self.code_source.setContextMenuPolicy(Qt.CustomContextMenu)
        self.code_source.customContextMenuRequested.connect(self.show_code_context)
        self.surface.addWidget(self.code_source)
        self.scroll.setContextMenuPolicy(Qt.CustomContextMenu)
        self.scroll.customContextMenuRequested.connect(self.show_context)
        settings = appearance().settings
        self.set_alignment(str(settings.value("appearance/document_alignment", "left"))
                           if settings is not None else "left", persist=False)
        self.rebuild()

    def bind_document(self, service, identifier):
        self.document_service, self.document_id = service, identifier
        self.media.bind(service, identifier)

    def change_media_policy(self):
        value = self.media_policy.currentData()
        if value == "https" and QMessageBox.question(
                self, "Externe Bilder automatisch laden?",
                    "Öffentliche HTTPS-Bilder in diesem Fenster automatisch laden?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            with QSignalBlocker(self.media_policy):
                self.media_policy.setCurrentIndex(self.media_policy.findData(self.media.policy))
            return
        self.media.set_policy(value)
        self.persist_media_settings()

    def motion_setting(self, name, value):
        setattr(self.media, name, value)
        self.persist_media_settings()
        if name == "reduced_motion" and value:
            for item in self.media.resources.values():
                if item.movie and item.state == "ready":
                    self.media.action(item, "pause", self)

    def restore_media_settings(self):
        from .media_source import MediaLimits
        settings = appearance().settings
        if not settings:
            return
        policy = str(settings.value("markdown/media_policy", "ask"))
        self.media.policy = policy if policy in {"ask", "https", "block"} else "ask"
        for key, default in (("autoplay", True), ("reduced_motion", False)):
            setattr(self.media, key, str(settings.value("markdown/" + key,
                default)).lower() == "true")
        fields = {}
        defaults = MediaLimits()
        for name in defaults.__dataclass_fields__:
            default = getattr(defaults, name)
            try:
                value = type(default)(settings.value("markdown/limits/" + name, default))
                if value > 0 and value <= default * 16:
                    fields[name] = value
            except (ValueError, TypeError):
                pass
        self.media.limits = MediaLimits(**fields)

    def persist_media_settings(self):
        settings = appearance().settings
        if settings:
            settings.setValue("markdown/media_policy", self.media.policy)
            for name in ("autoplay", "reduced_motion"):
                settings.setValue("markdown/" + name, getattr(self.media, name))
            for name in self.media.limits.__dataclass_fields__:
                settings.setValue("markdown/limits/" + name, getattr(self.media.limits, name))
            settings.sync()

    def media_limits_dialog(self):
        from PySide6.QtWidgets import QDialogButtonBox, QDoubleSpinBox, QFormLayout, QSpinBox
        from .media_source import MediaLimits
        dialog = QDialog(self)
        dialog.setWindowTitle("Grenzen der Markdown-Medienanzeige")
        form, fields = QFormLayout(dialog), {}
        definitions = (("transferred", "Übertragung je Bild (MiB)", 1024 * 1024),
                       ("pixels", "Pixel je Frame (Millionen)", 1_000_000),
                       ("concurrent", "Gleichzeitige Abrufe", 1),
                       ("redirects", "Weiterleitungen", 1),
                       ("inactivity", "Inaktivität (Sekunden)", 1),
                       ("total", "Gesamtdauer (Sekunden)", 1),
                       ("memory", "Bild- und Framespeicher (MiB)", 1024 * 1024))
        for name, title, unit in definitions:
            field = QDoubleSpinBox() if name in {"inactivity", "total"} else QSpinBox()
            numeric = float if name in {"inactivity", "total"} else int
            field.setRange(1, numeric(getattr(MediaLimits(), name) * 16 / unit))
            field.setValue(numeric(getattr(self.media.limits, name) / unit))
            field.setAccessibleName(title)
            form.addRow(title, field)
            fields[name] = field, unit
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() == QDialog.Accepted:
            values = {name: field.value() * unit for name, (field, unit) in fields.items()}
            self.media.stop()
            self.media.limits = MediaLimits(**values)
            self.persist_media_settings()
            self.rebuild()
        dialog.deleteLater()

    def closeEvent(self, event):
        self.media.stop()
        super().closeEvent(event)

    def set_alignment(self, alignment: str, *, persist: bool = True) -> None:
        self.alignment = alignment if alignment in {"left", "center", "right"} else "left"
        for block in self.blocks:
            block.view.set_content_alignment(self.alignment)
            block.fit()
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
        self._selection = (0, 0)
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
            if block.controls:
                for _, buttons, _ in block.controls.rows.values():
                    buttons["source"].setEnabled(not value)
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

    def selection(self):
        field = (self.code_source if self.mode == "code" else
                 self.active.source if self.active else None)
        if field is None:
            return self._selection
        cursor = field.textCursor()
        offset = 0 if field is self.code_source else self.active.start
        raw = (self._text[offset:] if field is self.code_source else
               self._text[self.active.start:self.active.end])
        plain = field.toPlainText()
        def position(value):
            target = python_position(plain, value)
            return offset + source_position(raw, target)
        return position(cursor.selectionStart()), position(cursor.selectionEnd())

    def select_source(self, start, end, *, activate=True):
        self._selection = (start, end)
        if self.mode == "code":
            field, offset = self.code_source, 0
        else:
            block = next((b for b in self.blocks if b.start <= start <= b.end), self.blocks[-1])
            self.scroll.ensureWidgetVisible(block)
            if not activate:
                from .markdown_syntax import visible
                selected = visible(parser().parseInline(self._text[start:end])[0].children)
                if selected:
                    found = block.view.document().find(selected)
                    if not found.isNull():
                        block.view.setTextCursor(found)
                return
            self.activate(block)
            field, offset = block.source, block.start
        cursor = field.textCursor()
        prefix = self._text[offset:start].replace("\r\n", "\n").replace("\r", "\n")
        selected = self._text[start:end].replace("\r\n", "\n").replace("\r", "\n")
        cursor.setPosition(utf16_position(prefix, len(prefix)))
        cursor.setPosition(utf16_position(prefix + selected, len(prefix + selected)),
            QTextCursor.KeepAnchor)
        field.setTextCursor(cursor)

    def apply_edit(self, start, end, value, *, selection=None):
        if self._read_only or self._text[start:end] == value:
            return
        previous = self._text[start:end]
        self._undo.append((start, previous, value))
        self._undo = self._undo[-100:]
        self._redo.clear()
        self._text = self._text[:start] + value + self._text[end:]
        self.rebuild()
        self.textChanged.emit()
        self.select_source(*(selection or (start + len(value), start + len(value))))

    def format_selection(self, kind):
        start, end = self.selection()
        for token in parser().parse(self._text):
            if token.type in {"fence", "code_block"} and token.map:
                lines = self._text.splitlines(keepends=True)
                left, right = len("".join(lines[:token.map[0]])), len("".join(lines[:token.map[1]]))
                if left <= start < right or (start < left < end):
                    QMessageBox.information(self, "Codeblock",
                        "Diese Auswahl ist Code. Im Quelltext bearbeiten.")
                    return
        value = self._text[start:end] or {"heading": "Überschrift", "code": "Code"}.get(kind,
            "Text")
        pairs = {"bold": ("**", "**"), "italic": ("*", "*"), "strike": ("~~", "~~"),
                 "inline": ("`", "`"), "heading": ("## ", ""), "list": ("- ", ""),
                 "todo": ("- [ ] ", ""), "quote": ("> ", "")}
        if kind == "code":
            runs = re.findall(r"`+", value)
            fence = "`" * max(3, max(map(len, runs), default=0) + 1)
            before, after = fence + "text\n", "\n" + fence
        else:
            before, after = pairs[kind]
        if kind in {"list", "todo", "quote"}:
            value = re.sub(r"(?<=\n)(?!$)", before, value)
        if kind == "inline" and "`" in value:
            before = after = "`" * (max(map(len, re.findall(r"`+", value))) + 1)
            value = " " + value + " "
        if kind in {"heading", "list", "todo", "quote", "code"}:
            before = ("\n" if start and self._text[start - 1] not in "\r\n" else "") + before
            after += "\n" if end < len(self._text) and self._text[end:end + 1] not in "\r\n" else ""
        newline = "\r\n" if "\r\n" in self._text else "\r" if "\r" in self._text else "\n"
        before, value, after = (part.replace("\r\n", "\n").replace("\n", newline)
                                for part in (before, value, after))
        replacement = before + value + after
        self.apply_edit(start, end, replacement, selection=(start + len(before), start
            + len(before) + len(value)))

    def scroll_section(self, identifier):
        from urllib.parse import unquote
        heading = next((h for h in headings(self._text)
            if h.identifier == unquote(identifier)), None)
        if heading is None:
            QMessageBox.information(self, "Abschnitt fehlt", "Abschnitt nicht gefunden: "
                + identifier)
            return False
        self.select_source(heading.offset, heading.offset, activate=False)
        if self.mode == "md":
            block = next(b for b in self.blocks if b.start <= heading.offset < b.end)
            block.setStyleSheet("MarkdownBlock { border: 2px solid #729ac1; }")
            timer = QTimer(block)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: block.setStyleSheet(""))
            timer.start(1500)
        return True

    def set_mode(self, mode: str) -> None:
        if mode not in {"md", "code"}:
            raise ValueError("Unknown Markdown editor mode")
        if self.mode == mode:
            return
        self._selection = self.selection()
        self.mode = mode
        self.active = None
        for button in self.mode_buttons.buttons():
            button.setChecked(button.objectName() == "markdown_mode_" + mode)
        self.rebuild()
        self.surface.setCurrentWidget(self.code_source if mode == "code" else self.scroll)
        if mode == "code":
            self.code_source.setFocus()
            self.select_source(*self._selection, activate=False)
        else:
            self.select_source(*self._selection, activate=False)
        self.modeChanged.emit(mode)

    def _sync_code(self) -> None:
        # Loading an unchanged source must not normalize line endings or mark it dirty.
        if self.code_source.toPlainText() == self._text:
            return
        cursor = self.code_source.textCursor().position()
        anchor = self.code_source.textCursor().anchor()
        scroll = self.code_source.verticalScrollBar().value()
        with QSignalBlocker(self.code_source):
            self.code_source.setPlainText(self._text)
        selection = self.code_source.textCursor()
        selection.setPosition(min(anchor, self.code_source.document().characterCount() - 1))
        selection.setPosition(min(cursor, self.code_source.document().characterCount() - 1),
            QTextCursor.KeepAnchor)
        self.code_source.setTextCursor(selection)
        self.code_source.verticalScrollBar().setValue(scroll)

    def _code_changed(self) -> None:
        if self.mode != "code" or self._read_only:
            return
        value, previous = self.code_source.toPlainText(), self._text
        if value == previous:
            return
        start, end, value = preserved_edit(previous, value)
        if previous[start:end] == value:
            return
        self._undo.append((start, previous[start:end], value))
        self._undo = self._undo[-100:]
        self._redo.clear()
        self._text = previous[:start] + value + previous[end:]
        self.textChanged.emit()

    def eventFilter(self, watched, event) -> bool:
        fields = [self.code_source] + [b.source for b in self.blocks]
        if (watched in [field.viewport() for field in fields]
                and event.type() in {QEvent.DragEnter, QEvent.DragMove, QEvent.Drop}
                and not self._read_only and image_mime(event.mimeData())):
            if event.type() == QEvent.Drop:
                self.paste_image(event.mimeData())
            event.acceptProposedAction()
            return True
        if (watched in fields
                and event.type() in {QEvent.ShortcutOverride, QEvent.KeyPress}):
            if event.matches(QKeySequence.Paste):
                mime = QApplication.clipboard().mimeData()
                if image_mime(mime):
                    if event.type() == QEvent.KeyPress and not self._read_only:
                        self.paste_image(mime)
                    event.accept()
                    return True
            undo = event.matches(QKeySequence.Undo)
            redo = event.matches(QKeySequence.Redo)
            if undo or redo:
                if event.type() == QEvent.KeyPress:
                    self.undo() if undo else self.redo()
                event.accept()
                return True
        if watched is self.code_source.viewport():
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._code_press = event.position().toPoint()
            elif event.type() == QEvent.MouseMove and self._code_press is not None:
                if (event.position().toPoint() - self._code_press).manhattanLength() > 4:
                    self._code_press = None
            elif event.type() == QEvent.MouseButtonRelease:
                pressed, self._code_press = self._code_press, None
                point = event.position().toPoint()
                if (pressed is not None and (point - pressed).manhattanLength() <= 4
                        and event.button() == Qt.LeftButton
                            and event.modifiers() & Qt.ControlModifier):
                    cursor = self.code_source.cursorForPosition(point)
                    offset = source_position(self._text,
                        python_position(self.code_source.toPlainText(), cursor.position()))
                    for start, end, token in link_spans(self._text):
                        if start <= offset < end and token.type == "link_open":
                            from PySide6.QtCore import QUrl
                            self.blocks[0].view._open_link(QUrl(token.attrGet("href")))
                            return True
        return super().eventFilter(watched, event)

    def dragEnterEvent(self, event):
        if not self._read_only and image_mime(event.mimeData()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        if not self._read_only:
            self.paste_image(event.mimeData())
            event.acceptProposedAction()

    def paste_image(self, mime):
        if self._read_only:
            return
        urls = mime.urls() if mime.hasUrls() else []
        if urls:
            for url in urls:
                if url.isLocalFile():
                    self.reference_dialog(image=True, file=url.toLocalFile())
        elif mime.hasImage():
            self.reference_dialog(image=True, clipboard_image=QApplication.clipboard().image())

    def reference_dialog(self, *, image=False, span=None, file=None, clipboard_image=None,
                         selection_override=None, table_cell=False):
        from .insert_dialogs import ReferenceDialog
        from .markdown_syntax import inline_reference
        from ...domain.models import StudioError
        if self._read_only:
            return
        caller = QApplication.focusWidget()
        if caller is None or not self.isAncestorOf(caller):
            caller = self.code_source if self.mode == "code" else (
                self.active.source if self.active else self)
        start, end = (selection_override or self.selection()) if span is None else span[:2]
        source, label, title, target = "", self._text[start:end], "", ""
        if span:
            token = span[2]
            source = token.attrGet("src") or token.attrGet("href") or ""
            title = token.attrGet("title") or ""
            label = token.content if image else self.link_label(start, end)
            if not image:
                syntax, environment = parser(), {}
                syntax.parse(self._text, environment)
                children = syntax.parseInline(label, environment)[0].children
                if len(children) == 1 and children[0].type == "image":
                    picture = children[0]
                    target, source, image = source, picture.attrGet("src"), True
                    label, title = picture.content, picture.attrGet("title") or ""
        dialog = ReferenceDialog(self, image=image, source=source, label=label, title=title,
            target=target)
        self._dialog_active = True
        identity = (self.document_service, self.document_id, self._text)
        try:
            if file:
                dialog.set_file(file)
            if clipboard_image is not None:
                dialog.set_clipboard_image(clipboard_image)
            if dialog.exec() != QDialog.Accepted or identity != (self.document_service,
                self.document_id, self._text):
                return
            source = dialog.source.text().strip()
            if image and dialog.copy_file.isChecked():
                if not self.import_image:
                    raise StudioError("validation", "Übernehmen benötigt den Dokumentdienst.")
                from ...application.document_resources import read_image_file
                read_image_file(dialog.selected_file.path, self.media.limits.transferred,
                    dialog.selected_file.digest)
                source = self.import_image(dialog.selected_file.path)
                result = inline_reference(dialog.label.text(), source, dialog.title.text(),
                    image=True)
                if dialog.target.text().strip():
                    from urllib.parse import quote
                    result = "[" + result + "](<" + quote(dialog.target.text().strip(),
                        safe="/:#?=&%+@!$;,*~-._") + ">)"
            else:
                result = dialog.result_markdown
            if image:
                from urllib.parse import quote
                self.media.grants()["urls"].add(parser().normalizeLink(quote(source,
                    safe="/:#?=&%+@!$;,*~-._")))
                if dialog.selected_file:
                    grant = dialog.selected_file
                    self.media.grants()["files"][str(grant.path)] = grant
            if table_cell:
                from .markdown_source import escape_cell
                result = escape_cell(result).strip()
            self.apply_edit(start, end, result)
        except (StudioError, OSError, ValueError) as error:
            QMessageBox.information(self, "Einfügen nicht möglich", str(error))
        finally:
            from shiboken6 import isValid
            dialog.release_temporary()
            dialog.deleteLater()
            def restore_focus():
                if caller is not None and isValid(caller) and caller.isVisible():
                    self.window().activateWindow()
                    caller.setFocus(Qt.PopupFocusReason)
                self._dialog_active = False
            QTimer.singleShot(0, self, restore_focus)

    def link_label(self, start, end):
        source = self._text[start:end]
        if source.startswith("<") and source.endswith(">"):
            return source[1:-1]
        if source.startswith("[["):
            body = source[2:-2]
            return body.split("|", 1)[-1]
        md = parser()
        from markdown_it.rules_inline.state_inline import StateInline
        state = StateInline(source, md, {}, [])
        left = 2 if source.startswith("![") else 1
        right = md.helpers.parseLinkLabel(state, left - 1, True)
        return source[left:right] if right >= 0 else source

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
        self.media.retain({source for block in self.blocks for source,
            _ in block.view.media_sources})
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
        if (not self._rebuilding and not self._dialog_active
                and self.active is block and not block.source.hasFocus()
                and QApplication.activePopupWidget() is None):
            focus = QApplication.focusWidget()
            if (focus is None or not self.window().isActiveWindow()
                    or QApplication.activeModalWidget() is not None):
                return
            if focus and any(other is not block and other.isAncestorOf(focus)
                             for other in self.blocks):
                # Do not destroy the table cell/checkbox which just received focus.
                self.active = None
                block.render()
                self.refresh_references(block)
                return
            self.rebuild()

    def refresh_references(self, changed_block):
        _, references = markdown_spans(self._text)
        for block in self.blocks:
            if block.references != references:
                block.references = references
                if block.table_editor:
                    delegate = block.table_editor.table.itemDelegate()
                    delegate.references = references
                    delegate.cache.clear()
                    block.table_editor.table.viewport().update()
                elif block is not self.active:
                    block.view.preview(self._text[block.start:block.end], references=references)
                    block.fit()

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

    def context_menu(self, block=None, field=None, point=None) -> QMenu:
        if isinstance(field, QPlainTextEdit):
            menu = QMenu(self)
            for title, callback, enabled in (
                ("Rückgängig", self.undo, bool(self._undo) and not self._read_only),
                ("Wiederholen", self.redo, bool(self._redo) and not self._read_only),
                ("Ausschneiden", field.cut,
                 field.textCursor().hasSelection() and not self._read_only),
                ("Kopieren", field.copy, field.textCursor().hasSelection()),
                ("Einfügen", lambda: self.paste_image(QApplication.clipboard().mimeData())
                 if image_mime(QApplication.clipboard().mimeData())
                 else field.paste(), not self._read_only and field.canPaste()),
                ("Alles auswählen", field.selectAll, True),
            ):
                menu.addAction(title, callback).setEnabled(enabled)
        else:
            menu = field.createStandardContextMenu() if field else QMenu(self)
        menu.addSeparator()
        if block and field is block.view:
            selected = field.textCursor().selectedText().replace("\u2029", "\n")
            offset = self._text.find(selected, block.start, block.end) if selected else block.start
            self._selection = (max(block.start, offset), max(block.start, offset) + len(selected))
        for title, kind in (("Fett", "bold"), ("Kursiv", "italic"), ("Durchstreichen", "strike"),
                            ("Inline-Code", "inline")):
            menu.addAction(title, lambda checked=False,
                value=kind: self.format_selection(value)).setEnabled(not self._read_only)
        if block:
            for heading in headings(self._text):
                if block.start <= heading.offset < block.end:
                    menu.addAction("Abschnittslink kopieren", lambda checked=False, h=heading:
                                   QApplication.clipboard().setText("#" + h.identifier))
            target = field.anchorAt(point) if point is not None and field is block.view else ""
            if target:
                from PySide6.QtCore import QUrl
                menu.addAction("Link öffnen", lambda: block.view._open_link(QUrl(target)))
                menu.addAction("Ziel kopieren", lambda: QApplication.clipboard().setText(target))
                span = next((s for s in link_spans(self._text) if block.start <= s[0] < block.end
                             and s[2].attrGet("href") == target), None)
                if span:
                    menu.addAction("Link bearbeiten …",
                        lambda: self.reference_dialog(span=span)).setEnabled(not self._read_only)
                    menu.addAction("Verknüpfung entfernen", lambda: self.apply_edit(
                        span[0], span[1],
                            self.link_label(*span[:2]))).setEnabled(not self._read_only)
        menu.addAction("Bild einfügen …",
            lambda: self.reference_dialog(image=True)).setEnabled(not self._read_only)
        position = self.selection()[0] if isinstance(field,
            QPlainTextEdit) else block.end if block else len(self._text)
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
        if self._read_only:
            return
        if kind == "link":
            self.reference_dialog()
            return
        if kind != "table":
            self.format_selection(kind)
            return
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
