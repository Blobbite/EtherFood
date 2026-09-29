"""Native current-file Python editing with a preserved draft and explicit diagnostics."""

import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..application.pipeline_workspace import PipelineWorkspace
from ..application.workspace_files import WorkspaceFiles
from ..domain.models import StudioError
from .common import button, label, show_error
from .python_editor import PythonEditor


class PortsEditor(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label(title))
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Name", "Typ", "Mehrfach", "Optional", "Animiert"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumHeight(120)
        self.table.setMaximumHeight(220)
        layout.addWidget(self.table)
        row = QHBoxLayout()
        row.addWidget(button("Anschluss hinzufügen", "add_port", self.add))
        row.addWidget(button("Anschluss entfernen", "remove_port", self.remove))
        row.addStretch()
        layout.addLayout(row)
        self.extra = {}

    def load(self, ports):
        self.table.setRowCount(0)
        self.extra = {
            k: {
                f: v
                for f, v in spec.items()
                if f not in {"type", "multiple", "required", "animated"}
            }
            for k, spec in ports.items()
        }
        for name, spec in ports.items():
            self.add(name, spec)

    def add(self, name=None, spec=None):
        spec = spec or {"type": "file"}
        name = name if isinstance(name, str) else "port" + str(self.table.rowCount() + 1)
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(name))
        kind = QComboBox()
        kind.addItems(["file", "image", "spritesheet", "gif", "json", "html"])
        kind.setCurrentText(spec["type"])
        self.table.setCellWidget(row, 1, kind)
        for column, checked in (
            (2, spec.get("multiple", False)),
            (3, not spec.get("required", True)),
            (4, spec.get("animated", False)),
        ):
            box = QCheckBox()
            box.setAccessibleName(self.table.horizontalHeaderItem(column).text() + " · " + name)
            box.setChecked(checked)
            self.table.setCellWidget(row, column, box)

    def remove(self):
        if self.table.currentRow() >= 0:
            self.table.removeRow(self.table.currentRow())

    def value(self):
        result = {}
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0).text().strip()
            if name in result:
                raise StudioError("validation", "Anschlussname ist doppelt: " + name)
            result[name] = self.extra.get(name, {}) | {
                "type": self.table.cellWidget(row, 1).currentText(),
                "multiple": self.table.cellWidget(row, 2).isChecked(),
                "required": not self.table.cellWidget(row, 3).isChecked(),
                "animated": self.table.cellWidget(row, 4).isChecked(),
            }
        from ..domain.pipeline_contract import ports

        return ports(result)


