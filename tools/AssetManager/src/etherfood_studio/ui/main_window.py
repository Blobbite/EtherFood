"""Usable local dashboard: project navigation, canvas, notes and tasks."""

from pathlib import Path
import sqlite3
import sys
from typing import Callable

from PySide6.QtCore import QSettings, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QHBoxLayout, QInputDialog, QMainWindow,
    QMessageBox, QPlainTextEdit, QScrollArea, QSizePolicy, QSpinBox, QSplitter, QTabWidget,
    QToolBar, QTreeWidgetItem, QTreeWidgetItemIterator, QVBoxLayout, QWidget,
)

from ..application.commands import Command, Commands
from ..application.asset_service import AssetService
from ..application.document_service import DocumentService
from ..application.project_service import ProjectService
from ..application.status_service import STATE_NAMES, STEP_NAMES, StatusService, status_reason
from ..application.tree_service import TreeService
from ..domain.models import StudioError
from ..domain.relations import CARD_KINDS
from ..domain.notes import is_note
from .canvas.view import Canvas
from .canvas.actions import CanvasActions
from .asset_wizard import AssetWizard
from .asset_workspace import AssetWorkspace
from .common import button, label, show_error
from .documents.editor import DocumentEditor
from .project_dialog import ProjectDialog
from .navigation import Navigation
from .presentation import KIND_NAMES, kind_icon, record_icon
from .project_tree import EDGE_ROLE, ProjectTree
from .notes import NotesPanel
from .tasks.panel import TasksPanel
from .tasks.kanban import KanbanPanel
from .jobs import JobsDialog
from .build_plan import BuildPlanDialog
from .appearance import AppearanceDialog, BUTTON_STYLES, appearance
from .action_icons import action_icon
from .theme import color


