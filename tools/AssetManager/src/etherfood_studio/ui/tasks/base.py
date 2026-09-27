"""Shared task contents and revision-safe actions for lists and Kanban."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLineEdit, QMessageBox, QPlainTextEdit,
    QVBoxLayout, QWidget,
)

from ...application.issue_service import Finding, IssueService, PRIORITIES
from ...application.project_service import ProjectService
from ...domain.models import Record, StudioError
from ..common import button, label, show_error
from .editor import TaskEditor
from .checklist import ChecklistEditor

STATE_NAMES = {
    "open": "Offen", "in_progress": "In Arbeit", "blocked": "Blockiert", "done": "Erledigt",
}


class TaskPanel(QWidget):
    focus_requested = Signal(str)
    document_requested = Signal(str)
    changed = Signal()

    def __init__(self, owner_id: str | None = None) -> None:
        super().__init__()
        self.fixed_owner = owner_id
        self.selected_record = None
        self.project: ProjectService | None = None
        self.current_card: str | None = owner_id
        self.details = QPlainTextEdit()
        self.details.setObjectName("task_details")
        self.details.setReadOnly(True)
        self.details.setPlaceholderText("Inhalt auswählen: Beschreibung und Fundstelle lesen.")
        self.detail_page = QWidget()
        detail_layout = QVBoxLayout(self.detail_page)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        self.detail_title = label("Aufgabe oder Issue auswählen", "task_detail_title")
        self.detail_title.setStyleSheet("font-weight: bold;")
        detail_layout.addWidget(self.detail_title)
        self.checklist = ChecklistEditor(editable=False)
        self.checklist.changed.connect(self.save_checklist)
        self.checklist.edit_requested.connect(lambda: self.edit_current(focus_todos=True))
        detail_layout.addWidget(self.checklist, 1)
        detail_layout.addWidget(label("Zusatzinformationen", "task_information_heading"))
        self.details.setMaximumHeight(185)
        self.details.setMinimumHeight(85)
        detail_layout.addWidget(self.details)
        self.actions = QHBoxLayout()
        self.create_task = button("+ Aufgabe", "new_task", lambda: self.new_item(False))
        self.create_issue = button("+ Issue", "new_issue", lambda: self.new_item(True))
        self.actions.addWidget(self.create_task)
        self.actions.addWidget(self.create_issue)
        self.edit_button = button("Bearbeiten / Öffnen", "edit_task", self.edit_current)
        self.actions.addWidget(self.edit_button)
        self.new_status = QComboBox()
        self.new_status.setObjectName("task_new_status")
        for key, title in STATE_NAMES.items():
            self.new_status.addItem(title, key)
        self.actions.addWidget(self.new_status)
        self.status_button = button("Status setzen", "set_task_status", self.change_status)
        self.actions.addWidget(self.status_button)
        self.show_details(None)
        self.setEnabled(False)

    def bind(self, project: ProjectService) -> None:
        self.project = project
        self.setEnabled(True)
        self.refresh_scopes()

    def refresh_scopes(self) -> None:
        self.refresh()

    def refresh(self, *args: object) -> None:
        raise NotImplementedError

    def show_details(self, row: Record | None) -> None:
        self.detail_title.setText(row.title if row else "Aufgabe oder Issue auswählen")
        self.edit_button.setEnabled(row is not None)
        self.selected_record = row
        is_task = row is not None and row.kind in {"task", "issue"}
        self.new_status.setEnabled(is_task)
        self.status_button.setEnabled(is_task)
        self.checklist.fill([])
        self.checklist.setEnabled(False)
        self.checklist.setVisible(is_task)
        if row is None or not self.project:
            self.details.clear()
            return
        lines = [row.title, "", row.data.get("body", "") or "Noch keine Beschreibung.", ""]
        if row.kind in {"task", "issue"}:
            self.new_status.setCurrentIndex(self.new_status.findData(row.data["status"]))
            self.checklist.fill(row.data.get("checklist", []))
            self.checklist.setEnabled(True)
            lines.extend([f"Status: {STATE_NAMES[row.data['status']]}",
                          f"Priorität: {row.data['priority']}",
                          f"Zuständig: {row.data.get('assignee') or 'Nicht zugewiesen'}"])
            if row.data.get("approval_needed"):
                lines.append("Aufgabenabnahme: " + ("bestätigt" if row.data.get(
                    "approval_confirmed") else "noch erforderlich"))
            finding = {key: value for key, value in row.data.get("finding", {}).items()
                       if value is not None}
            if finding:
                lines.append("Fundstelle: " + "; ".join(f"{key}: {value}"
                                                     for key, value in finding.items()))
        lines.extend(["", self.project.breadcrumb(row.owner_id),
                      f"Revision {row.revision_no} · ID {row.id}"])
        self.details.setPlainText("\n".join(lines))

    def save_checklist(self) -> None:
        record = self.selected_record
        if not record or record.kind not in {"task", "issue"}:
            return
        try:
            IssueService(self.project).update(record.id, record.title, record.data["body"],
                record.revision_no, priority=record.data["priority"],
                assignee=record.data.get("assignee", ""), checklist=self.checklist.value())
            self.refresh()
            self.changed.emit()
        except StudioError as error:
            show_error(self, error)
            self.refresh()

    def show_record(self, identifier: str) -> None:
        raise NotImplementedError

    def edit_current(self, *, focus_todos: bool = False) -> None:
        if not self.selected_record or not self.project:
            return
        record = self.project.catalog.get(self.selected_record.id)
        if record.kind == "document":
            self.document_requested.emit(record.id)
        else:
            dialog = TaskEditor(IssueService(self.project), record, self, focus_todos=focus_todos)
            if dialog.exec() == QDialog.Accepted:
                self.refresh()
                self.changed.emit()
            dialog.deleteLater()

    def new_item(self, issue: bool) -> None:
        if not self.project or not self.current_card:
            return
        dialog = QDialog(self)
        dialog.setObjectName("task_create_dialog")
        dialog.setWindowTitle("Issue anlegen" if issue else "Aufgabe anlegen")
        layout = QFormLayout(dialog)
        title, owner = QLineEdit(), QLineEdit()
        title.setObjectName("new_task_title")
        body = QPlainTextEdit()
        body.setObjectName("new_task_body")
        priority = QComboBox()
        priority.addItems(list(PRIORITIES))
        priority.setCurrentText("normal")
        approval = QCheckBox("Benötigt ausdrückliche Aufgabenabnahme")
        for caption, widget in (("Titel", title), ("Beschreibung", body), ("Priorität", priority),
                                 ("Zuständig (optional)", owner), ("Abnahme", approval)):
            layout.addRow(caption, widget)
        checklist = ChecklistEditor(parent=dialog)
        layout.addRow(checklist)
        location = {}
        if issue:
            for key, caption in (("pose", "Pose"), ("direction", "Richtung"),
                                  ("graphics_profile", "Grafikprofil"),
                                  ("frame_count", "Frames"), ("frame_index", "Frame-Index")):
                field = QLineEdit()
                location[key] = field
                layout.addRow(caption + " (optional)", field)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        created = None

        def create() -> None:
            nonlocal created
            try:
                checklist.commit_pending()
                fields = {key: widget.text().strip() or None for key, widget in location.items()}
                for key in ("frame_count", "frame_index"):
                    if fields.get(key) is not None:
                        fields[key] = int(fields[key])
                card = self.project.catalog.get(self.current_card)
                if card.kind == "asset":
                    fields["asset_id"] = card.id
                created = IssueService(self.project).create(
                    self.current_card, title.text(), body.toPlainText(), issue=issue,
                    priority=priority.currentText(), approval_needed=approval.isChecked(),
                    assignee=owner.text(), finding=Finding(**fields), checklist=checklist.value(),
                )
                dialog.accept()
            except (StudioError, ValueError) as error:
                show_error(dialog, error)

        buttons.accepted.connect(create)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted and created:
            self.show_record(created.id)
            self.changed.emit()
        dialog.deleteLater()

    def change_status(self) -> None:
        if self.selected_record:
            self.apply_status(self.selected_record, self.new_status.currentData())

    def apply_status(self, record: Record, status: str) -> None:
        if not self.project or record.kind not in {"task", "issue"}:
            return
        if record.data["status"] == status:
            return
        approved = False
        if record.data.get("approval_needed") and status == "done":
            approved = QMessageBox.question(
                self, "Aufgabenabnahme", "Aufgabe ausdrücklich abnehmen? Keine Asset-Freigabe!",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            ) == QMessageBox.StandardButton.Yes
            if not approved:
                return
        try:
            IssueService(self.project).set_status(record.id, status, record.revision_no,
                                                  approval_confirmed=approved)
            self.refresh()
            self.changed.emit()
        except StudioError as exc:
            show_error(self, exc)
            self.refresh()
