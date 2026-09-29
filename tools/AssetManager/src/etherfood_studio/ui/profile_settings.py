"""Existing graphics-profile editing, independent from pipeline execution."""

from copy import deepcopy
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from ..application.commands import Command, Commands
from ..application.profile_service import ProfileService
from ..domain.graphics import proportional_size, validate_profiles
from ..domain.models import StudioError
from .common import button, label, show_error


def choice(values, current=None):
    widget = QComboBox()
    for key, title in values:
        widget.addItem(title, key)
    widget.setCurrentIndex(max(0, widget.findData(current)))
    return widget


def readonly(text):
    item = QTableWidgetItem(str(text))
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


class ProfileSizeEdit(QLineEdit):
    """Keep full persisted precision rather than rounding settings just by opening the form."""

    def __init__(self, value):
        super().__init__(str(value))
        self.setToolTip(
            "Ein proportionaler Wert: Faktor (z. B. 0.5) " "oder maximale Kante in Pixeln."
        )

    def value(self):
        try:
            return float(self.text().strip().replace(",", "."))
        except ValueError as error:
            raise StudioError("validation", "Faktor/Kante benötigt eine gültige Zahl.") from error

    def setValue(self, value):
        self.setText(str(value))


class ProfileDialog(QDialog):
    """Edit stable project keys and proportional per-frame dimensions."""

    changed = Signal()

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project, self.service = project, ProfileService(project)
        self.revision = project.project().revision_no
        self.original = list(self.service.profiles().values())
        self.commands = Commands(project)
        self.draft, self.track_changes = deepcopy(self.original), False
        self.loading_rows = True
        self.filling = False
        self.setWindowTitle("Projektweite Grafikprofile")
        self.resize(1160, 620)
        layout = QVBoxLayout(self)
        layout.addWidget(
            label(
                "Größen gelten pro Frame, nicht für das gesamte Spritesheet. Bestehende Schlüssel "
                "bleiben unverändert. Deaktivierte Profile sind nicht angefordert; Pixel High kann "
                "für Pixel Low trotzdem intern nötig sein. Beispielquelle: 512 × 256 Pixel."
            )
        )
        self.table = QTableWidget(0, 9)
        self.table.setObjectName("pipeline_profiles")
        self.table.setHorizontalHeaderLabels(
            [
                "Schlüssel",
                "Anzeigename",
                "Aktiv",
                "Verfahren",
                "Größenmodus",
                "Wert",
                "Farben",
                "Pixel-High-Bezug",
                "Beispiel pro Frame",
            ]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemChanged.connect(self.update_samples)
        layout.addWidget(self.table)
        self.notice = label("", "pipeline_profile_notice")
        layout.addWidget(self.notice)
        actions = QHBoxLayout()
        actions.addWidget(button("+ Profil", "pipeline_profile_add", self.add_profile))
        self.undo_button = button(
            "Entwurf rückgängig", "pipeline_profile_undo", lambda: self.history(False)
        )
        self.redo_button = button(
            "Entwurf wiederholen", "pipeline_profile_redo", lambda: self.history(True)
        )
        actions.addWidget(self.undo_button)
        actions.addWidget(self.redo_button)
        actions.addStretch()
        actions.addWidget(button("Profile speichern", "pipeline_profile_save", self.save))
        actions.addWidget(button("Schließen", "pipeline_profile_close", self.reject))
        layout.addLayout(actions)
        for profile in self.original:
            self.add_row(profile, existing=True)
        self.loading_rows = False
        self.track_changes = True
        self.table.resizeColumnsToContents()
        self.update_samples()

    def add_row(self, profile, *, existing=False):
        self.filling = True
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(
            row, 0, readonly(profile["key"]) if existing else QTableWidgetItem(profile["key"])
        )
        self.table.setItem(row, 1, QTableWidgetItem(profile["name"]))
        enabled = QCheckBox()
        enabled.setChecked(profile["enabled"])
        method = choice(
            (
                ("comic", "Comic · glatt"),
                ("pixel", "Pixel High · Palette"),
                ("pixel_low", "Pixel Low · gleiche Palette"),
            ),
            profile["method"],
        )
        mode = choice((("factor", "Faktor"), ("max_edge", "Maximale Kante")), profile["mode"])
        size = ProfileSizeEdit(profile["value"])
        colors = QSpinBox()
        colors.setRange(2, 256)
        colors.setValue(profile["colors"])
        colors.setKeyboardTracking(False)
        parent = choice(
            ((None, "HD-Quelle"), (profile["parent"], profile["parent"] or "")), profile["parent"]
        )
        for column, widget in enumerate((enabled, method, mode, size, colors, parent), 2):
            self.table.setCellWidget(row, column, widget)
        self.table.setItem(row, 8, readonly(""))
        self.filling = False
        enabled.toggled.connect(self.update_samples)
        method.currentIndexChanged.connect(self.update_samples)
        mode.currentIndexChanged.connect(lambda: self.update_mode(row))
        size.textChanged.connect(self.update_samples)
        colors.valueChanged.connect(self.update_samples)
        parent.currentIndexChanged.connect(self.update_samples)
        self.update_mode(row)

    def update_mode(self, row):
        size, mode = self.table.cellWidget(row, 5), self.table.cellWidget(row, 4).currentData()
        size.setPlaceholderText("Faktor > 0 bis 1" if mode == "factor" else "Ganze Pixelzahl")
        self.update_samples()

    def add_profile(self):
        keys = {self.table.item(row, 0).text() for row in range(self.table.rowCount())}
        index = 1
        while f"custom_{index}" in keys:
            index += 1
        self.add_row(
            {
                "key": f"custom_{index}",
                "name": "Eigenes Profil",
                "enabled": True,
                "method": "comic",
                "mode": "factor",
                "value": 0.5,
                "colors": 64,
                "parent": None,
            }
        )
        self.table.setCurrentCell(self.table.rowCount() - 1, 1)

    def values(self):
        result = []
        for row in range(self.table.rowCount()):
            mode = self.table.cellWidget(row, 4).currentData()
            value = self.table.cellWidget(row, 5).value()
            result.append(
                {
                    "key": self.table.item(row, 0).text().strip(),
                    "name": self.table.item(row, 1).text().strip(),
                    "enabled": self.table.cellWidget(row, 2).isChecked(),
                    "method": self.table.cellWidget(row, 3).currentData(),
                    "mode": mode,
                    "value": int(value) if mode == "max_edge" and value.is_integer() else value,
                    "colors": self.table.cellWidget(row, 6).value(),
                    "parent": self.table.cellWidget(row, 7).currentData(),
                }
            )
        return result

    def update_samples(self, *_args):
        if self.filling or self.loading_rows:
            return
        self.filling = True
        try:
            values = self.values()
            parents = [(p["key"], p["name"]) for p in values if p["method"] == "pixel"]
            for row, profile in enumerate(values):
                low = profile["method"] == "pixel_low"
                parent = self.table.cellWidget(row, 7)
                selected = parent.currentData()
                parent.blockSignals(True)
                parent.clear()
                for key, title in (parents if low else [(None, "HD-Quelle")]):
                    parent.addItem(f"{title} · {key}" if key else title, key)
                parent.setCurrentIndex(max(0, parent.findData(selected)))
                parent.setEnabled(low)
                parent.blockSignals(False)
                self.table.cellWidget(row, 6).setEnabled(profile["method"] == "pixel")
            profiles = validate_profiles(self.values())
            for row, profile in enumerate(profiles.values()):
                size = (512, 256)
                if profile["parent"]:
                    parent = profiles[profile["parent"]]
                    size = proportional_size(*size, parent["mode"], parent["value"])
                width, height = proportional_size(*size, profile["mode"], profile["value"])
                self.table.item(row, 8).setText(f"{width} × {height} px")
            self.notice.setText(
                "Proportional, ohne Vergrößerung; Pixelmaße werden halb aufgerundet. "
                "Pixel Low übernimmt die Palette seines Pixel-High-Profils."
            )
        except (StudioError, ValueError) as error:
            self.notice.setText(str(error))
            for row in range(self.table.rowCount()):
                self.table.item(row, 8).setText("–")
        finally:
            self.filling = False
        if self.track_changes:
            self.record_change()

    def record_change(self):
        try:
            before, after = deepcopy(self.draft), self.values()
            validate_profiles(after)
        except (StudioError, ValueError):
            return
        if before != after:
            initial = [True]

            def forward():
                if initial[0]:
                    initial[0] = False
                else:
                    self.restore_draft(after)

            self.commands.execute(
                Command("Profilentwurf ändern", forward, lambda: self.restore_draft(before))
            )
            self.draft = deepcopy(after)
        self.undo_button.setEnabled(bool(self.commands.done))
        self.redo_button.setEnabled(bool(self.commands.undone))

    def restore_draft(self, values):
        self.track_changes = False
        self.loading_rows = True
        self.filling = True
        self.table.setRowCount(0)
        keys = {profile["key"] for profile in self.original}
        for profile in values:
            self.add_row(profile, existing=profile["key"] in keys)
        self.draft = deepcopy(values)
        self.track_changes = True
        self.loading_rows = False
        self.update_samples()

    def history(self, redo):
        self.commands.redo() if redo else self.commands.undo()
        self.undo_button.setEnabled(bool(self.commands.done))
        self.redo_button.setEnabled(bool(self.commands.undone))

    def save(self):
        try:
            self.service.save(self.values(), self.revision)
            self.original = deepcopy(self.values())
            self.revision = self.project.project().revision_no
            self.changed.emit()
            self.accept()
        except (StudioError, OSError, ValueError) as error:
            show_error(self, error)

    def may_close(self):
        try:
            unchanged = self.values() == self.original
        except (StudioError, ValueError):
            unchanged = False
        return (
            unchanged
            or QMessageBox.question(
                self,
                "Ungespeicherte Profile",
                "Änderungen an Projektprofilen verwerfen?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        )

    def reject(self):
        if self.may_close():
            super().reject()

    def closeEvent(self, event):
        event.accept() if self.may_close() else event.ignore()
