"""Scoped, directly editable post-its over the shared revisioned note service."""

import sqlite3

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLineEdit,
    QListWidgetItem, QMessageBox, QPlainTextEdit, QVBoxLayout, QWidget,
)

from ..application.note_service import NoteService
from ..domain.models import StudioError
from ..domain.notes import NOTE_COLORS
from .common import button, label, show_error
from .note_details import NoteDetails
from .note_board import NoteBoard

NOTE_ROLE = Qt.ItemDataRole.UserRole
LOCATION_ROLE = Qt.ItemDataRole.UserRole + 1


class NoteEditor(QDialog):
    def __init__(self, service: NoteService, owner: str, record=None, parent=None) -> None:
        super().__init__(parent)
        self.service, self.owner, self.record = service, owner, record
        self.saved_record = None
        self.setObjectName("note_editor")
        self.setWindowTitle("Notiz bearbeiten" if record else "Neue Notiz")
        self.resize(580, 540)
        layout = QFormLayout(self)
        self.title = QLineEdit(record.title if record else "")
        self.title.setObjectName("note_title")
        self.body = QPlainTextEdit(record.data.get("body", "") if record else "")
        self.body.setObjectName("note_body")
        self.body.setPlaceholderText("Gedanken, Fragen oder nächste Schritte …")
        self.color = QComboBox()
        self.color.setObjectName("note_color")
        for key, (name, value) in NOTE_COLORS.items():
            self.color.addItem(name, key)
            self.color.setItemData(self.color.count() - 1, QColor(value), Qt.BackgroundRole)
        self.color.setCurrentIndex(self.color.findData(
            record.data.get("note_color", "yellow") if record else "yellow"))
        self.pinned = QCheckBox("Oben anheften")
        self.pinned.setObjectName("note_pinned")
        self.pinned.setChecked(bool(record and record.data.get("note_pinned")))
        layout.addRow("Titel", self.title)
        layout.addRow("Text (Markdown bleibt erhalten)", self.body)
        layout.addRow("Farbe", self.color)
        layout.addRow(self.pinned)
        layout.addRow(label("Zuordnung: " + service.project.breadcrumb(owner)))
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.save)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)
        self.initial = self.values()

    def values(self):
        return (self.title.text(), self.body.toPlainText(), self.color.currentData(),
                self.pinned.isChecked())

    def save(self) -> bool:
        try:
            title, body, color, pinned = self.values()
            self.saved_record = self.service.write(
                self.owner, title, body, identifier=self.record.id if self.record else None,
                expected_revision=self.record.revision_no if self.record else None,
                color=color, pinned=pinned,
            )
            self.accept()
            return True
        except StudioError as error:
            show_error(self, error)
            return False

    def reject(self) -> None:
        if self.values() != self.initial:
            answer = QMessageBox.question(
                self, "Notizentwurf", "Änderungen vor dem Schließen speichern?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Cancel,
            )
            if answer == QMessageBox.Cancel or (answer == QMessageBox.Save and not self.save()):
                return
            if answer == QMessageBox.Save:
                return
        super().reject()


class NoteItem(QListWidgetItem):
    def __lt__(self, other) -> bool:
        def key(item):
            record = item.data(NOTE_ROLE)
            return ((not record.data.get("note_pinned", False), record.title.casefold(), record.id)
                    if record else (True, "\uffff", ""))
        return key(self) < key(other)


