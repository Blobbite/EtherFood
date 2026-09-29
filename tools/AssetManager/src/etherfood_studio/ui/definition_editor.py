"""One native pipeline canvas with compact inline node, input and Folder editing."""

from copy import deepcopy
import json

from PySide6.QtCore import QMimeData, QPointF, Qt, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..application.pipeline_workspace import PipelineWorkspace
from ..domain.models import StudioError, new_id
from ..domain.pipeline_contract import INPUT, folder_path
from ..storage.sqlite_repository import canonical
from .canvas.edges import EdgeItem
from .canvas.items import CardItem
from .canvas.view import Canvas
from .common import button, label, show_error
from .script_workspace import PortsEditor

SCRIPT_MIME = "application/x-etherfood-current-script"


class DefinitionCanvas(Canvas):
    script_dropped = Signal(str, float, float)
    remove_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("pipeline_canvas")
        self.setAccessibleName("Pipelinedefinition: Eingänge, Skripte und Folder verbinden")
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(SCRIPT_MIME):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasFormat(SCRIPT_MIME):
            point = self.mapToScene(event.position().toPoint())
            identifier = bytes(event.mimeData().data(SCRIPT_MIME)).decode("utf-8")
            self.script_dropped.emit(identifier, point.x(), point.y())
            event.acceptProposedAction()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.remove_requested.emit()
            event.accept()
        else:
            super().keyPressEvent(event)

    def render_definition(self, definition, scripts, positions, selected=None):
        self.rendering = True
        self.scene().blockSignals(True)
        self.cancel_connection()
        self.edges_by_id.clear()
        self.scene().clear()
        self.items_by_id.clear()
        entries = [(INPUT, "Eingabe", ", ".join(definition["inputs"]) or "Anschlüsse festlegen", 0)]
        for node in definition["nodes"]:
            script = scripts.get(node["script_id"])
            entries.append(
                (
                    node["id"],
                    script.title if script else "Skript fehlt",
                    (
                        ", ".join(script.data["inputs"]) + " → " + ", ".join(script.data["outputs"])
                        if script
                        else node["script_id"]
                    ),
                    1,
                )
            )
        entries += [
            ("folder:" + f["id"], "Folder · " + f["id"], f["directory"], 2)
            for f in definition["folders"]
        ]
        counts = {}
        for identifier, title, summary, depth in entries:
            position = positions.get(
                identifier, {"x": depth * 340, "y": counts.get(depth, 0) * 150}
            )
            counts[depth] = counts.get(depth, 0) + 1
            item = CardItem(identifier, title, "pipeline", summary, self, 280, 110)
            item.setPos(position["x"], position["y"])
            self.scene().addItem(item)
            self.items_by_id[identifier] = item
            item.setSelected(identifier == selected)
        edges = [
            (str(index), e["from"], e["to"], e["out"] + " → " + e["in"])
            for index, e in enumerate(definition["connections"])
        ]
        edges += [
            ("folder:" + f["id"], f["node"], "folder:" + f["id"], f["port"])
            for f in definition["folders"]
        ]
        for key, source, target, caption in edges:
            if source not in self.items_by_id or target not in self.items_by_id:
                continue
            edge = EdgeItem(
                {"id": key, "source_id": source, "target_id": target, "kind": "depends_on"}, self
            )
            text = edge.caption.childItems()[0]
            text.setText(caption)
            edge.caption.setRect(text.boundingRect().adjusted(0, 0, 10, 6))
            self.scene().addItem(edge)
            self.edges_by_id[key] = edge
        self.scene().blockSignals(False)
        self.rendering = False
        self.update_edges()
        self.update_scene_rect()


