"""Explicit background scan and review; all catalog writes stay on the GUI thread."""

from collections import Counter
import hashlib
import json
from pathlib import Path
from threading import Event
from typing import Callable

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QHBoxLayout, QLineEdit, QMessageBox, QPlainTextEdit,
    QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from ..application.asset_service import AssetService
from ..application.inventory_scan import ScanResult, scan_inventory
from ..application.inventory_service import InventoryService, PreparedInventory, prepare_adoption
from ..domain.models import StudioError
from ..storage.inventory_files import ScanLimits, inside_reference, read_bytes
from .common import button, label, show_error

STATES = {"proposal": "Vorschlag", "duplicate": "Doppelte Variante – eine wählen",
          "needs_review": "Manuell klären", "not_required": "Nicht erforderlich",
          "missing": "Fehlt", "found": "Gefunden, nicht abgenommen", "conflict": "Konflikt"}


class InventoryWorker(QThread):
    result_ready = Signal(object)
    failed = Signal(object)
    progress = Signal(int)

    def __init__(self, call: Callable, cancel: Event, parent=None) -> None:
        super().__init__(parent)
        self.call, self.cancel = call, cancel

    def run(self) -> None:
        try:
            self.result_ready.emit(self.call())
        except Exception as error:
            self.failed.emit(error)


