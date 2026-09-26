"""Search and filter real documents/tasks and focus their owning cards."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QVBoxLayout, QWidget,
)

from ...application.document_service import DocumentService
from ...application.issue_service import Finding, IssueService, PRIORITIES, TASK_STATES
from ...application.project_service import ProjectService
from ...domain.models import StudioError
from ..common import button, label, show_error

STATE_NAMES = {
    "open": "Offen", "in_progress": "In Arbeit", "blocked": "Blockiert", "done": "Erledigt",
}


class TasksPanel(QWidget):
    focus_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.project: ProjectService | None = None
        self.current_card: str | None = None
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
            self.kind.addItem(title, key)
        self.asset_type = QComboBox()
        self.asset_type.setObjectName("task_asset_type_filter")
        for title, key in (("Alle Assettypen", None), ("Animiert", "animated"),
                           ("Statisch", "static"), ("Effekt", "effect")):
            self.asset_type.addItem(title, key)
        for widget in (self.query, self.scope, self.state, self.kind, self.asset_type):
            filters.addWidget(widget)
        layout.addLayout(filters)
        self.results = QListWidget()
        self.results.setObjectName("task_results")
        self.results.itemActivated.connect(self._focus)
        self.results.itemClicked.connect(self._focus)
        layout.addWidget(self.results, 1)
        self.empty = label("Projekt öffnen, um Aufgaben und Dokumente zu sehen.", "task_empty")
        layout.addWidget(self.empty)
        actions = QHBoxLayout()
        actions.addWidget(button("+ Aufgabe", "new_task", lambda: self.new_item(False)))
        actions.addWidget(button("+ Issue", "new_issue", lambda: self.new_item(True)))
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
        self.results.clear()
        kind = self.kind.currentData()
        rows = []
        if kind != "document":
            rows.extend(IssueService(self.project).search(
                self.query.text(), scope_id=self.scope.currentData(),
                status=self.state.currentData(),
                kind=kind, asset_type=self.asset_type.currentData(),
            ))
        if kind in {None, "document"} and self.state.currentData() is None:
            documents = DocumentService(self.project).search(
                self.query.text(), scope_id=self.scope.currentData(),
            )
            rows.extend(row for row in documents if not self.asset_type.currentData()
                        or self.project.catalog.get(row.owner_id).data.get("workflow")
                        == self.asset_type.currentData())
        for row in rows:
            state = STATE_NAMES.get(row.data.get("status"), row.data.get("document_type", ""))
            item = QListWidgetItem(f"{row.title} · {state}")
            item.setData(Qt.ItemDataRole.UserRole, row.id)
            item.setData(Qt.ItemDataRole.UserRole + 1, row.owner_id)
            item.setToolTip(self.project.breadcrumb(row.owner_id))
            self.results.addItem(item)
        self.empty.setText(f"{len(rows)} Treffer · Klick fokussiert die Bezugskarte."
                           if rows else "Keine Treffer. Filter ändern oder eine Aufgabe anlegen.")

    def _focus(self, item: QListWidgetItem) -> None:
        self.focus_requested.emit(item.data(Qt.ItemDataRole.UserRole + 1))

    def new_item(self, issue: bool) -> None:
        if not self.project or not self.current_card:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Issue anlegen" if issue else "Aufgabe anlegen")
        layout = QFormLayout(dialog)
        title, owner = QLineEdit(), QLineEdit()
        title.setObjectName("new_task_title")
        body = QPlainTextEdit()
        priority = QComboBox()
        priority.addItems(list(PRIORITIES))
        priority.setCurrentText("normal")
        approval = QCheckBox("Benötigt ausdrückliche Aufgabenabnahme")
        for caption, widget in (("Titel", title), ("Beschreibung", body), ("Priorität", priority),
                                 ("Zuständig (optional)", owner), ("Abnahme", approval)):
            layout.addRow(caption, widget)
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
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            fields = {key: widget.text().strip() or None for key, widget in location.items()}
            for key in ("frame_count", "frame_index"):
                if fields.get(key) is not None:
                    fields[key] = int(fields[key])
            card = self.project.catalog.get(self.current_card)
            if card.kind == "asset":
                fields["asset_id"] = card.id
            IssueService(self.project).create(
                self.current_card, title.text(), body.toPlainText(), issue=issue,
                priority=priority.currentText(), approval_needed=approval.isChecked(),
                assignee=owner.text(), finding=Finding(**fields),
            )
            self.refresh()
        except (StudioError, ValueError) as exc:
            show_error(self, exc)

    def change_status(self) -> None:
        item = self.results.currentItem()
        if not item or not self.project:
            return
        record = self.project.catalog.get(item.data(Qt.ItemDataRole.UserRole))
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
        except StudioError as exc:
            show_error(self, exc)
