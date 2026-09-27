"""Background dry-run and diagnostic execution, with a visible plan/actual comparison."""

from threading import Event

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QPlainTextEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
)

from ..application.build_graphs import asset_graph, diagnostic_graph
from ..application.build_planner import BuildPlanner
from .common import button, label

NAMES = {"new": "Neu", "reused": "Wiederverwendet", "stale": "Veraltet",
         "blocked": "Blockiert", "not_required": "Nicht erforderlich", "built": "Neu gebaut",
         "failed": "Fehlgeschlagen", "cancelled": "Abgebrochen"}
PARTS = {"profile": "Masterprofil", "mask": "Maske", "maskcheck": "Maskenprüfung",
         "color": "Farben", "frames": "Frames", "geometry": "Geometrie",
         "scale": "Grafikstufe", "preview": "Vorschau", "checks": "Prüfungen",
         "package": "Paket", "static": "Einzelbild", "none": "Ohne Richtung",
         "comic_high": "Comic High", "comic_mid": "Comic Mittel", "comic_low": "Comic Low",
         "pixel_high": "Pixel Art High", "pixel_low": "Pixel Art Low"}


class PlanWorker(QThread):
    result = Signal(object)
    failed = Signal(str)
    event_received = Signal(object)

    def __init__(self, project, owner_id, diagnostic, plan=None, parent=None):
        super().__init__(parent)
        self.project, self.owner_id = project, owner_id
        self.diagnostic, self.plan = diagnostic, plan
        self.cancelled = Event()

    def run(self):
        try:
            planner = BuildPlanner(self.project)
            if self.plan is None:
                graph = diagnostic_graph() if self.diagnostic else \
                    asset_graph(self.project, self.owner_id, cancelled=self.cancelled.is_set)
                value = planner.plan(self.owner_id, graph, cancelled=self.cancelled.is_set)
            else:
                value = planner.execute(self.plan, cancelled=self.cancelled.is_set,
                                        on_event=self.event_received.emit)
            self.result.emit(value)
        except Exception as error:
            self.failed.emit(str(error))


