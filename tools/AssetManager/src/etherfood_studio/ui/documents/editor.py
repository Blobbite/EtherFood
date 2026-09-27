"""Revision-aware editor; previews never fetch files or network resources."""

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QHBoxLayout, QInputDialog, QListWidget, QMessageBox,
    QPlainTextEdit, QVBoxLayout, QWidget,
)

from ...application.document_service import DocumentService, TEMPLATES
from ...domain.models import Record, StudioError
from ...domain.notes import NOTE_TEMPLATES, is_note
from ..common import button, label, show_error
from ..presentation import kind_icon
from .preview import SafePreview
from .live_markdown import LiveMarkdownEditor


class DocumentEditor(QWidget):
    saved = Signal()

    def __init__(self, *, notes_only: bool = False) -> None:
        super().__init__()
        self.notes_only = notes_only
        self.service: DocumentService | None = None
        self.owner_id: str | None = None
        self.current: Record | None = None
        self.dirty = False
        self._loading = False
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.documents = QComboBox()
        self.documents.setObjectName("document_selection")
        self.documents.setAccessibleName("Dokument auswählen")
        self.documents.currentIndexChanged.connect(self._select_document)
        top.addWidget(self.documents, 1)
        top.addWidget(button("+ Dokumentation", "new_document", self.new_document))
        top.addWidget(button("Markdown importieren", "import_markdown", self.import_dialog))
        layout.addLayout(top)
        self.state = label("Karte auswählen und Dokumentation anlegen.", "document_state")
        layout.addWidget(self.state)
        self.editor = LiveMarkdownEditor()
        self.editor.setObjectName("markdown_editor")
        self.editor.setAccessibleName("Markdown-Text bearbeiten")
        self.editor.setPlaceholderText("Noch kein Dokument. Über + Dokumentation anlegen.")
        self.editor.textChanged.connect(self._changed)
        layout.addWidget(self.editor, 1)
        bottom = QHBoxLayout()
        self.save_button = button("Speichern · Strg+S", "save_document", self.save)
        bottom.addWidget(self.save_button)
        bottom.addWidget(button("+ Anhang", "add_attachment", self.attach_dialog))
        bottom.addWidget(button("Anhang ansehen", "view_attachment", self.view_attachment))
        layout.addLayout(bottom)
        self.attachments = QListWidget()
        self.attachments.setObjectName("document_attachments")
        self.attachments.setMaximumHeight(90)
        layout.addWidget(self.attachments)
        self.setEnabled(False)

    def bind(self, service: DocumentService) -> None:
        self.service = service
        self.current = None
        self.owner_id = None
        self.dirty = False
        self.setEnabled(True)

    def confirm_discard(self) -> bool:
        if not self.dirty:
            return True
        answer = QMessageBox.question(
            self, "Nicht gespeicherte Änderungen", "Dokument vor dem Wechsel speichern?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        if answer == QMessageBox.StandardButton.Save:
            return self.save()
        return True

    def show_card(self, owner_id: str) -> bool:
        if owner_id == self.owner_id:
            return True
        if not self.confirm_discard():
            return False
        self.owner_id = owner_id
        self.refresh_documents()
        return True

    def refresh_documents(self, select_id: str | None = None) -> None:
        self.documents.blockSignals(True)
        self.documents.clear()
        rows = self.service.documents(self.owner_id) if self.service and self.owner_id else []
        for row in rows:
            if is_note(row) != self.notes_only:
                continue
            generated = row.data["document_type"] == "generated"
            suffix = " [Bericht, schreibgeschützt]" if generated else ""
            self.documents.addItem(kind_icon("note" if is_note(row) else "document"),
                                   row.title + suffix, row.id)
        index = self.documents.findData(select_id) if select_id else 0
        self.documents.setCurrentIndex(max(0, index) if self.documents.count() else -1)
        self.documents.blockSignals(False)
        self._load(self.documents.currentData())

    def open_document(self, identifier: str) -> bool:
        if not self.service:
            return False
        if self.current and self.current.id == identifier:
            return True
        record = self.service.catalog.get(identifier)
        if record.kind != "document" or is_note(record) != self.notes_only \
                or not self.confirm_discard():
            return False
        self.owner_id = record.owner_id
        self.refresh_documents(identifier)
        return True

    def _load(self, identifier: str | None) -> None:
        self._loading = True
        self.current = self.service.catalog.get(identifier) if identifier else None
        self.editor.setPlainText(self.current.data["body"] if self.current else "")
        generated = bool(self.current and self.current.data["document_type"] == "generated")
        self.editor.setReadOnly(self.current is None or generated)
        self.save_button.setEnabled(self.current is not None and not generated)
        self.attachments.clear()
        if self.current:
            for attachment in self.current.data["attachments"]:
                self.attachments.addItem(attachment["original_name"])
        self.attachments.setVisible(self.attachments.count() > 0)
        self.dirty = False
        self._loading = False
        self.state.setText(f"Revision {self.current.revision_no} · "
                           + ("Bericht (nur lesen)" if generated else "gespeichert")
                           if self.current else "Noch kein Dokument. + Dokumentation wählen.")

    def _select_document(self, index: int) -> None:
        if not self.confirm_discard():
            self.documents.blockSignals(True)
            self.documents.setCurrentIndex(self.documents.findData(self.current.id))
            self.documents.blockSignals(False)
            return
        self._load(self.documents.itemData(index))

    def _changed(self) -> None:
        if self._loading or self.current is None:
            return
        self.dirty = self.editor.toPlainText() != self.current.data["body"]
        self.state.setText("Ungespeicherte Änderungen" if self.dirty else "Gespeichert")

    @property
    def preview(self) -> SafePreview:
        return self.editor.blocks[0].view

    def save(self) -> bool:
        if self.current is None or not self.service or not self.dirty:
            return True
        try:
            updated = self.service.save(self.current.id, self.editor.toPlainText(),
                                        self.current.revision_no)
        except (StudioError, OSError) as exc:
            show_error(self, exc)
            return False
        self.current = updated
        self.dirty = False
        self.state.setText(f"Gespeichert · Revision {updated.revision_no}")
        self.saved.emit()
        return True

    def create_document(self, title: str, template: str = "Dokumentation") -> Record:
        if not self.service or not self.owner_id:
            raise StudioError("validation", "Zuerst eine Karte auswählen.")
        record = self.service.create(self.owner_id, title, template=template)
        self.refresh_documents(record.id)
        self.editor.setFocus()
        self.saved.emit()
        return record

    def new_document(self) -> None:
        if not self.confirm_discard() or not self.owner_id:
            return
        title, accepted = QInputDialog.getText(self, "Neue Dokumentation", "Titel")
        if not accepted:
            return
        templates = [key for key in TEMPLATES if key not in NOTE_TEMPLATES]
        template, accepted = QInputDialog.getItem(self, "Vorlage", "Typ", templates, 0, False)
        if accepted:
            try:
                self.create_document(title, template)
            except StudioError as exc:
                show_error(self, exc)

    def import_file(self, path: Path, *, replace_current: bool = False) -> Record:
        if not self.owner_id or not self.service:
            raise StudioError("validation", "Zuerst eine Karte auswählen.")
        selected = self.current if replace_current else None
        record = self.service.import_markdown(
            self.owner_id, path, identifier=selected.id if selected else None,
            expected_revision=selected.revision_no if selected else None,
        )
        self.refresh_documents(record.id)
        self.saved.emit()
        return record

    def import_dialog(self) -> None:
        if not self.confirm_discard() or not self.owner_id:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Markdown importieren", "", "Markdown (*.md)")
        if not path:
            return
        try:
            self.import_file(Path(path))
        except StudioError as exc:
            if exc.code == "conflict" and self.current:
                answer = QMessageBox.question(
                    self, "Neue Dokumentrevision?", "Als neue Revision des gewählten Dokuments?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if answer == QMessageBox.StandardButton.Yes:
                    try:
                        self.import_file(Path(path), replace_current=True)
                    except (StudioError, OSError) as error:
                        show_error(self, error)
            else:
                show_error(self, exc)
        except OSError as exc:
            show_error(self, exc)

    def attach_dialog(self) -> None:
        if not self.current or not self.confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Anhang sicher importieren")
        if path:
            try:
                updated = self.service.attach(self.current.id, Path(path), self.current.revision_no)
                self.refresh_documents(updated.id)
            except (StudioError, OSError) as exc:
                show_error(self, exc)

    def view_attachment(self) -> None:
        index = self.attachments.currentRow()
        if not self.current or index < 0:
            return
        try:
            path = self.service.attachment_path(self.current.id, index)
            dialog = QDialog(self)
            dialog.setWindowTitle("Anhang – keine automatische Ausführung")
            layout = QVBoxLayout(dialog)
            viewer = QPlainTextEdit()
            viewer.setReadOnly(True)
            content = self.service.attachment_text(self.current.id, index)
            viewer.setPlainText(content)
            layout.addWidget(viewer)
            layout.addWidget(label(f"Geschützter Blob: {path.name}"))
            dialog.resize(650, 420)
            dialog.exec()
        except (StudioError, OSError) as exc:
            show_error(self, exc)
