"""Requirements editor, separate from the later character import wizard."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLineEdit,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from ..application.asset_service import AssetService
from ..domain.assets import (
    CAPABILITIES, DIRECTION_TEMPLATES, GRAPHICS, TYPE_PRESETS, AssetDefinition,
    default_definition, new_pose,
)
from ..domain.models import StudioError
from .common import button, label, show_error

CAPTION = {"animated": "Animiert", "directional": "Gerichtet",
           "supports_materials": "Materialien", "static_image": "Statisch",
           "package_member": "Paketmitglied"}


class AssetSettingsDialog(QDialog):
    def __init__(self, service: AssetService, identifier: str, parent=None) -> None:
        super().__init__(parent)
        self.service, self.identifier = service, identifier
        self.record = service.asset(identifier)
        self.setObjectName("asset_requirements")
        self.setWindowTitle("Asset-Anforderungen · " + self.record.title)
        self.resize(1000, 660)
        layout = QVBoxLayout(self)
        layout.addWidget(label(
            "Anforderungen, keine Freigabe. Frames = Bilder pro Zyklus; FPS = Abspieltempo. "
            "Vorhandene Quellverweise bleiben bei Änderungen erhalten."
        ))
        form = QFormLayout()
        self.preset = QComboBox()
        for key, (title, _) in TYPE_PRESETS.items():
            self.preset.addItem(title, key)
        preset_row = QHBoxLayout()
        preset_row.addWidget(self.preset)
        preset_row.addWidget(button("Vorlage laden", "asset_load_preset", self.load_preset))
        form.addRow("Neue Vorlage (ersetzt Eingaben)", preset_row)
        self.type_id, self.type_label = QLineEdit(), QLineEdit()
        form.addRow("Typ-ID", self.type_id)
        form.addRow("Typname", self.type_label)
        caps = QHBoxLayout()
        self.capabilities = {}
        for key in CAPABILITIES:
            check = QCheckBox(CAPTION[key])
            self.capabilities[key] = check
            caps.addWidget(check)
        form.addRow("Fähigkeiten", caps)
        self.directions = QLineEdit()
        direction_row = QHBoxLayout()
        direction_row.addWidget(self.directions)
        for count in (8, 4, 2, 1):
            direction_row.addWidget(button(str(count), f"asset_directions_{count}",
                lambda checked=False, n=count: self.directions.setText(
                    ",".join(DIRECTION_TEMPLATES[n]))))
        form.addRow("Richtungen (Reihenfolge)", direction_row)
        profiles = QHBoxLayout()
        self.graphics = {}
        for name in GRAPHICS:
            check = QCheckBox(name)
            self.graphics[name] = check
            profiles.addWidget(check)
        form.addRow("Grafikprofile", profiles)
        self.frames = QLineEdit()
        form.addRow("Frames (z. B. 8,10,12,14,16)", self.frames)
        layout.addLayout(form)
        layout.addWidget(label(
            "Posen: Quellart spritesheet oder single_image; Loop ja/nein; leere Richtungen "
            "erben die Asset-Auswahl. Einzelbilder: keine FPS, Loop nein. "
            "Statische Assets: Posen, Frames und ggf. Richtungen leer lassen."
        ))
        self.poses = QTableWidget(0, 8)
        self.poses.setObjectName("asset_poses")
        self.poses.setHorizontalHeaderLabels([
            "Name", "Exportname", "Quellart", "Loop", "Richtungen", "FPS", "Anker X", "Anker Y",
        ])
        self.poses.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.poses, 1)
        row = QHBoxLayout()
        row.addWidget(button("+ Pose", "asset_add_pose", lambda: self.add_pose(new_pose())))
        row.addWidget(button("Pose entfernen", "asset_remove_pose", self.remove_pose))
        row.addWidget(button("Matrix prüfen", "asset_matrix", self.preview))
        layout.addLayout(row)
        self.summary = label("", "asset_matrix_summary")
        layout.addWidget(self.summary)
        actions = QHBoxLayout()
        actions.addWidget(button("Speichern", "asset_save", self.save))
        actions.addWidget(button("Abbrechen", "asset_cancel", self.reject))
        layout.addLayout(actions)
        existing = self.record.data.get("asset_definition")
        self.fill(AssetDefinition.from_data(existing) if existing else default_definition())

    def fill(self, definition: AssetDefinition) -> None:
        self.type_id.setText(definition.type_id)
        self.type_label.setText(definition.type_label)
        for key, check in self.capabilities.items():
            check.setChecked(key in definition.capabilities)
        self.directions.setText(",".join(definition.directions))
        for key, check in self.graphics.items():
            check.setChecked(key in definition.graphics)
        self.frames.setText(",".join(map(str, definition.frames)))
        self.poses.setRowCount(0)
        for pose in definition.poses:
            self.add_pose(pose)
        self.preview()

    def load_preset(self) -> None:
        self.fill(default_definition(self.preset.currentData()))

    def add_pose(self, pose) -> None:
        row = self.poses.rowCount()
        self.poses.insertRow(row)
        values = [pose.display_name, pose.export_name, pose.source_kind,
                  "ja" if pose.loop else "nein", ",".join(pose.directions or ()),
                  "" if pose.fps is None else str(pose.fps), *map(str, pose.anchor)]
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setData(Qt.ItemDataRole.UserRole, pose.id)
            self.poses.setItem(row, col, item)

    def remove_pose(self) -> None:
        if self.poses.currentRow() >= 0:
            self.poses.removeRow(self.poses.currentRow())

    @staticmethod
    def split(text: str) -> list[str]:
        return [v.strip() for v in text.split(",") if v.strip()]

    def value(self) -> AssetDefinition:
        poses = []
        try:
            for row in range(self.poses.rowCount()):
                v = [self.poses.item(row, c).text().strip() for c in range(8)]
                if v[3] not in {"ja", "nein"}:
                    raise ValueError("Loop: ja/nein")
                poses.append({"id": self.poses.item(row, 0).data(Qt.ItemDataRole.UserRole),
                              "display_name": v[0], "export_name": v[1], "source_kind": v[2],
                              "loop": v[3] == "ja", "directions": self.split(v[4]) or None,
                              "fps": float(v[5]) if v[5] else None,
                              "anchor": [float(v[6]), float(v[7])]})
            data = {"schema_version": 1, "type": {"id": self.type_id.text().strip(),
                    "label": self.type_label.text().strip(), "capabilities": [
                        k for k, c in self.capabilities.items() if c.isChecked()]},
                    "directions": self.split(self.directions.text()), "graphics": [
                        k for k, c in self.graphics.items() if c.isChecked()],
                    "frames": [int(v) for v in self.split(self.frames.text())], "poses": poses}
        except ValueError as error:
            raise StudioError("validation", "Ungültige Zahl oder Loop-Angabe.") from error
        return AssetDefinition.from_data(data)

    def preview(self) -> None:
        try:
            definition = self.value()
            self.summary.setText(f"{len(definition.expected())} erwartete Varianten · "
                                 "Vorhandensein ist kein Prüfergebnis und keine Freigabe.")
        except StudioError as error:
            self.summary.setText(str(error))

    def save(self) -> None:
        try:
            self.service.configure(self.identifier, self.value().to_data(), self.record.revision_no)
        except StudioError as error:
            show_error(self, error)
            return
        self.accept()