class ScriptWorkspace(QWidget):
    changed = Signal()
    test_requested = Signal(str)
    environment_requested = Signal(str)

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.files, self.service = WorkspaceFiles(project), PipelineWorkspace(project)
        self.current = None
        self.digest = None
        self.setObjectName("python_workspace")
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.title = QLineEdit()
        self.title.setPlaceholderText("Skriptname")
        self.title.setObjectName("script_title")
        layout.addWidget(self.title)
        for text, name, call in (
            ("Speichern", "script_save", self.save),
            ("Neu laden", "script_reload", self.reload),
            ("Prüfen", "script_check", self.diagnose),
            ("Testlauf", "script_test", self.request_test),
        ):
            row.addWidget(button(text, name, call))
        layout.addLayout(row)
        self.path_label = label(
            "In der Struktur eine Python-Datei auswählen.", "script_current_path"
        )
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.path_label)
        self.editor = PythonEditor()
        self.editor.setObjectName("current_python_editor")
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.editor)
        description = QWidget()
        form = QFormLayout(description)
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.entry = QLineEdit("run")
        self.dependencies = QLineEdit()
        self.dependencies.setPlaceholderText("Bibliotheken mit Version, durch Komma getrennt")
        self.helpers = QLineEdit()
        self.helpers.setPlaceholderText(
            "Relative Hilfsdateipfade in .tools/scrips, durch Komma getrennt"
        )
        self.execution = QComboBox()
        self.execution.addItem("Je Quelle", "map")
        self.execution.addItem("Quellen eines Assets sammeln", "collect")
        self.inputs = PortsEditor("Eingänge")
        self.outputs = PortsEditor("Ausgänge")
        self.parameters = QPlainTextEdit("{}")
        self.parameters.setMaximumHeight(110)
        form.addRow("Python-Einstieg", self.entry)
        form.addRow("Verarbeitung", self.execution)
        form.addRow("Bibliotheken", self.dependencies)
        form.addRow("Hilfsdateien", self.helpers)
        form.addRow(
            button(
                "Bibliotheken prüfen / einrichten …", "script_environment", self.request_environment
            )
        )
        form.addRow(self.inputs)
        form.addRow(self.outputs)
        form.addRow("Parameterbeschreibung (JSON)", self.parameters)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(description)
        splitter.addWidget(scroll)
        splitter.setSizes([500, 230])
        layout.addWidget(splitter, 1)
        self.diagnostics = QPlainTextEdit()
        self.diagnostics.setObjectName("script_diagnostics")
        self.diagnostics.setReadOnly(True)
        self.diagnostics.setMaximumHeight(125)
        layout.addWidget(self.diagnostics)
        self.loaded_description = None
        self.helper_path = None
        self.setEnabled(False)

    @property
    def dirty(self):
        if self.current is None:
            return False
        try:
            return (
                self.editor.document().isModified()
                or self.title.text() != self.current.title
                or self.description() != self.loaded_description
            )
        except (StudioError, ValueError):
            return True

    def description(self):
        return {
            "entry_point": self.entry.text().strip(),
            "execution": self.execution.currentData(),
            "inputs": self.inputs.value(),
            "outputs": self.outputs.value(),
            "parameters": json.loads(self.parameters.toPlainText()),
            "dependencies": [v.strip() for v in self.dependencies.text().split(",") if v.strip()],
            "helpers": [v.strip() for v in self.helpers.text().split(",") if v.strip()],
        }

    def confirm_discard(self):
        if not self.dirty:
            return True
        choice = QMessageBox.warning(
            self,
            "Ungespeicherter Python-Entwurf",
            "Änderungen vor dem Verlassen speichern?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        return self.save() if choice == QMessageBox.Save else choice == QMessageBox.Discard

    def reload(self):
        if self.current:
            if self.helper_path:
                self.open_helper(self.current.id, self.helper_path)
            else:
                self.open(self.current.id, force=True)

    def open(self, identifier, *, force=False):
        if (
            not force
            and self.current
            and self.current.id == identifier
            and self.helper_path is None
        ):
            return True
        if not self.confirm_discard():
            return False
        try:
            record = self.project.catalog.get(identifier)
            text, digest = self.files.text(identifier)
            self.current, self.digest = record, digest
            self.helper_path = None
            self.editor.setPlainText(text)
            self.editor.document().setModified(False)
            self.title.setText(record.title)
            self.path_label.setText(record.data["path"])
            self.entry.setText(record.data["entry_point"])
            self.execution.setCurrentIndex(
                self.execution.findData(record.data.get("execution", "map"))
            )
            self.dependencies.setText(", ".join(record.data.get("dependencies", [])))
            self.helpers.setText(", ".join(record.data.get("helpers", [])))
            self.inputs.load(record.data["inputs"])
            self.outputs.load(record.data["outputs"])
            self.parameters.setPlainText(
                json.dumps(record.data["parameters"], ensure_ascii=False, indent=2)
            )
            self.loaded_description = self.description()
            self.setEnabled(True)
            self.editor.setReadOnly(record.archived)
            self.title.setEnabled(True)
            self.title.setReadOnly(record.archived)
            for control in (
                self.entry,
                self.execution,
                self.dependencies,
                self.helpers,
                self.inputs,
                self.outputs,
                self.parameters,
            ):
                control.setEnabled(not record.archived)
            self.diagnostics.setPlainText(
                "Gespeicherter Stand geladen. Speichern erteilt keine Freigabe."
            )
            self.editor.setFocus()
            return True
        except (StudioError, OSError, ValueError) as error:
            show_error(self, error)
            return False

    def open_helper(self, identifier, path):
        if not self.confirm_discard():
            return False
        self.current = None
        if not self.open(identifier):
            return False
        try:
            from ..application.workspace_files import content_hash

            data = self.files.script_files(identifier)
            if path not in self.current.data.get("helpers", []):
                raise StudioError("validation", "Hilfsdatei ist diesem Skript nicht zugeordnet.")
            text = data[path].decode("utf-8-sig")
            self.helper_path, self.digest = path, content_hash(data[path])
            self.helper_bom = data[path].startswith(b"\xef\xbb\xbf")
            self.editor.setPlainText(text)
            self.editor.document().setModified(False)
            self.path_label.setText(
                ".tools/scrips/" + path + " · Hilfsdatei von " + self.current.title
            )
            for control in (
                self.title,
                self.entry,
                self.execution,
                self.dependencies,
                self.helpers,
                self.inputs,
                self.outputs,
                self.parameters,
            ):
                control.setEnabled(False)
            return True
        except (StudioError, OSError, UnicodeError) as error:
            self.diagnostics.setPlainText(str(error))
            return False

    def save(self):
        if self.current is None:
            return False
        if not self.dirty:
            return True
        try:
            description = self.description()
            with self.project.catalog.transaction():
                if self.helper_path:
                    self.project._check_revision(
                        self.project.catalog.get(self.current.id), self.current.revision_no
                    )
                    raw = self.editor.toPlainText().encode(
                        "utf-8-sig" if self.helper_bom else "utf-8"
                    )
                    record = self.files.helper(
                        self.current.id, self.helper_path, raw, expected_hash=self.digest
                    )
                    from ..application.workspace_files import content_hash

                    digest = content_hash(raw)
                else:
                    record, digest = self.files.save(
                        self.current.id,
                        self.editor.toPlainText(),
                        self.digest,
                        self.current.revision_no,
                    )
                if description != self.loaded_description:
                    record = self.files.save_description(record.id, description, record.revision_no)
                if record.title != self.title.text().strip():
                    record = self.project.rename(record.id, self.title.text(), record.revision_no)
            self.current, self.digest = record, digest
            self.loaded_description = description
            self.editor.document().setModified(False)
            self.diagnostics.setPlainText(
                "Aktuelle Datei gespeichert. Prüfung und Freigabe stehen getrennt."
            )
            self.changed.emit()
            return True
        except (StudioError, OSError, ValueError) as error:
            self.diagnostics.setPlainText(str(error) + "\nDer Editorentwurf bleibt erhalten.")
            return False

    def diagnose(self):
        if self.current is None:
            return
        if self.dirty:
            # Syntax of the draft is useful without replacing the executable current file.
            import ast

            try:
                ast.parse(self.editor.toPlainText())
                message = "Entwurf syntaktisch gültig. Importprüfung nach ausdrücklichem Speichern."
            except SyntaxError as error:
                message = str(error)
                self.editor.goto_line(error.lineno or 1)
            self.diagnostics.setPlainText(message)
            return
        try:
            value = self.service.script_snapshot(self.current.id)
            self.diagnostics.setPlainText(
                "\n".join(value["issues"]) or "Syntax, Einstieg, Hilfsdateien und Imports geprüft."
            )
        except (StudioError, OSError, ValueError) as error:
            self.diagnostics.setPlainText(str(error))

    def request_test(self):
        if self.current and self.require_saved():
            self.test_requested.emit(self.current.id)

    def request_environment(self):
        if self.current and self.require_saved():
            self.environment_requested.emit(self.current.id)

    def require_saved(self):
        if not self.dirty:
            return True
        if (
            QMessageBox.question(
                self,
                "Entwurf speichern",
                "Den Entwurf vor dieser Aktion als aktuelle Datei speichern?",
                QMessageBox.Save | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            != QMessageBox.Save
        ):
            return False
        return self.save()
