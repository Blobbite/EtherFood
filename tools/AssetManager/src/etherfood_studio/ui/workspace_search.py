"""Identically arranged native search views for the two main editors."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..application.search_service import SearchService
from .common import label
from .presentation import KIND_NAMES, kind_icon


class WorkspaceSearch(QWidget):
    open_requested = Signal(object)

    def __init__(self, area, parent=None):
        super().__init__(parent)
        self.area, self.service = area, None
        self.hits = []
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setObjectName(area + "_search_query")
        self.query.setPlaceholderText(
            "Projekt durchsuchen" if area == "project" else "Skripte und Pipelines durchsuchen"
        )
        self.state = QComboBox()
        for text, value in (("Aktiv", "active"), ("Archiv", "archived"), ("Papierkorb", "trash")):
            self.state.addItem(text, value)
        row.addWidget(self.query, 1)
        row.addWidget(self.state)
        layout.addLayout(row)
        self.table = QTableWidget(0, 3)
        self.table.setObjectName(area + "_search_results")
        self.table.setHorizontalHeaderLabels(["Typ", "Name", "Bereich / Pfad"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.cellDoubleClicked.connect(self.activate)
        self.table.itemActivated.connect(lambda item: self.activate(item.row()))
        layout.addWidget(self.table, 1)
        layout.addWidget(label("Enter oder Doppelklick öffnet das tatsächliche Objekt."))
        self.query.textChanged.connect(self.refresh)
        self.query.returnPressed.connect(lambda: self.activate(max(0, self.table.currentRow())))
        self.state.currentIndexChanged.connect(self.refresh)
        from .appearance import appearance

        appearance().changed.connect(self.refresh)

    def bind(self, project):
        self.service = SearchService(project)
        self.refresh()

    def refresh(self):
        if self.service is None:
            return
        self.hits = self.service.query(
            self.query.text(), area=self.area, state=self.state.currentData()
        )
        self.table.setRowCount(len(self.hits))
        for index, hit in enumerate(self.hits):
            for column, text in enumerate(
                (KIND_NAMES.get(hit.kind, "Verwendung"), hit.title, hit.location)
            ):
                item = QTableWidgetItem(text)
                item.setData(Qt.UserRole, hit.id)
                item.setToolTip(text)
                if column == 0:
                    item.setIcon(kind_icon(hit.kind))
                self.table.setItem(index, column, item)

    def refresh_scopes(self):
        self.refresh()

    def activate(self, row=None, column=0):
        row = self.table.currentRow() if row is None else row
        if 0 <= row < len(self.hits):
            self.open_requested.emit(self.hits[row])

    def keyPressEvent(self, event):
        if event.key() in {Qt.Key_Return, Qt.Key_Enter}:
            self.activate()
            event.accept()
        else:
            super().keyPressEvent(event)
