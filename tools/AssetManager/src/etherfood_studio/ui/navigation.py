"""Context actions reuse the same services and unsaved-change guards as the main UI."""

from typing import TYPE_CHECKING, Callable

from PySide6.QtCore import QPoint, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QInputDialog, QMenu

from ..domain.relations import PARENTS
from .presentation import kind_icon

if TYPE_CHECKING:
    from .main_window import MainWindow


class Navigation:
    def __init__(self, window: "MainWindow") -> None:
        self.window = window
        window.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        window.tree.customContextMenuRequested.connect(self.show_tree)
        window.canvas.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        window.canvas.customContextMenuRequested.connect(self.show_canvas)

    def show_tree(self, point: QPoint) -> None:
        item = self.window.tree.itemAt(point)
        if item:
            menu = self.menu(item.data(0, Qt.ItemDataRole.UserRole))
            menu.exec(self.window.tree.viewport().mapToGlobal(point))
            menu.deleteLater()

    def show_canvas(self, point: QPoint) -> None:
        if not self.window.project:
            return
        card = self.window.canvas.card_at(self.window.canvas.mapToScene(point))
        if card:
            menu = self.menu(card.identifier)
        else:
            selected = self.window.selected_id
            if len(self.window.canvas.selected_ids()) <= 1 and selected and \
                    self.window.project.catalog.get(selected).kind == "global":
                menu = self.menu(selected)
                menu.addSeparator()
            else:
                menu = QMenu(self.window)
                self.window.canvas_actions.add_arrangements(menu)
            self.add_pipeline_actions(menu)
        menu.exec(self.window.canvas.viewport().mapToGlobal(point))
        menu.deleteLater()

    def add_pipeline_actions(self, menu: QMenu) -> None:
        menu.addSection("Pipelines des Projekts")
        for title, name, call in (
            ("Ablaufeditor öffnen …", "context_workflow_open", self.window.show_pipeline_menu),
            ("Neuer Ablauf …", "context_pipeline_new", lambda: self.window.create_pipeline()),
            (
                "Werkzeugpaket / Ablauf importieren …",
                "context_pipeline_import",
                self.window.import_pipeline,
            ),
        ):
            item = menu.addAction(kind_icon("pipeline"), title)
            item.setObjectName(name)
            item.triggered.connect(call)

    def _on_card(self, identifier: str, call: Callable) -> None:
        if self.window.select_card(identifier):
            call()

    def open_folder(self, identifier):
        from ..domain.models import StudioError
        from .common import show_error

        try:
            path = self.window.project.files.path(identifier)
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
                raise StudioError("unavailable", "Ordner konnte nicht geöffnet werden.")
        except (StudioError, OSError) as error:
            show_error(self.window, error)

    def menu(self, identifier: str) -> QMenu:
        window = self.window
        record = window.project.catalog.get(identifier)
        menu = QMenu(window)
        window.canvas_actions.add_arrangements(menu, identifier)

        def action(title: str, name: str, kind: str, call: Callable) -> None:
            item = menu.addAction(kind_icon(kind), title)
            item.setObjectName(name)
            item.triggered.connect(call)

        if record.kind in {"document", "task", "issue"}:
            action("Öffnen / Bearbeiten", "context_edit", record.kind,
                   lambda: window.open_content(identifier, edit=True))
            if record.kind == "document" and record.data.get("automation"):
                visible = window.project.catalog.layout(identifier).get("document_visible", False)
                action("Im Canvas ausblenden" if visible else "Im Canvas einblenden",
                       "context_document_canvas", "document",
                       lambda: self.document_canvas(identifier, not visible))
            if record.kind == "document" and record.data["document_type"] == "manual" and \
                    not record.data.get("automation"):
                action("Umbenennen …", "context_rename", "document",
                       lambda: self.rename_document(identifier))
            return menu
        action("Ordner öffnen", "context_folder", "document",
               lambda: self.open_folder(identifier))
        action("Dokumente / Notiz öffnen", "context_open", "document",
               lambda: self._on_card(identifier, self.open_notes))
        if not record.archived:
            if record.kind == "pipeline":
                action("Pipeline öffnen …", "context_pipeline_open", "pipeline",
                       lambda: window.open_pipeline(identifier))
            if record.kind == "project":
                self.add_pipeline_actions(menu)
                menu.addSeparator()
            if record.kind == "asset":
                action("Asset-Menü öffnen …", "context_asset_workspace", "asset",
                       lambda: self._on_card(identifier, window.asset_workspace))
            if record.kind in {"global", "act", "chapter", "package"}:
                action("Vorhandenes Asset verwenden …", "context_use_existing", "asset",
                       lambda: self._on_card(identifier, window.use_existing_dialog))
            action("Neue Notiz …", "context_new_note", "note",
                   lambda: self._on_card(identifier, self.new_note))
            for kind, title in (("task", "Neue Aufgabe …"), ("issue", "Neues Issue …")):
                action(title, "context_new_" + kind, kind,
                       lambda checked=False, issue=kind == "issue": self._on_card(
                           identifier, lambda: self.new_task(issue)))
            menu.addSeparator()
            for kind, title in (("act", "Neuer Akt …"), ("chapter", "Neues Kapitel …"),
                                ("note", "Neue Notizkarte …"), ("asset", "Neues Asset …"),
                                ("package", "Neues Paket …")):
                if record.kind in PARENTS[kind]:
                    action(title, "context_card_" + kind, kind,
                           lambda checked=False, value=kind: self._on_card(
                               identifier, lambda: window.create_dialog(value)))
        menu.addSeparator()
        action("Umbenennen …", "context_rename", record.kind,
               lambda: self._on_card(identifier, window.rename_dialog))
        if record.kind not in {"project", "global"}:
            action("Wiederherstellen" if record.archived else "Archivieren …",
                   "context_archive", record.kind,
                   lambda: self._on_card(identifier, window.archive_dialog))
        return menu

    def document_canvas(self, identifier, visible):
        window = self.window
        if not window.prepare_content_change():
            return
        data = window.project.catalog.layout(identifier) | {"document_visible": visible}
        window.perform(lambda: window.commands.layout(identifier, data))
        window.refresh()
        if visible:
            window.tabs.setCurrentIndex(0)
            window.canvas.focus_card(identifier)

    def open_notes(self) -> None:
        if self.window.project.catalog.get(self.window.selected_id).kind == "note":
            self.window.tabs.setCurrentWidget(self.window.notes)
            return
        self.window.tabs.setCurrentWidget(self.window.documents)
        if not self.window.documents.current:
            self.window.documents.new_document()

    def new_note(self) -> None:
        self.window.tabs.setCurrentWidget(self.window.notes)
        self.window.notes.new_note()

    def new_task(self, issue: bool) -> None:
        self.window.tabs.setCurrentWidget(self.window.tasks)
        self.window.tasks.new_item(issue)

    def rename_document(self, identifier: str) -> None:
        window = self.window
        record = window.project.catalog.get(identifier)
        title, accepted = QInputDialog.getText(window, "Dokument umbenennen", "Name",
                                               text=record.title)
        if not accepted or not window.prepare_content_change():
            return

        def rename() -> None:
            current = window.project.catalog.get(identifier)
            window.documents.service.rename(identifier, title, current.revision_no)
            if window.documents.current:
                window.documents.refresh_documents(window.documents.current.id)
            window.refresh()

        window.perform(rename)