class DefinitionEditor(QWidget):
    changed = Signal()
    overview_requested = Signal()
    script_requested = Signal(str)
    check_requested = Signal(str)

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project, self.service = project, PipelineWorkspace(project)
        self.current = None
        self.value, self.saved = {}, {}
        self.positions, self.selected = {}, None
        self.done, self.undone = [], []
        layout = QVBoxLayout(self)
        row = QGridLayout()
        self.title = QLineEdit()
        self.title.setObjectName("pipeline_title")
        layout.addWidget(self.title)
        for index, (text, name, call) in enumerate(
            (
                ("Übersicht", "pipeline_overview", self.overview),
                ("Speichern", "pipeline_save", self.save),
                ("Neu laden", "pipeline_reload", self.reload),
                ("Prüfen", "pipeline_check", self.check),
                ("Zurück", "pipeline_undo", self.undo),
                ("Wiederholen", "pipeline_redo", self.redo),
            )
        ):
            row.addWidget(button(text, name, call), index // 3, index % 3)
        layout.addLayout(row)
        self.notice = label("", "pipeline_usage_notice")
        self.notice.setWordWrap(True)
        layout.addWidget(self.notice)
        splitter = QSplitter(Qt.Vertical)
        self.canvas = DefinitionCanvas()
        self.canvas.selected.connect(self.select, Qt.QueuedConnection)
        self.canvas.moved.connect(
            lambda key, x, y: self.move({key: {"x": x, "y": y}}), Qt.QueuedConnection
        )
        self.canvas.moved_many.connect(self.move, Qt.QueuedConnection)
        self.canvas.connection_requested.connect(self.connect, Qt.QueuedConnection)
        self.canvas.reconnect_requested.connect(self.reconnect, Qt.QueuedConnection)
        self.canvas.script_dropped.connect(self.add_script, Qt.QueuedConnection)
        self.canvas.remove_requested.connect(self.remove, Qt.QueuedConnection)
        self.canvas.setContextMenuPolicy(Qt.CustomContextMenu)
        self.canvas.customContextMenuRequested.connect(self.context_menu)
        splitter.addWidget(self.canvas)
        self.inspector = QWidget()
        self.form = QFormLayout(self.inspector)
        self.inspector_scroll = QScrollArea()
        self.inspector_scroll.setObjectName("pipeline_inline_editor")
        self.inspector_scroll.setWidgetResizable(True)
        self.inspector_scroll.setWidget(self.inspector)
        self.inspector_scroll.setMinimumHeight(130)
        splitter.addWidget(self.inspector_scroll)
        splitter.setSizes([560, 160])
        layout.addWidget(splitter, 1)
        self.clear_inspector()

    @property
    def dirty(self):
        return self.current is not None and (
            self.value != self.saved or self.title.text() != self.current.title
        )

    def confirm_discard(self):
        if not self.dirty:
            return True
        answer = QMessageBox.warning(
            self,
            "Ungespeicherte Pipelinedefinition",
            "Definition vor dem Verlassen speichern? Änderungen gelten für alle Verwendungen.",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        return self.save() if answer == QMessageBox.Save else answer == QMessageBox.Discard

    def reload(self):
        if self.current:
            self.open(self.current.id, force=True)

    def open(self, identifier, *, force=False):
        if not force and self.current and identifier == self.current.id:
            return True
        if not self.confirm_discard():
            return False
        self.save_position()
        try:
            value, digest = self.service.files.definition(identifier)
            if not isinstance(value, dict) or not all(
                isinstance(value.get(key), kind)
                for key, kind in (
                    ("nodes", list),
                    ("connections", list),
                    ("folders", list),
                    ("inputs", dict),
                )
            ):
                raise StudioError(
                    "validation", "Ablaufdatei ist ungültig; externe Fassung bleibt erhalten."
                )
            self.current = self.project.catalog.get(identifier)
            self.value, self.saved, self.digest = deepcopy(value), deepcopy(value), digest
            self.positions = self.project.catalog.layout(identifier).get("pipeline_nodes", {})
            self.done, self.undone, self.selected = [], [], None
            self.title.setText(self.current.title)
            self.title.setReadOnly(self.current.archived)
            self.inspector.setEnabled(not self.current.archived)
            uses = self.service.usages(identifier, include_archived=True)
            self.notice.setText(
                "Gemeinsame Definition · "
                + str(len(uses))
                + " Verwendung(en): "
                + (", ".join(r.title for r in uses) or "noch keine")
            )
            self.render()
            self.canvas.resetTransform()
            view = self.project.catalog.layout(identifier).get("pipeline_view", {})
            self.canvas.scale(view.get("zoom", 0.85), view.get("zoom", 0.85))
            self.canvas.centerOn(view.get("x", 300), view.get("y", 150))
            return True
        except (StudioError, OSError, ValueError, KeyError, TypeError) as error:
            self.notice.setText(str(error))
            return False

    def save_position(self):
        if self.current:
            center = self.canvas.mapToScene(self.canvas.viewport().rect().center())
            layout = self.project.catalog.layout(self.current.id) | {
                "pipeline_nodes": self.positions,
                "pipeline_view": {
                    "zoom": self.canvas.transform().m11(),
                    "x": center.x(),
                    "y": center.y(),
                },
            }
            self.project.catalog.save_layout(self.current.id, layout)

    def save(self):
        if not self.current:
            return False
        if not self.dirty:
            self.save_position()
            return True
        try:
            with self.project.catalog.transaction():
                record, digest = self.service.files.save(
                    self.current.id,
                    canonical(self.value) + "\n",
                    self.digest,
                    self.current.revision_no,
                )
                if record.title != self.title.text().strip():
                    record = self.project.rename(record.id, self.title.text(), record.revision_no)
                self.save_position()
            self.current, self.digest, self.saved = record, digest, deepcopy(self.value)
            self.changed.emit()
            return True
        except (StudioError, OSError, ValueError) as error:
            self.notice.setText(str(error) + " · Entwurf bleibt erhalten.")
            return False

    def overview(self):
        self.save_position()
        if self.confirm_discard():
            if self.dirty:
                self.value = deepcopy(self.saved)
                self.title.setText(self.current.title)
            self.overview_requested.emit()

    def check(self):
        if not self.current:
            return
        if self.dirty:
            if (
                QMessageBox.question(
                    self,
                    "Entwurf vor Prüfung speichern",
                    "Aktuelle Verschaltung speichern und anschließend prüfen?",
                    QMessageBox.Save | QMessageBox.Cancel,
                    QMessageBox.Cancel,
                )
                != QMessageBox.Save
            ):
                return
            if not self.save():
                return
        self.check_requested.emit(self.current.id)

    def mutate(self, call):
        if not self.current or self.project.catalog.get(self.current.id).archived:
            self.notice.setText("Inaktive Definition zuerst wiederherstellen.")
            return
        before = deepcopy(self.value)
        try:
            call()
            if before != self.value:
                self.done.append(before)
                self.undone.clear()
                self.render()
        except (StudioError, ValueError, KeyError, TypeError) as error:
            self.value = before
            self.notice.setText(str(error))

    def undo(self):
        if self.done:
            self.undone.append(deepcopy(self.value))
            self.value = self.done.pop()
            self.render()
            if self.selected:
                self.select(self.selected)

    def redo(self):
        if self.undone:
            self.done.append(deepcopy(self.value))
            self.value = self.undone.pop()
            self.render()
            if self.selected:
                self.select(self.selected)

    def render(self):
        scripts = {r.id: r for r in self.service.scripts(include_archived=True)}
        self.canvas.render_definition(self.value, scripts, self.positions, self.selected)

    def move(self, values):
        if self.current:
            self.positions.update(values)
            self.save_position()  # Layout never enters the executable JSON or code approval.

    def add_script(self, identifier, x=340, y=0):
        if not self.current:
            return
        record = self.project.catalog.get(identifier)
        if record.kind != "script" or record.archived:
            return
        node = {
            "id": new_id(),
            "script_id": identifier,
            "parameters": {k: v["default"] for k, v in record.data["parameters"].items()},
        }
        self.positions[node["id"]] = {"x": x, "y": y}
        self.selected = node["id"]
        self.mutate(lambda: self.value["nodes"].append(node))
        self.select(node["id"])

    def add_folder(self):
        if not self.current:
            return
        index = 1
        existing = {f["id"] for f in self.value["folders"]}
        while "output" + str(index) in existing:
            index += 1
        name = "output" + str(index)
        self.mutate(
            lambda: self.value["folders"].append(
                {"id": name, "node": "", "port": "", "directory": "Ausgabe", "scope": "asset"}
            )
        )
        self.select("folder:" + name)

    def clear_inspector(self):
        while self.form.count():
            item = self.form.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()

    def select(self, identifier):
        if not self.current:
            return
        self.selected = identifier
        self.clear_inspector()
        if identifier == INPUT:
            editor = PortsEditor("Benannte Pipelineeingänge")
            editor.load(self.value["inputs"])
            self.form.addRow(editor)
            self.form.addRow(
                button(
                    "Eingänge übernehmen",
                    "pipeline_inputs_apply",
                    lambda: self.mutate(lambda: self.value.update(inputs=editor.value())),
                )
            )
            resources = QPlainTextEdit(
                json.dumps(self.value.get("resources", {}), ensure_ascii=False, indent=2)
            )
            resources.setObjectName("pipeline_resources")
            resources.setMaximumHeight(120)
            resources.setToolTip(
                "Benannte Ressourcen, z. B. "
                '{"palette": {"binding": "color_profile", "mode": "fixed"}}'
            )
            self.form.addRow("Ressourcen (JSON)", resources)
            self.form.addRow(
                button(
                    "Ressourcen übernehmen",
                    "pipeline_resources_apply",
                    lambda: self.mutate(
                        lambda: self.value.update(resources=json.loads(resources.toPlainText()))
                    ),
                )
            )
        elif identifier.startswith("folder:"):
            folder = next(
                (f for f in self.value["folders"] if "folder:" + f["id"] == identifier), None
            )
            if folder:
                self.folder_form(folder)
        else:
            node = next((n for n in self.value["nodes"] if n["id"] == identifier), None)
            if node:
                self.node_form(node)

    def node_form(self, node):
        record = self.project.catalog.get(node["script_id"])
        self.form.addRow(label(record.title + " · " + record.data["path"]))
        for key, spec in record.data["parameters"].items():
            if any(
                node["parameters"].get(k) not in values
                for k, values in spec.get("visible_if", {}).items()
            ):
                continue
            value = node["parameters"].get(key, spec["default"])
            if spec["type"] in {"integer", "number"}:
                if (
                    spec["type"] == "integer"
                    and not -(2**31) <= spec["minimum"] <= spec["maximum"] < 2**31
                ):
                    field = QLineEdit(str(value))
                    field.editingFinished.connect(
                        lambda n=node["id"], k=key, w=field: self.number_parameter(n, k, w.text())
                    )
                else:
                    field = QSpinBox() if spec["type"] == "integer" else QDoubleSpinBox()
                    if isinstance(field, QDoubleSpinBox):
                        field.setDecimals(15)
                    field.setRange(spec["minimum"], spec["maximum"])
                    field.setValue(value)
                    field.editingFinished.connect(
                        lambda n=node["id"], k=key, w=field, initial=field.value(): (
                            self.parameter(n, k, w.value()) if w.value() != initial else None
                        )
                    )
            elif spec["type"] == "boolean":
                field = QCheckBox()
                field.setChecked(value)
                field.toggled.connect(lambda v, n=node["id"], k=key: self.parameter(n, k, v))
            elif spec["type"] in {"choice", "resource"}:
                field = QComboBox()
                field.addItems(
                    spec["choices"]
                    if spec["type"] == "choice"
                    else list(dict.fromkeys([value, "", *self.value.get("resources", {})]))
                )
                field.setCurrentText(value)
                field.currentTextChanged.connect(
                    lambda v, n=node["id"], k=key: self.parameter(n, k, v)
                )
            else:
                field = QLineEdit(value)
                field.editingFinished.connect(
                    lambda n=node["id"], k=key, w=field: self.parameter(n, k, w.text())
                )
            field.setObjectName("pipeline_parameter_" + key)
            field.setToolTip(spec.get("description", ""))
            disabled = spec.get("disabled_if", {})
            field.setEnabled(
                not disabled
                or not all(node["parameters"].get(k) in values for k, values in disabled.items())
            )
            self.form.addRow(spec.get("label", key), field)

    def number_parameter(self, identifier, key, text):
        try:
            self.parameter(identifier, key, int(text))
        except ValueError:
            self.notice.setText("Parameter benötigt eine ganze Zahl; Eingabe bleibt sichtbar.")

    def parameter(self, identifier, key, value):
        def change():
            node = next(n for n in self.value["nodes"] if n["id"] == identifier)
            node["parameters"][key] = value
            if "resources" in node:
                node["resources"] = [
                    v
                    for v in node["parameters"].values()
                    if isinstance(v, str) and v in self.value.get("resources", {})
                ]

        self.mutate(change)
        record = self.project.catalog.get(
            next(n["script_id"] for n in self.value["nodes"] if n["id"] == identifier)
        )
        if any(
            key in spec.get("visible_if", {}) or key in spec.get("disabled_if", {})
            for spec in record.data["parameters"].values()
        ):
            self.select(identifier)

    def folder_form(self, folder):
        path = QLineEdit(folder["directory"])
        path.setObjectName("pipeline_folder_directory")
        scope = QComboBox()
        scope.addItem("Beim jeweiligen Asset", "asset")
        scope.addItem("Gemeinsame Projektablage", "project")
        scope.setCurrentIndex(scope.findData(folder.get("scope", "asset")))
        self.form.addRow("Folder · " + folder["id"], label(folder["node"] + " / " + folder["port"]))
        self.form.addRow("Ziel unter verwalteten Ergebnissen", path)
        self.form.addRow("Zuordnung", scope)

        def apply():
            def change():
                current = next(f for f in self.value["folders"] if f["id"] == folder["id"])
                current.update(directory=folder_path(path.text()), scope=scope.currentData())

            self.mutate(change)

        self.form.addRow(button("Folder übernehmen", "pipeline_folder_apply", apply))

    def connect(self, source, target, replacing=None):
        if not self.current or source == target or source.startswith("folder:") or target == INPUT:
            return
        scripts = self.service.descriptions()
        nodes = {n["id"]: n for n in self.value["nodes"]}
        outputs = (
            self.value["inputs"]
            if source == INPUT
            else scripts[nodes[source]["script_id"]]["outputs"]
        )
        inputs = (
            {"input": {"type": "file"}}
            if target.startswith("folder:")
            else scripts[nodes[target]["script_id"]]["inputs"]
        )
        self.clear_inspector()
        self.form.addRow(label("Verbindung ausdrücklich auswählen"))
        out, incoming = QComboBox(), QComboBox()
        out.addItems(list(outputs))
        incoming.addItems(list(inputs))
        self.form.addRow("Ausgang", out)
        self.form.addRow("Eingang", incoming)

        def apply():
            def change():
                if target.startswith("folder:"):
                    folder = next(f for f in self.value["folders"] if "folder:" + f["id"] == target)
                    folder.update(node=source, port=out.currentText())
                else:
                    if replacing is not None:
                        self.value["connections"] = [
                            edge
                            for i, edge in enumerate(self.value["connections"])
                            if str(i) != replacing.removeprefix("edge:")
                        ]
                    from ..domain.pipeline_contract import compatible, topological

                    if (
                        not out.currentText()
                        or not incoming.currentText()
                        or not compatible(
                            outputs[out.currentText()]["type"],
                            inputs[incoming.currentText()]["type"],
                        )
                    ):
                        raise StudioError("validation", "Anschlusstypen passen nicht.")
                    edge = {
                        "from": source,
                        "out": out.currentText(),
                        "to": target,
                        "in": incoming.currentText(),
                    }
                    if edge in self.value["connections"]:
                        return
                    if any(
                        e["to"] == target and e["in"] == incoming.currentText()
                        for e in self.value["connections"]
                    ) and not inputs[incoming.currentText()].get("multiple"):
                        raise StudioError("validation", "Einzeleingang ist bereits verbunden.")
                    edges = self.value["connections"] + [edge]
                    topological({INPUT, *nodes}, [(e["from"], e["to"]) for e in edges])
                    self.value["connections"].append(edge)

            self.mutate(change)

        self.form.addRow(button("Verbinden", "pipeline_connect_apply", apply))

    def reconnect(self, identifier, source, target):
        self.connect(source, target, replacing=identifier)

    def remove(self):
        if not self.current:
            return
        nodes = self.canvas.selected_ids() - {INPUT}
        edges = {key for key, edge in self.canvas.edges_by_id.items() if edge.isSelected()}

        def change():
            self.value["nodes"] = [n for n in self.value["nodes"] if n["id"] not in nodes]
            self.value["folders"] = [
                f for f in self.value["folders"] if "folder:" + f["id"] not in nodes
            ]
            self.value["connections"] = [
                e
                for index, e in enumerate(self.value["connections"])
                if str(index) not in edges and e["from"] not in nodes and e["to"] not in nodes
            ]
            for folder in self.value["folders"]:
                if folder["node"] in nodes or "folder:" + folder["id"] in edges:
                    folder.update(node="", port="")

        self.mutate(change)
        self.clear_inspector()

    def context_menu(self, position):
        card = self.canvas.card_at(self.canvas.mapToScene(position))
        menu = QMenu(self)
        if card:
            self.canvas.select_many({card.identifier})
            node = next((n for n in self.value["nodes"] if n["id"] == card.identifier), None)
            if node:
                action = menu.addAction("Skript bearbeiten")
                action.setObjectName("context_script_edit")
                action.triggered.connect(lambda: self.script_requested.emit(node["script_id"]))
            if card.identifier != INPUT:
                menu.addAction("Knoten entfernen", self.remove)
        menu.addAction("Folder hinzufügen", self.add_folder)
        menu.exec(self.canvas.viewport().mapToGlobal(position))
        menu.deleteLater()