class NotesPanel(QWidget):
    changed = Signal()
    focus_requested = Signal(str)

    def __init__(self, before_edit, *, stacked: bool = False) -> None:
        super().__init__()
        self.before_edit = before_edit
        self.project = None
        self.current_card = None
        self._selecting = False
        self._positions = {}
        self._empty_editor = NoteDetails(self)
        self._empty_editor.hide()
        layout = QVBoxLayout(self)
        self.scope_label = label("Projekt öffnen, um Notizen zu sehen.", "notes_scope")
        layout.addWidget(self.scope_label)
        filters = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setObjectName("notes_search")
        self.query.setPlaceholderText("Notizen durchsuchen …")
        filters.addWidget(self.query, 1)
        self.color = QComboBox()
        self.color.setObjectName("notes_color_filter")
        self.color.addItem("Alle Farben", None)
        for key, (name, _) in NOTE_COLORS.items():
            self.color.addItem(name, key)
        filters.addWidget(self.color)
        filters.addWidget(button("+ Notiz", "new_note", self.new_note))
        filters.addWidget(button("Gesamtes Projekt", "notes_project", self.show_project))
        self.owner_button = button("Zum Bezug", "note_owner", self.focus_owner)
        filters.addWidget(self.owner_button)
        layout.addLayout(filters)
        self.notes = NoteBoard(stacked=stacked)
        self.notes.currentItemChanged.connect(self._selection)
        self.notes.moved.connect(self._moved)
        layout.addWidget(self.notes, 1)
        self.query.textChanged.connect(self.refresh)
        self.color.currentIndexChanged.connect(self.refresh)
        self.setEnabled(False)

    @property
    def editor(self) -> NoteDetails:
        item = self.notes.currentItem()
        if item:
            return self.notes.itemWidget(item)
        if self.notes.count():
            return self.notes.itemWidget(self.notes.item(0))
        return self._empty_editor

    def _cards(self) -> list:
        return [(self.notes.item(i), self.notes.itemWidget(self.notes.item(i)))
                for i in range(self.notes.count())]

    def _remove(self, item, card) -> None:
        card.timer.stop()
        card.hide()
        self.notes.detach_handle(card.grip)
        self.notes.removeItemWidget(item)
        self.notes.takeItem(self.notes.row(item))
        card.deleteLater()

    def bind(self, project) -> None:
        self.notes.blockSignals(True)
        for item, card in self._cards():
            self._remove(item, card)
        self.notes.reset_extent()
        self.notes.blockSignals(False)
        self.project = project
        self._positions.clear()
        self.current_card = project.project().id
        self._empty_editor.bind(NoteService(project), self.current_card)
        self.setEnabled(True)
        self.refresh()

    def set_scope(self, identifier: str) -> bool:
        if identifier != self.current_card:
            if not self.confirm_discard():
                return False
            self.notes.blockSignals(True)
            for item, card in self._cards():
                self._remove(item, card)
            self.notes.reset_extent()
            self.notes.blockSignals(False)
            self.current_card = identifier
            self._positions.clear()
            for field in (self.query, self.color):
                field.blockSignals(True)
            self.query.clear()
            self.color.setCurrentIndex(0)
            for field in (self.query, self.color):
                field.blockSignals(False)
        self.refresh()
        return True

    def selected(self):
        item = self.notes.currentItem()
        return item.data(NOTE_ROLE) if item else None

    def _append(self, record=None, *, placeholder: bool = False):
        item = NoteItem()
        item.setSizeHint(QSize(334, 284))
        item.setData(NOTE_ROLE, record)
        card = NoteDetails()
        card.placeholder_draft = placeholder
        card.bind(NoteService(self.project), self.current_card, record)
        if self.notes.free:
            point = self._positions[record.id] if record else self._next_position()
        self.notes.addItem(item)
        self.notes.setItemWidget(item, card)
        self.notes.attach_handle(item, card.grip)
        if self.notes.free:
            self._place(item, card, point)
        card.activated.connect(lambda: self.notes.setCurrentItem(item))
        card.saved.connect(lambda: self._saved(item, card))
        return item

    def refresh(self, *args) -> None:
        if not self.project or not self.current_card:
            return
        service = NoteService(self.project)
        rows = service.notes(self.current_card, self.query.text(), self.color.currentData())
        if self.notes.free:
            all_rows = service.notes(self.current_card)
            for row in all_rows:
                position = service.position(row.id)
                if position is not None:
                    self._positions[row.id] = QPoint(round(position["x"]), round(position["y"]))
            for row in all_rows:
                if row.id not in self._positions:
                    self._positions[row.id] = self._next_position()
        wanted = {row.id: row for row in rows}
        present = set()
        self.notes.blockSignals(True)
        for item, card in self._cards():
            record = card.current
            if record and record.id in wanted:
                latest = wanted[record.id]
                if not card.dirty and latest.revision_no != record.revision_no:
                    card.load(latest)
                item.setData(NOTE_ROLE, card.current)
                if self.notes.free:
                    self._place(item, card, self._positions[record.id])
                present.add(record.id)
            elif not card.dirty and (record or self.query.text() or self.color.currentData()
                                     or (rows and card.placeholder_draft)):
                self._remove(item, card)
        for row in rows:
            if row.id not in present:
                self._append(row)
        if not self.notes.count() and not self.query.text() and self.color.currentData() is None:
            self._append(placeholder=True)
        self.notes.sortItems()
        self.notes.restore_positions()
        if self.notes.currentItem() is None and self.notes.count():
            self.notes.setCurrentRow(0)
        self.notes.blockSignals(False)
        self.scope_label.setText("Bereich: " + self.project.breadcrumb(self.current_card)
                                 + " · Direkt schreiben · Rechtsklick: Farbe"
                                 + (" · Griffleiste ziehen" if self.notes.free else ""))
        self.owner_button.setEnabled(self.selected() is not None)

    def _selection(self, item, previous) -> None:
        if self._selecting:
            return
        self._selecting = True
        try:
            previous_card = self.notes.itemWidget(previous) if previous else None
            if previous_card and not previous_card.confirm_discard():
                self.notes.blockSignals(True)
                self.notes.setCurrentItem(previous)
                self.notes.blockSignals(False)
            self.owner_button.setEnabled(self.selected() is not None)
        finally:
            self._selecting = False

    def _saved(self, item, card) -> None:
        item.setData(NOTE_ROLE, card.current)
        if self.notes.free:
            self._positions[card.current.id] = self.notes.position(item)
        self.owner_button.setEnabled(self.selected() is not None)
        self.changed.emit()

    def _next_position(self) -> QPoint:
        points = list(self._positions.values())
        points.extend(self.notes.position(item) for item, card in self._cards())
        occupied = [QRect(point, QSize(334, 284)) for point in points]
        index = 0
        while True:
            point = QPoint(16 + index % 3 * 334, 16 + index // 3 * 284)
            if not any(QRect(point, QSize(334, 284)).intersects(rect) for rect in occupied):
                return point
            index += 1

    def _place(self, item, card, point: QPoint) -> None:
        self.notes.place_item(item, point)
        card.board_position = {"x": point.x(), "y": point.y()}

    def _moved(self, item, point: QPoint, original: QPoint) -> None:
        card = self.notes.itemWidget(item)
        position = {"x": point.x(), "y": point.y()}
        try:
            if card.current:
                card.service.place(card.current.id, position)
                self._positions[card.current.id] = point
            card.board_position = position
        except (StudioError, OSError, sqlite3.Error) as error:
            self._place(item, card, original)
            show_error(self, error)

    def confirm_discard(self) -> bool:
        return all(card.confirm_discard() for _, card in self._cards())

    def save(self) -> bool:
        return all(card.save() for _, card in self._cards())

    def new_note(self) -> None:
        if not self.project or not self.before_edit() or not self.confirm_discard():
            return
        self.query.clear()
        self.color.setCurrentIndex(0)
        draft = next((item for item, card in self._cards() if card.current is None), None)
        if draft is None:
            draft = self._append()
        self.notes.itemWidget(draft).placeholder_draft = False
        self.notes.setCurrentItem(draft)
        self.notes.scrollToItem(draft)
        self.notes.itemWidget(draft).editor.setFocus()

    def edit_note(self, *, new: bool = False) -> None:
        if new:
            self.new_note()
        else:
            self.editor.editor.setFocus()

    def select_note(self, identifier: str) -> bool:
        same = self.selected() is not None and self.selected().id == identifier
        if not self.project or (not same and not self.confirm_discard()):
            return False
        self.query.clear()
        self.color.setCurrentIndex(0)
        self.refresh()
        for item, card in self._cards():
            if card.current and card.current.id == identifier:
                self.notes.setCurrentItem(item)
                self.notes.scrollToItem(item)
                return self.selected() is not None and self.selected().id == identifier
        return False

    def show_project(self) -> None:
        if self.project:
            self.focus_requested.emit(self.project.project().id)

    def focus_owner(self) -> None:
        if self.selected():
            self.focus_requested.emit(self.selected().owner_id)