class MainWindow(QMainWindow):
    def __init__(self, settings: QSettings | None = None) -> None:
        super().__init__()
        self.setObjectName("asset_studio_window")
        self.setWindowTitle("EtherFood · Asset Studio")
        self.resize(1440, 900)
        self.setMinimumSize(1050, 640)
        self.settings = settings or QSettings("EtherFood", "AssetStudio")
        appearance().configure(self.settings)
        self.project: ProjectService | None = None
        self.commands: Commands | None = None
        self.selected_id: str | None = None
        self.selected_content_id: str | None = None
        self._refreshing = False
        self.job_dialog = None
        self.build_dialog = None
        self._close_after_jobs = False
        self._build_ui()
        appearance().changed.connect(self.apply_appearance)
        self.apply_appearance()
        self.navigation = Navigation(self)
        geometry = self.settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        self._recent_menu()

    def _build_ui(self) -> None:
        toolbar = QToolBar("Projekt")
        toolbar.setObjectName("project_toolbar")
        toolbar.setMovable(False)
        toolbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.project_toolbar = toolbar
        self._action(toolbar, "Neues Projekt", self.new_dialog, "Ctrl+N", "new_project")
        self._action(toolbar, "Öffnen …", self.open_dialog, "Ctrl+O", "open_project")
        self.recent_menu = self.menuBar().addMenu("Zuletzt verwendet")
        self._action(toolbar, "Demo anlegen", self.demo_dialog, "", "create_demo")
        toolbar.addSeparator()
        self.undo_action = self._action(toolbar, "Rückgängig", lambda: self.undo(False),
                                        "Ctrl+Z", "undo")
        self.redo_action = self._action(toolbar, "Wiederholen", lambda: self.undo(True),
                                        "Ctrl+Shift+Z", "redo")
        self._action(toolbar, "Aufträge …", self.show_jobs, "", "show_jobs")
        self._action(toolbar, "Buildplan …", self.show_build_plan, "", "show_build_plan")
        for text in ("Bildpipeline (später)", "Godot bereitstellen (später)"):
            action = toolbar.addAction(text)
            action.setObjectName("image_pipeline" if text.startswith("Bild") else "godot_export")
            action.setEnabled(False)
            action.setToolTip("Produktive Bildverarbeitung/Godot folgen in späteren Issues.")
        center = QWidget()
        outer = QVBoxLayout(center)
        tools_row = QHBoxLayout()
        tools_row.addWidget(toolbar, 1)
        self.settings_button = button("Einstellungen", "appearance_settings_button",
                                      self.show_appearance_settings)
        tools_row.addWidget(self.settings_button)
        outer.addLayout(tools_row)
        self.breadcrumb = label(
            "Projekt öffnen oder ein neues Projekt in einem leeren Ordner anlegen.", "breadcrumb",
        )
        outer.addWidget(self.breadcrumb)
        self.root_notice = label(
            "Lokale Verwaltung · Keine produktive Asset-Freigabe", "root_status",
        )
        outer.addWidget(self.root_notice)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.tree = ProjectTree(self)
        self.tree.setIconSize(QSize(40, 20))
        self.tree.drop_requested.connect(self.tree_drop, Qt.ConnectionType.QueuedConnection)
        self.tree.setObjectName("project_tree")
        self.tree.setAccessibleName("Projektbaum; Verweise öffnen dieselbe Asset-Karte")
        self.tree.setHeaderLabels(["Projekt und Verwendungen"])
        self.tree.itemSelectionChanged.connect(self._tree_selected)
        self.tree.itemExpanded.connect(lambda item: self._tree_collapse(item, False))
        self.tree.itemCollapsed.connect(lambda item: self._tree_collapse(item, True))
        self.splitter.addWidget(self.tree)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("workspace_tabs")
        canvas_page = QWidget()
        canvas_layout = QVBoxLayout(canvas_page)
        actions = QHBoxLayout()
        for text, name, call in (
            ("+ Akt", "add_act", lambda: self.create_dialog("act")),
            ("+ Kapitel", "add_chapter", lambda: self.create_dialog("chapter")),
            ("+ Nebenkarte", "add_card", lambda: self.create_dialog("side")),
            ("+", "zoom_in", lambda: self.canvas.zoom(1.15)),
            ("−", "zoom_out", lambda: self.canvas.zoom(1 / 1.15)),
            ("Anordnen", "auto_layout", self.auto_layout),
            ("Manuell", "restore_layout", self.restore_layout),
        ):
            actions.addWidget(button(text, name, call))
        actions.addStretch(1)
        canvas_layout.addLayout(actions)
        self.canvas = Canvas()
        # Saving a dirty note can rebuild the scene; finish the pointer event first.
        self.canvas.selected.connect(self._canvas_selected, Qt.ConnectionType.QueuedConnection)
        self.canvas.open_requested.connect(self.open_canvas_content,
                                            Qt.ConnectionType.QueuedConnection)
        self.canvas.moved.connect(self.move_card, Qt.ConnectionType.QueuedConnection)
        self.canvas_actions = CanvasActions(self)
        self.canvas.moved_many.connect(self.canvas_actions.move_many,
                                       Qt.ConnectionType.QueuedConnection)
        self.canvas.create_requested.connect(self.canvas_actions.create_at,
                                             Qt.ConnectionType.QueuedConnection)
        self.canvas.toggle_requested.connect(self.toggle_card, Qt.ConnectionType.QueuedConnection)
        self.canvas.resized.connect(self.resize_canvas_card, Qt.ConnectionType.QueuedConnection)
        self.canvas.connection_requested.connect(self.connect_cards,
                                                 Qt.ConnectionType.QueuedConnection)
        self.canvas.reconnect_requested.connect(self.reconnect_cards,
                                                Qt.ConnectionType.QueuedConnection)
        canvas_layout.addWidget(self.canvas, 1)
        canvas_layout.addWidget(label(
            "Linien: ─ gehört zu · – – verwendet · · · benötigt. "
            "Kreise ziehen: verbinden · Linie anklicken: umhängen · ◢: Größe · "
            "Mittlere Maustaste: Ansicht verschieben · Strg+Z: zurück · "
            "Strg+Mausrad: Zoom · Doppelklick: Gruppe klappen."
        ))
        self.tabs.addTab(canvas_page, "Projekt-Canvas")
        self.tasks = KanbanPanel()
        self.tasks.focus_requested.connect(self.select_card)
        self.tasks.changed.connect(self.refresh)
        self.tabs.addTab(self.tasks, "Aufgaben-Kanban")
        self.notes = NotesPanel(self.prepare_content_change)
        self.notes.changed.connect(self._notes_changed)
        self.notes.focus_requested.connect(self.select_card)
        self.tabs.addTab(self.notes, "Notizen")
        self.documents = DocumentEditor()
        self.documents.saved.connect(self._document_saved)
        self.tabs.addTab(self.documents, "Dokumentation && Anhänge")
        self.search = TasksPanel(search_only=True)
        self.search.focus_requested.connect(self.select_card)
        self.search.document_requested.connect(self.open_document)
        self.search.changed.connect(self.refresh)
        self.tabs.addTab(self.search, "Suche")
        self.splitter.addWidget(self.tabs)
        properties = QWidget()
        property_layout = QVBoxLayout(properties)
        property_layout.addWidget(label("Karteneigenschaften", "properties_title"))
        self.workflow_status = label("Status / nächster Schritt: Karte auswählen.",
                                      "workflow_status")
        property_layout.addWidget(self.workflow_status)
        self.usage = label("Herkunft und gemeinsame Verwendungen", "asset_usage")
        self.usage.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        property_layout.addWidget(self.usage)
        self.details = QPlainTextEdit()
        self.details.setObjectName("card_properties")
        self.details.setReadOnly(True)
        self.details.setMinimumHeight(140)
        property_layout.addWidget(self.details, 1)
        size_row = QHBoxLayout()
        self.card_width, self.card_height = QSpinBox(), QSpinBox()
        self.card_width.setObjectName("card_view_width")
        self.card_height.setObjectName("card_view_height")
        self.card_width.setRange(200, 1000)
        self.card_height.setRange(100, 400)
        self.card_width.setPrefix("B: ")
        self.card_height.setPrefix("H: ")
        size_row.addWidget(self.card_width)
        size_row.addWidget(self.card_height)
        size_row.addWidget(button("Ansicht", "resize_card", self.resize_card))
        property_layout.addLayout(size_row)
        for text, name, call in (
            ("Umbenennen", "rename_card", self.rename_dialog),
            ("Archivieren / Wiederherstellen", "archive_card", self.archive_dialog),
        ):
            property_layout.addWidget(button(text, name, call))
        self.relation_kind = QComboBox()
        self.relation_kind.setObjectName("relation_kind")
        self.relation_kind.addItem("Verwendung → uses", "uses")
        self.relation_kind.addItem("Voraussetzung → depends_on", "depends_on")
        self.relation_target = QComboBox()
        self.relation_target.setObjectName("relation_target")
        property_layout.addWidget(label("Zielkarte für Verbindung (Zuordnung: im Baum ziehen)"))
        property_layout.addWidget(self.relation_kind)
        property_layout.addWidget(self.relation_target)
        property_layout.addWidget(button("Verbindung anlegen", "add_relation", self.link_dialog))
        self.use_existing = button("Vorhandenes Asset verwenden …", "use_existing_asset",
                                    self.use_existing_dialog)
        property_layout.addWidget(self.use_existing)
        self.relations = QComboBox()
        self.relations.setObjectName("existing_relations")
        property_layout.addWidget(self.relations)
        property_layout.addWidget(button("Verbindung lösen", "remove_relation", self.unlink_dialog))
        property_scroll = QScrollArea()
        property_scroll.setWidgetResizable(True)
        property_scroll.setWidget(properties)
        property_scroll.setMinimumWidth(270)
        self.splitter.addWidget(property_scroll)
        self.splitter.setSizes([250, 880, 290])
        self.splitter.setStretchFactor(1, 1)
        # Canvas geometry/relations are not task controls; give the board their space.
        self.tabs.currentChanged.connect(lambda index: property_scroll.setVisible(
            self.tabs.widget(index) not in {self.tasks, self.notes, self.documents}))
        outer.addWidget(self.splitter, 1)
        self.jobs = label("Keine Aufträge. Diagnose über Aufträge …; keine Asset-Freigabe.",
                          "job_status")
        outer.addWidget(self.jobs)
        self.setCentralWidget(center)
        save = QAction("Dokument speichern", self)
        save.setShortcut(QKeySequence.StandardKey.Save)
        save.triggered.connect(lambda: (self.notes if self.tabs.currentWidget() is self.notes
                                        else self.documents).save())
        self.addAction(save)
        search = QAction("Suche", self)
        search.setShortcut(QKeySequence("Ctrl+F"))
        search.triggered.connect(self._focus_search)
        self.addAction(search)
        self.statusBar().showMessage("Bereit · Projekt wählen")

    def apply_appearance(self) -> None:
        self.project_toolbar.setIconSize(QSize(16, 16))
        self.project_toolbar.setToolButtonStyle(BUTTON_STYLES[appearance().buttons])
        for action in self.project_toolbar.actions():
            if action.objectName():
                action.setIcon(action_icon(action.objectName()))
        self.workflow_status.setStyleSheet(
            f"QLabel {{ background: {color('warning')}; color: {color('warning_text')}; "
            f"padding: 8px; border: 1px solid {color('border')}; "
            "border-radius: 4px; font-weight: bold; }")
        if self.project:
            records = {record.id: record for record in self.project.catalog.records()}
            iterator = QTreeWidgetItemIterator(self.tree)
            while iterator.value():
                item = iterator.value()
                record = records.get(item.data(0, Qt.UserRole))
                if record:
                    item.setIcon(0, record_icon(record))
                iterator += 1

    def show_appearance_settings(self) -> None:
        dialog = AppearanceDialog(self)
        dialog.exec()
        dialog.deleteLater()

    def open_document(self, identifier: str) -> None:
        self.open_content(identifier)

    def open_content(self, identifier: str, *, edit: bool = False) -> bool:
        if not self.project:
            return False
        record = self.project.catalog.get(identifier)
        if is_note(record):
            if not self.prepare_content_change() or not self.select_card(record.owner_id):
                self._select_tree_item(self.selected_content_id or self.selected_id)
                return False
            self.notes.query.clear()
            self.notes.color.setCurrentIndex(0)
            if not self.notes.select_note(identifier):
                return False
            self.tabs.setCurrentWidget(self.notes)
            if edit:
                self.notes.editor.editor.setFocus()
        elif record.kind == "document":
            if not self.notes.confirm_discard():
                return False
            if not self.documents.open_document(identifier):
                self._select_tree_item(self.selected_content_id or self.selected_id)
                return False
            self.select_card(record.owner_id)
            self.tabs.setCurrentWidget(self.documents)
        elif record.kind in {"task", "issue"}:
            if not self.select_card(record.owner_id):
                return False
            self.tasks.show_record(identifier)
            self.tabs.setCurrentWidget(self.tasks)
            if edit:
                self.tasks.edit_current()
        else:
            return False
        self.selected_content_id = identifier
        self._select_tree_item(identifier)
        return True

    def _select_tree_item(self, identifier: str | None) -> None:
        self._refreshing = True
        for item in self.tree.findItems("", Qt.MatchFlag.MatchContains
                                        | Qt.MatchFlag.MatchRecursive):
            if item.data(0, Qt.ItemDataRole.UserRole) == identifier:
                self.tree.setCurrentItem(item)
                self.tree.scrollToItem(item)
                break
        self._refreshing = False

    def _action(self, toolbar: QToolBar, text: str, call: Callable,
                shortcut: str, name: str) -> QAction:
        action = toolbar.addAction(text)
        action.setObjectName(name)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(call)
        return action

    def create_asset(self, owner_id: str | None = None) -> None:
        if not self.project:
            return
        if not owner_id:
            parent = self.project.catalog.get(self.selected_id or self.project.project().id)
            while parent.kind not in {"global", "act", "chapter", "package"} and parent.owner_id:
                parent = self.project.catalog.get(parent.owner_id)
            owner_id = parent.id
        assets = AssetService(self.project)
        def create(title: str, owner: str, data: dict):
            identifier = self.commands.create_card("asset", title, owner,
                                                   assets.creation_data(data))
            return self.project.catalog.get(identifier)
        dialog = AssetWizard(assets, self, owner_id=owner_id, create=create)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            self.select_card(dialog.created.id)
        dialog.deleteLater()

    def asset_workspace(self) -> None:
        if not self.project or not self.selected_id or not self.prepare_content_change():
            return
        def edit() -> None:
            dialog = AssetWorkspace(AssetService(self.project), self.selected_id, self)
            dialog.exec()
            if dialog.changed:
                self.documents.refresh_documents()
                self.refresh()
            dialog.deleteLater()
        self.perform(edit)

    def open_pipeline(self, identifier: str) -> None:
        if not self.project or not self.prepare_content_change():
            return
        def edit():
            from .pipeline_editor import PipelineEditor
            dialog = PipelineEditor(self.project, identifier, self, commands=self.commands)
            dialog.exec()
            self.refresh()
            dialog.deleteLater()
        self.perform(edit)

    def create_pipeline(self, *, choose_template=False) -> None:
        if not self.project or not self.prepare_content_change():
            return
        from ..application.pipeline_service import PipelineService
        from ..domain.pipeline_recipes import TEMPLATES, template

        identifier = "empty"
        if choose_template:
            title, accepted = QInputDialog.getItem(self, "Pipeline-Vorlage", "Ausgangspunkt",
                                                   list(TEMPLATES.values()), 0, False)
            if not accepted:
                return
            identifier = next(key for key, value in TEMPLATES.items() if value == title)
        title, accepted = QInputDialog.getText(self, "Neue projektweite Pipeline", "Name",
                                               text=TEMPLATES[identifier])
        if not accepted:
            return
        def create():
            service = PipelineService(self.project)
            key = self.commands.create_card("pipeline", title, service.global_id,
                {"project_id": service.project_id, "recipe": template(identifier)})
            self.refresh()
            self.select_card(key)
            self.open_pipeline(key)
        self.perform(create)

    def import_pipeline(self) -> None:
        if not self.project or not self.prepare_content_change():
            return
        def load():
            from .pipeline_exchange_dialogs import import_pipeline
            record = import_pipeline(self.project, self)
            if record:
                def archived(value):
                    current = self.project.catalog.get(record.id)
                    if current.archived != value:
                        self.project.archive(record.id, value, current.revision_no)
                self.commands.execute(Command("Pipeline-Kopie importieren",
                    lambda: archived(False), lambda: archived(True)))
                self.refresh()
                self.select_card(record.id)
                self.open_pipeline(record.id)
        self.perform(load)

    def perform(self, call: Callable) -> bool:
        try:
            call()
            return True
        except (StudioError, OSError, sqlite3.Error, ValueError) as exc:
            show_error(self, exc)
            return False

    def _recent_menu(self) -> None:
        self.recent_menu.clear()
        recent = self.settings.value("recent_projects", [])
        if isinstance(recent, str):
            recent = [recent]
        for path in recent:
            action = self.recent_menu.addAction(str(path))
            action.triggered.connect(lambda checked=False, value=path:
                                     self.perform(lambda: self.open_project(Path(value))))
        if not recent:
            self.recent_menu.addAction("Noch keine Projekte").setEnabled(False)

    def _bind(self, project: ProjectService) -> None:
        if self.job_dialog:
            self.job_dialog.close()
            self.job_dialog.deleteLater()
            self.job_dialog = None
        if self.project:
            self.project.catalog.close()
        self.project = project
        self.commands = Commands(project)
        self.selected_id = None
        self.selected_content_id = None
        self.documents.bind(DocumentService(project))
        self.tasks.bind(project)
        self.notes.bind(project)
        self.search.bind(project)
        missing = project.unavailable_roots()
        self.root_notice.setText("Nicht verfügbare Wurzeln: " + ", ".join(missing) if missing
                                 else "Lokaler Katalog geöffnet · Keine produktive Asset-Freigabe")
        self.setWindowTitle(project.project().title + " · EtherFood Asset Studio")
        recent = self.settings.value("recent_projects", [])
        if isinstance(recent, str):
            recent = [recent]
        path = str(project.catalog.path.parent)
        self.settings.setValue("recent_projects", [path] + [p for p in recent if p != path][:7])
        self._recent_menu()
        self.refresh()
        self.select_card(project.project().id)
        self.canvas.resetTransform()
        zoom = float(self.settings.value("zoom", 0.8))
        self.canvas.zoom(max(0.25, min(2.5, zoom)))
        self.canvas.focus_card(project.project().id)
        self.statusBar().showMessage("Projekt geöffnet · " + project.project().title)

    def new_project(self, directory: Path, title: str,
                    roots: dict[str, Path] | None = None) -> bool:
        if not self.jobs_idle() or not self.prepare_content_change():
            return False
        self._bind(ProjectService.new(directory, title, roots))
        return True

    def open_project(self, directory: Path) -> bool:
        if not self.jobs_idle() or not self.prepare_content_change():
            return False
        self._bind(ProjectService.open(directory))
        return True

    def new_dialog(self) -> None:
        dialog = ProjectDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            roots = dialog.roots()
            if "WORKSPACE_ROOT" not in roots:
                show_error(self, StudioError("validation", "Projektordner fehlt."))
                return
            self.perform(lambda: self.new_project(
                roots["WORKSPACE_ROOT"], dialog.title.text(), roots,
            ))

    def open_dialog(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Studio-Projektordner öffnen")
        if path:
            self.perform(lambda: self.open_project(Path(path)))

    def demo_dialog(self) -> None:
        if not self.project:
            return
        if QMessageBox.question(self, "Synthetische Demo", "Demo anlegen (kein Spielkanon)?") \
                == QMessageBox.StandardButton.Yes:
            if self.perform(self.project.demo):
                self.refresh()

    def refresh(self) -> None:
        if not self.project:
            return
        self._refreshing = True
        self.tree.clear()
        cards = self.project.cards(include_archived=True)
        items = {}
        for card in cards:
            suffix = " [Archiv]" if card.archived else ""
            text = KIND_NAMES[card.kind] + " · " + card.title + suffix
            item = QTreeWidgetItem([text])
            item.setData(0, Qt.ItemDataRole.UserRole, card.id)
            item.setData(0, Qt.ItemDataRole.UserRole + 1, card.kind)
            item.setIcon(0, kind_icon(card.kind))
            items[card.id] = item
        for card in cards:
            if card.owner_id in items:
                items[card.owner_id].addChild(items[card.id])
            else:
                self.tree.addTopLevelItem(items[card.id])
        for record in self.project.catalog.records():
            if record.kind in {"document", "task", "issue"} and record.owner_id in items:
                display_kind = "note" if is_note(record) else record.kind
                item = QTreeWidgetItem([KIND_NAMES[display_kind] + " · " + record.title])
                item.setData(0, Qt.ItemDataRole.UserRole, record.id)
                item.setData(0, Qt.ItemDataRole.UserRole + 1, record.kind)
                item.setIcon(0, record_icon(record))
                item.setToolTip(0, "Inhalt öffnen · Rechtsklick: bearbeiten")
                items[record.owner_id].addChild(item)
                items[record.id] = item
        for edge in self.project.catalog.relations():
            if edge["kind"] == "uses" and edge["source_id"] in items:
                target = self.project.catalog.get(edge["target_id"])
                item = QTreeWidgetItem(["↪ " + target.title + " (Verweis)"])
                item.setData(0, Qt.ItemDataRole.UserRole, target.id)
                item.setData(0, Qt.ItemDataRole.UserRole + 1, "reference")
                item.setData(0, EDGE_ROLE, edge["id"])
                item.setIcon(0, kind_icon(target.kind))
                item.setToolTip(0, "Herkunft: " + self.project.breadcrumb(target.id))
                items[edge["source_id"]].addChild(item)
        for card in cards:
            items[card.id].setExpanded(not self.project.catalog.layout(card.id).get("collapsed"))
        selected = self.selected_content_id or self.selected_id
        if selected in items:
            self.tree.setCurrentItem(items[selected])
        self.canvas.render(self.project, self.selected_content_id or self.selected_id)
        self._refreshing = False
        self.tasks.refresh_scopes()
        self.notes.refresh()
        self.search.refresh_scopes()
        self._properties()
        if self.selected_id:
            self.breadcrumb.setText(self.project.breadcrumb(self.selected_id))
        self.undo_action.setEnabled(bool(self.commands.done))
        self.redo_action.setEnabled(bool(self.commands.undone))

    def _tree_selected(self) -> None:
        item = self.tree.currentItem()
        if item and not self._refreshing and self.tree.dragged is None:
            identifier = item.data(0, Qt.ItemDataRole.UserRole)
            if item.data(0, Qt.ItemDataRole.UserRole + 1) in {"document", "task", "issue"}:
                self.open_content(identifier)
            elif self.select_card(identifier):
                self.selected_content_id = None
                if self.project.catalog.get(identifier).kind == "note":
                    self.tabs.setCurrentWidget(self.notes)

    def _canvas_selected(self, identifier: str) -> None:
        # Keep the camera fixed while Qt still tracks a press/drag on the card.
        if self.canvas.selected_ids() != {identifier}:
            return
        record = self.project.catalog.get(identifier)
        if record.kind in {"document", "task", "issue"}:
            if self.select_card(record.owner_id, center=False):
                self.selected_content_id = record.id
                self._select_tree_item(record.id)
                self.canvas.focus_card(record.id, center=False)
        else:
            self.select_card(identifier, center=False)

    def open_canvas_content(self, identifier: str) -> None:
        record = self.project.catalog.get(identifier)
        if record.kind == "pipeline":
            self.open_pipeline(identifier)
        elif record.kind == "note":
            if not self.select_card(record.id):
                return
            self.tabs.setCurrentWidget(self.notes)
            self.notes.query.clear()
            self.notes.color.setCurrentIndex(0)
            self.notes.refresh()
        else:
            self.open_content(identifier, edit=True)

    def select_card(self, identifier: str, *, center: bool = True) -> bool:
        if not self.project or self._refreshing:
            return False
        if identifier == self.selected_id:
            return True
        if not self.notes.confirm_discard():
            self._select_tree_item(self.selected_content_id or self.selected_id)
            return False
        if not self.documents.show_card(identifier):
            self.canvas.focus_card(self.selected_id, center=center)
            self._select_tree_item(self.selected_content_id or self.selected_id)
            return False
        self.selected_id = identifier
        self.selected_content_id = None
        self.tasks.set_scope(identifier)
        self.notes.set_scope(identifier)
        self.search.current_card = identifier
        self.breadcrumb.setText(self.project.breadcrumb(identifier))
        current = self.tree.currentItem()
        if current is None or current.data(0, Qt.ItemDataRole.UserRole) != identifier:
            self._refreshing = True
            for item in self.tree.findItems("", Qt.MatchFlag.MatchContains
                                            | Qt.MatchFlag.MatchRecursive):
                if item.data(0, Qt.ItemDataRole.UserRole) == identifier:
                    self.tree.setCurrentItem(item)
                    self.tree.scrollToItem(item)
                    break
            self._refreshing = False
        view_changes = {}
        ancestor = self.project.catalog.get(identifier).owner_id
        while ancestor:
            layout = self.project.catalog.layout(ancestor)
            if layout.get("collapsed"):
                view_changes[ancestor] = layout | {"collapsed": False}
            ancestor = self.project.catalog.get(ancestor).owner_id
        if view_changes:
            self.commands.layouts(view_changes)
            self.canvas.render(self.project, identifier)
        self.canvas.focus_card(identifier, center=center)
        self._properties()
        return True

    def _properties(self) -> None:
        if not self.project or not self.selected_id:
            return
        record = self.project.catalog.get(self.selected_id)
        layout = self.canvas.default_positions(self.project).get(record.id, {})
        layout |= self.project.catalog.layout(record.id)
        self.card_width.setValue(layout.get("w", 250))
        self.card_height.setValue(layout.get("h", 100))
        states = StatusService(self.project).status(record.id)
        self.workflow_status.setText("Status / nächster Schritt\n"
                                     + StatusService(self.project).summary(record.id))
        self.usage.setText(self.project.usage_description(record.id))
        self.use_existing.setEnabled(record.kind in {"global", "act", "chapter", "package"}
                                      and not record.archived)
        self.details.setPlainText(
            f"{record.title}\n{KIND_NAMES[record.kind]} · Revision {record.revision_no}\n"
            f"ID: {record.id}\n\n" + "\n\n".join(
                f"{STEP_NAMES[value.id]}: {STATE_NAMES[value.state]}\n{status_reason(value)}"
                for value in states.values()
            )
        )
        self.relation_target.clear()
        for card in self.project.cards():
            if card.id != record.id:
                self.relation_target.addItem(KIND_NAMES[card.kind] + " · " + card.title, card.id)
        self.relations.clear()
        for edge in self.project.affected_relations(record.id):
            if edge["kind"] != "belongs_to":
                source = self.project.catalog.get(edge["source_id"]).title
                target = self.project.catalog.get(edge["target_id"]).title
                self.relations.addItem(edge["kind"] + ": " + source + " → " + target, edge["id"])

    def resize_card(self) -> None:
        if self.project and self.selected_id:
            layout = self.project.catalog.layout(self.selected_id)
            self.commands.layout(self.selected_id, layout | {
                "w": self.card_width.value(), "h": self.card_height.value(),
            })
            self.refresh()

    def resize_canvas_card(self, identifier: str, width: float, height: float) -> None:
        if self.project:
            layout = self.project.catalog.layout(identifier)
            self.commands.layout(identifier, layout | {"w": width, "h": height})
            self.refresh()

    def connect_cards(self, source: str, target: str) -> None:
        if not self.project:
            return
        if self.project.catalog.get(source).kind in {"document", "task", "issue"}:
            self.move_canvas_content(source, target)
            return
        kinds = {"Verwendet vorhandenes Asset/Paket": "uses",
                 "Benötigt Voraussetzung": "depends_on",
                 "Gehört zu (Hierarchie umordnen)": "belongs_to"}
        source_name = self.project.catalog.get(source).title
        target_name = self.project.catalog.get(target).title
        choice, accepted = QInputDialog.getItem(
            self, "Verbindungstyp wählen", f"{source_name} → {target_name}", list(kinds), 0, False,
        )
        if accepted:
            kind = kinds[choice]
            call = (lambda: self.commands.move(source, target)) if kind == "belongs_to" \
                else (lambda: self.commands.link(source, target, kind))
            if self.perform(call):
                self.refresh()

    def reconnect_cards(self, identifier: str, source: str, target: str) -> None:
        if identifier.startswith("content:"):
            if source != identifier.removeprefix("content:"):
                show_error(self, StudioError("validation", "Nur das Eigentümerende umhängen."))
            else:
                self.move_canvas_content(source, target)
            return
        if self.project and self.perform(lambda: self.commands.relink(identifier, source, target)):
            self.refresh()

    def move_canvas_content(self, source: str, target: str) -> None:
        if self.project and self.prepare_content_change():
            self.tree_drop(TreeService(self.commands).capture(source), target, False)

    def _tree_collapse(self, item: QTreeWidgetItem, collapsed: bool) -> None:
        if not self._refreshing and self.project and self.tree.dragged is None \
                and item.data(0, Qt.ItemDataRole.UserRole + 1) in CARD_KINDS:
            identifier = item.data(0, Qt.ItemDataRole.UserRole)
            layout = self.project.catalog.layout(identifier) | {"collapsed": collapsed}
            self.commands.layout(identifier, layout)
            self.canvas.render(self.project, self.selected_id)

    def toggle_card(self, identifier: str) -> None:
        if self.project:
            layout = self.project.catalog.layout(identifier)
            self.commands.layout(identifier, layout | {"collapsed": not layout.get("collapsed")})
            self.refresh()

    def move_card(self, identifier: str, x: float, y: float) -> None:
        if self.project:
            layout = self.project.catalog.layout(identifier)
            if "manual" in layout:
                layout = layout | {"manual": {"x": x, "y": y}}
            self.commands.layout(identifier, layout | {"x": x, "y": y})
            self.refresh()

    def auto_layout(self) -> None:
        if not self.project:
            return
        values = {}
        for key, defaults in self.canvas.default_positions(self.project).items():
            old = self.project.catalog.layout(key)
            manual = old.get("manual", {name: old.get(name, defaults[name]) for name in ("x", "y")})
            values[key] = defaults | old | {
                "x": defaults["x"], "y": defaults["y"], "manual": manual,
            }
        self.commands.layouts(values)
        self.refresh()

    def restore_layout(self) -> None:
        if self.project:
            values = {key: self.project.catalog.layout(key)
                      for key in self.canvas.default_positions(self.project)}
            self.commands.layouts({key: value | value.get("manual", {})
                                   for key, value in values.items()})
            self.refresh()

    def undo(self, redo: bool) -> None:
        if self.tabs.currentWidget() is self.notes and self.notes.editor.editor.hasFocus():
            editor = self.notes.editor.editor
            editor.redo() if redo else editor.undo()
            return
        if self.tabs.currentWidget() is self.documents and self.documents.editor.hasFocus():
            if redo:
                self.documents.editor.redo()
            else:
                self.documents.editor.undo()
            return
        stack = (self.commands.undone if redo else self.commands.done) if self.commands else []
        if stack and stack[-1].title == "Zuordnung ändern" and not self.prepare_content_change():
            return
        if self.commands and self.perform(self.commands.redo if redo else self.commands.undo):
            self.sync_document_owner()
            self.refresh()
            if self.selected_content_id:
                identifier = self.selected_content_id
                self.select_card(self.project.catalog.get(identifier).owner_id)
                self.selected_content_id = identifier
                self._select_tree_item(identifier)

    def create_dialog(self, kind: str) -> None:
        if not self.project:
            return
        parent = self.project.catalog.get(self.selected_id or self.project.project().id)
        if kind == "act":
            parent = self.project.project()
        elif kind == "chapter":
            while parent.kind != "act" and parent.owner_id:
                parent = self.project.catalog.get(parent.owner_id)
            if parent.kind != "act":
                show_error(self, StudioError("validation", "Zuerst einen Akt auswählen."))
                return
        else:
            if parent.kind == "project":
                parent = next(card for card in self.project.cards() if card.kind == "global")
            if kind == "side":
                names = {"Notiz": "note", "Asset": "asset", "Paket": "package"}
                name, accepted = QInputDialog.getItem(self, "Nebenkarte", "Typ",
                                                      list(names), 0, False)
                if not accepted:
                    return
                kind = names[name]
        if kind == "asset":
            self.create_asset(parent.id)
            return
        title, accepted = QInputDialog.getText(self, "Karte anlegen", "Name")
        if accepted:
            def create() -> None:
                identifier = self.commands.create_card(kind, title, parent.id)
                self.refresh()
                self.select_card(identifier)
            self.perform(create)

    def rename_dialog(self) -> None:
        if not self.project or not self.selected_id:
            return
        record = self.project.catalog.get(self.selected_id)
        title, accepted = QInputDialog.getText(self, "Umbenennen", "Name", text=record.title)
        if accepted and self.perform(lambda: self.project.rename(
            record.id, title, record.revision_no,
        )):
            self.breadcrumb.setText(self.project.breadcrumb(record.id))
            self.refresh()

    def prepare_content_change(self) -> bool:
        if not self.documents.confirm_discard() or not self.notes.confirm_discard():
            return False
        if self.documents.dirty:
            self.documents.refresh_documents(self.documents.current.id)
        return True

    def tree_drop(self, drag, target: str, copy: bool) -> None:
        if not self.project or not self.perform(
                lambda: TreeService(self.commands).apply(drag, target, copy)):
            return
        self.sync_document_owner()
        self.refresh()
        if not drag.edge and not copy:
            record = self.project.catalog.get(drag.record.id)
            if record.kind in {"task", "issue", "document"}:
                self.select_card(record.owner_id)
                self.selected_content_id = record.id
                self._select_tree_item(record.id)
            else:
                self.select_card(record.id)
        self.statusBar().showMessage("Zuordnung gespeichert · Strg+Z: rückgängig", 7000)

    def sync_document_owner(self) -> None:
        for editor in (self.documents, self.notes.editor):
            current = editor.current
            if current and not editor.dirty:
                editor.owner_id = self.project.catalog.get(current.id).owner_id
                editor.refresh_documents(current.id)

    def archive_dialog(self) -> None:
        if not self.project or not self.selected_id:
            return
        record = self.project.catalog.get(self.selected_id)
        count = len(self.project.affected_relations(record.id))
        action = "Wiederherstellen" if record.archived else "Archivieren"
        if QMessageBox.question(self, action, f"{count} Beziehungen bleiben erhalten. "
                                "Es werden keine Dateien gelöscht. Fortfahren?") \
                == QMessageBox.StandardButton.Yes:
            if self.perform(lambda: self.project.archive(record.id, not record.archived,
                                                         record.revision_no)):
                self.refresh()

    def link_dialog(self) -> None:
        if self.project and self.selected_id and self.relation_target.currentData():
            if self.perform(lambda: self.commands.link(self.selected_id,
                                                       self.relation_target.currentData(),
                                                       self.relation_kind.currentData())):
                self.refresh()

    def use_existing_dialog(self) -> None:
        if not self.project or not self.selected_id:
            return
        used = {edge["target_id"] for edge in self.project.catalog.relations()
                if edge["source_id"] == self.selected_id and edge["kind"] == "uses"}
        choices = {f"{self.project.breadcrumb(card.id)} [{card.id[:8]}]": card.id
                   for card in self.project.cards() if card.kind in {"asset", "package"}
                   and card.id not in used and card.id != self.selected_id}
        if not choices:
            QMessageBox.information(self, "Vorhandenes Asset verwenden",
                                    "Keine weitere Asset-/Paketkarte vorhanden. "
                                    "Zuerst eine Karte anlegen; dies importiert noch keine Grafik.")
            return
        choice, accepted = QInputDialog.getItem(
            self, "Gemeinsame Verwendung", "Vorhandene Karte verknüpfen – keine Kopie",
            list(choices), 0, False,
        )
        if accepted and self.perform(lambda: self.commands.link(
            self.selected_id, choices[choice], "uses",
        )):
            self.refresh()

    def unlink_dialog(self) -> None:
        identifier = self.relations.currentData()
        if not self.project or not identifier:
            return
        if QMessageBox.question(self, "Verbindung lösen", "Nur Verwendung/Voraussetzung entfernen? "
                                "Die Karte und ihre Dateien bleiben erhalten.") \
                == QMessageBox.StandardButton.Yes:
            if self.perform(lambda: self.commands.unlink(identifier)):
                self.refresh()

    def _document_saved(self) -> None:
        if self.documents.current:
            self.selected_content_id = self.documents.current.id
        self.refresh()

    def _notes_changed(self) -> None:
        if self.documents.current and not self.documents.dirty:
            self.documents.refresh_documents(self.documents.current.id)
        self.refresh()

    def _focus_search(self) -> None:
        self.tabs.setCurrentWidget(self.search)
        self.search.query.setFocus()

    def closeEvent(self, event: QCloseEvent) -> None:
        modal = QApplication.activeModalWidget()
        if isinstance(modal, BuildPlanDialog) and modal.worker:
            modal.cancel()
            event.ignore()
            return
        if self.build_dialog and self.build_dialog.worker:
            self.build_dialog.cancel()
            event.ignore()
            self.statusBar().showMessage("Buildprüfung wird beendet; danach erneut schließen.")
            return
        if self.job_dialog and self.job_dialog.runner.active:
            event.ignore()
            if QMessageBox.question(self, "Laufende Aufträge",
                                    "Aufträge abbrechen und nach dem sicheren Ende schließen?") \
                    == QMessageBox.StandardButton.Yes:
                self._close_after_jobs = True
                for identifier in tuple(self.job_dialog.runner.active):
                    self.job_dialog.runner.cancel(identifier)
            return
        if not self.prepare_content_change():
            event.ignore()
            return
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("zoom", self.canvas.transform().m11())
        if self.project:
            self.project.catalog.close()
            self.project = None
        event.accept()

    def jobs_idle(self) -> bool:
        if self.build_dialog and self.build_dialog.worker:
            self.statusBar().showMessage("Zuerst den laufenden Buildplan abschließen/abbrechen.")
            return False
        if self.job_dialog and self.job_dialog.runner.active:
            self.statusBar().showMessage("Erst Aufträge beenden/abbrechen, dann Projekt wechseln.")
            return False
        return True

    def show_jobs(self) -> None:
        if not self.project:
            return
        if self.job_dialog is None:
            self.job_dialog = JobsDialog(self.project, self)
            self.job_dialog.changed.connect(self._jobs_changed)
        self.job_dialog.owner_id = self.selected_id or self.project.project().id
        self.job_dialog.show()
        self.job_dialog.raise_()

    def show_build_plan(self) -> None:
        if self.project:
            dialog = BuildPlanDialog(self.project, self.selected_id or self.project.project().id,
                                     self)
            self.build_dialog = dialog
            dialog.exec()
            self.build_dialog = None
            dialog.deleteLater()
            if self.job_dialog:
                self.job_dialog.refresh()

    def _jobs_changed(self) -> None:
        count = len(self.job_dialog.runner.active)
        self.jobs.setText(f"{count} laufende Aufträge · Details unter Aufträge …")
        if self._close_after_jobs and not count:
            self._close_after_jobs = False
            QTimer.singleShot(0, self.close)


def launch(project: Path | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv[:1])
    window = MainWindow()
    window.show()
    if project:
        QTimer.singleShot(0, lambda: window.perform(lambda: window.open_project(project)))
    return app.exec()
