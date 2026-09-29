"""Usable local dashboard: project navigation, canvas, notes and tasks."""

from pathlib import Path
import sqlite3
import sys
from typing import Callable

from PySide6.QtCore import QSettings, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QMainWindow,
    QGridLayout,
    QListWidget,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QToolBar,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QVBoxLayout,
    QWidget,
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
        self.processing = None
        self._close_after_processing = False
        self._section_rows = [0, 0]
        self._navigating = False
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
        toolbar.addSeparator()
        self.undo_action = self._action(toolbar, "Rückgängig", lambda: self.undo(False),
                                        "Ctrl+Z", "undo")
        self.redo_action = self._action(toolbar, "Wiederholen", lambda: self.undo(True),
                                        "Ctrl+Shift+Z", "redo")
        center = QWidget()
        outer = QVBoxLayout(center)
        tools_row = QHBoxLayout()
        tools_row.addWidget(toolbar, 1)
        self.settings_button = button("Einstellungen", "appearance_settings_button",
                                      self.show_appearance_settings)
        self.godot_button = button("Godot bereitstellen", "godot_export", lambda: None)
        self.godot_button.setEnabled(False)
        tools_row.addWidget(self.godot_button)
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
        body = QHBoxLayout()
        self.main_navigation = QListWidget()
        self.main_navigation.setObjectName("main_editor_navigation")
        self.main_navigation.addItems(["Projekt", "Skripte & Pipelines"])
        self.main_navigation.setFixedWidth(155)
        self.main_navigation.setCurrentRow(0)
        self.section_navigation = QListWidget()
        self.section_navigation.setObjectName("section_navigation")
        self.section_navigation.setFixedWidth(190)
        self.section_navigation.addItems(self.section_names(0))
        self.section_navigation.setCurrentRow(0)
        body.addWidget(self.main_navigation)
        body.addWidget(self.section_navigation)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.structure_stack = QStackedWidget()
        self.workspace_stack = QStackedWidget()
        self.splitter.addWidget(self.structure_stack)
        self.splitter.addWidget(self.workspace_stack)
        self.splitter.setSizes([250, 850])
        self.splitter.setStretchFactor(1, 1)
        body.addWidget(self.splitter, 1)
        self.tree = ProjectTree(self)
        self.tree.setIconSize(QSize(40, 20))
        self.tree.drop_requested.connect(self.tree_drop, Qt.ConnectionType.QueuedConnection)
        self.tree.setObjectName("project_tree")
        self.tree.setAccessibleName("Projektbaum; Verweise öffnen dieselbe Asset-Karte")
        self.tree.setHeaderLabels(["Projekt und Verwendungen"])
        self.tree.itemSelectionChanged.connect(self._tree_selected)
        self.tree.itemExpanded.connect(lambda item: self._tree_collapse(item, False))
        self.tree.itemCollapsed.connect(lambda item: self._tree_collapse(item, True))
        self.project_structure = QWidget()
        structure_layout = QVBoxLayout(self.project_structure)
        structure_layout.setContentsMargins(0, 0, 0, 0)
        structure_layout.addWidget(self.tree, 1)
        self.project_archive_view = QComboBox()
        self.project_archive_view.setObjectName("project_storage_view")
        self.project_archive_view.addItem("Ablage: Archiv", "archived")
        self.project_archive_view.addItem("Ablage: Papierkorb · 30 Tage", "trash")
        self.project_archive_view.currentIndexChanged.connect(self.refresh)
        structure_layout.addWidget(self.project_archive_view)
        self.structure_stack.addWidget(self.project_structure)
        self.structure_stack.addWidget(QWidget())
        self.tabs = QStackedWidget()
        self.tabs.setObjectName("workspace_tabs")
        canvas_page = QWidget()
        canvas_layout = QVBoxLayout(canvas_page)
        actions = QGridLayout()
        for index, (text, name, call) in enumerate(
            (
                ("+ Akt", "add_act", lambda: self.create_dialog("act")),
                ("+ Kapitel", "add_chapter", lambda: self.create_dialog("chapter")),
                ("+ Nebenkarte", "add_card", lambda: self.create_dialog("side")),
                ("+", "zoom_in", lambda: self.canvas.zoom(1.15)),
                ("−", "zoom_out", lambda: self.canvas.zoom(1 / 1.15)),
                ("Anordnen", "auto_layout", self.auto_layout),
                ("Manuell", "restore_layout", self.restore_layout),
            )
        ):
            actions.addWidget(button(text, name, call), index // 4, index % 4)
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
        from .usage_editor import UsageEditor

        self.usage_editor = UsageEditor(self)
        canvas_layout.addWidget(self.usage_editor)
        canvas_layout.addWidget(label(
            "Linien: ─ gehört zu · – – verwendet · · · benötigt. "
            "Kreise ziehen: verbinden · Linie anklicken: umhängen · ◢: Größe · "
            "Mittlere Maustaste: Ansicht verschieben · Strg+Z: zurück · "
            "Strg+Mausrad: Zoom · Doppelklick: Gruppe klappen."
        ))
        self.tabs.addWidget(canvas_page)
        self.tasks = KanbanPanel()
        self.tasks.focus_requested.connect(self.select_card)
        self.tasks.changed.connect(self.refresh)
        self.tabs.addWidget(self.tasks)
        self.notes = NotesPanel(self.prepare_content_change)
        self.notes.changed.connect(self._notes_changed)
        self.notes.focus_requested.connect(self.select_card)
        self.tabs.addWidget(self.notes)
        self.documents = DocumentEditor()
        self.documents.navigate = self.open_document
        self.documents.saved.connect(self._document_saved)
        self.tabs.addWidget(self.documents)
        from .workspace_search import WorkspaceSearch

        self.search = WorkspaceSearch("project")
        self.search.open_requested.connect(self.open_search_hit)
        self.tabs.addWidget(self.search)
        self.workspace_stack.addWidget(self.tabs)
        self.workspace_stack.addWidget(QWidget())
        outer.addLayout(body, 1)
        self.main_navigation.currentRowChanged.connect(self.set_main_editor)
        self.section_navigation.currentRowChanged.connect(self.set_section)
        self.tabs.currentChanged.connect(self.project_section_changed)
        self.canvas.delete_requested.connect(self.remove_dialog, Qt.QueuedConnection)
        self.setCentralWidget(center)
        save = QAction("Dokument speichern", self)
        save.setShortcut(QKeySequence.StandardKey.Save)
        save.triggered.connect(self.save_active)
        self.addAction(save)
        search = QAction("Suche", self)
        search.setShortcut(QKeySequence("Ctrl+F"))
        search.triggered.connect(self._focus_search)
        self.addAction(search)
        self.statusBar().showMessage("Bereit · Projekt wählen")

    @staticmethod
    def section_names(editor):
        return (
            ["Projekt-Canvas", "Aufgaben-Kanban", "Notizen", "Dokumentation & Anhänge", "Suche"]
            if editor == 0
            else ["Pipeline-Editor", "Python-Editor", "Suche"]
        )

    def set_main_editor(self, index):
        if self._navigating or index not in (0, 1):
            return
        self._navigating = True
        self.main_navigation.setCurrentRow(index)
        self.section_navigation.clear()
        self.section_navigation.addItems(self.section_names(index))
        self.section_navigation.setCurrentRow(self._section_rows[index])
        self.structure_stack.setCurrentIndex(index)
        self.workspace_stack.setCurrentIndex(index)
        self._navigating = False
        self.set_section(self._section_rows[index])

    def set_section(self, index):
        if self._navigating or index < 0:
            return
        main = self.main_navigation.currentRow()
        self._section_rows[main] = index
        self._navigating = True
        self.section_navigation.setCurrentRow(index)
        if main == 0:
            self.tabs.setCurrentIndex(index)
            if index == 4:
                self.search.refresh()
        elif self.processing:
            self.processing.set_section(index)
        self._navigating = False
        self.undo_action.setEnabled(True)
        self.redo_action.setEnabled(True)

    def project_section_changed(self, index):
        self._section_rows[0] = index
        if not self._navigating:
            self.set_main_editor(0)

    def tools_section_requested(self, index):
        self._section_rows[1] = index
        self.set_main_editor(1)

    def processing_finished(self):
        if self._close_after_processing:
            self._close_after_processing = False
            QTimer.singleShot(0, self.close)

    def save_active(self):
        if self.main_navigation.currentRow() == 1 and self.processing:
            if self.processing.pages.currentIndex() == 1:
                self.processing.python.save()
            elif self.processing.pipeline_pages.currentWidget() is self.processing.editor:
                self.processing.editor.save()
        elif self.tabs.currentWidget() is self.documents:
            self.documents.save()
        elif self.tabs.currentWidget() is self.notes:
            self.notes.save()

    def open_search_hit(self, hit):
        self.set_main_editor(0)
        if hit.state != "active":
            self.project_archive_view.setCurrentIndex(0 if hit.state == "archived" else 1)
            self._select_tree_item(hit.id)
            self.statusBar().showMessage("Inhalt in der Ablage; zum Bearbeiten wiederherstellen.")
            return
        if hit.edge_id:
            edge = next(e for e in self.project.catalog.relations() if e["id"] == hit.edge_id)
            self.select_card(edge["source_id"])
            self.tabs.setCurrentIndex(0)
            for item in self.tree.findItems("", Qt.MatchContains | Qt.MatchRecursive):
                if item.data(0, EDGE_ROLE) == hit.edge_id:
                    self.tree.setCurrentItem(item)
                    break
        elif hit.kind in {"document", "task", "issue"}:
            self.open_content(hit.id)
        elif self.select_card(hit.id):
            self.tabs.setCurrentIndex(0)

    def store_content(self, identifiers, state):
        if not self.project or not self.prepare_content_change():
            return
        from ..application.lifecycle_service import LifecycleService

        service = LifecycleService(self.project)
        try:
            impact = service.impact(identifiers)
        except StudioError as error:
            show_error(self, error)
            return
        details = []
        for row in impact:
            details.append(row["title"])
            if row["children"]:
                details.append("  Inhalte: " + ", ".join(row["children"]))
            if row["usages"]:
                details.append("  Betroffene Verwendungen: " + ", ".join(row["usages"]))
            details.append(f"  {len(row['connections'])} zugehörige Verbindungen")
        action = "Archivieren" if state == "archived" else "Entfernen"
        message = "\n".join(details) + (
            "\n\nOhne Ablaufdatum im Archiv wiederherstellbar."
            if state == "archived"
            else "\n\n30 Tage im Papierkorb wiederherstellbar. "
            "Danach werden ausschließlich zugehörige verwaltete Daten endgültig gelöscht."
        )
        if (
            QMessageBox.question(
                self, action, message, QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel
            )
            != QMessageBox.Yes
        ):
            return
        if self.perform(lambda: service.command(self.commands, identifiers, state)):
            self.refresh()
            self.processing.refresh()

    def restore_content(self, identifier, target=None):
        from ..application.lifecycle_service import LifecycleService

        if self.perform(
            lambda: LifecycleService(self.project).command(
                self.commands, [identifier], target=target
            )
        ):
            self.refresh()
            self.processing.refresh()

    def remove_dialog(self):
        if not self.project:
            return
        identifiers = self.canvas.selected_ids() or {self.selected_content_id or self.selected_id}
        self.store_content([key for key in identifiers if key], "trash")

    def use_pipeline(self):
        if not self.processing:
            return
        self.tabs.setCurrentIndex(0)
        self.usage_editor.choose_definition(self.selected_id or self.project.project().id)

    def apply_appearance(self) -> None:
        self.project_toolbar.setIconSize(QSize(16, 16))
        self.project_toolbar.setToolButtonStyle(BUTTON_STYLES[appearance().buttons])
        for action in self.project_toolbar.actions():
            if action.objectName():
                action.setIcon(action_icon(action.objectName()))
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
        from .settings import SettingsDialog

        dialog = SettingsDialog(self)
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
            if not self.select_card(record.owner_id):
                return False
            if not self.documents.open_document(identifier):
                self._select_tree_item(self.selected_content_id or self.selected_id)
                return False
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

    def show_pipeline_menu(self):
        if self.processing:
            self.set_main_editor(1)
            self.set_section(0)

    def open_pipeline(self, identifier):
        if not self.project or not self.processing:
            return
        record = self.project.catalog.get(identifier)
        definition = record.data["definition_id"] if record.kind == "pipeline_usage" else identifier
        if self.processing.open_definition(definition):
            self.set_main_editor(1)
            self.set_section(0)

    def create_pipeline(self, **unused):
        if self.processing:
            self.set_main_editor(1)
            self.processing.create_pipeline()

    def import_pipeline(self):
        if self.processing:
            self.set_main_editor(1)
            self.processing.import_files()

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

    def _bind(self, project):
        from ..application.workspace_migration import WorkspaceMigration
        from .pipeline_workspace import PipelineWorkspace

        try:
            WorkspaceMigration(project).run()
        except Exception:
            project.catalog.close()
            raise
        if self.processing:
            self.processing.controller.stop()
            self.workspace_stack.removeWidget(self.processing)
            self.structure_stack.removeWidget(self.processing.structure)
            self.processing.structure.deleteLater()
            self.processing.deleteLater()
        else:
            for stack in (self.workspace_stack, self.structure_stack):
                placeholder = stack.widget(1)
                stack.removeWidget(placeholder)
                placeholder.deleteLater()
        if self.project:
            self.project.catalog.close()
        self.project = project
        self.commands = Commands(project)
        self.processing = PipelineWorkspace(project, self, commands=self.commands)
        self.processing.changed.connect(self.refresh)
        self.processing.section_requested.connect(self.tools_section_requested)
        self.processing.controller.idle.connect(self.processing_finished)
        self.workspace_stack.addWidget(self.processing)
        self.structure_stack.addWidget(self.processing.structure)
        self.selected_id = self.selected_content_id = None
        self.documents.bind(DocumentService(project))
        self.tasks.bind(project)
        self.notes.bind(project)
        self.search.bind(project)
        missing = project.unavailable_roots()
        self.root_notice.setText(
            "Nicht verfügbare Wurzeln: " + ", ".join(missing)
            if missing
            else "Lokales Projekt · Verarbeitung benötigt eine ausdrückliche Freigabe"
        )
        self.setWindowTitle(project.project().title + " · EtherFood Asset Studio")
        recent = self.settings.value("recent_projects", [])
        if isinstance(recent, str):
            recent = [recent]
        path = str(project.catalog.path.parent)
        self.settings.setValue("recent_projects", [path] + [p for p in recent if p != path][:7])
        self._recent_menu()
        self._section_rows = [0, 0]
        self.set_main_editor(0)
        self.refresh()
        self.select_card(project.project().id)
        self.canvas.resetTransform()
        zoom = float(self.settings.value("zoom", 0.8))
        self.canvas.zoom(max(0.25, min(2.5, zoom)))
        self.canvas.focus_card(project.project().id)
        self.statusBar().showMessage("Projekt geöffnet · " + project.project().title)
        self.processing.controller.maintenance()
        self.processing.controller.schedule()

    def new_project(self, directory: Path, title: str,
                    roots: dict[str, Path] | None = None) -> bool:
        if not self.processing_idle() or not self.prepare_content_change():
            return False
        self._bind(ProjectService.new(directory, title, roots))
        return True

    def open_project(self, directory: Path) -> bool:
        if not self.processing_idle() or not self.prepare_content_change():
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
        if (
            QMessageBox.question(
                self,
                "Synthetische Demo",
                "Synthetische Assets, aktuelle Skripte und ungeprüfte Pipelines anlegen?",
                QMessageBox.Yes | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            == QMessageBox.Yes
        ):
            from ..application.workspace_demo import WorkspaceDemo

            if self.perform(lambda: WorkspaceDemo(self.project).create()):
                self.processing.content_changed()
                self.statusBar().showMessage(
                    "Demo vorhanden. Bestehende Demo wird nicht dupliziert."
                )

    def refresh(self):
        if not self.project:
            return
        self.documents.refresh_current()
        self._refreshing = True
        from .project_tree import populate_project_tree

        populate_project_tree(self)
        self.canvas.render(self.project, self.selected_content_id or self.selected_id)
        self._refreshing = False
        self.tasks.refresh_scopes()
        self.notes.refresh()
        self.search.refresh()
        if self.selected_id:
            try:
                self.breadcrumb.setText(self.project.breadcrumb(self.selected_id))
            except StudioError:
                self.selected_id = None
        self.undo_action.setEnabled(True)
        self.redo_action.setEnabled(True)

    def _tree_selected(self) -> None:
        item = self.tree.currentItem()
        if item and not self._refreshing and self.tree.dragged is None:
            identifier = item.data(0, Qt.ItemDataRole.UserRole)
            if not identifier:
                return
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

    def open_canvas_content(self, identifier):
        record = self.project.catalog.get(identifier)
        if record.kind in {"pipeline", "pipeline_usage"}:
            self.select_card(identifier, center=False)
        elif record.kind == "note":
            if self.select_card(record.id):
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
        return True

    def resize_canvas_card(self, identifier: str, width: float, height: float) -> None:
        if self.project:
            if self.project.catalog.get(identifier).kind in {
                "project",
                "pipeline",
                "pipeline_usage",
                "note",
            }:
                return
            layout = self.project.catalog.layout(identifier)
            self.commands.layout(identifier, layout | {"w": width, "h": height})
            self.refresh()

    def connect_cards(self, source: str, target: str) -> None:
        if not self.project:
            return
        if self.project.catalog.get(source).kind in {"document", "task", "issue"}:
            self.move_canvas_content(source, target)
            return
        source_record, target_record = (self.project.catalog.get(key) for key in (source, target))
        if source_record.kind == target_record.kind == "pipeline_usage":
            self.perform(lambda: self.usage_editor.open(target, source=source))
            return
        if "pipeline_usage" in {source_record.kind, target_record.kind}:
            usage, scope = (
                (source, target) if source_record.kind == "pipeline_usage" else (target, source)
            )
            self.perform(lambda: self.usage_editor.open(usage, target=scope))
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
        if identifier.startswith(("scope:", "result:")):
            usage = identifier.split(":")[1]
            self.perform(lambda: self.usage_editor.open(usage))
            return
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
        if self.main_navigation.currentRow() == 1 and self.processing:
            focus = QApplication.focusWidget()
            structure = self.processing.structure
            in_structure = focus is structure or focus is not None and structure.isAncestorOf(focus)
            if in_structure and self.commands:
                self.perform(self.commands.redo if redo else self.commands.undo)
                self.processing.refresh()
            elif self.processing.pages.currentIndex() == 1:
                editor = self.processing.python.editor
                editor.redo() if redo else editor.undo()
            elif self.processing.pipeline_pages.currentWidget() is self.processing.editor:
                self.processing.editor.redo() if redo else self.processing.editor.undo()
            else:
                if self.commands:
                    self.perform(self.commands.redo if redo else self.commands.undo)
                    self.processing.refresh()
            return
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
        if not self.usage_editor.confirm_discard():
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

    def archive_dialog(self):
        if not self.project or not self.selected_id:
            return
        from ..application.lifecycle_service import LifecycleService

        service = LifecycleService(self.project)
        if service.state(self.selected_id):
            self.restore_content(self.selected_id)
        else:
            self.store_content([self.selected_id], "archived")

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

    def _document_saved(self) -> None:
        if self.documents.current:
            self.selected_content_id = self.documents.current.id
        self.refresh()

    def _notes_changed(self) -> None:
        if self.documents.current and not self.documents.dirty:
            self.documents.refresh_documents(self.documents.current.id)
        self.refresh()

    def _focus_search(self):
        self.set_section(4 if self.main_navigation.currentRow() == 0 else 2)
        (
            self.search if self.main_navigation.currentRow() == 0 else self.processing.search
        ).query.setFocus()

    def closeEvent(self, event):
        if self.processing and self.processing.busy:
            event.ignore()
            if (
                QMessageBox.question(
                    self,
                    "Laufende Verarbeitung",
                    "Durchgang sicher abbrechen und anschließend schließen?",
                    QMessageBox.Yes | QMessageBox.Cancel,
                    QMessageBox.Cancel,
                )
                == QMessageBox.Yes
            ):
                self._close_after_processing = True
                self.processing.controller.stop()
            return
        if (
            not self.prepare_content_change()
            or self.processing
            and not self.processing.confirm_discard()
        ):
            event.ignore()
            return
        if self.processing:
            self.processing.editor.save_position()
            self.processing.controller.stop()
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("zoom", self.canvas.transform().m11())
        if self.project:
            self.project.catalog.close()
            self.project = None
        event.accept()

    def processing_idle(self):
        if self.processing and self.processing.busy:
            self.statusBar().showMessage(
                "Durchgang abbrechen oder seinen kontrollierten Abschluss abwarten."
            )
            return False
        return not self.processing or self.processing.confirm_discard()

    def show_start_page(self):
        if self.project and self.select_card(self.project.project().id):
            document = next(row for row in self.documents.service.documents(self.selected_id)
                            if row.data.get("automation") == "index")
            self.open_document(document.id)


def launch(project: Path | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv[:1])
    window = MainWindow()
    window.show()
    if project:
        QTimer.singleShot(0, lambda: window.perform(lambda: window.open_project(project)))
    return app.exec()
