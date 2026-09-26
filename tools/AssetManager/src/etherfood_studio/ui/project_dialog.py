"""Explicit project creation; optional external roots are never guessed."""

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QLineEdit, QWidget,
)

from .common import button


class ProjectDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Neues lokales Studio-Projekt")
        self.setObjectName("new_project_dialog")
        form = QFormLayout(self)
        self.title = QLineEdit()
        self.title.setObjectName("new_project_name")
        form.addRow("Projektname", self.title)
        self.paths = {}
        for alias, caption in (("WORKSPACE_ROOT", "Leerer Projektordner"),
                                ("TOOL_ROOT", "PyGameTools (optional)"),
                                ("VERSIONS_ROOT", "Versionsarchiv (optional)"),
                                ("GODOT_ROOT", "Godot-Projekt (optional)")):
            row = QHBoxLayout()
            field = QLineEdit()
            field.setObjectName("root_" + alias.lower())
            self.paths[alias] = field
            row.addWidget(field)
            row.addWidget(button("Wählen …", "choose_" + alias.lower(),
                                 lambda checked=False, target=field: self.choose(target)))
            form.addRow(caption, row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        self.resize(680, 260)

    def choose(self, field: QLineEdit) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Verzeichnis auswählen")
        if chosen:
            field.setText(chosen)

    def roots(self) -> dict[str, Path]:
        return {alias: Path(field.text()) for alias, field in self.paths.items() if field.text()}
