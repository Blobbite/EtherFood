"""Project-scoped task/issue board, independent of the project search."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLineEdit, QScrollArea, QSizePolicy, QSplitter, QVBoxLayout, QWidget,
)

from ...application.kanban_service import KanbanService
from ...domain.models import new_id
from ..common import button, label
from ..presentation import kind_icon
from .base import STATE_NAMES, TaskPanel
from .column import KanbanColumn, StatusHeader, TASK_ROLE


class KanbanPanel(TaskPanel):
    def __init__(self, owner_id: str | None = None, *, compact: bool = False) -> None:
        super().__init__(owner_id)
        self.compact = compact
        self.records = {}
        self.columns = {}
        self.headings = {}
        self.dragged_record = None
        self.drag_token = new_id()
        layout = QVBoxLayout(self)
        self.scope_label = label("Projekt öffnen, um Aufgaben zu sehen.", "kanban_scope")
        self.scope_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.scope_label)
        filters = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setObjectName("kanban_filter")
        self.query.setPlaceholderText("Aufgaben in diesem Bereich filtern …")
        self.query.setAccessibleName("Kanban nach Titel, Text oder To-do filtern")
        filters.addWidget(self.query, 1)
        self.kind = QComboBox()
        self.kind.setObjectName("kanban_kind_filter")
        for title, key in (("Aufgaben + Issues", None), ("Nur Aufgaben", "task"),
                           ("Nur Issues", "issue")):
            self.kind.addItem(title, key)
            if key:
                self.kind.setItemIcon(self.kind.count() - 1, kind_icon(key))
        filters.addWidget(self.kind)
        project_button = button("Gesamtes Projekt", "kanban_project", self.show_project)
        project_button.setVisible(not compact)
        filters.addWidget(project_button)
        layout.addLayout(filters)
        board_page = QWidget()
        board_layout = QVBoxLayout(board_page) if compact else QHBoxLayout(board_page)
        board_layout.setContentsMargins(0, 0, 0, 0)
        board_layout.setSpacing(4)
        colors = {"open": "#5a729a", "in_progress": "#2967a1",
                  "blocked": "#9d6825", "done": "#398155"}
        for status, title in STATE_NAMES.items():
            page = QWidget()
            column_layout = QVBoxLayout(page)
            column_layout.setContentsMargins(0, 0, 0, 0)
            heading = StatusHeader(self, status) if compact else label("")
            heading.setObjectName("kanban_heading_" + status)
            heading.setText(title + " · 0")
            heading.setStyleSheet(f"background: {colors[status]}; color: white; padding: 8px; "
                                  "border-radius: 5px; font-weight: bold;")
            if compact:
                heading.setStyleSheet(f"background: {colors[status]}; color: white; "
                                      "padding: 2px 6px; text-align: left; border-radius: 3px;")
                heading.setFixedHeight(26)
                heading.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
            column_layout.addWidget(heading)
            column = KanbanColumn(self, status)
            column.setAccessibleName(title + " – Aufgaben und Issues")
            column_layout.addWidget(column, 1)
            board_layout.addWidget(page, 0 if compact else 1)
            self.columns[status] = column
            self.headings[status] = heading
            if compact:
                column.setMinimumHeight(70)
                column.setMaximumHeight(240)
                heading.toggled.connect(column.setVisible)
                heading.toggled.connect(lambda expanded, control=heading:
                                        control.setArrowType(Qt.DownArrow if expanded
                                                             else Qt.RightArrow))
                heading.setChecked(status != "done")
                column.setVisible(heading.isChecked())
        if compact:
            board_layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(board_page)
        scroll.setMinimumHeight(180)
        self.board_scroll = scroll
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.board_splitter = splitter
        splitter.addWidget(scroll)
        self.detail_page.setMinimumWidth(270)
        self.detail_page.setMaximumWidth(380)
        self.checklist.items.setMaximumHeight(16777215)
        self.checklist.setMinimumHeight(160)
        splitter.addWidget(self.detail_page)
        splitter.setCollapsible(1, False)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([620, 310])
        layout.addWidget(splitter, 1)
        self.empty = label("Klick: Inhalt · Doppelklick: bearbeiten · Ziehen: Status wechseln.",
                           "kanban_summary")
        layout.addWidget(self.empty)
        self.owner_button = button("Zum Bezug", "kanban_owner", self.focus_owner)
        self.owner_button.setEnabled(False)
        self.actions.addWidget(self.owner_button)
        layout.addLayout(self.actions)
        self.query.textChanged.connect(self.refresh)
        self.kind.currentIndexChanged.connect(self.refresh)

    def bind(self, project) -> None:
        self.current_card = self.fixed_owner or project.project().id
        self.selected_record = None
        self.dragged_record = None
        self.drag_token = new_id()
        super().bind(project)

    def set_scope(self, identifier: str) -> None:
        self.current_card = identifier
        self.refresh()

    def show_project(self) -> None:
        if self.project:
            self.focus_requested.emit(self.project.project().id)

    def focus_owner(self) -> None:
        if self.selected_record:
            self.focus_requested.emit(self.selected_record.owner_id)

    def refresh(self, *args: object) -> None:
        if not self.project or not self.current_card:
            return
        selected = self.selected_record.id if self.selected_record else None
        entries = KanbanService(self.project).entries(
            self.current_card, self.query.text(), kind=self.kind.currentData(),
        )
        self.records = {entry.record.id: entry.record for entry in entries}
        self.scope_label.setText("Bereich / neue Aufgaben: "
                                 + self.project.breadcrumb(self.current_card))
        for status, column in self.columns.items():
            column.fill(entries, selected)
            self.headings[status].setText(f"{STATE_NAMES[status]} · {len(column.items_by_id)}")
        self.show_details(self.records.get(selected))
        self.owner_button.setEnabled(self.selected_record is not None)
        self.empty.setText(
            f"{len(entries)} Aufgaben/Issues · Klick: Inhalt · Doppelklick: bearbeiten · "
            "Ziehen: Status wechseln."
            if entries else "Keine Aufgaben im Bereich/Filter. + Aufgabe oder + Issue anlegen."
        )

    def select_item(self, column: KanbanColumn) -> None:
        item = column.currentItem()
        identifier = item.data(0, TASK_ROLE) if item else None
        if identifier not in self.records:
            return
        for other in self.columns.values():
            if other is not column:
                other.blockSignals(True)
                other.setCurrentItem(None)
                other.blockSignals(False)
        self.show_details(self.records[identifier])
        self.owner_button.setEnabled(True)

    def show_record(self, identifier: str) -> None:
        if not self.project:
            return
        self.query.clear()
        self.kind.setCurrentIndex(0)
        self.refresh()
        for column in self.columns.values():
            if identifier in column.items_by_id:
                if self.compact:
                    self.headings[column.status].setChecked(True)
                item = column.items_by_id[identifier]
                parent = item.parent()
                while parent:
                    parent.setExpanded(True)
                    parent = parent.parent()
                column.setCurrentItem(item)
                column.scrollToItem(item)
                self.select_item(column)
                break

    def apply_status(self, record, status: str) -> None:
        super().apply_status(record, status)
        if self.compact and record.id in self.records:
            self.headings[self.records[record.id].data["status"]].setChecked(True)
