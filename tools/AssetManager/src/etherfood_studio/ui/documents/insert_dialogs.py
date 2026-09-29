"""Explicit link/image insertion; previews and cancelled dialogs never create attachments."""

import os
import tempfile
from pathlib import Path
from urllib.parse import quote, urlsplit

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout,
)

from ...application.document_resources import FileGrant
from ...domain.models import StudioError
from .markdown_syntax import headings, inline_reference, parser
from .media import MediaControls, MediaSession
from .preview import SafePreview


class ReferenceDialog(QDialog):
    def __init__(self, host, *, image=False, source="", label="", title="", target=""):
        super().__init__(host)
        self.host, self.image_mode = host, image
        self.service, self.identifier = host.document_service, host.document_id
        self.selected_file = None
        self.temporary = None
        self.preview_session = MediaSession(self)
        self.preview_session.bind(self.service, self.identifier)
        self.preview_session.limits = host.media.limits
        self.preview_session.policy = host.media.policy
        self.preview_session.autoplay = host.media.autoplay
        self.preview_session.reduced_motion = host.media.reduced_motion
        self.setWindowTitle("Bild einfügen" if image else "Link einfügen")
        layout, form = QVBoxLayout(self), QFormLayout()
        self.label = QLineEdit(label)
        self.source = QLineEdit(source)
        self.title = QLineEdit(title)
        self.target = QLineEdit(target)
        for text, field in (("Alternativtext" if image else "Anzeigetext", self.label),
                            ("Bildquelle" if image else "Ziel", self.source),
                                ("Optionaler Titel", self.title)):
            field.setAccessibleName(text)
            form.addRow(text, field)
        if image:
            self.target.setAccessibleName("Getrenntes Linkziel für anklickbares Bild")
            form.addRow("Linkziel (optional)", self.target)
        layout.addLayout(form)
        self.documents = QComboBox()
        self.documents.addItem("Internes Dokument auswählen …", None)
        if self.service:
            for record in self.service.catalog.records():
                if record.kind == "document" and not record.archived:
                    self.documents.addItem(record.title + " · "
                        + str(self.service.path(record.id).relative_to(
                        self.service.catalog.path.parent)), record.id)
        self.documents.currentIndexChanged.connect(self.choose_document)
        layout.addWidget(self.documents)
        self.sections = QComboBox()
        self.sections.addItem("Abschnitt auswählen …", "")
        self.sections.currentIndexChanged.connect(self.choose_section)
        layout.addWidget(self.sections)
        self.destination_base = ""
        self.copy_file = QCheckBox("Datei ins Projekt übernehmen (vorhandener Anhangsweg)")
        self.copy_file.setChecked(False)
        if image:
            row = QHBoxLayout()
            choose = QPushButton("Datei verknüpfen …")
            choose.clicked.connect(self.choose_file)
            row.addWidget(choose)
            attachments = QPushButton("Projektbild / vorhandenen Anhang auswählen …")
            attachments.clicked.connect(self.choose_project_image)
            attachments.setEnabled(bool(self.service))
            row.addWidget(attachments)
            layout.addLayout(row)
            layout.addWidget(self.copy_file)
            self.attachments = QComboBox()
            self.attachments.addItem("Vorhandenen Anhang auswählen …", None)
            if self.service and self.identifier:
                record = self.service.catalog.get(self.identifier)
                for index, item in enumerate(record.data["attachments"]):
                    self.attachments.addItem(item["original_name"], index)
            self.attachments.currentIndexChanged.connect(self.choose_attachment)
            layout.addWidget(self.attachments)
        preview_button = QPushButton("Vorschau ausdrücklich laden" if image
            else "Zielvorschau anzeigen")
        preview_button.clicked.connect(self.preview)
        layout.addWidget(preview_button)
        self.preview_view = SafePreview()
        self.preview_view.media = self.preview_session
        self.preview_session.changed.connect(self.preview_view.update_media)
        self.preview_view.setMaximumHeight(220)
        layout.addWidget(self.preview_view)
        self.preview_controls = None
        self.result_markdown = None
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.finished.connect(self.cleanup)
        self.resize(760, 540)

    def relative(self, path):
        base = self.service.path(self.identifier).parent
        return quote(os.path.relpath(path, base).replace(os.sep, "/"), safe="/.-_")

    def choose_document(self):
        identifier = self.documents.currentData()
        if not identifier or not self.service:
            return
        self.destination_base = self.relative(self.service.path(identifier))
        field = self.target if self.image_mode else self.source
        field.setText(self.destination_base)
        self.sections.clear()
        self.sections.addItem("Ohne Abschnitt", "")
        for item in headings(self.service.catalog.get(identifier).data["body"]):
            self.sections.addItem(item.title + " (#" + item.identifier + ")", item.identifier)

    def choose_section(self):
        if not self.destination_base:
            return
        section = self.sections.currentData()
        field = self.target if self.image_mode else self.source
        field.setText(self.destination_base + ("#" + section if section else ""))

    def set_file(self, path):
        grant = FileGrant.select(Path(path), self.preview_session.limits.transferred)
        self.selected_file = grant
        self.preview_session.grants()["files"][str(grant.path)] = grant
        if self.service and grant.path.is_relative_to(self.service.catalog.path.parent):
            self.source.setText(self.relative(grant.path))
        else:
            self.source.setText(grant.path.as_uri())
        if not self.label.text():
            self.label.setText(grant.path.stem)

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Bilddatei gezielt auswählen", "",
                                            "Bilder (*.png *.jpg *.jpeg *.webp *.gif *.svg);;"
                                            "Alle Dateien (*)")
        if path:
            try:
                self.set_file(path)
            except (StudioError, OSError) as error:
                QMessageBox.information(self, "Bildquelle", str(error))

    def choose_project_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Projektbild auswählen",
            str(self.service.catalog.path.parent))
        if path:
            try:
                self.set_file(path)
            except (StudioError, OSError) as error:
                QMessageBox.information(self, "Bildquelle", str(error))

    def choose_attachment(self):
        index = self.attachments.currentData()
        if index is not None:
            self.source.setText(self.relative(self.service.attachment_path(self.identifier, index)))
            self.label.setText(self.attachments.currentText())
            self.selected_file = None

    def set_clipboard_image(self, image):
        handle = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        handle.close()
        self.temporary = Path(handle.name)
        if not image.save(str(self.temporary), "PNG"):
            self.temporary.unlink(missing_ok=True)
            self.temporary = None
            raise StudioError("failed", "Zwischenablagebild konnte nicht vorbereitet werden.")
        self.set_file(self.temporary)
        self.label.setText("Bild aus Zwischenablage")
        self.copy_file.setChecked(True)
        self.copy_file.setEnabled(False)

    def preview(self):
        if not self.image_mode:
            self.preview_view.setPlainText("Ziel: " + self.source.text() + "\n" + self.title.text())
            return
        source = self.source.text().strip()
        # Preview grants only this URL; private networks still need their own approval.
        self.preview_session.grants()["urls"].add(parser().normalizeLink(quote(source,
            safe="/:#?=&%+@!$;,*~-._")))
        self.preview_view.preview(inline_reference(self.label.text(), source,
            self.title.text(), image=True))
        if self.preview_controls:
            self.layout().removeWidget(self.preview_controls)
            self.preview_controls.deleteLater()
        self.preview_controls = MediaControls(self.preview_session, self.preview_view.media_sources)
        self.layout().insertWidget(self.layout().count() - 1, self.preview_controls)

    def accept(self):
        if self.host.isReadOnly():
            return
        source = self.source.text().strip()
        if not source:
            self.source.setFocus()
            return
        if self.copy_file.isChecked() and self.image_mode and (not self.selected_file
            or not self.service):
            QMessageBox.information(self, "Übernehmen nicht möglich",
                "Zuerst ein Dokument und eine Bilddatei auswählen.")
            return
        # Import happens in the calling document's command, after OK, never during preview.
        self.result_markdown = inline_reference(self.label.text() or "Link", source,
                                                self.title.text(), image=self.image_mode)
        if self.image_mode and self.target.text().strip():
            target = quote(self.target.text().strip(), safe="/:#?=&%+@!$;,*~-._")
            self.result_markdown = "[" + self.result_markdown + "](<" + target + ">)"
        super().accept()

    def cleanup(self, result=QDialog.Rejected):
        self.preview_session.stop()
        if result != QDialog.Accepted:
            self.release_temporary()

    def release_temporary(self):
        if self.temporary:
            self.temporary.unlink(missing_ok=True)
            self.temporary = None
