"""Package files, editable drafts, diagnostics, environments and explicit code versions."""

from copy import deepcopy
import difflib
import ast
import json

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..application.tool_environments import ToolEnvironments
from ..application.tool_packages import ToolPackageService
from ..domain.models import StudioError
from .common import button, label, show_error
from .python_editor import PythonEditor


class WorkThread(QThread):
    result = Signal(object, object)
    progress = Signal(str)

    def __init__(self, call, parent=None):
        super().__init__(parent)
        self.call = call

    def run(self):
        try:
            self.result.emit(self.call(self), None)
        except Exception as error:
            self.result.emit(None, str(error))


class ToolEditor(QWidget):
    changed = Signal()
    flow_requested = Signal(str, str)

    def __init__(self, project, digest, parent=None, *, source=None):
        super().__init__(parent)
        self.project, self.service, self.digest = project, ToolPackageService(project), digest
        previous = project.catalog.db.execute(
            "SELECT id FROM tool_drafts WHERE base_digest=? ORDER BY rowid DESC LIMIT 1", (digest,)
        ).fetchone()
        self.draft = (
            self.service.load_draft(previous[0]) if previous else self.service.draft(digest)
        )
        self.files = dict(self.draft["files"])
        self.files["manifest.json"] = (
            json.dumps(self.draft["manifest"], ensure_ascii=False, indent=2) + "\n"
        ).encode()
        self.current_file, self.worker = None, None
        self.base = {
            **self.service.contents(digest),
            "manifest.json": (
                json.dumps(self.service.details(digest)["manifest"], ensure_ascii=False, indent=2)
                + "\n"
            ).encode(),
        }
        layout = QVBoxLayout(self)
        package = self.draft["manifest"]
        layout.addWidget(
            label(
                package["name"] + " · " + package["version"] + " · Entwurf\n"
                "Verwendete Abläufe behalten ihre Paketversion. "
                "Änderungen werden als neue Version übernommen."
            )
        )
        actions = QHBoxLayout()
        for text, name, call in (
            ("Entwurf speichern", "tool_save", self.save),
            ("Prüfen", "tool_check", self.check),
            ("Neue Datei", "tool_add_file", self.add_file),
            ("Neue Version übernehmen", "tool_publish", self.publish),
            ("Fehlerkontext kopieren", "tool_ai_context", self.copy_context),
        ):
            actions.addWidget(button(text, name, call))
        layout.addLayout(actions)
        compose = QHBoxLayout()
        compose.addWidget(
            button("+ Skriptbaustein", "tool_add_step", lambda: self.add_entry(False))
        )
        compose.addWidget(button("+ Teilablauf", "tool_add_flow", lambda: self.add_entry(True)))
        compose.addStretch()
        layout.addLayout(compose)
        splitter = QSplitter()
        self.file_list = QListWidget()
        self.file_list.setObjectName("tool_files")
        self.file_list.currentTextChanged.connect(self.open_file)
        for name in sorted(set(package["files"]) | set(self.files)):
            self.file_list.addItem(name)
        splitter.addWidget(self.file_list)
        self.tabs = QTabWidget()
        self.code = PythonEditor()
        self.diff = QPlainTextEdit()
        self.diff.setReadOnly(True)
        self.tabs.addTab(self.code, "Datei / Python")
        self.tabs.addTab(self.diff, "Vergleich mit Paketversion")
        self.tabs.currentChanged.connect(lambda: self.refresh_diff())
        splitter.addWidget(self.tabs)
        splitter.setSizes([230, 850])
        layout.addWidget(splitter, 1)
        self.entries = QComboBox()
        self.entries.setObjectName("tool_entry")
        for entry in package["steps"]:
            self.entries.addItem(entry["name"], entry["id"])
        for entry in package["flows"]:
            self.entries.addItem(entry["name"] + " · Ablauf", entry["id"])
        self.assets = QComboBox()
        for asset in project.cards():
            if asset.kind == "asset" and "asset_definition" in asset.data:
                self.assets.addItem(asset.title, asset.id)
        row = QHBoxLayout()
        self.setup_button = button(
            "Umgebung einrichten / reparieren", "tool_environment_prepare", self.prepare_environment
        )
        row.addWidget(self.setup_button)
        row.addWidget(button("Paketversion freigeben", "tool_approve", self.approve))
        row.addWidget(self.entries)
        row.addWidget(self.assets)
        self.test_button = button("Entwurf testen", "tool_test", self.test)
        row.addWidget(self.test_button)
        self.cancel_button = button("Abbrechen", "tool_test_cancel", self.cancel)
        self.cancel_button.setEnabled(False)
        row.addWidget(self.cancel_button)
        layout.addLayout(row)
        self.diagnostics = QPlainTextEdit()
        self.diagnostics.setObjectName("tool_diagnostics")
        self.diagnostics.setReadOnly(True)
        self.diagnostics.setMaximumHeight(190)
        layout.addWidget(self.diagnostics)
        self.file_list.setCurrentRow(
            next(
                (
                    i
                    for i in range(self.file_list.count())
                    if self.file_list.item(i).text() == source
                ),
                0,
            )
        )
        self.check()

    def safe(self, call):
        try:
            return call()
        except (StudioError, OSError, ValueError, KeyError, TypeError) as error:
            self.diagnostics.setPlainText(str(error))
            return None

    def capture(self):
        if self.current_file and not self.code.isReadOnly():
            self.files[self.current_file] = self.code.toPlainText().encode("utf-8")

    def open_file(self, name):
        self.capture()
        self.current_file = name
        try:
            text = self.files.get(name, b"").decode("utf-8")
            self.code.setReadOnly(False)
        except UnicodeError:
            text = "Binäre Hilfsdatei · bleibt unverändert im Paket."
            self.code.setReadOnly(True)
        self.code.setPlainText(text)
        if hasattr(self, "entries"):
            for entry in self.draft["manifest"]["steps"]:
                if entry["source"] == name:
                    self.entries.setCurrentIndex(self.entries.findData(entry["id"]))
                    break
        self.refresh_diff()

    def values(self):
        self.capture()
        manifest = json.loads(self.files["manifest.json"])
        return manifest, {k: v for k, v in self.files.items() if k != "manifest.json"}

    def save(self):
        def write():
            manifest, files = self.values()
            self.draft = self.service.save_draft(
                self.draft["id"], manifest, files, self.draft["revision"]
            )
            self.diagnostics.setPlainText(
                "Entwurf gespeichert · Revision " + str(self.draft["revision"])
            )
            return True

        return bool(self.safe(write))

    def check(self):
        def inspect():
            manifest, files = self.values()
            preview = self.service.inspect_content(manifest, files)
            environments = ToolEnvironments(self.project)
            missing = environments.diagnostics(manifest)
            issues = list(preview.issues) + missing
            if not missing:
                issues += environments.import_diagnostics(manifest, files)
            messages = [
                f"{issue.get('path', '')}:{issue.get('line', '')} {issue['message']}"
                for issue in issues
            ]
            messages += [
                "Bibliotheken: "
                + (", ".join(manifest["dependencies"]) or "Python-Standardbibliothek"),
                "Python " + manifest["python"] + " · " + str(len(files)) + " Paketdateien",
            ]
            imports = set()
            for name, raw in files.items():
                if not name.endswith(".py"):
                    continue
                try:
                    for node in ast.walk(ast.parse(raw)):
                        if isinstance(node, ast.Import):
                            imports.update(alias.name.split(".")[0] for alias in node.names)
                        elif isinstance(node, ast.ImportFrom) and node.module:
                            imports.add(node.module.split(".")[0])
                except (SyntaxError, UnicodeError, ValueError):
                    pass
            messages.append("Verwendete Imports: " + (", ".join(sorted(imports)) or "keine"))
            self.diagnostics.setPlainText(
                "\n".join(messages)
                if issues
                else "Schnittstelle und Syntax gültig.\n" + "\n".join(messages)
            )
            return preview

        return self.safe(inspect)

    def refresh_diff(self):
        self.capture()
        name = self.current_file
        if not name:
            return
        before = self.base.get(name, b"").decode("utf-8", errors="replace").splitlines(True)
        after = self.files.get(name, b"").decode("utf-8", errors="replace").splitlines(True)
        self.diff.setPlainText(
            "".join(
                difflib.unified_diff(
                    before, after, fromfile="Paket/" + name, tofile="Entwurf/" + name
                )
            )
            or "Keine Änderungen."
        )

    def add_file(self):
        name, ok = QInputDialog.getText(
            self, "Paketdatei hinzufügen", "Relativer Dateiname, z. B. helpers/convert.py"
        )
        if not ok:
            return

        def add():
            from ..domain.tool_contract import relative_name

            relative_name(name)
            manifest, _ = self.values()
            if name in self.files:
                raise StudioError("conflict", "Datei ist bereits vorhanden.")
            self.files[name] = b""
            manifest["files"].append(name)
            self.files["manifest.json"] = (
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
            ).encode()
            self.current_file = None
            self.file_list.addItem(name)
            self.file_list.setCurrentRow(self.file_list.count() - 1)

        self.safe(add)

    def add_entry(self, flow):
        name, ok = QInputDialog.getText(
            self,
            "Teilablauf" if flow else "Skriptbaustein",
            "Stabile Kennung (Kleinbuchstaben, Ziffern, _)",
        )
        if not ok:
            return

        def add():
            from ..domain.tool_contract import KEY, empty_workflow

            if not KEY.fullmatch(name):
                raise StudioError("validation", "Ungültige Bausteinkennung.")
            manifest, _ = self.values()
            if any(entry["id"] == name for entry in manifest["steps"] + manifest["flows"]):
                raise StudioError("conflict", "Kennung ist bereits vorhanden.")
            if flow:
                manifest["flows"].append(
                    {
                        "id": name,
                        "name": name,
                        "description": "Eigener Teilablauf",
                        "recipe": empty_workflow(),
                    }
                )
            else:
                filename = name + ".py"
                manifest["files"].append(filename)
                manifest["steps"].append(
                    {
                        "id": name,
                        "name": name,
                        "description": "Eigener Baustein",
                        "source": filename,
                        "entry_point": "run",
                        "execution": "map",
                        "capabilities": [],
                        "parameters": {},
                        "inputs": {"image": {"type": "image"}},
                        "outputs": {"image": {"type": "image", "directory": "Ergebnisse/" + name}},
                    }
                )
                self.files[filename] = (
                    b"def run(context, inputs, parameters):\n"
                    b"    source = inputs['image']\n"
                    b"    result = context.artifact('image.png', source.type, source.metadata)\n"
                    b"    result.path.write_bytes(source.path.read_bytes())\n"
                    b"    return {'image': result}\n"
                )
                self.file_list.addItem(filename)
            self.files["manifest.json"] = (
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
            ).encode()
            self.current_file = None
            self.file_list.setCurrentRow(
                next(
                    i
                    for i in range(self.file_list.count())
                    if self.file_list.item(i).text() == "manifest.json"
                )
            )
            self.open_file("manifest.json")
            self.save()
            self.entries.addItem(name, name)
            if flow:
                self.flow_requested.emit(self.digest, name)

        self.safe(add)

    def publish(self):
        preview = self.check()
        if not preview or preview.issues:
            return
        base = self.service.details(self.digest)
        if (
            preview.digest != self.digest
            and preview.manifest["version"] == base["manifest"]["version"]
        ):
            parts = preview.manifest["version"].split(".")
            version, accepted = QInputDialog.getText(
                self,
                "Neue Paketversion",
                "Version",
                text=".".join([*parts[:2], str(int(parts[2]) + 1)]),
            )
            if not accepted:
                return
            manifest, _ = self.values()
            manifest["version"] = version
            self.files["manifest.json"] = (
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
            ).encode()
            if self.current_file == "manifest.json":
                self.code.setPlainText(self.files["manifest.json"].decode())
        if not self.save():
            return

        def publish():
            package = self.service.publish_draft(self.draft["id"])
            self.digest = package["digest"]
            self.diagnostics.setPlainText(
                "Paketversion übernommen. Im Ablauf die gewünschte neue Version auswählen.\n"
                + self.digest
            )
            self.changed.emit()

        self.safe(publish)

    def copy_context(self):
        self.capture()
        text = (
            "Werkzeugpaket · SDK: run(context, inputs, parameters) → benannte Artifact-Ausgänge\n"
        )
        text += self.diagnostics.toPlainText() + "\n\n" + self.files["manifest.json"].decode()
        if self.current_file and self.current_file != "manifest.json":
            text += "\n\nDatei: " + self.current_file + "\n" + self.code.toPlainText()
        QApplication.clipboard().setText(text)
        self.diagnostics.appendPlainText(
            "Fehlerkontext in Zwischenablage. Vorschläge können hier eingefügt und geprüft werden."
        )

    def start(self, call, callback):
        if self.worker:
            return
        self.worker = WorkThread(call, self)
        worker = self.worker
        self.setup_button.setEnabled(False)
        self.test_button.setEnabled(False)
        worker.progress.connect(self.diagnostics.appendPlainText)
        worker.result.connect(
            lambda result, error: (
                self.diagnostics.appendPlainText(error) if error else callback(result)
            )
        )
        worker.finished.connect(self.work_finished)
        worker.start()

    def work_finished(self):
        self.worker.deleteLater()
        self.worker = None
        self.setup_button.setEnabled(True)
        self.test_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def prepare_environment(self):
        preview = self.check()
        if preview:
            self.start(
                lambda worker: ToolEnvironments(self.project).prepare(
                    preview.manifest, on_output=worker.progress.emit
                ),
                lambda result: self.diagnostics.appendPlainText("Python-Umgebung ist bereit."),
            )

    def approve(self):
        if (
            QMessageBox.question(
                self,
                "Python-Code freigeben",
                "Diese Paketversion mit Benutzerrechten ausführen? "
                "Eine Bibliotheksumgebung ist keine Sicherheits-Sandbox.\nSHA-256: " + self.digest,
            )
            == QMessageBox.Yes
        ):
            self.safe(lambda: self.service.approve(self.digest))
            self.check()

    def test(self):
        if not self.assets.currentData() or not self.save():
            self.diagnostics.appendPlainText(
                "Für den Test eine importierte Asset-Quelle auswählen."
            )
            return
        preview = self.check()
        if not preview or preview.issues:
            return
        if (
            QMessageBox.question(
                self,
                "Entwurf testen",
                "Diesen Code mit Benutzerrechten im Job-Arbeitsordner testen? "
                "Ergebnisse werden nicht in Asset-Ausgabeordner veröffentlicht.",
            )
            != QMessageBox.Yes
        ):
            return
        package = self.safe(lambda: self.service.register(preview))
        if not package:
            return
        self.service.approve(package["digest"])
        asset, entry = self.assets.currentData(), self.entries.currentData()
        self.cancel_button.setEnabled(True)
        self.start(
            lambda worker: self.service.test(
                package["digest"],
                entry,
                asset,
                cancelled=worker.isInterruptionRequested,
                on_event=lambda event: worker.progress.emit(str(event)),
            ),
            lambda result: self.diagnostics.appendPlainText(
                "Testlauf: " + result["status"] + "\n" + str(result.get("run_id", ""))
            ),
        )

    def cancel(self):
        if self.worker:
            self.worker.requestInterruption()
