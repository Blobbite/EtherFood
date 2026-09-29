"""Shared tool structure, traffic-light overview and persistent Python/pipeline editors."""

from pathlib import Path

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..application.lifecycle_service import LifecycleService
from ..application.pipeline_workspace import PipelineWorkspace as WorkspaceService
from ..application.workspace_files import SCRIPT_ROOT
from ..domain.models import StudioError, new_id
from .common import button, label, show_error
from .definition_editor import DefinitionEditor, SCRIPT_MIME
from .pipeline_controller import PipelineController
from .presentation import kind_icon
from .script_workspace import ScriptWorkspace
from .workspace_search import WorkspaceSearch


class ToolTree(QTreeWidget):
    file_moved = Signal(str, str)

    def __init__(self, workspace):
        super().__init__()
        self.workspace = workspace
        self.token = new_id()
        self.setObjectName("tools_structure")
        self.setHeaderLabel("Skripte & Pipelines")
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)

    def startDrag(self, supported):
        item = self.currentItem()
        data = item.data(0, Qt.UserRole) if item else None
        mime = self.drag_mime(data)
        if mime is None:
            return
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.CopyAction | Qt.MoveAction, Qt.MoveAction)

    def drag_mime(self, data):
        if not data or data[0] not in {"script", "folder", "pipeline_definition"}:
            return None
        mime = QMimeData()
        mime.setData("application/x-etherfood-tool-tree", self.token.encode())
        if data[0] == "pipeline_definition":
            mime.setData("application/x-etherfood-definition", data[1].encode())
            return mime
        if data[0] == "script":
            mime.setData(SCRIPT_MIME, data[1].encode())
            path = (
                self.workspace.project.catalog.get(data[1]).data["path"].removeprefix(SCRIPT_ROOT)
            )
        else:
            path = data[1]
        mime.setData("application/x-etherfood-tool-path", path.encode())
        return mime

    def dragEnterEvent(self, event):
        if bytes(event.mimeData().data("application/x-etherfood-tool-tree")) == self.token.encode():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        item = self.itemAt(event.position().toPoint())
        data = item.data(0, Qt.UserRole) if item else None
        if data and (data[0] == "folder" or data == ("group", "pipelines")):
            self.dragEnterEvent(event)
        else:
            event.ignore()

    def dropEvent(self, event):
        item = self.itemAt(event.position().toPoint())
        data = item.data(0, Qt.UserRole) if item else None
        if bytes(event.mimeData().data("application/x-etherfood-tool-tree")) != self.token.encode():
            event.ignore()
            return
        if data == ("group", "pipelines") and event.mimeData().hasFormat(
            "application/x-etherfood-definition"
        ):
            identifier = bytes(event.mimeData().data("application/x-etherfood-definition")).decode()
            record = self.workspace.project.catalog.get(identifier)
            if record.kind == "pipeline_definition" and LifecycleService(
                self.workspace.project
            ).state(identifier):
                self.workspace.restore(identifier)
                event.acceptProposedAction()
                return
        if (
            data
            and data[0] == "folder"
            and event.mimeData().hasFormat("application/x-etherfood-tool-path")
        ):
            old = bytes(event.mimeData().data("application/x-etherfood-tool-path")).decode()
            new = "/".join(v for v in (data[1], Path(old).name) if v)
            self.file_moved.emit(old, new)
            event.acceptProposedAction()
        else:
            event.ignore()


