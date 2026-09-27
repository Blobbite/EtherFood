"""Explicit source mappings and cancellable imports using an isolated DB connection."""

from pathlib import Path
import re
from threading import Event

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLineEdit, QMessageBox,
    QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from ..application.asset_service import AssetService
from ..application.project_service import ProjectService
from ..application.source_import import ImportPlan, SourceImportService, SourceSpec
from ..domain.models import StudioError
from ..domain.sources import SourceKey
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
                 *, pose_id: str | None = None) -> None:
        super().__init__(parent)
        self.assets, self.identifier = assets, identifier
        self.definition = assets.definition(identifier)
        self.pose_id = pose_id
        self.plan: ImportPlan | None = None
        self.worker: SourceWorker | None = None
        self.changed = self.pending_close = False
        self.setObjectName("source_import_dialog")
        self.setWindowTitle("Quellen importieren · " + assets.asset(identifier).title)
        self.resize(1100, 720)
        layout = QVBoxLayout(self)
        layout.addWidget(label(
            "Geprüfte PNG-Kopien zentral speichern. Originale bleiben unverändert. "
            "Raster = Spalten × Zeilen, immer ausdrücklich auswählen; keine Animationserzeugung."
        ))
        self.tabs = QTabWidget()
        page = QWidget()
        form = QVBoxLayout(page)
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

    def invalidate(self, *args) -> None:
        self.plan = None
        self.import_button.setEnabled(False)

    def revision_changed(self) -> None:
        self.changed = True
        self.invalidate()

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
                pose.addItem(value.display_name, value.id)
            if not self.definition.poses:
                pose.addItem("Statisches Bild", None)
            if self.pose_id:
                pose.setCurrentIndex(max(0, pose.findData(self.pose_id)))
            direction = QComboBox()
            direction.addItem("Bitte wählen", "?")
            directions = tuple(dict.fromkeys((*self.definition.directions,
                *(d for p in self.definition.poses for d in p.directions or ()))))
            for value in directions or (None,):
                direction.addItem(value or "Ohne Richtung", value)
            match = re.search(r"(?:^|_)(NO|NW|SO|SW|N|O|S|W)(?=_|\.|$)", path.stem, re.I)
            if match and direction.findData(match[1].upper()) >= 0:
                direction.setCurrentIndex(direction.findData(match[1].upper()))
            elif not directions:
                direction.setCurrentIndex(1)
            kind = QComboBox()
            kind.addItem("Spritesheet", "spritesheet")
            kind.addItem("Source-Einzelbild", "single_image")
            selected = next((p for p in self.definition.poses if p.id == pose.currentData()), None)
            single = selected is None or selected.source_kind == "single_image"
            kind.setCurrentIndex(int(single))
            grid = QComboBox()
            grid.setEditable(True)
            grid.addItems(["16x1", "1x16", "4x4", "4x2", "5x2", "4x3", "7x2", "1x1"])
            grid.setCurrentText("1x1" if single else "16x1")
            grid.setToolTip("Spalten × Zeilen; keine Ableitung aus den Bildproportionen.")
            frames = QSpinBox()
            frames.setRange(1, 64)
            frames.setValue(1 if single else 16)
            for column, widget in enumerate((pose, direction, kind, grid, frames), 1):
                self.table.setCellWidget(row, column, widget)
            for combo in (pose, direction, kind, grid):
                combo.currentTextChanged.connect(self.invalidate)
            kind.currentIndexChanged.connect(lambda index, g=grid:
                                             g.setCurrentText("1x1" if index else "16x1"))
            grid.currentTextChanged.connect(lambda text, f=frames: self.grid_frames(text, f))
            frames.valueChanged.connect(self.invalidate)
        self.invalidate()

    @staticmethod
    def grid_frames(text: str, frames: QSpinBox) -> None:
        match = re.fullmatch(r"\s*(\d+)\s*[x×]\s*(\d+)\s*", text)
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
            match = re.fullmatch(r"\s*(\d+)\s*[x×]\s*(\d+)\s*", grid.currentText())
            if not match:
                raise StudioError("validation", "Raster als Spalten×Zeilen angeben, z. B. 16x1.")
            result.append(SourceSpec(
                Path(self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)),
                SourceKey(pose.currentData(), direction.currentData(), kind.currentData()),
                int(match[1]), int(match[2]), frames.value(), self.external_tool.text().strip(),
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
                self.identifier, revision, specs, cancelled=cancel, progress=progress))
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
            self.plan = result
            self.status.setText(f"{len(result.sources)} Quellen geprüft. "
                f"{len(self.definition.expected())} Zielvarianten laut Anforderungen (noch nicht "
                "erzeugt). Raster/Zuordnung prüfen, danach Import bestätigen.")
        else:
            self.changed = True
            self.plan = None
            self.deliveries.refresh()
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
