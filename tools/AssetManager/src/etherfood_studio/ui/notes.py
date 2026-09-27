"""Scoped sticky-note dashboard and conflict-safe editor over existing documents."""

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPen
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLineEdit,
    QListView, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QStyledItemDelegate,
    QStyle, QVBoxLayout, QWidget,
)

from ..application.note_service import NoteService
from ..domain.models import StudioError
from ..domain.notes import NOTE_COLORS
from .common import button, label, show_error

NOTE_ROLE = Qt.ItemDataRole.UserRole
LOCATION_ROLE = Qt.ItemDataRole.UserRole + 1


class NoteDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index) -> QSize:
        return QSize(230, 178)

    def paint(self, painter, option, index) -> None:
        note = index.data(NOTE_ROLE)
        if not note:
            return
        box = QRectF(option.rect).adjusted(5, 5, -7, -7)
        painter.save()
        painter.setClipRect(box)
        painter.setBrush(QColor(NOTE_COLORS[note.data.get("note_color", "yellow")][1]))
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        painter.setPen(QPen(QColor("#2472ab" if selected else "#a0a0a0"), 2 if selected else 1))
        painter.drawRoundedRect(box, 7, 7)
        painter.setPen(QColor("#263238"))
        font = QFont(option.font)
        font.setBold(True)
        painter.setFont(font)
        inset = 10
        if note.data.get("note_pinned"):
            # Draw a pin without depending on an installed emoji font.
            painter.setBrush(QColor("#536d80"))
            painter.drawEllipse(QPointF(box.left() + 14, box.top() + 13), 3, 3)
            painter.drawLine(QPointF(box.left() + 14, box.top() + 16),
                             QPointF(box.left() + 11, box.top() + 23))
            inset = 23
        painter.drawText(box.adjusted(inset, 8, -10, -112), Qt.TextWordWrap, note.title)
        font.setBold(False)
        painter.setFont(font)
        painter.drawText(box.adjusted(10, 48, -10, -32), Qt.TextWordWrap,
                         note.data.get("body", "")[:350] or "Leere Notiz · Doppelklick: schreiben")
        painter.setPen(QColor("#52606a"))
        location = painter.fontMetrics().elidedText(index.data(LOCATION_ROLE), Qt.ElideLeft,
                                                     int(box.width() - 20))
        painter.drawText(box.adjusted(10, 0, -10, -9), Qt.AlignLeft | Qt.AlignBottom, location)
        painter.restore()


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


class NotesPanel(QWidget):
    changed = Signal()
    document_requested = Signal(str)
    focus_requested = Signal(str)

    def __init__(self, before_edit) -> None:
        super().__init__()
        self.before_edit = before_edit
        self.project = None
        self.current_card = None
        layout = QVBoxLayout(self)
        self.scope_label = label("Projekt öffnen, um Notizen zu sehen.", "notes_scope")
        layout.addWidget(self.scope_label)
        filters = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setObjectName("notes_search")
        self.query.setPlaceholderText("Notizen in diesem Bereich durchsuchen …")
        filters.addWidget(self.query, 1)
        self.color = QComboBox()
        self.color.setObjectName("notes_color_filter")
        self.color.addItem("Alle Farben", None)
        for key, (name, value) in NOTE_COLORS.items():
            self.color.addItem(name, key)
        filters.addWidget(self.color)
        filters.addWidget(button("Gesamtes Projekt", "notes_project", self.show_project))
        layout.addLayout(filters)
        self.notes = QListWidget()
        self.notes.setObjectName("notes_board")
        self.notes.setViewMode(QListView.IconMode)
        self.notes.setResizeMode(QListView.Adjust)
        self.notes.setMovement(QListView.Static)
        self.notes.setWrapping(True)
        self.notes.setGridSize(QSize(230, 178))
        self.notes.setItemDelegate(NoteDelegate(self.notes))
        self.notes.itemDoubleClicked.connect(lambda item: self.edit_note())
        layout.addWidget(self.notes, 1)
        self.summary = label("Freie Notizen und Testnotizen; Dokumentation bleibt separat.")
        layout.addWidget(self.summary)
        actions = QHBoxLayout()
        actions.addWidget(button("+ Notiz", "new_note", self.new_note))
        self.edit_button = button("Notiz bearbeiten", "edit_note", self.edit_note)
        self.open_button = button("Dokument / Anhänge", "note_document", self.open_document)
        self.owner_button = button("Zum Bezug", "note_owner", self.focus_owner)
        for widget in (self.edit_button, self.open_button, self.owner_button):
            actions.addWidget(widget)
        layout.addLayout(actions)
        self.notes.currentItemChanged.connect(self.update_actions)
        self.query.textChanged.connect(self.refresh)
        self.color.currentIndexChanged.connect(self.refresh)
        self.update_actions()
        self.setEnabled(False)

    def bind(self, project) -> None:
        self.project = project
        self.current_card = project.project().id
        self.setEnabled(True)
        self.refresh()

    def set_scope(self, identifier: str) -> None:
        self.current_card = identifier
        self.refresh()

    def selected(self):
        item = self.notes.currentItem()
        return item.data(NOTE_ROLE) if item else None

    def update_actions(self, *args) -> None:
        for widget in (self.edit_button, self.open_button, self.owner_button):
            widget.setEnabled(self.selected() is not None)

    def refresh(self, *args) -> None:
        if not self.project or not self.current_card:
            return
        selected = self.selected()
        rows = NoteService(self.project).notes(self.current_card, self.query.text(),
                                               self.color.currentData())
        self.notes.clear()
        for row in rows:
            item = QListWidgetItem(row.title)
            item.setData(NOTE_ROLE, row)
            location = self.project.breadcrumb(row.owner_id)
            item.setData(LOCATION_ROLE, location)
            item.setToolTip(("Angeheftet · " if row.data.get("note_pinned") else "")
                            + row.title + "\n" + location)
            self.notes.addItem(item)
            if selected and row.id == selected.id:
                self.notes.setCurrentItem(item)
        self.scope_label.setText("Bereich / neue Notizen: "
                                 + self.project.breadcrumb(self.current_card))
        self.summary.setText(f"{len(rows)} Notizen · Doppelklick: bearbeiten · "
                             "Farben und Anheften im Notizeditor.")
        self.update_actions()

    def show_project(self) -> None:
        if self.project:
            self.focus_requested.emit(self.project.project().id)

    def focus_owner(self) -> None:
        if self.selected():
            self.focus_requested.emit(self.selected().owner_id)

    def open_document(self) -> None:
        if self.selected():
            self.document_requested.emit(self.selected().id)

    def new_note(self) -> None:
        self.edit_note(new=True)

    def edit_note(self, *, new: bool = False) -> None:
        record = None if new else self.selected()
        if not self.project or (not new and not record) or not self.before_edit():
            return
        # Saving a pending document may have changed this exact note revision.
        if record:
            record = self.project.catalog.get(record.id)
        editor = NoteEditor(NoteService(self.project), record.owner_id if record
                            else self.current_card, record, self)
        if editor.exec() == QDialog.Accepted:
            self.query.clear()
            self.color.setCurrentIndex(0)
            self.refresh()
            self.select_note(editor.saved_record.id)
            self.changed.emit()
        editor.deleteLater()

    def select_note(self, identifier: str) -> None:
        for index in range(self.notes.count()):
            item = self.notes.item(index)
            if item.data(NOTE_ROLE).id == identifier:
                self.notes.setCurrentItem(item)
                self.notes.scrollToItem(item)
                break
