"""One asset identity, real source/build status and separate later Godot approval."""

from PySide6.QtCore import QThread, Signal, QUrl, Qt
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QMessageBox, QPlainTextEdit, QTabWidget, QVBoxLayout, QWidget,
)

from ..application.asset_service import AssetService
from ..application.document_service import DocumentService
from ..application.pipeline_results import PipelineResults
from ..application.status_service import STATE_NAMES, STEP_NAMES, StatusService, status_reason
from ..domain.assets import default_definition
from ..domain.models import StudioError
from .asset_settings import AssetDefinitionEditor, import_pose_sources
from ..application.profile_service import ProfileService
from .common import button, label, show_error
from .documents.editor import DocumentEditor
from .notes import NotesPanel
from .inventory import InventoryDialog
from .sources import SourcesPanel
from .tasks.kanban import KanbanPanel


class AssetResultStatusWorker(QThread):
    result = Signal(object)

    def __init__(self, project, identifier, parent=None):
        super().__init__(parent)
        self.project, self.identifier = project, identifier

    def run(self):
        try:
            result = PipelineResults(self.project).latest(self.identifier)
        except Exception as error:
            result = {"state": "invalid", "reason": str(error), "artifacts": []}
        self.result.emit(result)


class AssetWorkspace(QDialog):
    def __init__(self, assets: AssetService, identifier: str, parent=None) -> None:
        super().__init__(parent)
        self.assets, self.identifier = assets, identifier
        self.record = assets.asset(identifier)
        self.changed = False
        self.status_worker, self.pending_close = None, False
        self.setObjectName("asset_workspace")
        self.setWindowTitle("Asset-Menü · " + self.record.title)
        self.resize(1320, 920)
        layout = QVBoxLayout(self)
        layout.addWidget(label(f"{self.record.title} · ID: {identifier}\n"
                               "Dieselbe Karte wie im Projektbaum; keine zweite Asset-Kopie."))
        self.workflow = QPlainTextEdit()
        self.workflow.setObjectName("asset_workflow_steps")
        self.workflow.setReadOnly(True)
        self.workflow.setMaximumHeight(150)
        layout.addWidget(self.workflow)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("asset_workspace_tabs")
        self.overview = QPlainTextEdit()
        self.overview.setReadOnly(True)
        self.tabs.addTab(self.overview, "Übersicht")
        self.sources_page = QWidget()
        self.sources_layout = QVBoxLayout(self.sources_page)
        self.inventory_button = button("Vorhandenen Bestand lesend erfassen …",
                                        "workspace_inventory", self.open_inventory)
        self.sources_layout.addWidget(self.inventory_button)
        self.sources = None
        self.sources_notice = label("Zuerst unter Posen die Anforderungen speichern.")
        self.sources_layout.addWidget(self.sources_notice)
        self.tabs.addTab(self.sources_page, "Quellen / Revisionen")
        poses_page = QWidget()
        poses_layout = QVBoxLayout(poses_page)
        existing = self.record.data.get("asset_definition")
        self.editor = AssetDefinitionEditor(
            assets.parse_definition(existing) if existing else default_definition(),
            self, profiles=ProfileService(assets.project).profiles(),
        )
        self.editor.source_requested.connect(self.import_pose)
        self.definition_baseline = self.editor.value().to_data()
        poses_layout.addWidget(self.editor, 1)
        poses_layout.addWidget(button("Anforderungen speichern", "workspace_save_requirements",
                                      self.save_requirements))
        self.tabs.addTab(poses_page, "Posen")
        results_page = QWidget()
        result_layout = QVBoxLayout(results_page)
        result_layout.addWidget(label("Varianten bleiben Ableitungen dieses Assets. "
            "Raster, Frameauswahl, Timing, Profil, Anker, Crop und logische Größe werden "
            "mit den geprüften PNG-Ergebnissen gespeichert. Eine technische Erzeugung "
            "ist noch keine Sichtabnahme oder Godot-Freigabe."))
        self.result_status = label("Ergebnisstatus noch nicht aktuell geprüft.",
                                   "asset_result_status")
        result_layout.addWidget(self.result_status)
        self.result_check = button("Ergebnisstatus prüfen (ohne Build)",
                                    "asset_result_check", self.check_results)
        result_layout.addWidget(self.result_check)
        self.result_list = QPlainTextEdit()
        self.result_list.setReadOnly(True)
        self.result_list.setObjectName("asset_pipeline_results")
        result_layout.addWidget(self.result_list, 1)
        self.tabs.addTab(results_page, "Varianten")
        self.references = None
        self.references_page = QWidget()
        self.references_layout = QVBoxLayout(self.references_page)
        self.tabs.addTab(self.references_page, "Referenzen / Masken")
        self.tabs.currentChanged.connect(self.open_references)
        for title in ("Prüfungen",):
            page = QWidget()
            index = self.tabs.addTab(page, title)
            self.tabs.setTabEnabled(index, False)
            self.tabs.setTabToolTip(index, "Folgepaket: noch nicht implementiert. "
                                    "Import ist keine Erzeugung, Prüfung oder Freigabe.")
        self.documents = DocumentEditor()
        self.documents.bind(DocumentService(assets.project))
        self.documents.show_card(identifier)
        self.documents.saved.connect(self.did_change)
        self.documentation = QTabWidget()
        self.documentation.setObjectName("asset_documentation_tabs")
        self.documentation.addTab(self.documents, "Dokumente && Anhänge")
        self.notes = NotesPanel(self.documents.confirm_discard, stacked=True)
        self.notes.bind(assets.project)
        self.notes.set_scope(identifier)
        self.notes.findChild(QWidget, "notes_project").hide()
        self.notes.owner_button.hide()
        self.notes.changed.connect(self.did_change)
        self.documentation.addTab(self.notes, "Notizen")
        self.tasks = KanbanPanel(owner_id=identifier, compact=True)
        self.tasks.bind(assets.project)
        self.tasks.changed.connect(self.did_change)
        self.documentation.addTab(self.tasks, "Aufgaben && Issues")
        self.tabs.addTab(self.documentation, "Dokumentation")
        layout.addWidget(self.tabs, 1)
        actions = QHBoxLayout()
        actions.addWidget(button("Quellen / Lieferstand ansehen", "workspace_sources",
                                 lambda: self.tabs.setCurrentWidget(self.sources_page)))
        for title, name in (("Godot-Test (später)", "workspace_godot"),):
            action = button(title, name, lambda: None)
            action.setEnabled(False)
            action.setToolTip("Der zugehörige Ausführungsdienst ist noch nicht implementiert.")
            actions.addWidget(action)
        actions.addWidget(button("Schließen", "workspace_close", self.reject))
        layout.addLayout(actions)
        save = QAction(self)
        save.setShortcut(QKeySequence.StandardKey.Save)
        save.triggered.connect(self.save_current_tab)
        self.addAction(save)
        self.refresh()

    def save_current_tab(self) -> None:
        if self.tabs.currentWidget() is self.documentation:
            if self.documentation.currentWidget() is self.documents:
                self.documents.save()
            elif self.documentation.currentWidget() is self.notes:
                self.notes.save()
        elif self.tabs.currentIndex() == 2:
            self.save_requirements()

    def check_results(self):
        if self.status_worker:
            return
        self.result_status.setText("Ergebnisse und aktuelle Anforderungen werden geprüft …")
        self.result_check.setEnabled(False)
        self.status_worker = AssetResultStatusWorker(self.assets.project, self.identifier, self)
        self.status_worker.result.connect(self.present_result_status)
        self.status_worker.finished.connect(self.result_check_finished)
        self.status_worker.start()

    def present_result_status(self, result):
        names = {"ready": "Aktuell und geprüft", "stale": "Veraltet",
                 "not_started": "Kein vollständiger Bildlauf", "invalid": "Ungültig"}
        text = (names[result["state"]] + " · " + result["reason"] +
                f"\n{len(result['artifacts'])} Bildableitungen; keine persönliche Freigabe.")
        self.result_status.setText(text)
        detail = "\n".join(
            f"{item['usage']} · {item['port']} · {item['state']}\n{item['file_path']}"
            for item in result["artifacts"]
        )
        self.result_list.setPlainText(detail)

    def result_check_finished(self):
        self.status_worker.deleteLater()
        self.status_worker = None
        self.result_check.setEnabled(True)
        if self.pending_close:
            self.pending_close = False
            self.reject()

    def refresh(self) -> None:
        self.record = self.assets.asset(self.identifier)
        self.editor.update_profiles(ProfileService(self.assets.project).profiles())
        if not self.status_worker:
            self.result_status.setText("Ergebnisstatus noch nicht aktuell geprüft. "
                                       "Prüfung startet keinen Build.")
        self.tasks.refresh()
        self.inventory_button.setEnabled(bool(self.record.data.get("asset_definition")))
        statuses = StatusService(self.assets.project).status(self.identifier)
        self.workflow.setPlainText("Nächster Schritt / echte Voraussetzungen\n" + "\n".join(
            f"{STEP_NAMES[row.id]}: {STATE_NAMES[row.state]} · {status_reason(row)}"
            for row in statuses.values()
        ))
        self.overview.setPlainText(
            self.assets.project.usage_description(self.identifier)
            + "\n\nQuelle importiert ≠ Varianten erzeugt ≠ geprüft ≠ freigegeben.\n"
            "Verarbeitung und Animationen werden unter Skripte & Pipelines zusammengestellt. "
            "Quellen und Posen können hier jederzeit ergänzt werden."
        )
        if self.record.data.get("asset_definition"):
            if self.sources is None:
                self.sources = SourcesPanel(self.assets, self.identifier, self)
                self.sources.changed.connect(self.did_change)
                self.sources_layout.addWidget(self.sources)
            else:
                self.sources.refresh()
            self.editor.set_source_counts(self.sources.service.matrix(self.identifier))
            self.sources_notice.hide()
            definition = self.assets.definition(self.identifier)
            self.overview.appendPlainText(
                "\nAusgabevarianten und Ordner sind in den zugewiesenen Abläufen definiert. "
                "Prüfung und Freigabe befinden sich unter Skripte & Pipelines."
            )

    def open_inventory(self) -> None:
        try:
            dialog = InventoryDialog(self.assets, self.identifier, self)
            dialog.exec()
            if dialog.changed:
                self.did_change()
            dialog.deleteLater()
        except StudioError as error:
            show_error(self, error)

    def did_change(self) -> None:
        self.changed = True
        self.refresh()

    def save_requirements(self) -> bool:
        try:
            self.record = self.assets.configure(self.identifier, self.editor.value().to_data(),
                                                 self.record.revision_no)
            self.definition_baseline = self.editor.value().to_data()
            self.did_change()
            return True
        except StudioError as error:
            show_error(self, error)
            return False

    def import_pose(self, pose_id: str) -> None:
        try:
            self.record, changed = import_pose_sources(
                self, self.assets, self.record, self.editor.value(), pose_id,
            )
            if changed:
                self.did_change()
        except StudioError as error:
            show_error(self, error)

    def reject(self) -> None:
        if self.references:
            if self.references.worker:
                if not self.pending_close:
                    self.pending_close = True
                    self.references.worker.finished.connect(self.reject)
                return
            self.pending_close = False
            if not self.references.confirm_close():
                return
            self.changed |= self.references.changed
        if self.status_worker:
            self.pending_close = True
            self.result_status.setText("Ergebnisprüfung läuft; Fenster schließt anschließend.")
            return
        try:
            dirty = self.editor.value().to_data() != self.definition_baseline
        except StudioError:
            dirty = True
        if dirty:
            answer = QMessageBox.question(self, "Anforderungen noch nicht gespeichert",
                "Anforderungen vor dem Schließen speichern?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
            if answer == QMessageBox.StandardButton.Cancel:
                return
            if answer == QMessageBox.StandardButton.Save and not self.save_requirements():
                return
        if self.documents.confirm_discard() and self.notes.confirm_discard():
            super().reject()

    def closeEvent(self, event) -> None:
        event.ignore()
        self.reject()

    def open_references(self, index):
        if self.tabs.widget(index) == self.references_page and self.references is None:
            from .reference_materials import ReferenceMaterialsDialog

            self.references = ReferenceMaterialsDialog(
                self.assets.project, self.identifier, self.references_page, embedded=True
            )
            self.references.setWindowFlags(Qt.Widget)
            self.references_layout.addWidget(self.references)
