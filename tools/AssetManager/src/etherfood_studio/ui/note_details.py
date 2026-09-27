"""Embedded note editor with shared safe preview/attachments, never a documentation tab."""

from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLineEdit, QPushButton, QWidget

from ..domain.models import StudioError
from ..domain.notes import NOTE_COLORS
from .common import show_error
from .documents.editor import DocumentEditor


class NoteDetails(DocumentEditor):
    def __init__(self) -> None:
        super().__init__(notes_only=True)
        self.setObjectName("note_details")
        self.documents.hide()
        for name in ("new_document", "import_markdown"):
            self.findChild(QPushButton, name).hide()
        for widget in self.findChildren(QWidget):
            if widget.objectName():
                widget.setObjectName("note_inline_" + widget.objectName())
        fields = QHBoxLayout()
        self.title = QLineEdit()
        self.title.setObjectName("note_inline_title")
        self.title.setPlaceholderText("Titel der Notiz")
        self.color = QComboBox()
        self.color.setObjectName("note_inline_color")
        for key, (label, _) in NOTE_COLORS.items():
            self.color.addItem(label, key)
        self.pinned = QCheckBox("Anheften")
        self.pinned.setObjectName("note_inline_pinned")
        fields.addWidget(self.title, 1)
        fields.addWidget(self.color)
        fields.addWidget(self.pinned)
        self.layout().insertLayout(0, fields)
        self.title.textChanged.connect(self._changed)
        self.color.currentIndexChanged.connect(self._changed)
        self.pinned.toggled.connect(self._changed)
        self.editor.setPlaceholderText("Eine Notiz im Dashboard auswählen oder + Notiz verwenden.")

    def _load(self, identifier) -> None:
        super()._load(identifier)
        self._loading = True
        record = self.current
        self.title.setText(record.title if record else "")
        self.color.setCurrentIndex(self.color.findData(
            record.data.get("note_color", "yellow") if record else "yellow"))
        self.pinned.setChecked(bool(record and record.data.get("note_pinned")))
        for field in (self.title, self.color, self.pinned):
            field.setEnabled(record is not None)
        if not record:
            self.state.setText("Notiz auswählen; Text, Farbe und Anhänge hier bearbeiten.")
        self._loading = False
        self.dirty = False

    def _changed(self, *args) -> None:
        super()._changed()
        if self._loading or not self.current:
            return
        self.dirty |= (self.title.text() != self.current.title
                       or self.color.currentData() != self.current.data.get("note_color", "yellow")
                       or self.pinned.isChecked() != self.current.data.get("note_pinned", False))
        self.state.setText("Ungespeicherte Notiz" if self.dirty else "Gespeichert")

    def save(self) -> bool:
        if not self.current or not self.dirty:
            return True
        try:
            self.current = self.service.write(
                self.current.owner_id, self.title.text(), self.editor.toPlainText(),
                identifier=self.current.id, expected_revision=self.current.revision_no,
                color=self.color.currentData(), pinned=self.pinned.isChecked(),
            )
        except (StudioError, OSError) as error:
            show_error(self, error)
            return False
        self.dirty = False
        self.state.setText(f"Gespeichert · Revision {self.current.revision_no}")
        self.saved.emit()
        return True
