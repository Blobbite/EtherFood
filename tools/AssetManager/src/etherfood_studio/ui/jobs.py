"""Visible diagnostic jobs, raw output and explicit cancellation; no asset approval."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QPlainTextEdit, QSplitter, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout,
)

from ..application.job_service import JobService
from ..pipelines.adapters import MODES
from .common import button, label, show_error
from .process_runner import ProcessRunner

STATUS = {"running": "Läuft", "cancelling": "Wird abgebrochen", "cancelled": "Abgebrochen",
          "succeeded": "Geprüft erfolgreich", "failed": "Fehlgeschlagen",
          "interrupted": "Unterbrochen"}


class JobsDialog(QDialog):
    changed = Signal()

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Aufträge · sichere Pipeline-Diagnose")
        self.resize(950, 650)
        self.project = project
        self.owner_id = project.project().id
        self.service = JobService(project)
        self.runner = ProcessRunner(self.service, self)
        self.runner.event_received.connect(lambda *args: self.refresh())
        self.runner.finished.connect(lambda *args: self.refresh())
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(label(
            "Diagnose, keine Bilderzeugung/Freigabe. Maximal zwei Aufträge gleichzeitig. "
            "Originale bleiben geschützt; laufende Aufträge lassen sich abbrechen."))
        row = QHBoxLayout()
        self.mode = QComboBox()
        for key, title in zip(MODES, ("Erfolg", "Fehler (Exit 7)", "Ausgabe fehlt",
                                     "Langer Lauf", "Lauf mit Kindprozess")):
            self.mode.addItem(title, key)
        row.addWidget(self.mode)
        row.addWidget(button("Diagnose starten", "start_diagnostic", self.start_diagnostic))
        row.addWidget(button("FramReduce prüfen (--help)", "check_framreduce", self.start_help))
        row.addWidget(button("Abbrechen", "cancel_job", self.cancel_selected))
        row.addWidget(button("Aktualisieren", "refresh_jobs", self.refresh))
        self.layout.addLayout(row)
        splitter = QSplitter(Qt.Orientation.Vertical)
        self.list = QTreeWidget()
        self.list.setHeaderLabels(["Auftrag", "Adapter", "Status", "Begründung"])
        self.list.currentItemChanged.connect(lambda *args: self.show_details())
        splitter.addWidget(self.list)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        splitter.addWidget(self.details)
        self.layout.addWidget(splitter)
        self.refresh()

    def start_diagnostic(self):
        self.start("diagnostic", {"mode": self.mode.currentData()})

    def start_help(self):
        self.start("framreduce-help", {})

    def start(self, adapter, parameters):
        try:
            request = self.service.prepare(self.owner_id, adapter, parameters)
            self.runner.start(request)
            self.refresh(request.job_id)
        except Exception as error:
            show_error(self, error)

    def selected(self):
        item = self.list.currentItem()
        return item.data(0, Qt.ItemDataRole.UserRole) if item else None

    def refresh(self, selected=None):
        selected = selected or self.selected()
        self.list.blockSignals(True)
        self.list.clear()
        for row in self.service.store.rows():
            item = QTreeWidgetItem([row["id"][:8], row["request"]["adapter"],
                                    STATUS[row["status"]], (row["result"] or {}).get("reason", "")])
            item.setData(0, Qt.ItemDataRole.UserRole, row["id"])
            self.list.addTopLevelItem(item)
            if row["id"] == selected:
                self.list.setCurrentItem(item)
        self.list.blockSignals(False)
        self.show_details()
        self.changed.emit()

    def show_details(self):
        identifier = self.selected()
        if not identifier:
            self.details.clear()
            return
        row = self.service.store.get(identifier)
        parts = ["Auftrag: " + identifier, "Status: " + STATUS[row["status"]],
                 "Arbeitsraum: " + str(self.service.workspace(identifier)),
                 "Argumente: " + repr(row["request"]["argv"]),
                 "Werkzeug-Hashes: " + repr(row["request"]["tool_hashes"]),
                 "Ereignisse: " + repr(self.service.store.events(identifier))]
        for name in ("stdout.log", "stderr.log", "host-stderr.log"):
            path = self.service.workspace(identifier) / "logs" / name
            if path.is_file():
                with path.open("rb") as stream:
                    stream.seek(max(0, path.stat().st_size - 65536))
                    parts += [name + " (letzte 64 KiB)", stream.read().decode("utf-8", "replace")]
        self.details.setPlainText("\n\n".join(parts))

    def cancel_selected(self):
        self.runner.cancel(self.selected())
        self.refresh()
