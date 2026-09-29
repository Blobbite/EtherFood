"""Unified library and editors for scripts, packages, reusable flows and Python environments."""

from copy import deepcopy
import json
from pathlib import Path
import sys

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from ..application.pipeline_service import PipelineService
from ..application.commands import Command, Commands
from ..application.tool_exchange import ToolExchange
from ..application.tool_packages import ToolPackageService
from ..application.workflow_migration import WorkflowMigration
from ..domain.models import StudioError, new_id
from ..domain.tool_contract import empty_workflow, operation, package_manifests, resolve_local
from ..storage.tool_archives import read_archive, read_json
from .common import button, label, show_error
from .pipeline_editor import PipelineEditor
from .tool_editor import ToolEditor


class ProcessingDialog(QDialog):
    """Keep draft saves and worker lifetimes safe when opened from an asset."""

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Verarbeitung · Ablaufeditor")
        self.resize(1450, 900)
        self.workspace = ProcessingWorkspace(project, self)
        QVBoxLayout(self).addWidget(self.workspace)

    def reject(self):
        if self.workspace.leave():
            super().reject()

    def closeEvent(self, event):
        event.ignore()
        self.reject()


class ProcessingWorkspace(QWidget):
    changed = Signal()

    def __init__(self, project, parent=None, *, commands=None):
        super().__init__(parent)
        self.setObjectName("processing_workspace")
        self.project, self.service = project, ToolPackageService(project)
        self.commands = commands or Commands(project)
        WorkflowMigration(project).ensure()
        self.current = None
        self.history = []
        self.navigating_back = False
        layout = QVBoxLayout(self)
        actions = QHBoxLayout()
        actions.addWidget(button("Bibliothek", "workflow_home", self.home))
        actions.addWidget(button("Zurück", "workflow_back", self.back))
        for title, name, call in (
            ("Neuer Ablauf", "workflow_new", self.new_workflow),
            ("Neuer Python-Baustein", "workflow_new_script", self.new_script),
            ("Importieren", "workflow_import", self.import_package),
            ("Exportieren", "workflow_export", self.export_selected),
            ("Bibliothek aktualisieren", "workflow_refresh", self.refresh),
        ):
            actions.addWidget(button(title, name, call))
        layout.addLayout(actions)
        self.breadcrumb = label("Verarbeitung · Bibliothek", "workflow_breadcrumb")
        layout.addWidget(self.breadcrumb)
        split = QSplitter()
        library = QWidget()
        self.library_panel = library
        library_layout = QVBoxLayout(library)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Bausteine, Pakete und Abläufe suchen …")
        self.search.textChanged.connect(self.filter)
        library_layout.addWidget(self.search)
        self.library = QTreeWidget()
        self.library.setObjectName("workflow_library")
        self.library.setHeaderLabels(["Bibliothek", "Version"])
        self.library.setColumnWidth(0, 260)
        self.library.header().setStretchLastSection(False)
        self.library.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.library.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        library.setMinimumWidth(300)
        self.library.itemClicked.connect(self.describe)
        self.library.itemDoubleClicked.connect(self.open_item)
        library_layout.addWidget(self.library, 1)
        library_layout.addWidget(
            label(
                "Klick: Beschreibung · Doppelklick: öffnen\n"
                "Pakete enthalten Bausteine und Abläufe. "
                "Bausteine werden im Ablaufcanvas verbunden."
            )
        )
        split.addWidget(library)
        self.pages = QStackedWidget()
        self.welcome = QPlainTextEdit()
        self.welcome.setReadOnly(True)
        self.pages.addWidget(self.welcome)
        split.addWidget(self.pages)
        split.setSizes([320, 1050])
        layout.addWidget(split, 1)
        self.description = label("", "workflow_library_description")
        layout.addWidget(self.description)
        self.refresh()

    @property
    def busy(self):
        return isinstance(self.current, ToolEditor) and self.current.worker is not None

    def safe(self, call):
        try:
            return call()
        except (StudioError, OSError, ValueError, KeyError, TypeError) as error:
            show_error(self, error)
            return None

    def refresh(self):
        WorkflowMigration(self.project).ensure()
        selected = (
            self.library.currentItem().data(0, Qt.UserRole) if self.library.currentItem() else None
        )
        self.library.clear()
        scripts = QTreeWidgetItem(self.library, ["Skriptbausteine"])
        packages = QTreeWidgetItem(self.library, ["Werkzeugpakete"])
        flows = QTreeWidgetItem(self.library, ["Abläufe"])
        for package in self.service.packages():
            manifest, digest = package["manifest"], package["digest"]
            item = QTreeWidgetItem(packages, [manifest["name"], manifest["version"]])
            item.setData(0, Qt.UserRole, ("package", digest, None))
            for entry in manifest["steps"]:
                child = QTreeWidgetItem(scripts, [entry["name"], manifest["version"]])
                child.setToolTip(0, manifest["name"] + "\n" + entry["description"])
                child.setData(0, Qt.UserRole, ("tool", digest, entry["id"]))
                nested = QTreeWidgetItem(item, [entry["name"], "Python"])
                nested.setData(0, Qt.UserRole, ("tool", digest, entry["id"]))
            for entry in manifest["flows"]:
                child = QTreeWidgetItem(item, [entry["name"], "Teilablauf"])
                child.setData(0, Qt.UserRole, ("flow", digest, entry["id"]))
        for recipe in PipelineService(self.project).recipes():
            item = QTreeWidgetItem(flows, [recipe.title, "Projekt"])
            item.setData(0, Qt.UserRole, ("recipe", recipe.id, None))
        for group in (scripts, packages, flows):
            group.setExpanded(True)
        self.filter(self.search.text())
        self.welcome.setPlainText(
            "Ablaufeditor\n\n1. Ablauf anlegen oder einen Paketablauf öffnen.\n"
            "2. Assets einblenden und kleine Python-Bausteine verbinden.\n"
            "3. Ausgabeordner in den Eigenschaften festlegen.\n"
            "4. Paketdateien prüfen, Python-Umgebung einrichten und Code freigeben.\n"
            "5. Ablauf prüfen und ausführen.\n\n"
            "Ein Werkzeugpaket wird einmal importiert und kann in mehreren Abläufen "
            "verwendet werden. Doppelklick auf einen Baustein öffnet seinen Python-Entwurf; "
            "Teilabläufe öffnen ihren Canvas."
        )
        self.changed.emit()

    def filter(self, text):
        def match(item):
            children = [match(item.child(i)) for i in range(item.childCount())]
            visible = (
                not text
                or text.casefold() in (item.text(0) + item.toolTip(0)).casefold()
                or any(children)
            )
            item.setHidden(not visible)
            return visible

        for index in range(self.library.topLevelItemCount()):
            match(self.library.topLevelItem(index))

    def describe(self, item, column=0):
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        kind, identifier, entry = data
        if kind == "recipe":
            record = PipelineService(self.project).recipe(identifier)
            self.description.setText(
                record.title + " · " + str(len(record.data["recipe"]["steps"])) + " Schritte"
            )
            return
        package = self.service.details(identifier)
        manifest = package["manifest"]
        errors = self.service.diagnostics(identifier)
        description = manifest["description"]
        if entry:
            spec = next(
                value for value in manifest["steps"] + manifest["flows"] if value["id"] == entry
            )
            description = spec["description"]
        self.description.setText(
            description
            + "\nPython "
            + manifest["python"]
            + " · "
            + (", ".join(manifest["dependencies"]) or "Standardbibliothek")
            + "\n"
            + ("; ".join(issue["message"] for issue in errors) or "Paket und Umgebung bereit")
        )

    def leave(self):
        if self.busy:
            self.description.setText("Den laufenden Test zuerst abschließen oder abbrechen.")
            return False
        if isinstance(self.current, (ToolEditor, PipelineEditor)):
            return self.current.save()
        return True

    def display(self, widget, breadcrumb):
        old = self.current
        self.current = widget
        self.pages.addWidget(widget)
        self.pages.setCurrentWidget(widget)
        self.library_panel.setVisible(not isinstance(widget, PipelineEditor))
        self.breadcrumb.setText("Verarbeitung / " + breadcrumb)
        if old:
            self.pages.removeWidget(old)
            old.deleteLater()

    def open_item(self, item, column=0):
        data = item.data(0, Qt.UserRole)
        if data:
            self.open(*data)

    def open(self, kind, identifier, entry=None):
        if not self.leave():
            return

        def show():
            if kind == "recipe":
                editor = PipelineEditor(self.project, identifier, self, commands=self.commands)
                editor.setWindowFlags(Qt.Widget)
                editor.entry_open_requested.connect(self.open_operation)
                editor.saved.connect(self.refresh)
                self.display(editor, editor.record.title)
            elif kind == "flow":
                self.open_flow(identifier, entry)
            else:
                manifest = self.service.details(identifier)["manifest"]
                source = next(
                    (step["source"] for step in manifest["steps"] if step["id"] == entry), None
                )
                editor = ToolEditor(self.project, identifier, self, source=source)
                editor.changed.connect(self.refresh)
                editor.flow_requested.connect(
                    lambda digest, entry: self.open("flow", digest, entry)
                )
                self.display(
                    editor, manifest["name"] + (" / " + entry if entry else " / Paketdateien")
                )
            value = (kind, identifier, entry)
            if not self.navigating_back and (not self.history or self.history[-1] != value):
                self.history.append(value)

        self.safe(show)

    def home(self):
        if self.leave():
            self.library_panel.show()
            self.pages.setCurrentWidget(self.welcome)
            self.breadcrumb.setText("Verarbeitung / Bibliothek")

    def back(self):
        if len(self.history) < 2:
            self.home()
            return
        if not self.leave():
            return
        self.history.pop()
        self.navigating_back = True
        try:
            self.open(*self.history[-1])
        finally:
            self.navigating_back = False

    def open_operation(self, value):
        kind, digest, entry = value.split(":", 2)
        self.open(kind, digest, entry)

    def open_flow(self, digest, entry):
        draft_id = self.project.catalog.db.execute(
            "SELECT id FROM tool_drafts WHERE base_digest=? ORDER BY rowid DESC LIMIT 1", (digest,)
        ).fetchone()
        draft = self.service.load_draft(draft_id[0]) if draft_id else self.service.draft(digest)
        flow = next(flow for flow in draft["manifest"]["flows"] if flow["id"] == entry)
        recipe = resolve_local(flow["recipe"], digest)

        def save(value):
            current = self.service.load_draft(draft["id"])
            for node in value["steps"]:
                for prefix, local in (("tool:", "local:"), ("flow:", "local-flow:")):
                    if node["operation"].startswith(prefix + digest + ":"):
                        node["operation"] = local + node["operation"].split(":")[-1]
            target = next(flow for flow in current["manifest"]["flows"] if flow["id"] == entry)
            target["recipe"] = value
            self.service.save_draft(
                current["id"], current["manifest"], current["files"], current["revision"]
            )

        editor = PipelineEditor(
            self.project,
            None,
            self,
            draft_recipe=recipe,
            draft_title=flow["name"],
            draft_save=save,
            draft_manifests=package_manifests(draft["manifest"], digest),
        )
        editor.setWindowFlags(Qt.Widget)
        editor.entry_open_requested.connect(self.open_operation)
        editor.layout().insertWidget(
            0,
            button(
                "Diesen Teilablauf als Projektablauf verwenden",
                "workflow_use_flow",
                lambda: self.use_entry(digest, entry),
            ),
        )
        self.display(editor, draft["manifest"]["name"] + " / " + flow["name"] + " / Entwurf")

    def use_entry(self, digest, entry):
        record = self.safe(lambda: self.service.create_recipe(digest, entry))
        if record:
            self.refresh()
            self.open("recipe", record.id)

    def new_workflow(self):
        name, accepted = QInputDialog.getText(self, "Neuer Ablauf", "Name")
        if accepted:
            service = PipelineService(self.project)
            identifier = self.safe(
                lambda: self.commands.create_card(
                    "pipeline",
                    name,
                    service.project_id,
                    {"project_id": service.project_id, "recipe": empty_workflow()},
                )
            )
            if identifier:
                self.refresh()
                self.open("recipe", identifier)

    def new_script(self):
        name, accepted = QInputDialog.getText(self, "Neuer Python-Baustein", "Name")
        if not accepted:
            return
        manifest = {
            "contract": "studio-tool-package-v1",
            "id": "custom-" + new_id()[:8],
            "name": name,
            "version": "1.0.0",
            "description": "Eigener Python-Baustein",
            "python": f"{sys.version_info.major}.{sys.version_info.minor}",
            "dependencies": [],
            "files": ["step.py"],
            "flows": [],
            "steps": [
                {
                    "id": "process",
                    "name": name,
                    "description": "Eine Datei verarbeiten",
                    "source": "step.py",
                    "entry_point": "run",
                    "execution": "map",
                    "capabilities": [],
                    "parameters": {},
                    "inputs": {"image": {"type": "image"}},
                    "outputs": {
                        "image": {"type": "image", "directory": "Ergebnisse/eigener-baustein"}
                    },
                }
            ],
        }
        code = (
            b"def run(context, inputs, parameters):\n"
            b"    source = inputs['image']\n"
            b"    result = context.artifact('image.png', source.type, source.metadata)\n"
            b"    result.path.write_bytes(source.path.read_bytes())\n"
            b"    return {'image': result}\n"
        )
        package = self.safe(
            lambda: self.service.register(self.service.inspect_content(manifest, {"step.py": code}))
        )
        if package:
            self.refresh()
            self.open("tool", package["digest"], "process")

    def import_package(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Werkzeugpaket, Python-Skript oder Ablauf importieren",
            "",
            "Python / Paket (*.py *.zip *.json *.canvas)",
        )
        if not path:
            return

        def inspect():
            candidate = Path(path)
            if candidate.suffix.lower() == ".json" and candidate.stat().st_size > 2 * 1024 * 1024:
                raise StudioError("validation", "Paketbeschreibung ist zu groß.")
            archive = read_archive(path) if candidate.suffix.lower() == ".zip" else {}
            document = (
                read_json(candidate.read_bytes()) if candidate.suffix.lower() == ".json" else {}
            )
            if (
                candidate.suffix.lower() == ".canvas"
                or "recipe.json" in archive
                or (document and document.get("contract") != "studio-tool-package-v1")
            ):
                self.import_legacy(candidate, document)
                return
            bundle = bool({"workflow.json", "toolkit.json"} & set(archive))
            preview = (
                ToolExchange(self.project).preview(path) if bundle else self.service.preview(path)
            )
            messages = (
                list(preview.issues) if bundle else [item["message"] for item in preview.issues]
            )
            details = (
                "\n".join(messages)
                if messages
                else "Paketdateien und Schnittstellen sind vollständig."
            )
            details += (
                "\n\nBibliotheken werden gesondert eingerichtet. "
                "Codefreigaben werden nicht importiert."
            )
            dialog = QMessageBox(
                QMessageBox.Information,
                "Importprüfung",
                details,
                QMessageBox.Ok | QMessageBox.Cancel,
                self,
            )
            description = (
                {"recipe": preview.recipe, "packages": [p.manifest for p in preview.packages]}
                if bundle
                else preview.manifest
            )
            dialog.setDetailedText(json.dumps(description, ensure_ascii=False, indent=2))
            if dialog.exec() != QMessageBox.Ok:
                return
            if bundle:
                record = ToolExchange(self.project).register(preview)
                if preview.root_package:
                    self.refresh()
                    self.open("package", record["digest"])
                    return

                def archive(value):
                    current = self.project.catalog.get(record.id)
                    if current.archived != value:
                        self.project.archive(record.id, value, current.revision_no)

                self.commands.execute(
                    Command("Ablauf importieren", lambda: archive(False), lambda: archive(True))
                )
                self.refresh()
                self.open("recipe", record.id)
            else:
                package = self.service.register(preview)
                self.refresh()
                self.open("package", package["digest"])

        self.safe(inspect)

    def import_legacy(self, path, document):
        from ..application.pipeline_exchange import PipelineExchange
        from .pipeline_exchange_dialogs import PipelineImportDialog, PluginPackageImportDialog

        if document.get("contract") == "studio-python-step-v2":
            dialog = PluginPackageImportDialog(self.project, path, self)
        else:
            preview = PipelineExchange(self.project).preview(path)
            dialog = PipelineImportDialog(self.project, preview, self)
        if dialog.exec() == QDialog.Accepted and dialog.record:
            self.refresh()
            self.open("recipe", dialog.record.id)
        dialog.deleteLater()

    def export_selected(self):
        item = self.library.currentItem()
        data = (
            self.history[-1]
            if self.current and self.history
            else (item.data(0, Qt.UserRole) if item else None)
        )
        if not data:
            self.description.setText("Zuerst ein Paket oder einen Ablauf auswählen.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export mit Paketdateien", "werkzeuge.zip", "ZIP (*.zip)"
        )
        if path:
            self.safe(
                lambda: (
                    ToolExchange(self.project).export(data[1], path)
                    if data[0] == "recipe"
                    else ToolExchange(self.project).export_package(data[1], path)
                )
            )
