"""Revision-safe task editor that keeps local text on conflicts or cancelled closes."""

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QMessageBox, QPlainTextEdit,
    QWidget,
)

from ...application.issue_service import IssueService, PRIORITIES
from ...domain.models import Record, StudioError
from ..common import label, show_error
from .checklist import ChecklistEditor


class TaskEditor(QDialog):
    def __init__(self, service: IssueService, record: Record, parent: QWidget) -> None:
        super().__init__(parent)
        self.service, self.record = service, record
        self.setObjectName("task_editor")
        self.setWindowTitle("Issue bearbeiten" if record.kind == "issue" else "Aufgabe bearbeiten")
        self.resize(680, 680)
        layout = QFormLayout(self)
        self.title = QLineEdit(record.title)
        self.title.setObjectName("edit_task_title")
        self.body = QPlainTextEdit(record.data["body"])
        self.body.setObjectName("edit_task_body")
        self.priority = QComboBox()
        self.priority.addItems(list(PRIORITIES))
        self.priority.setCurrentText(record.data["priority"])
        self.assignee = QLineEdit(record.data.get("assignee", ""))
        for caption, widget in (("Titel", self.title), ("Beschreibung", self.body),
                                 ("Priorität", self.priority), ("Zuständig", self.assignee)):
            layout.addRow(caption, widget)
        self.checklist = ChecklistEditor(record.data.get("checklist", []), self)
        layout.addRow(self.checklist)
        layout.addRow(label("Änderungen heben eine alte Aufgabenabnahme auf. "
                            "Keine Asset-Freigabe."))
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save
                                       | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.save)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

    def dirty(self) -> bool:
        return (self.title.text() != self.record.title
                or self.body.toPlainText() != self.record.data["body"]
                or self.priority.currentText() != self.record.data["priority"]
                or self.assignee.text() != self.record.data.get("assignee", "")
                or self.checklist.value() != self.record.data.get("checklist", [])
                or bool(self.checklist.text.text().strip()))

    def save(self) -> bool:
        try:
            self.checklist.commit_pending()
            self.record = self.service.update(
                self.record.id, self.title.text(), self.body.toPlainText(),
                self.record.revision_no, priority=self.priority.currentText(),
                assignee=self.assignee.text(),
                checklist=self.checklist.value(),
            )
        except StudioError as exc:
            show_error(self, exc)
            return False
        self.accept()
        return True

    def reject(self) -> None:
        if self.dirty():
            answer = QMessageBox.question(
                self, "Ungespeicherte Aufgabe", "Änderungen vor dem Schließen speichern?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel,
            )
            if answer == QMessageBox.StandardButton.Cancel:
                return
            if answer == QMessageBox.StandardButton.Save:
                self.save()
                return
        super().reject()
