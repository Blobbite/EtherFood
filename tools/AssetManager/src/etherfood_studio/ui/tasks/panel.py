"""Independent project search and the asset-local task list."""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QSplitter, QVBoxLayout,
)

from ...application.document_service import DocumentService
from ...application.issue_service import IssueService
from ..common import label
from ..appearance import appearance
from ..presentation import KIND_NAMES, kind_icon, record_icon
from .base import STATE_NAMES, TaskPanel


class TasksPanel(TaskPanel):
    def __init__(self, owner_id: str | None = None, *, search_only: bool = False) -> None:
        super().__init__(owner_id)
        layout = QVBoxLayout(self)
        filters = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setObjectName("project_search")
        self.query.setPlaceholderText("Titel, Text oder To-do suchen …")
        self.query.setAccessibleName("Dokumente, Aufgaben und Issues durchsuchen")
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
        # Two rows keep search usable in a narrow main-window pane.
        layout.addWidget(self.query)
        for widget in (self.scope, self.state, self.kind, self.asset_type):
            filters.addWidget(widget)
        if owner_id:
            self.scope.hide()
            self.asset_type.hide()
        layout.addLayout(filters)
        self.results = QListWidget()
        self.results.setObjectName("task_results")
        self.results.setIconSize(QSize(40, 20))
        self.results.itemActivated.connect(self._focus)
        self.results.itemClicked.connect(self._focus)
        self.results.currentItemChanged.connect(self._show_details)
        self.results.itemDoubleClicked.connect(lambda item: self.edit_current())
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.results)
        splitter.addWidget(self.detail_page)
        layout.addWidget(splitter, 1)
        self.empty = label("Projekt öffnen, um Inhalte zu suchen.", "task_empty")
        layout.addWidget(self.empty)
        layout.addLayout(self.actions)
        if search_only:
            for widget in (self.create_task, self.create_issue, self.new_status,
                           self.status_button):
                widget.hide()
        self.query.textChanged.connect(self.refresh)
        for widget in (self.scope, self.state, self.kind, self.asset_type):
            widget.currentIndexChanged.connect(self.refresh)
        appearance().changed.connect(self.refresh_icons)

    def refresh_icons(self) -> None:
        for index in range(self.kind.count()):
            if kind := self.kind.itemData(index):
                self.kind.setItemIcon(index, kind_icon(kind))
        for index in range(self.results.count()):
            item = self.results.item(index)
            if self.project:
                item.setIcon(record_icon(self.project.catalog.get(item.data(Qt.UserRole))))

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
        selected = self.selected_record.id if self.selected_record else None
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
            item = QListWidgetItem(record_icon(row),
                                   f"{KIND_NAMES[row.kind]} · {row.title} · {state}")
            item.setData(Qt.ItemDataRole.UserRole, row.id)
            item.setData(Qt.ItemDataRole.UserRole + 1, row.owner_id)
            item.setData(Qt.ItemDataRole.UserRole + 2, (row.kind, row.data.get("status", "open")))
            item.setToolTip(self.project.breadcrumb(row.owner_id))
            self.results.addItem(item)
            if row.id == selected:
                self.results.setCurrentItem(item)
        self.results.blockSignals(False)
        self._show_details(self.results.currentItem())
        self.empty.setText(f"{len(rows)} Treffer · Klick: Inhalt lesen · Doppelklick: öffnen."
                           if rows else "Keine Treffer. Suchbegriff oder Filter ändern.")

    def _show_details(self, item: QListWidgetItem | None, previous: object = None) -> None:
        self.show_details(self.project.catalog.get(item.data(Qt.ItemDataRole.UserRole))
                          if item and self.project else None)

    def show_record(self, identifier: str) -> None:
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

    def _focus(self, item: QListWidgetItem) -> None:
        self.focus_requested.emit(item.data(Qt.ItemDataRole.UserRole + 1))