class BuildPlanDialog(QDialog):
    def __init__(self, project, owner_id, parent=None):
        super().__init__(parent)
        self.project, self.owner_id = project, owner_id
        self.worker, self.plan = None, None
        self.setWindowTitle("Buildplan · Dry-run und Cache")
        self.resize(1050, 720)
        layout = QVBoxLayout(self)
        self.notice = label("Dry-run prüft nur lesend. Keine Asset-, Build- oder Godot-Datei "
                            "wird geschrieben. Cache-Diagnose erzeugt ausschließlich Testberichte.")
        layout.addWidget(self.notice)
        actions = QHBoxLayout()
        self.mode = QComboBox()
        self.mode.addItem("Asset: Varianten und Blocker", False)
        self.mode.addItem("Technische Cache-Diagnose", True)
        if project.catalog.get(owner_id).kind != "asset":
            self.mode.setCurrentIndex(1)
        self.mode.currentIndexChanged.connect(self._mode_changed)
        actions.addWidget(self.mode)
        self.plan_button = button("Dry-run aktualisieren", "build_dry_run", self.preview)
        self.run_button = button("Diagnoseplan ausführen", "execute_build_plan", self.execute)
        self.run_button.setEnabled(False)
        actions.addWidget(self.plan_button)
        actions.addWidget(self.run_button)
        actions.addWidget(button("Abbrechen", "cancel_build_plan", self.cancel))
        layout.addLayout(actions)
        self.summary = label("Noch kein Plan erstellt.")
        layout.addWidget(self.summary)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Schritt / Variante", "Plan", "Grund / tatsächlicher Ablauf"])
        self.tree.currentItemChanged.connect(self.show_details)
        layout.addWidget(self.tree, 2)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        layout.addWidget(self.details, 1)

    def _mode_changed(self):
        self.plan = None
        self.run_button.setEnabled(False)
        self.summary.setText("Auswahl geändert; neuen Dry-run erstellen.")

    def preview(self):
        self.plan = None
        self.start_worker(None)

    def execute(self):
        if self.plan and self.mode.currentData():
            self.start_worker(self.plan)

    def start_worker(self, plan):
        if self.worker is not None:
            return
        self.worker = PlanWorker(self.project, self.owner_id, self.mode.currentData(), plan, self)
        self.worker.result.connect(self.present)
        self.worker.failed.connect(self.details.setPlainText)
        self.worker.event_received.connect(lambda event: self.details.appendPlainText(str(event)))
        self.worker.finished.connect(self._finished)
        self.mode.setEnabled(False)
        self.plan_button.setEnabled(False)
        self.run_button.setEnabled(False)
        self.details.setPlainText("Prüfung läuft im Hintergrund …")
        self.worker.start()

    def _finished(self):
        self.worker.deleteLater()
        self.worker = None
        self.mode.setEnabled(True)
        self.plan_button.setEnabled(True)
        self.run_button.setEnabled(bool(self.plan and self.mode.currentData()))

    def present(self, value):
        self.tree.clear()
        if isinstance(value, dict):
            for item in value["actual"]:
                self.add_row([
                    self.node_label(item["node"]), NAMES.get(item["planned"], item["planned"]),
                    NAMES.get(item["actual"], item["actual"]) + " · " + item.get("reason", ""),
                ], "\n".join(f"{key}: {data}" for key, data in item.items()))
            self.summary.setText("Ausführung: " + value["status"] + " · neuer Dry-run zeigt Cache")
            self.details.setPlainText("Unveränderlicher Vergleich: " + value["run_id"])
            self.plan = None
        else:
            self.plan = value
            self.summary.setText("Varianten: " + " · ".join(
                f"{NAMES[key]}: {count}" for key, count in value.counts.items()))
            for row in value.nodes:
                detail = (f"Technischer Knoten: {row.node.key}\nPhase: {row.node.stage}\n"
                          f"Zustand: {NAMES[row.state]}\nGrund: {row.reason}\n"
                          f"Input-Fingerprint: {row.fingerprint}\n"
                          f"Build-ID: {row.build_id or 'Noch kein gültiges Ergebnis'}\n"
                          f"Ergebnisdigest: {row.result_digest or 'Noch nicht vorhanden'}")
                self.add_row([self.node_label(row.node.key), NAMES[row.state], row.reason], detail)
            self.details.setPlainText("Entwurfsplan: " + value.id +
                                      "\nNur vollständig geprüfte Ergebnisse gelten als Cache.")
        for column in (0, 1):
            self.tree.resizeColumnToContents(column)
        self.tree.setColumnWidth(0, min(470, self.tree.columnWidth(0)))

    def node_label(self, key):
        parts = dict(PARTS)
        data = self.project.catalog.get(self.owner_id).data.get("asset_definition", {})
        parts.update((p["id"], p["display_name"]) for p in data.get("poses", []))
        return " / ".join(parts.get(part, part) for part in key.split("/"))

    def add_row(self, columns, detail):
        item = QTreeWidgetItem(columns)
        item.setData(0, Qt.ItemDataRole.UserRole, detail)
        for index, value in enumerate(columns):
            item.setToolTip(index, value)
        self.tree.addTopLevelItem(item)

    def show_details(self, current, previous=None):
        if current is not None:
            self.details.setPlainText(current.data(0, Qt.ItemDataRole.UserRole))

    def cancel(self):
        if self.worker:
            self.worker.cancelled.set()
            self.details.appendPlainText("Abbruch angefordert; Prozessende wird abgewartet.")

    def reject(self):
        if self.worker:
            self.cancel()
            self.notice.setText("Bitte Abschluss abwarten, danach das Fenster schließen.")
            return
        super().reject()

    def closeEvent(self, event):
        if self.worker:
            self.cancel()
            event.ignore()
        else:
            event.accept()
