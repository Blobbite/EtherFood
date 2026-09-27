"""Explicit source mappings and cancellable imports using an isolated DB connection."""

from pathlib import Path
import re
from threading import Event

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLineEdit, QMessageBox,
    QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from ..application.asset_service import AssetService
from ..application.project_service import ProjectService
from ..application.source_import import ImportPlan, SourceImportService, SourceSpec
from ..domain.models import StudioError
from ..domain.sources import SourceKey
from ..storage.grid_detection import named_grid
from .common import button, label, show_error
from .sources import SourcesPanel


class SourceWorker(QThread):
    result_ready = Signal(object)
    failed = Signal(object)
    progress = Signal(int)

    def __init__(self, root: Path, call, parent=None) -> None:
        super().__init__(parent)
        self.root, self.call = root, call
        self.cancel = Event()

    def run(self) -> None:
        project = None
        try:
            project = ProjectService.open(self.root)
            service = SourceImportService(AssetService(project))
            self.result_ready.emit(self.call(service, self.cancel.is_set, self.progress.emit))
        except Exception as error:
            self.failed.emit(error)
        finally:
            if project:
                project.catalog.close()


class SourceImportDialog(QDialog):
    def __init__(self, assets: AssetService, identifier: str, parent=None,
                 *, pose_id: str | None = None, keys: tuple[SourceKey, ...] | None = None) -> None:
        super().__init__(parent)
        self.assets, self.identifier = assets, identifier
        self.definition = assets.definition(identifier)
        self.keys = tuple(keys or ())
        self.pose_id = self.keys[0].pose_id if self.keys else pose_id
        self.plan: ImportPlan | None = None
        self.worker: SourceWorker | None = None
        self.changed = self.pending_close = False
        self.setObjectName("source_import_dialog")
        self.setWindowTitle("Quellen importieren · " + assets.asset(identifier).title)
        self.resize(1100, 720)
        layout = QVBoxLayout(self)
        layout.addWidget(label(
            "Geprüfte PNG-Kopien zentral speichern. Originale bleiben unverändert. "
            "Raster = Spalten × Zeilen. Automatische Vorschläge vor dem Import prüfen; "
            "keine Animationserzeugung."
        ))
        self.tabs = QTabWidget()
        page = QWidget()
        form = QVBoxLayout(page)
        self.bundles = QTreeWidget()
        self.bundles.setObjectName("source_saved_bundles")
        self.bundles.setHeaderLabels(["Gespeichertes Posenbündel", "Aktive Quellen",
                                      "Aufbewahrt", ""])
        self.bundles.setRootIsDecorated(False)
        for column, width in enumerate((235, 130, 140)):
            self.bundles.setColumnWidth(column, width)
        self.bundles.setMaximumHeight(130)
        form.addWidget(self.bundles)
        self.selection_scope = label("", "source_selection_scope")
        form.addWidget(self.selection_scope)
        controls = QHBoxLayout()
        self.choose = button("PNG-Dateien auswählen …", "source_choose", self.choose_files)
        self.remove = button("Zeile entfernen", "source_remove", self.remove_row)
        controls.addWidget(self.choose)
        controls.addWidget(self.remove)
        self.external_tool = QLineEdit()
        self.external_tool.setPlaceholderText("Externes Animationswerkzeug (optional)")
        self.external_tool.setMaxLength(128)
        self.external_tool.textChanged.connect(self.invalidate)
        controls.addWidget(self.external_tool, 1)
        form.addLayout(controls)
        self.table = QTableWidget(0, 6)
        self.table.setObjectName("source_import_files")
        self.table.setHorizontalHeaderLabels([
            "Originaldatei", "Pose", "Richtung", "Quellart", "Raster", "Frames",
        ])
        for column, width in enumerate((290, 160, 110, 160, 130, 80)):
            self.table.setColumnWidth(column, width)
        form.addWidget(self.table, 1)
        self.replace_active = QCheckBox("Bestehende aktive Zuordnungen bewusst ersetzen "
                                       "(alte Revisionen bleiben erhalten)")
        self.replace_active.setObjectName("source_replace_active")
        form.addWidget(self.replace_active)
        self.tabs.addTab(page, "Auswahl und Prüfung")
        self.deliveries = SourcesPanel(assets, identifier, self, include_import=False)
        self.deliveries.changed.connect(self.revision_changed)
        self.deliveries.import_requested.connect(self.select_scope)
        self.tabs.addTab(self.deliveries, "Lieferstand und Revisionen")
        layout.addWidget(self.tabs, 1)
        self.status = label("Noch keine Dateien ausgewählt.", "source_import_status")
        self.status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.status)
        actions = QHBoxLayout()
        self.check_button = button("Auswahl prüfen", "source_check", self.prepare)
        self.import_button = button("Geprüfte Quellen importieren", "source_import",
                                     self.import_plan)
        self.import_button.setEnabled(False)
        self.cancel_button = button("Vorgang abbrechen", "source_cancel", self.cancel_work)
        self.cancel_button.setEnabled(False)
        for widget in (self.check_button, self.import_button, self.cancel_button,
                       button("Schließen", "source_close", self.reject)):
            actions.addWidget(widget)
        layout.addLayout(actions)
        self.refresh_bundles()
        self.scope_caption()

    def scope_caption(self) -> None:
        self.selection_scope.setText(
            f"Neue Lieferung für {len(self.keys)} fest gewählte Richtung(en). "
            "Die Auswahl muss vollständig sein; andere Quellen bleiben unverändert."
            if self.keys else "Neue Auswahl: gespeicherte Bündel bleiben oben sichtbar. "
            "Einzelne Quellen und Revisionen unter Lieferstand und Revisionen bearbeiten.")

    def refresh_bundles(self) -> None:
        service = SourceImportService(self.assets)
        rows, revisions = service.matrix(self.identifier), service.revisions(self.identifier)
        poses = {p.id: p.display_name for p in self.definition.poses}
        self.bundles.clear()
        for pose_id in dict.fromkeys([*(r["key"].pose_id for r in rows),
                                     *(r.data["slot"]["pose_id"] for r in revisions)]):
            saved = [r for r in revisions if r.data["slot"]["pose_id"] == pose_id]
            if not saved:
                continue
            required = [r for r in rows if r["key"].pose_id == pose_id and r["required"]]
            count = sum(r["state"] == "imported" for r in required)
            item = QTreeWidgetItem(self.bundles, [poses.get(pose_id, "Statisch / frühere Pose"),
                f"{count}/{len(required)} geliefert", f"{len(saved)} Revisionen"])
            self.bundles.setItemWidget(item, 3, button(
                "Lieferstand öffnen", "bundle_" + str(pose_id),
                lambda checked=False, pid=pose_id: self.show_delivery(pid)))
        if not self.bundles.topLevelItemCount():
            QTreeWidgetItem(self.bundles, ["Noch keine gespeicherten Lieferbündel."])

    def show_delivery(self, pose_id) -> None:
        self.tabs.setCurrentWidget(self.deliveries)
        self.deliveries.show_pose(pose_id)

    def select_scope(self, keys) -> None:
        if self.table.rowCount() and QMessageBox.question(self, "Neue Auswahl beginnen?",
            "Die noch nicht importierte Dateiauswahl verwerfen? Gespeicherte Quellen bleiben "
            "erhalten.") != QMessageBox.StandardButton.Yes:
            return
        self.keys = tuple(keys or ())
        self.pose_id = self.keys[0].pose_id if self.keys else None
        self.table.setRowCount(0)
        self.replace_active.setChecked(False)
        self.invalidate()
        self.scope_caption()
        self.tabs.setCurrentIndex(0)
        self.choose_files()

    def invalidate(self, *args) -> None:
        self.plan = None
        self.import_button.setEnabled(False)

    def revision_changed(self) -> None:
        self.changed = True
        self.invalidate()
        self.refresh_bundles()

    def choose_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Source-PNGs / Spritesheets auswählen",
                                               "", "PNG-Bilder (*.png)")
        self.add_files([Path(p) for p in paths])

    def add_files(self, paths: list[Path]) -> None:
        if self.table.rowCount() + len(paths) > 128:
            self.status.setText("Höchstens 128 Quellen je Lieferung.")
            return
        for path in paths:
            row = self.table.rowCount()
            self.table.insertRow(row)
            item = QTableWidgetItem(path.name)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setToolTip(str(path))
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 0, item)
            pose = QComboBox()
            for value in self.definition.poses:
                if not self.keys or value.id in {k.pose_id for k in self.keys}:
                    pose.addItem(value.display_name, value.id)
            if not self.definition.poses:
                pose.addItem("Statisches Bild", None)
            if self.pose_id:
                pose.setCurrentIndex(max(0, pose.findData(self.pose_id)))
            direction = QComboBox()
            direction.addItem("Bitte wählen", "?")
            directions = tuple(dict.fromkeys((*self.definition.directions,
                *(d for p in self.definition.poses for d in p.directions or ()))))
            if self.keys:
                directions = tuple(dict.fromkeys(k.direction for k in self.keys))
            for value in directions or (None,):
                direction.addItem(value or "Ohne Richtung", value)
            match = re.search(r"(?:^|_)(NO|NW|SO|SW|N|O|S|W)(?=_|\.|$)", path.stem, re.I)
            if match and direction.findData(match[1].upper()) >= 0:
                direction.setCurrentIndex(direction.findData(match[1].upper()))
            elif not directions:
                direction.setCurrentIndex(1)
            elif not match and len(directions) == 1:
                direction.setCurrentIndex(1)
            kind = QComboBox()
            for title, value in (("Spritesheet", "spritesheet"),
                                 ("Source-Einzelbild", "single_image")):
                if not self.keys or value in {k.kind for k in self.keys}:
                    kind.addItem(title, value)
            selected = next((p for p in self.definition.poses if p.id == pose.currentData()), None)
            single = selected is None or selected.source_kind == "single_image"
            kind.setCurrentIndex(max(0, kind.findData("single_image" if single else "spritesheet")))
            single = kind.currentData() == "single_image"
            grid = QComboBox()
            grid.setEditable(True)
            grid.addItems(["Auto", "16x1", "1x16", "4x4", "4x2", "5x2", "4x3", "7x2", "1x1"])
            try:
                hint = named_grid(path.name)
            except StudioError:
                hint = None  # The worker reports conflicting names; no silent fallback.
            grid.setCurrentText("1x1" if single else f"{hint[0]}x{hint[1]}" if hint else "Auto")
            grid.setToolTip("Vorschlag aus Dateiname, sonst Auto-Prüfung der Transparenzabstände. "
                            "Spalten × Zeilen; manuell änderbar, nie nur aus dem Seitenverhältnis.")
            frames = QSpinBox()
            frames.setRange(1, 64)
            frames.setValue(1 if single else 16)
            self.grid_frames(grid.currentText(), frames)
            for column, widget in enumerate((pose, direction, kind, grid, frames), 1):
                self.table.setCellWidget(row, column, widget)
            for combo in (pose, direction, kind, grid):
                combo.currentTextChanged.connect(self.invalidate)
            kind.currentIndexChanged.connect(lambda index, g=grid, k=kind:
                g.setCurrentText("1x1" if k.currentData() == "single_image" else "Auto"))
            grid.currentTextChanged.connect(lambda text, f=frames: self.grid_frames(text, f))
            frames.valueChanged.connect(self.invalidate)
        self.invalidate()

    @staticmethod
    def grid_frames(text: str, frames: QSpinBox) -> None:
        frames.setEnabled(text.strip().casefold() != "auto")
        match = re.fullmatch(r"\s*(\d+)\s*[xX×]\s*(\d+)\s*", text)
        if match:
            frames.setValue(int(match[1]) * int(match[2]))

    def remove_row(self) -> None:
        self.table.removeRow(self.table.currentRow())
        self.invalidate()

    def specs(self) -> list[SourceSpec]:
        result = []
        for row in range(self.table.rowCount()):
            pose, direction, kind, grid, frames = [self.table.cellWidget(row, c)
                                                  for c in range(1, 6)]
            auto = grid.currentText().strip().casefold() == "auto"
            match = re.fullmatch(r"\s*(\d+)\s*[xX×]\s*(\d+)\s*", grid.currentText())
            if not match and not auto:
                raise StudioError("validation", "Raster als Spalten×Zeilen angeben, z. B. 16x1.")
            result.append(SourceSpec(
                Path(self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)),
                SourceKey(pose.currentData(), direction.currentData(), kind.currentData()),
                int(match[1]) if match else 16, int(match[2]) if match else 1,
                frames.value(), self.external_tool.text().strip(), auto_grid=auto,
            ))
        return result

    def launch(self, call) -> None:
        self.worker = SourceWorker(self.assets.project.catalog.path.parent, call, self)
        self.worker.result_ready.connect(self.receive)
        self.worker.failed.connect(self.failed)
        self.worker.progress.connect(lambda n: self.status.setText(f"{n} Quelle(n) verarbeitet …"))
        self.worker.finished.connect(self.finished_work)
        self.tabs.setEnabled(False)
        self.check_button.setEnabled(False)
        self.import_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.worker.start()

    def prepare(self) -> None:
        if self.worker:
            return
        try:
            specs = self.specs()
            revision = self.assets.asset(self.identifier).revision_no
            self.invalidate()
            self.status.setText("Quellen lesen und prüfen …")
            self.launch(lambda service, cancel, progress: service.prepare(
                self.identifier, revision, specs, required_keys=self.keys,
                cancelled=cancel, progress=progress))
        except StudioError as error:
            self.failed(error)

    def import_plan(self) -> None:
        if not self.plan or self.worker:
            return
        if QMessageBox.question(self, "Quellen zentral importieren?",
            f"{len(self.plan.sources)} geprüfte Dateien als neue Revisionen kopieren? "
            "Ziel: Studio-Projekt/.asset-studio/objects (SHA256). Originale bleiben erhalten. "
            "Es werden noch keine Grafik-/Framevarianten erzeugt.") \
                != QMessageBox.StandardButton.Yes:
            return
        plan, replace = self.plan, self.replace_active.isChecked()
        self.status.setText("Geprüfte Quellkopien importieren …")
        self.launch(lambda service, cancel, progress: service.import_plan(
            plan, replace_active=replace, cancelled=cancel, progress=progress))

    def receive(self, result) -> None:
        if isinstance(result, ImportPlan):
            for row, (spec, _) in enumerate(result.sources):
                self.table.cellWidget(row, 4).setCurrentText(f"{spec.columns}x{spec.rows}")
                self.table.cellWidget(row, 5).setValue(spec.frames)
            self.plan = result
            self.status.setText(f"{len(result.sources)} Quellen geprüft. "
                f"{len(self.definition.expected())} Zielvarianten laut Anforderungen (noch nicht "
                "erzeugt). Raster/Zuordnung prüfen, danach Import bestätigen.")
        else:
            self.changed = True
            self.plan = None
            self.table.setRowCount(0)
            self.replace_active.setChecked(False)
            self.deliveries.refresh()
            self.refresh_bundles()
            self.status.setText(f"{len(result)} neue Quellenrevisionen importiert. "
                                "Originale unverändert; keine Varianten erzeugt oder freigegeben.")
            self.tabs.setCurrentIndex(1)

    def failed(self, error) -> None:
        self.plan = None
        self.status.setText(str(error))
        if not (isinstance(error, StudioError) and error.code == "cancelled"):
            show_error(self, error if isinstance(error, StudioError) else
                       StudioError("source_import", "Quellimport fehlgeschlagen.", str(error)))

    def finished_work(self) -> None:
        worker, self.worker = self.worker, None
        worker.deleteLater()
        self.tabs.setEnabled(True)
        self.check_button.setEnabled(True)
        self.import_button.setEnabled(self.plan is not None)
        self.cancel_button.setEnabled(False)
        if self.pending_close:
            super().reject()

    def cancel_work(self) -> None:
        if self.worker:
            self.worker.cancel.set()
            self.status.setText("Abbruch angefordert …")

    def reject(self) -> None:
        if self.worker:
            self.pending_close = True
            self.cancel_work()
        else:
            super().reject()

    def closeEvent(self, event) -> None:
        if self.worker:
            event.ignore()
            self.reject()
        else:
            super().closeEvent(event)
