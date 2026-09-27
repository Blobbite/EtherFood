"""One asset identity, real source status and clearly unavailable later pipeline tabs."""

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QMessageBox, QPlainTextEdit, QTabWidget, QVBoxLayout, QWidget,
)

from ..application.asset_service import AssetService
from ..application.document_service import DocumentService
from ..application.status_service import STATE_NAMES, STEP_NAMES, StatusService, status_reason
from ..domain.assets import AssetDefinition, default_definition
from ..domain.models import StudioError
from .asset_settings import AssetDefinitionEditor, import_pose_sources
from .common import button, label, show_error
from .documents.editor import DocumentEditor
from .inventory import InventoryDialog
from .sources import SourcesPanel
from .tasks.panel import TasksPanel


class AssetWorkspace(QDialog):
    def __init__(self, assets: AssetService, identifier: str, parent=None) -> None:
        super().__init__(parent)
        self.assets, self.identifier = assets, identifier
        self.record = assets.asset(identifier)
        self.changed = False
        self.setObjectName("asset_workspace")
        self.setWindowTitle("Asset-Menü · " + self.record.title)
        self.resize(1180, 840)
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
            AssetDefinition.from_data(existing) if existing else default_definition(),
            self, source_actions=True,
        )
        self.editor.source_requested.connect(self.import_pose)
        poses_layout.addWidget(self.editor, 1)
        poses_layout.addWidget(button("Anforderungen speichern", "workspace_save_requirements",
                                      self.save_requirements))
        self.tabs.addTab(poses_page, "Posen")
        for title in ("Farben/Masken", "Varianten", "Prüfungen"):
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
        self.documentation.addTab(self.documents, "Notizen && Anhänge")
        self.tasks = TasksPanel(owner_id=identifier)
        self.tasks.bind(assets.project)
        self.tasks.changed.connect(self.did_change)
        self.documentation.addTab(self.tasks, "Aufgaben && Issues")
        self.tabs.addTab(self.documentation, "Dokumentation")
        layout.addWidget(self.tabs, 1)
        actions = QHBoxLayout()
        actions.addWidget(button("Quellen / Lieferstand ansehen", "workspace_sources",
                                 lambda: self.tabs.setCurrentWidget(self.sources_page)))
        for title, name in (("Varianten erzeugen (später)", "workspace_build"),
                            ("Godot-Test (später)", "workspace_godot")):
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
        elif self.tabs.currentIndex() == 2:
            self.save_requirements()

    def refresh(self) -> None:
        self.record = self.assets.asset(self.identifier)
        self.tasks.refresh()
        self.inventory_button.setEnabled(bool(self.record.data.get("asset_definition")))
        statuses = StatusService(self.assets.project).status(self.identifier)
        self.workflow.setPlainText("Nächster Schritt / echte Voraussetzungen\n" + "\n".join(
            f"{STEP_NAMES[row.id]}: {STATE_NAMES[row.state]} · {status_reason(row)}"
            for row in statuses.values()
        ))
        self.overview.setPlainText(self.assets.project.usage_description(self.identifier)
            + "\n\nQuelle importiert ≠ Varianten erzeugt ≠ geprüft ≠ freigegeben.\n"
            "Animationen werden im externen Werkzeug erstellt. "
            "Quellen und Posen können hier jederzeit ergänzt werden.")
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
            self.overview.appendPlainText(f"\n{len(definition.expected())} geplante Varianten; "
                                           "noch keine Erzeugung verfügbar.")

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
        try:
            dirty = self.editor.value().to_data() != self.record.data.get("asset_definition")
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
        if self.documents.confirm_discard():
            super().reject()

    def closeEvent(self, event) -> None:
        event.ignore()
        self.reject()
