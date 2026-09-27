"""Search and filter real documents/tasks and focus their owning cards."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QSplitter,
    QVBoxLayout, QWidget,
)

from ...application.document_service import DocumentService
from ...application.issue_service import Finding, IssueService, PRIORITIES, TASK_STATES
from ...application.project_service import ProjectService
from ...domain.models import StudioError
from ..common import button, label, show_error
from ..presentation import KIND_NAMES, kind_icon
from .editor import TaskEditor
from .checklist import ChecklistEditor

STATE_NAMES = {
    "open": "Offen", "in_progress": "In Arbeit", "blocked": "Blockiert", "done": "Erledigt",
}


class TasksPanel(QWidget):
    focus_requested = Signal(str)
    document_requested = Signal(str)
    changed = Signal()

    def __init__(self, owner_id: str | None = None) -> None:
        super().__init__()
        self.fixed_owner = owner_id
        self.selected_record = None
        self.project: ProjectService | None = None
        self.current_card: str | None = owner_id
        layout = QVBoxLayout(self)
        filters = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setObjectName("project_search")
        self.query.setPlaceholderText("Titel oder Text suchen …")
        self.query.setAccessibleName("Dokumente und Aufgaben durchsuchen")
        self.scope = QComboBox()
        self.scope.setObjectName("task_scope")
        self.state = QComboBox()
        self.state.setObjectName("task_status_filter")
        self.state.addItem("Alle Status", None)
        for key, title in STATE_NAMES.items():
            self.state.addItem(title, key)
        self.kind = QComboBox()
        self.kind.setObjectName("task_kind_filter")
        for title, key in (("Alle Inhalte", None), ("Aufgaben", "task"), ("Issues", "issue"),
                           ("Dokumente", "document")):
            if owner_id and key == "document":
                continue
            self.kind.addItem(title, key)
            if key:
                self.kind.setItemIcon(self.kind.count() - 1, kind_icon(key))
        self.asset_type = QComboBox()
        self.asset_type.setObjectName("task_asset_type_filter")
        for title, key in (("Alle Assettypen", None), ("Animiert", "animated"),
                           ("Statisch", "static"), ("Effekt", "effect")):
            self.asset_type.addItem(title, key)
        for widget in (self.query, self.scope, self.state, self.kind, self.asset_type):
            filters.addWidget(widget)
        if owner_id:
            self.scope.hide()
            self.asset_type.hide()
        layout.addLayout(filters)
        self.results = QListWidget()
        self.results.setObjectName("task_results")
        self.results.itemActivated.connect(self._focus)
        self.results.itemClicked.connect(self._focus)
        self.results.currentItemChanged.connect(self._show_details)
        self.results.itemDoubleClicked.connect(lambda item: self.edit_current())
        self.details = QPlainTextEdit()
        self.details.setObjectName("task_details")
        self.details.setReadOnly(True)
        self.details.setPlaceholderText("Inhalt auswählen: Beschreibung und Fundstelle lesen.")
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.results)
        detail_page = QWidget()
        detail_layout = QVBoxLayout(detail_page)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.addWidget(self.details, 1)
        self.checklist = ChecklistEditor(editable=False)
        self.checklist.changed.connect(self.save_checklist)
        detail_layout.addWidget(self.checklist)
        splitter.addWidget(detail_page)
        layout.addWidget(splitter, 1)
        self.empty = label("Projekt öffnen, um Aufgaben und Dokumente zu sehen.", "task_empty")
        layout.addWidget(self.empty)
        actions = QHBoxLayout()
        actions.addWidget(button("+ Aufgabe", "new_task", lambda: self.new_item(False)))
        actions.addWidget(button("+ Issue", "new_issue", lambda: self.new_item(True)))
        self.edit_button = button("Bearbeiten / Öffnen", "edit_task", self.edit_current)
        actions.addWidget(self.edit_button)
        self.new_status = QComboBox()
        self.new_status.setObjectName("task_new_status")
        for key, title in STATE_NAMES.items():
            self.new_status.addItem(title, key)
        actions.addWidget(self.new_status)
        actions.addWidget(button("Status setzen", "set_task_status", self.change_status))
        layout.addLayout(actions)
        self.query.textChanged.connect(self.refresh)
        for widget in (self.scope, self.state, self.kind, self.asset_type):
            widget.currentIndexChanged.connect(self.refresh)
        self.setEnabled(False)

    def bind(self, project: ProjectService) -> None:
        self.project = project
        self.setEnabled(True)
        self.refresh_scopes()

    def refresh_scopes(self) -> None:
        if not self.project:
            return
        current = self.scope.currentData()
        self.scope.blockSignals(True)
        self.scope.clear()
        self.scope.addItem("Gesamtes Projekt", None)
        for card in self.project.cards():
            if card.kind in {"act", "chapter"}:
                self.scope.addItem(self.project.breadcrumb(card.id), card.id)
        self.scope.setCurrentIndex(max(0, self.scope.findData(current)))
        self.scope.blockSignals(False)
        self.refresh()

    def refresh(self, *args: object) -> None:
        if not self.project:
            return
        current = self.results.currentItem()
        selected = current.data(Qt.ItemDataRole.UserRole) if current else None
        self.results.blockSignals(True)
        self.results.clear()
        kind = self.kind.currentData()
        rows = []
        if kind != "document":
            rows.extend(IssueService(self.project).search(
                self.query.text(), scope_id=self.fixed_owner or self.scope.currentData(),
                status=self.state.currentData(),
                kind=kind, asset_type=self.asset_type.currentData(),
            ))
        if not self.fixed_owner and kind in {None, "document"} \
                and self.state.currentData() is None:
            documents = DocumentService(self.project).search(
                self.query.text(), scope_id=self.scope.currentData(),
            )
            rows.extend(row for row in documents if not self.asset_type.currentData()
                        or self.project.catalog.get(row.owner_id).data.get("workflow")
                        == self.asset_type.currentData())
        for row in rows:
            state = STATE_NAMES.get(row.data.get("status"), row.data.get("document_type", ""))
            item = QListWidgetItem(kind_icon(row.kind),
                                   f"{KIND_NAMES[row.kind]} · {row.title} · {state}")
            item.setData(Qt.ItemDataRole.UserRole, row.id)
            item.setData(Qt.ItemDataRole.UserRole + 1, row.owner_id)
            item.setToolTip(self.project.breadcrumb(row.owner_id))
            self.results.addItem(item)
            if row.id == selected:
                self.results.setCurrentItem(item)
        self.results.blockSignals(False)
        self._show_details(self.results.currentItem())
        self.empty.setText(f"{len(rows)} Treffer · Klick: Inhalt lesen · Doppelklick: bearbeiten."
                           if rows else "Keine Treffer. Filter ändern oder eine Aufgabe anlegen.")

    def _show_details(self, item: QListWidgetItem | None, previous: object = None) -> None:
        self.edit_button.setEnabled(item is not None)
        self.selected_record = None
        self.checklist.fill([])
        self.checklist.setEnabled(False)
        if item is None or not self.project:
            self.details.clear()
            return
        row = self.project.catalog.get(item.data(Qt.ItemDataRole.UserRole))
        self.selected_record = row
        lines = [row.title, self.project.breadcrumb(row.owner_id),
                 f"Revision {row.revision_no} · ID {row.id}"]
        if row.kind in {"task", "issue"}:
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
        lines.extend(["", row.data.get("body", "") or "Noch keine Beschreibung."])
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
        # Explicit navigation must reveal the item even when an old filter hides it.
        self.query.clear()
        for widget in (self.scope, self.state, self.kind, self.asset_type):
            widget.setCurrentIndex(0)
        self.refresh()
        for index in range(self.results.count()):
            item = self.results.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == identifier:
                self.results.setCurrentItem(item)
                self.results.scrollToItem(item)
                break

    def edit_current(self) -> None:
        item = self.results.currentItem()
        if not item or not self.project:
            return
        record = self.project.catalog.get(item.data(Qt.ItemDataRole.UserRole))
        if record.kind == "document":
            self.document_requested.emit(record.id)
        elif TaskEditor(IssueService(self.project), record, self).exec() == QDialog.Accepted:
            self.refresh()
            self.changed.emit()

    def _focus(self, item: QListWidgetItem) -> None:
        self.focus_requested.emit(item.data(Qt.ItemDataRole.UserRole + 1))

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
        item = self.results.currentItem()
        if not item or not self.project:
            return
        record = self.project.catalog.get(item.data(Qt.ItemDataRole.UserRole))
        if record.kind not in {"task", "issue"}:
            return
        status = self.new_status.currentData()
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
