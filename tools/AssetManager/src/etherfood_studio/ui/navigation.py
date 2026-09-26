"""Context actions reuse the same services and unsaved-change guards as the main UI."""

from typing import TYPE_CHECKING, Callable

from PySide6.QtCore import QPoint, Qt
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
        card = self.window.canvas.card_at(self.window.canvas.mapToScene(point))
        if card:
            menu = self.menu(card.identifier)
            menu.exec(self.window.canvas.viewport().mapToGlobal(point))
            menu.deleteLater()

    def _on_card(self, identifier: str, call: Callable) -> None:
        if self.window.select_card(identifier):
            call()

    def menu(self, identifier: str) -> QMenu:
        window = self.window
        record = window.project.catalog.get(identifier)
        menu = QMenu(window)

        def action(title: str, name: str, kind: str, call: Callable) -> None:
            item = menu.addAction(kind_icon(kind), title)
            item.setObjectName(name)
            item.triggered.connect(call)

        if record.kind in {"document", "task", "issue"}:
            action("Öffnen / Bearbeiten", "context_edit", record.kind,
                   lambda: window.open_content(identifier, edit=True))
            if record.kind == "document" and record.data["document_type"] == "manual":
                action("Umbenennen …", "context_rename", "document",
                       lambda: self.rename_document(identifier))
            return menu
        action("Dokumente / Notiz öffnen", "context_open", "document",
               lambda: self._on_card(identifier, self.open_notes))
        if not record.archived:
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
            action("Hierarchie umordnen …", "context_reparent", record.kind,
                   lambda: self._on_card(identifier, self.reparent))
            action("Wiederherstellen" if record.archived else "Archivieren …",
                   "context_archive", record.kind,
                   lambda: self._on_card(identifier, window.archive_dialog))
        return menu

    def open_notes(self) -> None:
        self.window.tabs.setCurrentWidget(self.window.documents)
        if not self.window.documents.current:
            self.window.documents.new_document()

    def new_note(self) -> None:
        self.window.tabs.setCurrentWidget(self.window.documents)
        self.window.documents.new_document()

    def new_task(self, issue: bool) -> None:
        self.window.tabs.setCurrentWidget(self.window.tasks)
        self.window.tasks.new_item(issue)

    def rename_document(self, identifier: str) -> None:
        window = self.window
        record = window.project.catalog.get(identifier)
        title, accepted = QInputDialog.getText(window, "Dokument umbenennen", "Name",
                                               text=record.title)
        if not accepted or not window.documents.confirm_discard():
            return

        def rename() -> None:
            current = window.project.catalog.get(identifier)
            window.documents.service.rename(identifier, title, current.revision_no)
            if window.documents.current:
                window.documents.refresh_documents(window.documents.current.id)
            window.refresh()

        window.perform(rename)

    def reparent(self) -> None:
        window = self.window
        record = window.project.catalog.get(window.selected_id)
        choices = {window.project.breadcrumb(card.id): card.id for card in window.project.cards()
                   if card.kind in PARENTS[record.kind] and card.id != record.id}
        if not choices:
            return
        choice, accepted = QInputDialog.getItem(window, "Hierarchie umordnen", "Neuer Elternort",
                                               list(choices), 0, False)
        if accepted and window.perform(lambda: window.commands.move(record.id, choices[choice])):
            window.refresh()