class InventoryDialog(QDialog):
    def __init__(self, assets: AssetService, identifier: str, parent=None) -> None:
        super().__init__(parent)
        self.assets, self.identifier = assets, identifier
        self.definition = assets.definition(identifier)
        self.revision = assets.asset(identifier).revision_no
        config = assets.project.config
        self.limits = ScanLimits(max_bytes=config.max_file_bytes, max_pixels=config.max_pixels)
        self.scan: ScanResult | None = None
        self.worker: InventoryWorker | None = None
        self.cancel = Event()
        self.pending_close = False
        self.changed = False
        self.setObjectName("inventory_review")
        self.setWindowTitle("Bestand lesend erfassen · " + assets.asset(identifier).title)
        self.resize(1120, 760)
        layout = QVBoxLayout(self)
        layout.addWidget(label(
            "Nur Vorschläge und externe Verweise: keine Kopie, Umbenennung, Verarbeitung oder "
            "Freigabe. Einzelne Dateien bewusst ankreuzen; Herkunft bleibt zunächst unbekannt."
        ))
        root_row = QHBoxLayout()
        self.root = QLineEdit()
        self.root.setObjectName("inventory_root")
        self.root.setPlaceholderText("Bestandsordner für dieses Asset wählen (z. B. spritesheets)")
        root_row.addWidget(self.root, 1)
        self.choose_button = button("Ordner …", "inventory_choose", self.choose_root)
        self.scan_button = button("Lesend erfassen", "inventory_scan", self.start_scan)
        root_row.addWidget(self.choose_button)
        root_row.addWidget(self.scan_button)
        layout.addLayout(root_row)
        self.status = label("Noch kein Scan gestartet.", "inventory_status")
        layout.addWidget(self.status)
        self.tabs = QTabWidget()
        self.table = QTableWidget(0, 8)
        self.table.setObjectName("inventory_candidates")
        self.table.setHorizontalHeaderLabels([
            "Wahl", "Befund", "Relativer Quellpfad", "Pose", "Richtung", "Grafik",
            "Frames", "Herkunft",
        ])
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 390)
        self.table.itemSelectionChanged.connect(self.details)
        self.tabs.addTab(self.table, "Vorschläge")
        self.matrix = QPlainTextEdit()
        self.matrix.setReadOnly(True)
        self.tabs.addTab(self.matrix, "Erwartete Varianten")
        reports_page = QWidget()
        report_layout = QVBoxLayout(reports_page)
        self.reports = QPlainTextEdit()
        self.reports.setReadOnly(True)
        report_layout.addWidget(self.reports, 1)
        links = QHBoxLayout()
        self.pages = QComboBox()
        self.pages.setObjectName("inventory_comparisons")
        links.addWidget(self.pages, 1)
        links.addWidget(button("Verweis lesend öffnen", "inventory_read_page", self.read_page))
        report_layout.addLayout(links)
        self.tabs.addTab(reports_page, "Probleme / Fremdberichte / Vergleiche")
        layout.addWidget(self.tabs, 1)
        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMaximumHeight(120)
        layout.addWidget(self.detail)
        provenance_row = QHBoxLayout()
        provenance_row.addWidget(label("Herkunft für die Auswahl:"))
        self.provenance = QComboBox()
        self.provenance.addItem("Unbekannt (keine Vermutung)", "unknown")
        self.provenance.addItem("Eigenständiges Original (eigene Angabe)", "original")
        self.provenance.addItem("Ableitung (eigene Angabe + Quellhash)", "derived")
        provenance_row.addWidget(self.provenance)
        self.source_hash = QLineEdit()
        self.source_hash.setPlaceholderText("Nur Ableitung: SHA256 der Quelle")
        provenance_row.addWidget(self.source_hash)
        layout.addLayout(provenance_row)
        actions = QHBoxLayout()
        self.adopt_button = button("Auswahl als Verweise übernehmen", "inventory_adopt",
                                   self.prepare)
        self.adopt_button.setEnabled(False)
        actions.addWidget(self.adopt_button)
        actions.addWidget(button("Vorgang abbrechen", "inventory_cancel",
                                 lambda: self.cancel.set()))
        actions.addWidget(button("Schließen", "inventory_close", self.reject))
        layout.addLayout(actions)

    def choose_root(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Nur lesend: Bestandswurzel auswählen")
        if path:
            self.root.setText(path)

    def launch(self, call: Callable) -> None:
        self.cancel = Event()
        self.worker = InventoryWorker(call, self.cancel, self)
        self.worker.result_ready.connect(self.receive)
        self.worker.failed.connect(self.failed)
        self.worker.progress.connect(
            lambda n: self.status.setText(f"{n} Einträge lesend geprüft …"))
        self.worker.finished.connect(self.finished_work)
        for widget in (self.root, self.choose_button, self.scan_button, self.adopt_button,
                       self.table, self.provenance, self.source_hash):
            widget.setEnabled(False)
        self.worker.start()

    def start_scan(self) -> None:
        if self.worker or not self.root.text().strip():
            return
        root = Path(self.root.text().strip())
        self.scan = None
        self.table.setRowCount(0)
        self.matrix.clear()
        self.reports.clear()
        self.pages.clear()
        self.status.setText("Lesende Bestandserfassung läuft …")
        self.launch(lambda: scan_inventory(root, self.definition, limits=self.limits,
                    cancel=self.cancel, progress=self.worker.progress.emit))

    def receive(self, result) -> None:
        if self.cancel.is_set():
            self.status.setText("Abgebrochen; nichts übernommen.")
            return
        if isinstance(result, ScanResult):
            self.scan = result
            self.fill()
        elif isinstance(result, PreparedInventory):
            try:
                summary = InventoryService(self.assets).adopt(
                    self.identifier, self.revision, result, cancel=self.cancel,
                )
                self.changed = self.changed or summary["adopted"] > 0
                self.revision = self.assets.asset(self.identifier).revision_no
                self.status.setText(
                    f"Übernommen: {summary['adopted']} · Schon vorhanden: "
                    f"{summary['already_present']} · Nicht gewählt: {summary['not_selected']} · "
                    "Originale unverändert. Keine Freigabe. Bericht unter Dokumente."
                )
            except (StudioError, OSError) as error:
                self.failed(error)

    def finished_work(self) -> None:
        worker, self.worker = self.worker, None
        worker.deleteLater()
        for widget in (self.root, self.choose_button, self.scan_button, self.table,
                       self.provenance, self.source_hash):
            widget.setEnabled(True)
        self.adopt_button.setEnabled(self.scan is not None)
        if self.pending_close:
            super().reject()

    def failed(self, error: Exception) -> None:
        self.status.setText(str(error))
        if not (isinstance(error, StudioError) and error.code == "cancelled"):
            show_error(self, error if isinstance(error, StudioError) else
                       StudioError("inventory", "Bestandserfassung fehlgeschlagen.", str(error)))

    def fill(self) -> None:
        scan = self.scan
        poses = {p.id: p.display_name for p in self.definition.poses}
        self.table.setRowCount(len(scan.candidates))
        for row, candidate in enumerate(scan.candidates):
            key = candidate.variant
            values = ["", STATES[candidate.state], candidate.path,
                      poses.get(key.pose_id, "—") if key else "?",
                      key.direction or "—" if key else "?", key.graphics if key else "?",
                      str(key.frames) if key and key.frames else "—", "Unbekannt"]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                if col == 0 and candidate.state in {"proposal", "duplicate"}:
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(Qt.CheckState.Unchecked)
                self.table.setItem(row, col, item)
        matrix = scan.matrix()
        counts = Counter(matrix.values())
        self.status.setText(
            f"{len(scan.candidates)} PNGs · {counts['found']} gefundene Varianten · "
            f"{counts['missing']} fehlen · {counts['conflict']} Konflikte · "
            f"{len(scan.problems)} Dateiprobleme · {scan.skipped} Dateien/Ordner ausgelassen."
        )
        self.matrix.setPlainText("\n".join(
            f"{STATES[state]} | {poses.get(key.pose_id, 'statisch')} | {key.direction or '—'} | "
            f"{key.graphics} | Frames: {key.frames or '—'}" for key, state in matrix.items()
        ))
        self.reports.setPlainText(json.dumps({"Dateiprobleme": scan.problems,
            "Historische Fremdberichte (keine Freigabe)": scan.reports,
            "Lesende Vergleichsverweise": scan.pages}, ensure_ascii=False, indent=2))
        for page in scan.pages:
            self.pages.addItem(page["path"], page)

    def details(self) -> None:
        row = self.table.currentRow()
        if self.scan and 0 <= row < len(self.scan.candidates):
            c = self.scan.candidates[row]
            self.detail.setPlainText(f"{c.path}\nSHA256: {c.sha256}\n"
                                     f"Bild: {c.width} × {c.height} · Raster: {c.grid}\n" +
                                     "\n".join(c.notes))

    def prepare(self) -> None:
        if not self.scan or self.worker:
            return
        selected = [c.path for row, c in enumerate(self.scan.candidates)
                    if self.table.item(row, 0).checkState() == Qt.CheckState.Checked]
        if not selected:
            self.status.setText("Zuerst einzelne Vorschläge ankreuzen.")
            return
        answer = QMessageBox.question(self, "Katalogverweise übernehmen?",
            f"{len(selected)} ausgewählte Dateien nur referenzieren? "
            "Es werden keine Quellen kopiert und keine Freigaben erteilt.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        provenance = {"kind": self.provenance.currentData()}
        if provenance["kind"] == "derived":
            provenance["source_sha256"] = self.source_hash.text().strip()
        self.status.setText("Auswahl vor Übernahme erneut prüfen …")
        self.launch(lambda: prepare_adoption(self.scan, selected, provenance=provenance,
                                             limits=self.limits, cancel=self.cancel))

    def read_page(self) -> None:
        page = self.pages.currentData()
        if not self.scan or not page:
            return
        try:
            path = inside_reference(self.scan.root, self.scan.root, page["path"])
            raw = read_bytes(path, self.limits.max_report_bytes, Event())
            if hashlib.sha256(raw).hexdigest() != page["sha256"]:
                raise StudioError("conflict", "Vergleichsseite geändert; erneut erfassen.")
            dialog = QDialog(self)
            dialog.setWindowTitle("Lesender HTML-Quelltext · " + page["path"])
            dialog.resize(850, 600)
            layout = QVBoxLayout(dialog)
            layout.addWidget(label(
                "Sichere Textansicht; keine Skripte oder Bildressourcen geladen."))
            view = QPlainTextEdit()
            view.setReadOnly(True)
            view.setPlainText(raw.decode("utf-8", errors="replace"))
            layout.addWidget(view)
            layout.addWidget(button("Schließen", "comparison_close", dialog.accept))
            dialog.exec()
            dialog.deleteLater()
        except (StudioError, OSError) as error:
            self.failed(error)

    def reject(self) -> None:
        if self.worker:
            self.pending_close = True
            self.cancel.set()
            self.status.setText("Abbruch angefordert; warte auf laufenden Lesevorgang …")
            return
        super().reject()

    def closeEvent(self, event) -> None:
        if self.worker:
            event.ignore()
            self.reject()
        else:
            super().closeEvent(event)