class PipelineWorkspace(QWidget):
    changed = Signal()
    section_requested = Signal(int)

    def __init__(self, project, parent=None, *, commands):
        super().__init__(parent)
        self.project, self.commands = project, commands
        self.service = WorkspaceService(project)
        self.controller = PipelineController(project, self)
        self.controller.changed.connect(self.refresh_overview)
        self.controller.checked.connect(self.check_finished)
        self.controller.event.connect(self.run_event)
        self.structure = QWidget()
        structure = QVBoxLayout(self.structure)
        structure.setContentsMargins(0, 0, 0, 0)
        self.name = QLineEdit()
        self.name.setObjectName("new_tool_name")
        self.name.setPlaceholderText("Name für Pipeline, Skript oder Ordner")
        structure.addWidget(self.name)
        row = QHBoxLayout()
        for text, name, call in (
            ("+ Pipeline", "new_pipeline", self.create_pipeline),
            ("+ Skript", "new_script", self.create_script),
            ("+ Ordner", "new_script_folder", self.create_folder),
        ):
            row.addWidget(button(text, name, call))
        structure.addLayout(row)
        self.tree = ToolTree(self)
        self.tree.itemDoubleClicked.connect(self.activate)
        self.tree.file_moved.connect(self.move_file)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.context_menu)
        structure.addWidget(self.tree, 1)
        self.storage_state = QComboBox()
        self.storage_state.setObjectName("tools_storage")
        for text, value in (
            ("Ablage: Archiv", "archived"),
            ("Ablage: Papierkorb · 30 Tage", "trash"),
        ):
            self.storage_state.addItem(text, value)
        self.storage_state.currentIndexChanged.connect(self.refresh_tree)
        structure.addWidget(self.storage_state)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.pages = QStackedWidget()
        self.pipeline_pages = QStackedWidget()
        overview = QWidget()
        overview_layout = QVBoxLayout(overview)
        actions = QGridLayout()
        for index, (text, name, call) in enumerate(
            (
                ("Neue Pipeline", "pipeline_create", self.create_pipeline),
                ("Bearbeiten", "pipeline_edit", self.edit_selected),
                ("Prüfen", "pipeline_check_selected", self.check_selected),
                ("Freigeben", "pipeline_approve", self.approve_selected),
                ("Automatik pausieren/fortsetzen", "pipeline_pause", self.pause_selected),
            )
        ):
            actions.addWidget(button(text, name, call), index // 2, index % 2)
        overview_layout.addLayout(actions)
        self.overview = QTableWidget(0, 4)
        self.overview.setObjectName("pipeline_traffic_overview")
        self.overview.setHorizontalHeaderLabels(
            ["Status", "Pipeline", "Verwendungen", "Aktueller Stand"]
        )
        self.overview.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.overview.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.overview.horizontalHeader().setStretchLastSection(True)
        for column, width in enumerate((165, 235, 100, 200)):
            self.overview.setColumnWidth(column, width)
        self.overview.cellDoubleClicked.connect(lambda row, col: self.edit_selected())
        self.overview.itemSelectionChanged.connect(self.show_details)
        overview_layout.addWidget(self.overview, 1)
        bottom = QGridLayout()
        for index, (text, name, call) in enumerate(
            (
                ("Aktualisieren", "pipeline_refresh", self.controller.schedule),
                ("Erneut versuchen", "pipeline_retry", self.retry_selected),
                ("Durchgang abbrechen", "pipeline_cancel", self.controller.cancel),
                ("Importieren …", "tools_import", self.import_files),
                ("Exportieren …", "tools_export", self.export_selected),
            )
        ):
            bottom.addWidget(button(text, name, call), index // 2, index % 2)
        overview_layout.addLayout(bottom)
        self.details = QPlainTextEdit()
        self.details.setObjectName("pipeline_check_details")
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(130)
        self.details.hide()
        overview_layout.addWidget(self.details)
        self.pipeline_pages.addWidget(overview)
        self.editor = DefinitionEditor(project)
        self.editor.changed.connect(self.content_changed)
        self.editor.overview_requested.connect(lambda: self.pipeline_pages.setCurrentIndex(0))
        self.editor.script_requested.connect(self.open_script)
        self.editor.check_requested.connect(self.controller.check)
        self.pipeline_pages.addWidget(self.editor)
        self.pages.addWidget(self.pipeline_pages)
        self.python = ScriptWorkspace(project)
        self.python.changed.connect(self.content_changed)
        self.python.test_requested.connect(self.test_script)
        self.python.environment_requested.connect(self.prepare_environment)
        self.pages.addWidget(self.python)
        self.search = WorkspaceSearch("tools")
        self.search.bind(project)
        self.search.open_requested.connect(
            lambda hit: (
                self.open_script(hit.id) if hit.kind == "script" else self.open_definition(hit.id)
            )
        )
        self.pages.addWidget(self.search)
        layout.addWidget(self.pages)
        self.rows = []
        from .appearance import appearance

        appearance().changed.connect(self.refresh_overview)
        self.refresh()

    @property
    def busy(self):
        return self.controller.busy

    def set_section(self, index):
        self.pages.setCurrentIndex(index)
        self.refresh_tree()
        if index == 2:
            self.search.refresh()

    def confirm_discard(self):
        return self.python.confirm_discard() and self.editor.confirm_discard()

    def safe(self, call):
        try:
            return call()
        except (StudioError, OSError, ValueError) as error:
            show_error(self, error)
            return None

    def refresh(self):
        self.refresh_tree()
        self.refresh_overview()

    def refresh_tree(self):
        from ..application.search_service import SearchService

        selected = self.tree.currentItem()
        selected = selected.data(0, Qt.UserRole) if selected else None
        old_items = self.tree.findItems("", Qt.MatchContains | Qt.MatchRecursive)
        expanded = {str(i.data(0, Qt.UserRole)) for i in old_items if i.isExpanded()}
        scroll = self.tree.verticalScrollBar().value()
        self.tree.clear()
        state = self.storage_state.currentData()
        search = SearchService(self.project)
        if self.pages.currentIndex() != 1:
            definitions = self.tree_item(None, "Pipelines", ("group", "pipelines"), "pipeline")
            for record in self.service.definitions():
                self.tree_item(
                    definitions, record.title, ("pipeline_definition", record.id), "pipeline"
                )
        if self.pages.currentIndex() == 0:
            base = self.tree_item(None, "Programmbausteine", ("group", "base"), "package")
            for text, value in (("Eingabe", "input"), ("Ausgabe / Folder", "folder")):
                self.tree_item(base, text, ("builtin", value), "package")
            self.tree_item(None, "Weitere Bausteine", ("group", "additional"), "package")
        own = self.tree_item(None, "Eigene Skripte", ("folder", ""), "script")
        folders = {"": own}
        root = self.project.catalog.path.parent / SCRIPT_ROOT
        if root.is_dir():
            for path in sorted(root.rglob("*")):
                if (
                    path.is_dir()
                    and not path.is_symlink()
                    and not any(
                        p.startswith(".") or p == "__pycache__"
                        for p in path.relative_to(root).parts
                    )
                ):
                    relative = path.relative_to(root).as_posix()
                    parent = str(Path(relative).parent)
                    folders[relative] = self.tree_item(
                        folders.get("" if parent == "." else parent, own),
                        path.name,
                        ("folder", relative),
                        "package",
                    )
        shown_helpers = set()
        for record in self.service.scripts():
            path = Path(record.data["path"].removeprefix(SCRIPT_ROOT))
            parent = "" if str(path.parent) == "." else path.parent.as_posix()
            item = self.tree_item(
                folders.get(parent, own), record.title, ("script", record.id), "script"
            )
            item.setToolTip(0, record.data["path"])
            for helper in record.data.get("helpers", []):
                if helper in shown_helpers:
                    continue
                shown_helpers.add(helper)
                helper_path = Path(helper)
                helper_parent = (
                    "" if str(helper_path.parent) == "." else helper_path.parent.as_posix()
                )
                self.tree_item(
                    folders.get(helper_parent, own),
                    helper_path.name,
                    ("helper", (record.id, helper)),
                    "script",
                )
            if selected == ("script", record.id):
                self.tree.setCurrentItem(item)
        storage = self.tree_item(
            None,
            "Archiv" if state == "archived" else "Papierkorb · 30 Tage",
            ("group", "storage"),
            "package",
        )
        for record in self.service.definitions(include_archived=True) + self.service.scripts(
            include_archived=True
        ):
            if search.state(record) == state and (
                self.pages.currentIndex() != 1 or record.kind == "script"
            ):
                self.tree_item(storage, record.title, (record.kind, record.id), record.kind)
        order = self.project.catalog.layout(self.project.project().id).get("script_tree_order", {})
        for parent in folders.values():
            children = parent.takeChildren()
            children.sort(
                key=lambda item: (
                    order.get(self.tree_key(item), 1_000_000),
                    item.text(0).casefold(),
                )
            )
            parent.addChildren(children)
        if not old_items:
            self.tree.expandToDepth(1)
        for item in self.tree.findItems("", Qt.MatchContains | Qt.MatchRecursive):
            if str(item.data(0, Qt.UserRole)) in expanded:
                item.setExpanded(True)
            if item.data(0, Qt.UserRole) == selected:
                self.tree.setCurrentItem(item)
        self.tree.verticalScrollBar().setValue(scroll)

    @staticmethod
    def tree_key(item):
        kind, identifier = item.data(0, Qt.UserRole)
        return kind + ":" + str(identifier)

    def reorder_tree(self, item, direction):
        parent = item.parent()
        if parent is None:
            return
        children = [parent.child(i) for i in range(parent.childCount())]
        index = children.index(item)
        target = index + direction
        if not 0 <= target < len(children):
            return
        children[index], children[target] = children[target], children[index]
        owner = self.project.project().id
        layout = self.project.catalog.layout(owner)
        order = layout.get("script_tree_order", {}).copy()
        order.update({self.tree_key(child): i for i, child in enumerate(children)})
        self.commands.layout(owner, layout | {"script_tree_order": order})
        self.refresh_tree()

    def tree_item(self, parent, text, data, kind):
        item = QTreeWidgetItem([text])
        item.setData(0, Qt.UserRole, data)
        item.setIcon(0, kind_icon(kind))
        parent.addChild(item) if parent else self.tree.addTopLevelItem(item)
        return item

    def refresh_overview(self):
        current = self.selected_definition()
        self.rows = self.service.definitions()
        self.overview.blockSignals(True)
        self.overview.setRowCount(len(self.rows))
        for index, record in enumerate(self.rows):
            status, reason = self.service.status(record.id)
            names = {
                "green": "● Grün · freigegeben",
                "yellow": "● Gelb · Freigabe fehlt",
                "red": "⛔ Rot · blockiert",
            }
            usages = self.service.usages(record.id)
            state = self.service.state(record.id)
            running = [
                self.controller.states[r.id] for r in usages if r.id in self.controller.states
            ]
            failures = [
                v.get("reason", "")
                for v in running
                if v.get("state") in {"failed", "blocked"}
                and v.get("reason")
                and "Freigabe" not in v.get("reason", "")
            ]
            if failures and status == "green":
                status, reason = "red", "\n".join(failures)
            text = (
                "Pausiert"
                if state["paused"]
                else "Keine aktive Verwendung" if not usages else "Wartet"
            )
            if running and not state["paused"]:
                text = "; ".join(dict.fromkeys(self.run_label(v) for v in running))
            for col, value in enumerate((names[status], record.title, str(len(usages)), text)):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, record.id)
                item.setToolTip(value + "\n" + reason)
                if col == 0:
                    from PySide6.QtGui import QColor
                    from .theme import is_dark

                    colors = {
                        "green": "#79ce91" if is_dark() else "#186936",
                        "yellow": "#e8ca5f" if is_dark() else "#806000",
                        "red": "#ff9999" if is_dark() else "#a21b22",
                    }
                    item.setForeground(QColor(colors[status]))
                self.overview.setItem(index, col, item)
            if record.id == current:
                self.overview.selectRow(index)
        self.overview.blockSignals(False)
        if self.controller.last_error:
            self.details.setPlainText(self.controller.last_error)
            self.details.show()

    @staticmethod
    def run_label(event):
        if event["state"] == "running":
            return f"Läuft {event.get('completed', 0)}/{event.get('total', '?')}"
        if event.get("reason") == "Keine passenden Eingaben.":
            return "Keine passenden Eingaben"
        return {
            "succeeded": "Aktuell",
            "current": "Aktuell",
            "blocked": "Blockiert",
            "failed": "Fehler",
            "cancelled": "Abgebrochen",
            "stale": "Veraltet",
            "paused": "Pausiert",
        }.get(event["state"], "Läuft")

    def selected_definition(self):
        row = self.overview.currentRow()
        return (
            self.overview.item(row, 1).data(Qt.UserRole)
            if row >= 0 and self.overview.item(row, 1)
            else None
        )

    def show_details(self):
        identifier = self.selected_definition()
        self.details.setVisible(bool(identifier))
        if identifier:
            status, reason = self.service.status(identifier)
            values = [reason]
            for usage in self.service.usages(identifier):
                event = self.controller.states.get(usage.id, {})
                values.append(usage.title + ": " + event.get("reason", "Noch kein Durchgang."))
            self.details.setPlainText("\n".join(values))

    def open_definition(self, identifier):
        if self.editor.open(identifier):
            self.pipeline_pages.setCurrentWidget(self.editor)
            self.section_requested.emit(0)
            self.set_section(0)
            return True
        return False

    def open_script(self, identifier):
        if self.python.open(identifier):
            self.section_requested.emit(1)
            self.set_section(1)
            return True
        return False

    def activate(self, item, column=0):
        kind, identifier = item.data(0, Qt.UserRole)
        if kind == "pipeline_definition":
            self.open_definition(identifier)
        elif kind == "script":
            self.open_script(identifier)
        elif kind == "helper":
            if self.python.open_helper(*identifier):
                self.section_requested.emit(1)
                self.set_section(1)
        elif kind == "builtin" and self.editor.current:
            if identifier == "folder":
                self.editor.add_folder()
            else:
                from ..domain.pipeline_contract import INPUT

                self.editor.select(INPUT)

    def create_pipeline(self):
        if not self.editor.confirm_discard():
            return

        def create():
            record = self.service.files.create_definition(
                self.name.text().strip() or "Neue Pipeline"
            )
            self.name.clear()
            self.content_changed()
            self.open_definition(record.id)

        self.safe(create)

    def create_script(self):
        if not self.python.confirm_discard():
            return

        def create():
            record = self.service.files.create_script(self.name.text().strip() or "Neues Skript")
            self.name.clear()
            self.content_changed()
            self.open_script(record.id)

        self.safe(create)

    def create_folder(self):
        if not self.name.text().strip():
            self.name.setPlaceholderText("Ordnername hier eingeben, dann + Ordner")
            self.name.setFocus()
            return

        def create():
            self.service.files.create_folder(self.name.text().strip())
            self.name.clear()
            self.refresh_tree()

        self.safe(create)

    def edit_selected(self):
        if self.selected_definition():
            self.open_definition(self.selected_definition())

    def check_selected(self):
        if self.selected_definition():
            if self.controller.busy:
                self.details.show()
                self.details.setPlainText("Verarbeitung läuft. Danach erneut Prüfen wählen.")
                return
            self.details.setPlainText("Prüfung läuft …")
            self.details.show()
            self.controller.check(self.selected_definition())

    def check_finished(self, identifier, result):
        self.details.show()
        if "error" in result:
            self.details.setPlainText(result["error"])
        else:
            value = result["value"]
            self.details.setPlainText(
                "\n".join(value["issues"])
                if value["issues"]
                else "Prüfung erfolgreich. Ausdrückliche Freigabe erforderlich."
            )
            if not value.get("plan"):
                self.details.appendPlainText(
                    "Keine aktive Verwendung; strukturelle Prüfung ohne Assets."
                )
            for entry in value.get("plan", []):
                usage = self.project.catalog.get(entry["usage_id"])
                rows = entry.get("inputs", [])
                counts = {
                    state: sum(r["state"] == state for r in rows)
                    for state in ("matching", "nonmatching", "invalid")
                }
                self.details.appendPlainText(
                    f"\n{usage.title}: {counts['matching']} passend, "
                    f"{counts['nonmatching']} nicht passend, {counts['invalid']} fehlerhaft."
                )
                for row in rows:
                    asset = self.project.catalog.get(row["asset_id"])
                    self.details.appendPlainText("  " + asset.title + ": " + row["reason"])
                for target in entry.get("targets", []):
                    self.details.appendPlainText(
                        "  Folder " + target["output"] + ": " + target["path"]
                    )
                self.controller.states[entry["usage_id"]] = {
                    "state": "blocked" if entry["issues"] else "waiting",
                    "reason": "\n".join(entry["issues"]) or "Plan geprüft; kein Lauf gestartet.",
                }
        self.refresh_overview()

    def approve_selected(self):
        identifier = self.selected_definition()
        if not identifier:
            return
        record = self.project.catalog.get(identifier)
        if self.controller.busy:
            self.details.show()
            self.details.setPlainText("Laufende Prüfung/Verarbeitung zuerst beenden lassen.")
            return
        if self.python.current and self.python.dirty:
            value, _ = self.service.files.definition(identifier)
            if any(n["script_id"] == self.python.current.id for n in value["nodes"]):
                self.details.show()
                self.details.setPlainText(
                    "Offenen Python-Entwurf vor der Freigabe speichern oder verwerfen."
                )
                return
        if self.editor.current and self.editor.current.id == identifier and self.editor.dirty:
            self.details.setPlainText(
                "Offenen Definitionsentwurf vor der Freigabe speichern oder verwerfen."
            )
            return
        if (
            QMessageBox.question(
                self,
                "Pipeline lokal freigeben",
                record.title + " für automatische lokale Ausführung freigeben?\n"
                "Python-Code läuft mit den Rechten dieser Anwendung; keine Sicherheits-Sandbox.",
                QMessageBox.Yes | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            != QMessageBox.Yes
        ):
            return

        def approve():
            self.service.approve(identifier, self.service.state(identifier)["checked_hash"])
            self.controller.schedule()
            self.refresh_overview()

        self.safe(approve)

    def pause_selected(self):
        identifier = self.selected_definition()
        if identifier:
            self.service.pause(identifier, not self.service.state(identifier)["paused"])
            self.controller.schedule()
            self.refresh_overview()

    def retry_selected(self):
        for usage in self.service.usages(self.selected_definition()):
            self.controller.engine.retry(usage.id)
        self.controller.schedule()

    def content_changed(self):
        self.refresh()
        self.search.refresh()
        self.controller.watch()
        self.controller.schedule()
        self.changed.emit()

    def move_file(self, source, target):
        if not self.python.confirm_discard():
            return
        from ..application.commands import Command

        lifecycle = LifecycleService(self.project)
        record = next(
            (
                r
                for r in self.service.scripts(include_archived=True)
                if r.data["path"] == SCRIPT_ROOT + source
            ),
            None,
        )
        stored = lifecycle.state(record.id) if record else None
        if stored:
            snapshot = dict(stored)

            def forward():
                lifecycle.restore(record.id)
                if source != target:
                    self.service.files.move(source, target)

            def backward():
                if source != target:
                    self.service.files.move(target, source)
                lifecycle.change([record.id], snapshot["state"])
                self.project.catalog.db.execute(
                    "UPDATE lifecycle SET removed_at=?,purge_at=?,previous=? WHERE id=?",
                    (
                        snapshot["removed_at"],
                        snapshot["purge_at"],
                        __import__("json").dumps(snapshot["previous"]),
                        record.id,
                    ),
                )

        else:

            def forward():
                self.service.files.move(source, target)

            def backward():
                self.service.files.move(target, source)

        if self.safe(
            lambda: (
                self.commands.execute(
                    Command(
                        (
                            "Skript wiederherstellen und zuordnen"
                            if stored
                            else "Skriptdateien verschieben"
                        ),
                        forward,
                        backward,
                    )
                ),
                True,
            )[1]
        ):
            if self.python.current:
                key = self.python.current.id
                self.python.current = None
                self.python.open(key)
            self.content_changed()

    def context_menu(self, point):
        item = self.tree.itemAt(point)
        if not item:
            return
        kind, identifier = item.data(0, Qt.UserRole)
        if kind == "helper":
            menu = QMenu(self)
            menu.addAction("Hilfsdatei bearbeiten", lambda: self.activate(item))
            menu.exec(self.tree.viewport().mapToGlobal(point))
            menu.deleteLater()
            return
        if kind not in {"script", "pipeline_definition", "folder"}:
            return
        menu = QMenu(self)
        if (
            kind == "folder"
            or kind == "script"
            and not LifecycleService(self.project).state(identifier)
        ):
            menu.addAction("In Struktur nach oben", lambda: self.reorder_tree(item, -1))
            menu.addAction("In Struktur nach unten", lambda: self.reorder_tree(item, 1))
        if kind in {"script", "pipeline_definition"}:
            record = self.project.catalog.get(identifier)
            menu.addAction(
                "Skript bearbeiten" if kind == "script" else "Pipeline bearbeiten",
                lambda: self.activate(item),
            )
            state = LifecycleService(self.project).state(identifier)
            if state:
                menu.addAction("Wiederherstellen", lambda: self.restore(identifier))
            else:
                menu.addAction("Archivieren", lambda: self.store(identifier, "archived"))
                menu.addAction("Entfernen", lambda: self.store(identifier, "trash"))
        if kind in {"script", "folder"}:
            source = (
                self.project.catalog.get(identifier).data["path"].removeprefix(SCRIPT_ROOT)
                if kind == "script"
                else identifier
            )
            if source:
                menu.insertAction(
                    menu.actions()[0] if menu.actions() else None,
                    menu.addAction(
                        "Umbenennen / verschieben (Name oben)",
                        lambda: (
                            self.move_file(source, self.name.text().strip())
                            if self.name.text().strip()
                            else self.name.setFocus()
                        ),
                    ),
                )
        menu.exec(self.tree.viewport().mapToGlobal(point))
        menu.deleteLater()

    def store(self, identifier, state):
        if not self.confirm_discard():
            return
        lifecycle = LifecycleService(self.project)
        impact = lifecycle.impact([identifier])[0]
        text = (
            impact["title"]
            + "\nBetroffene Verwendungen: "
            + (", ".join(impact["usages"]) or "keine")
        )
        if state == "trash":
            text += "\n30 Tage wiederherstellbar; danach endgültige Bereinigung."
        if (
            QMessageBox.warning(
                self,
                "Entfernen" if state == "trash" else "Archivieren",
                text,
                QMessageBox.Ok | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            == QMessageBox.Ok
        ):
            self.safe(lambda: lifecycle.command(self.commands, [identifier], state))
            self.content_changed()

    def restore(self, identifier):
        self.safe(lambda: LifecycleService(self.project).command(self.commands, [identifier]))
        self.content_changed()

    def run_event(self, event):
        if event["state"] == "purged":
            self.commands.done.clear()
            self.commands.undone.clear()
            self.changed.emit()
        self.refresh_overview()

    def import_files(self):
        from ..application.workspace_exchange import WorkspaceExchange

        path, _ = QFileDialog.getOpenFileName(
            self, "Skript / Pipeline importieren", "", "Python oder Studio-Bündel (*.py *.zip)"
        )
        if path:
            self.safe(lambda: WorkspaceExchange(self.project).import_file(Path(path)))
            self.content_changed()

    def export_selected(self):
        from ..application.workspace_exchange import WorkspaceExchange

        identifier = self.selected_definition()
        item = self.tree.currentItem()
        if not identifier and item and item.data(0, Qt.UserRole)[0] == "script":
            identifier = item.data(0, Qt.UserRole)[1]
        if not identifier:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Vollständiges Werkzeugbündel exportieren", "pipeline.zip", "ZIP (*.zip)"
        )
        if path:
            self.safe(lambda: WorkspaceExchange(self.project).export(identifier, Path(path)))

    def prepare_environment(self, identifier):
        from ..application.tool_environments import ToolEnvironments

        record = self.project.catalog.get(identifier)
        if (
            QMessageBox.question(
                self,
                "Bibliotheken einrichten",
                ", ".join(record.data["dependencies"])
                + "\nIn getrennter projektlokaler Python-Umgebung einrichten?",
                QMessageBox.Yes | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            != QMessageBox.Yes
        ):
            return
        self.controller._start(
            lambda emit: ToolEnvironments(self.project).prepare(
                record.data, on_output=lambda text: emit({"state": "environment", "message": text})
            ),
            lambda result: self.python.diagnostics.setPlainText(
                result.get("error", "Umgebung geprüft.")
            ),
        )

    def test_script(self, identifier):
        from ..application.pipeline_tests import test_script, script_test_plan

        plan = self.safe(lambda: script_test_plan(self.project, identifier))
        if not plan:
            return
        inputs = "\n".join(
            (self.project.catalog.get(row["asset_id"]).title if row["asset_id"] else "Ohne Asset")
            + " · "
            + row["source_key"]
            for row in plan["rows"]
        )
        if (
            QMessageBox.question(
                self,
                "Ausdrücklicher Skripttest",
                "Gespeicherten Code mit passenden registrierten Eingaben lokal testen?\n"
                "Es werden keine produktiven Ergebnisse veröffentlicht.\n" + inputs,
                QMessageBox.Yes | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            != QMessageBox.Yes
        ):
            return
        self.controller._start(
            lambda emit: test_script(
                self.project, identifier, self.controller.engine, emit, plan=plan
            ),
            lambda result: self.python.diagnostics.setPlainText(
                result.get("error", str(result.get("value", "Test beendet.")))
            ),
        )
