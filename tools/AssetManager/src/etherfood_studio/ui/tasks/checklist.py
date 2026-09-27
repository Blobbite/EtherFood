"""The same checkable to-do list in creation, editing and read-side task details."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget,
)

from ...domain.models import StudioError, new_id
from ..common import button, label


class ChecklistEditor(QWidget):
    changed = Signal()
    edit_requested = Signal()

    def __init__(self, items=None, parent=None, *, editable=True) -> None:
        super().__init__(parent)
        self.editable = editable
        self.setObjectName("task_checklist")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.summary = label("", "checklist_summary")
        layout.addWidget(self.summary)
        self.items = QListWidget()
        self.items.setObjectName("checklist_items")
        self.items.setMaximumHeight(155)
        layout.addWidget(self.items)
        self.empty_button = button("To-dos hinzufügen …", "empty_checklist_edit",
                                   self.edit_requested.emit)
        layout.addWidget(self.empty_button)
        if editable:
            actions = QHBoxLayout()
            self.text = QLineEdit()
            self.text.setObjectName("checklist_new_text")
            self.text.setPlaceholderText("Neuer To-do-Punkt …")
            self.text.setMaxLength(500)
            self.text.returnPressed.connect(self.add)
            actions.addWidget(self.text, 1)
            actions.addWidget(button("+ Punkt", "checklist_add", self.add))
            actions.addWidget(button("Entfernen", "checklist_remove", self.remove))
            layout.addLayout(actions)
        else:
            layout.addStretch(1)
        self.fill(items or [])
        self.items.itemChanged.connect(self.notify)

    def fill(self, items) -> None:
        self.items.blockSignals(True)
        self.items.clear()
        for item in items:
            self._append(item)
        self.items.blockSignals(False)
        self.caption()

    def _append(self, value) -> None:
        item = QListWidgetItem(value["text"])
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable \
            | Qt.ItemFlag.ItemIsUserCheckable
        if self.editable:
            flags |= Qt.ItemFlag.ItemIsEditable
        item.setFlags(flags)
        item.setData(Qt.ItemDataRole.UserRole, value["id"])
        item.setCheckState(Qt.CheckState.Checked if value["done"]
                           else Qt.CheckState.Unchecked)
        self.items.addItem(item)

    def value(self) -> list[dict]:
        return [{"id": item.data(Qt.ItemDataRole.UserRole), "text": item.text(),
                 "done": item.checkState() == Qt.CheckState.Checked}
                for item in (self.items.item(i) for i in range(self.items.count()))]

    def caption(self) -> None:
        values = self.value()
        done = sum(item["done"] for item in values)
        self.summary.setText(f"To-dos: {done}/{len(values)} erledigt" if values else
                             "Noch keine To-dos.")
        self.empty_button.setVisible(not self.editable and not values)
        self.items.setVisible(self.editable or bool(values))

    def notify(self, *args) -> None:
        self.caption()
        self.changed.emit()

    def add(self) -> None:
        if self.text.text().strip() and self.items.count() >= 200:
            self.summary.setText("Höchstens 200 To-dos. Eingabe bleibt unverändert erhalten.")
        elif self.text.text().strip():
            self._append({"id": new_id(), "text": self.text.text().strip(), "done": False})
            self.text.clear()
            self.notify()

    def commit_pending(self) -> None:
        if self.text.text().strip() and self.items.count() >= 200:
            raise StudioError("validation", "Höchstens 200 To-dos. Eingabe bitte kürzen.")
        self.add()

    def remove(self) -> None:
        if self.items.currentRow() >= 0:
            self.items.takeItem(self.items.currentRow())
            self.notify()
