"""Edit a revision-aware post-it in place without attachments or a second editor."""

import sqlite3

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QLineEdit, QMenu, QMessageBox, QPlainTextEdit, QVBoxLayout,
)

from ..domain.models import StudioError
from ..domain.notes import NOTE_COLORS, NOTE_WORD_LIMIT, note_word_count
from .common import label, show_error


class NoteDetails(QFrame):
    saved = Signal()
    activated = Signal()
    SIZE = (320, 270)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.service = None
        self.owner_id = None
        self.current = None
        self.dirty = False
        self._loading = False
        self.board_position = None
        self.placeholder_draft = False
        self.setObjectName("note_card")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedSize(*self.SIZE)
        layout = QVBoxLayout(self)
        self.grip = label("⠿  Verschieben", "note_drag_handle")
        self.grip.setCursor(Qt.OpenHandCursor)
        self.grip.setToolTip("An dieser Leiste auf der Pinnwand verschieben")
        self.grip.setFixedHeight(20)
        layout.addWidget(self.grip)
        self.title = QLineEdit()
        self.title.setObjectName("note_inline_title")
        self.title.setPlaceholderText("Überschrift …")
        self.editor = QPlainTextEdit()
        self.editor.setObjectName("note_inline_markdown_editor")
        self.editor.setPlaceholderText("Hier klicken und eine kurze Notiz schreiben …")
        self.editor.setTabChangesFocus(True)
        self.color = QComboBox(self)
        for key, (name, _) in NOTE_COLORS.items():
            self.color.addItem(name, key)
        self.color.hide()
        self.pinned = QCheckBox("Anheften", self)
        self.pinned.hide()
        self.state = label("0 / 100 Wörter", "note_word_count")
        self.state.setWordWrap(True)
        layout.addWidget(self.title)
        layout.addWidget(self.editor, 1)
        layout.addWidget(self.state)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(900)
        self.timer.timeout.connect(lambda: self.save(quiet=True))
        for field in (self.title, self.editor):
            field.installEventFilter(self)
            field.textChanged.connect(self._changed)
            field.setContextMenuPolicy(Qt.CustomContextMenu)
            field.customContextMenuRequested.connect(
                lambda point, widget=field: self.show_context(widget, point))
        self.color.currentIndexChanged.connect(self._changed)
        self.pinned.toggled.connect(self._changed)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda point: self.show_context(self, point))
        self._style()

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.FocusIn:
            self.activated.emit()
        return super().eventFilter(watched, event)

    def bind(self, service, owner_id=None, record=None) -> None:
        self.timer.stop()
        self.service, self.owner_id = service, owner_id
        self.load(record)

    def load(self, record) -> None:
        self.timer.stop()
        self._loading = True
        self.current = record
        if record:
            self.owner_id = record.owner_id
        self.title.setText(record.title if record else "")
        self.editor.setPlainText(record.data.get("body", "") if record else "")
        self.color.setCurrentIndex(self.color.findData(
            record.data.get("note_color", "yellow") if record else "yellow"))
        self.pinned.setChecked(bool(record and record.data.get("note_pinned")))
        self._loading = False
        self.dirty = False
        self._style()
        self._caption()

    def refresh_documents(self, identifier=None) -> None:
        if not self.dirty and self.service:
            self.load(self.service.catalog.get(identifier) if identifier else None)

    def _style(self) -> None:
        color = NOTE_COLORS[self.color.currentData() or "yellow"][1]
        self.setStyleSheet(
            f"QFrame#note_card {{ background: {color}; border: 1px solid #aa9868; "
            "border-radius: 9px; }"
            f"QLineEdit, QPlainTextEdit {{ background: {color}; color: #263238; "
            "border: none; selection-background-color: #b3d6f5; }"
            "QLineEdit { font-weight: bold; } QLabel { color: #52606a; background: transparent; }"
        )
        # Native Qt themes may still paint the text viewport with their Base brush.
        palette = self.editor.palette()
        palette.setColor(QPalette.Base, QColor(color))
        self.editor.setPalette(palette)
        self.editor.viewport().setPalette(palette)

    def _caption(self, message: str = "") -> None:
        count = note_word_count(self.editor.toPlainText())
        legacy = self.current and self.editor.toPlainText() == self.current.data["body"]
        too_long = "Alttext bleibt erhalten" if legacy else "Zu lang – bitte kürzen"
        suffix = message or (too_long if count > NOTE_WORD_LIMIT
                             else "Ungespeichert · speichert automatisch" if self.dirty
                             else "Gespeichert" if self.current else "Direkt schreiben")
        self.state.setText(f"{'Angeheftet · ' if self.pinned.isChecked() else ''}"
                           f"{count} / {NOTE_WORD_LIMIT} Wörter · {suffix}")

    def _changed(self, *args) -> None:
        if self._loading:
            return
        self._style()
        if self.current:
            self.dirty = (self.title.text() != self.current.title
                          or self.editor.toPlainText() != self.current.data["body"]
                          or self.color.currentData() != self.current.data.get(
                              "note_color", "yellow")
                          or self.pinned.isChecked() != self.current.data.get("note_pinned", False))
        else:
            self.dirty = bool(self.title.text().strip() or self.editor.toPlainText().strip())
        self._caption()
        if self.dirty and self.service:
            self.timer.start()
        else:
            self.timer.stop()

    def save(self, *, quiet: bool = False) -> bool:
        self.timer.stop()
        if not self.service or not self.owner_id or not self.dirty:
            return True
        title = self.title.text().strip()
        if not title:
            existing = {row.title.casefold() for row in self.service.documents(self.owner_id)
                        if not self.current or row.id != self.current.id}
            title, counter = "Notiz", 1
            while title.casefold() in existing:
                counter += 1
                title = f"Notiz {counter}"
        try:
            self.current = self.service.write(
                self.owner_id, title, self.editor.toPlainText(),
                identifier=self.current.id if self.current else None,
                expected_revision=self.current.revision_no if self.current else None,
                color=self.color.currentData(), pinned=self.pinned.isChecked(),
                position=self.board_position if self.current is None else None,
            )
        except (StudioError, OSError, sqlite3.Error) as error:
            self._caption(str(error))
            if not quiet:
                show_error(self, error)
            return False
        self._loading = True
        self.title.setText(self.current.title)
        self._loading = False
        self.dirty = False
        self._caption()
        self.saved.emit()
        return True

    def confirm_discard(self) -> bool:
        if not self.dirty:
            return True
        self.timer.stop()
        answer = QMessageBox.question(
            self, "Notiz noch nicht gespeichert", "Notiz vor dem Wechsel speichern?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Cancel,
        )
        if answer == QMessageBox.Cancel:
            return False
        if answer == QMessageBox.Save:
            return self.save()
        self.load(self.service.catalog.get(self.current.id) if self.current else None)
        return True

    def context_menu(self, field=None) -> QMenu:
        menu = (field.createStandardContextMenu() if field in (self.title, self.editor)
                else QMenu(self))
        menu.addSeparator()
        colors = QMenu("Farbe", menu)
        menu.addMenu(colors)
        for key, (name, _) in NOTE_COLORS.items():
            action = colors.addAction(name)
            action.setObjectName("note_color_" + key)
            action.setCheckable(True)
            action.setChecked(self.color.currentData() == key)
            action.triggered.connect(lambda checked=False, value=key:
                                     self.color.setCurrentIndex(self.color.findData(value)))
        pinned = menu.addAction("Oben anheften")
        pinned.setCheckable(True)
        pinned.setChecked(self.pinned.isChecked())
        pinned.triggered.connect(self.pinned.setChecked)
        menu.addAction("Jetzt speichern · Strg+S", lambda: self.save())
        return menu

    def show_context(self, field, point) -> None:
        menu = self.context_menu(field)
        menu.exec(field.mapToGlobal(point))
        menu.deleteLater()
