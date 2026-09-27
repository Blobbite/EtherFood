"""Shared requirements form and pose-local access to verified source imports."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QGridLayout, QHBoxLayout, QLineEdit,
    QMessageBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ..application.asset_service import AssetService
from ..application.profile_service import ProfileService
from ..application.source_import import SourceImportService
from ..domain.assets import (
    CAPABILITIES, DIRECTION_TEMPLATES, GRAPHICS, TYPE_PRESETS, AssetDefinition,
    default_definition, new_pose,
)
from ..domain.models import StudioError
from .common import button, label, show_error

CAPTION = {"animated": "Animiert", "directional": "Gerichtet",
           "supports_materials": "Materialien", "static_image": "Statisch",
           "package_member": "Paketmitglied"}


class AssetDefinitionEditor(QWidget):
    source_requested = Signal(str)

    def __init__(self, definition: AssetDefinition, parent=None, *, source_actions=False,
                 include_presets=True, profiles=None) -> None:
        super().__init__(parent)
        self.profile_definitions = profiles
        self.source_actions = source_actions
        self.source_counts = {}
        self.setObjectName("asset_requirements_editor")
        layout = QVBoxLayout(self)
        layout.addWidget(label(
            "Anforderungen, keine Freigabe. Frames = Bilder pro Zyklus; FPS = Abspieltempo. "
            "Vorhandene Quellverweise bleiben bei Änderungen erhalten."
        ))
        form = QFormLayout()
        if include_presets:
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
        profile_row = QGridLayout()
        self.graphics = {}
        for index, name in enumerate(profiles if profiles is not None else GRAPHICS):
            check = QCheckBox(profiles[name]["name"] if profiles else name)
            if profiles and not profiles[name]["enabled"]:
                check.setToolTip("Projektweit deaktiviert: nicht als Pflichtausgabe angefordert.")
            self.graphics[name] = check
            profile_row.addWidget(check, index // 4, index % 4)
        form.addRow("Grafikprofile", profile_row)
        self.frames = QLineEdit()
        form.addRow("Frames (z. B. 8,10,12,14,16)", self.frames)
        layout.addLayout(form)
        layout.addWidget(label(
            "Posen: Quellart spritesheet oder single_image; Loop ja/nein; leere Richtungen "
            "erben die Asset-Auswahl. Einzelbilder: keine FPS, Loop nein. "
            "Statische Assets: Posen, Frames und ggf. Richtungen leer lassen."
        ))
        self.poses = QTableWidget(0, 9 if source_actions else 8)
        self.poses.setObjectName("asset_poses")
        self.poses.setHorizontalHeaderLabels([
            "Name", "Exportname", "Quellart", "Loop", "Richtungen", "FPS", "Anker X", "Anker Y",
        ] + (["Quellen / Lieferung"] if source_actions else []))
        for col, width in enumerate((120, 110, 115, 60, 115, 65, 65, 65, 225)):
            if col < self.poses.columnCount():
                self.poses.setColumnWidth(col, width)
        self.poses.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.poses, 1)
        row = QHBoxLayout()
        row.addWidget(button("+ Pose", "asset_add_pose", lambda: self.add_pose(new_pose())))
        row.addWidget(button("Pose entfernen", "asset_remove_pose", self.remove_pose))
        row.addWidget(button("Matrix prüfen", "asset_matrix", self.preview))
        layout.addLayout(row)
        self.summary = label("", "asset_matrix_summary")
        layout.addWidget(self.summary)
        self.fill(definition)

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
        if self.source_actions:
            text = "Spritesheets hinzufügen …" if pose.source_kind == "spritesheet" \
                else "Quellbilder hinzufügen …"
            action = button(text, "pose_sources_" + pose.id,
                             lambda checked=False, key=pose.id: self.source_requested.emit(key))
            action.setToolTip("Quellen dieser Pose prüfen und zentral importieren. "
                              "Geänderte Anforderungen vorher bewusst speichern.")
            self.poses.setCellWidget(row, 8, action)
            self.update_source_button(row)

    def set_source_counts(self, rows: list[dict]) -> None:
        self.source_counts = {}
        for entry in rows:
            if entry["required"]:
                counts = self.source_counts.setdefault(entry["key"].pose_id, [0, 0])
                counts[0] += int(entry["state"] == "imported")
                counts[1] += 1
        for row in range(self.poses.rowCount()):
            self.update_source_button(row)

    def update_source_button(self, row: int) -> None:
        if not self.source_actions:
            return
        identifier = self.poses.item(row, 0).data(Qt.ItemDataRole.UserRole)
        counts = self.source_counts.get(identifier)
        action = self.poses.cellWidget(row, 8)
        title = "Spritesheets hinzufügen …" if self.poses.item(row, 2).text() == "spritesheet" \
            else "Quellbilder hinzufügen …"
        action.setText(title + (f" · {counts[0]}/{counts[1]}" if counts else ""))
        action.setToolTip("Lieferstand der gespeicherten Anforderungen. "
                          "Geänderte Anforderungen vor dem Import bewusst speichern.")

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
        return AssetDefinition.from_data(data, profiles=self.profile_definitions)

    def preview(self) -> None:
        try:
            definition = self.value()
            self.summary.setText(f"{len(definition.expected())} erwartete Varianten · "
                                 "Vorhandensein ist kein Prüfergebnis und keine Freigabe.")
        except StudioError as error:
            self.summary.setText(str(error))

class AssetSettingsDialog(QDialog):
    def __init__(self, service: AssetService, identifier: str, parent=None) -> None:
        super().__init__(parent)
        self.service, self.identifier = service, identifier
        self.record = service.asset(identifier)
        self.changed = False
        self.setObjectName("asset_requirements")
        self.setWindowTitle("Asset-Anforderungen · " + self.record.title)
        self.resize(1160, 720)
        existing = self.record.data.get("asset_definition")
        self.editor = AssetDefinitionEditor(
            service.parse_definition(existing) if existing else default_definition(),
            self, source_actions=True, profiles=ProfileService(service.project).profiles(),
        )
        # Keep the established dialog inspection API while sharing one form with the wizard.
        for name in ("poses", "preset", "summary", "frames", "directions", "graphics",
                     "capabilities", "type_id", "type_label"):
            setattr(self, name, getattr(self.editor, name))
        self.editor.source_requested.connect(self.import_pose)
        if existing:
            self.editor.set_source_counts(SourceImportService(service).matrix(identifier))
        layout = QVBoxLayout(self)
        layout.addWidget(self.editor)
        actions = QHBoxLayout()
        actions.addWidget(button("Speichern", "asset_save", self.save))
        actions.addWidget(button("Schließen / ungespeicherte Eingaben verwerfen", "asset_cancel",
                                 self.reject))
        layout.addLayout(actions)

    def save(self) -> None:
        try:
            self.record = self.service.configure(self.identifier, self.editor.value().to_data(),
                                                  self.record.revision_no)
            self.changed = True
        except StudioError as error:
            show_error(self, error)
            return
        self.accept()

    def import_pose(self, pose_id: str) -> None:
        try:
            self.record, changed = import_pose_sources(
                self, self.service, self.record, self.editor.value(), pose_id,
            )
            self.changed = self.changed or changed
            if self.record.data.get("asset_definition"):
                self.editor.set_source_counts(SourceImportService(self.service).matrix(
                    self.identifier))
        except StudioError as error:
            show_error(self, error)


def import_pose_sources(parent, service: AssetService, record, definition: AssetDefinition,
                        pose_id: str):
    from .source_import_dialog import SourceImportDialog
    changed = False
    if definition.to_data() != record.data.get("asset_definition"):
        if QMessageBox.question(parent, "Anforderungen vor Import speichern?",
            "Die geänderten Anforderungen müssen vor dem Quellimport gespeichert werden. "
            "Ein späteres Schließen nimmt diese Speicherung oder Importe nicht zurück.") \
                != QMessageBox.StandardButton.Yes:
            return record, False
        record = service.configure(record.id, definition.to_data(), record.revision_no)
        changed = True
    dialog = SourceImportDialog(service, record.id, parent, pose_id=pose_id)
    dialog.exec()
    changed = changed or dialog.changed
    dialog.deleteLater()
    return service.asset(record.id), changed
