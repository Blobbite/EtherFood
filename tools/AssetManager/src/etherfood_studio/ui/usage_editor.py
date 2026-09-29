"""Explicit project input assignments, independent from definition and Folder editing."""

from copy import deepcopy
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from ..application.commands import Command
from ..application.lifecycle_service import LifecycleService
from ..application.pipeline_workspace import PipelineWorkspace
from ..domain.models import StudioError
from ..domain.pipeline_contract import output_ports
from .common import button, label


class UsageEditor(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.current = None
        self.connections = []
        self.setObjectName("pipeline_usage_editor")
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.title = label("Pipeline verwenden")
        top.addWidget(self.title, 1)
        top.addWidget(button("Schließen", "close_usage_editor", self.close_editor))
        layout.addLayout(top)
        self.create_page = QWidget()
        form = QHBoxLayout(self.create_page)
        self.definitions = QComboBox()
        self.definitions.setObjectName("usage_definition")
        form.addWidget(self.definitions, 1)
        form.addWidget(button("Verwendung anlegen", "create_pipeline_usage", self.create))
        self.pages = QStackedWidget()
        self.pages.addWidget(self.create_page)
        edit = QWidget()
        columns = QHBoxLayout(edit)
        self.targets = QListWidget()
        self.targets.setObjectName("usage_targets")
        self.targets.setMaximumHeight(150)
        self.targets.setAccessibleName("Ausgewählte Projektbereiche liefern Originalquellen")
        columns.addWidget(self.targets, 1)
        result = QVBoxLayout()
        ports = QHBoxLayout()
        self.predecessors, self.outputs, self.inputs = QComboBox(), QComboBox(), QComboBox()
        self.predecessors.currentIndexChanged.connect(self.fill_outputs)
        for control in (self.predecessors, self.outputs, self.inputs):
            ports.addWidget(control)
        ports.addWidget(button("Verbinden", "add_result_connection", self.add_connection))
        result.addLayout(ports)
        self.edges = QListWidget()
        self.edges.setMaximumHeight(90)
        self.edges.setAccessibleName("Ausdrückliche Ergebnisverbindungen")
        result.addWidget(self.edges)
        actions = QHBoxLayout()
        actions.addWidget(
            button("Verbindung lösen", "remove_result_connection", self.remove_connection)
        )
        actions.addStretch()
        actions.addWidget(button("Zuordnung speichern", "save_usage", self.save))
        result.addLayout(actions)
        columns.addLayout(result, 2)
        self.pages.addWidget(edit)
        layout.addWidget(self.pages)
        self.notice = label(
            "Originalquellen und Ergebnisse sind getrennte Eingabewege. "
            "Folder-Ziele werden in der gemeinsamen Definition bearbeitet."
        )
        layout.addWidget(self.notice)
        self.hide()

    @property
    def service(self):
        return PipelineWorkspace(self.window.project)

    def value(self):
        return {
            "targets": [
                self.targets.item(i).data(Qt.UserRole)
                for i in range(self.targets.count())
                if self.targets.item(i).checkState() == Qt.Checked
            ],
            "connections": deepcopy(self.connections),
        }

    @property
    def dirty(self):
        if not self.current or self.pages.currentIndex() != 1:
            return False
        value = self.value()
        return (
            set(value["targets"]) != set(self.current.data["targets"])
            or value["connections"] != self.current.data["connections"]
        )

    def confirm_discard(self):
        if not self.dirty:
            return True
        choice = QMessageBox.question(
            self,
            "Ungespeicherte Pipelinezuordnung",
            "Änderungen vor dem Verlassen speichern?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if choice == QMessageBox.Save:
            return self.save()
        if choice == QMessageBox.Discard:
            self.open(self.current.id, force=True)
            return True
        return False

    def close_editor(self):
        if self.confirm_discard():
            self.hide()

    def choose_definition(self, target):
        if not self.confirm_discard():
            return
        self.target = target
        if self.window.project.catalog.get(target).kind not in {
            "project",
            "global",
            "act",
            "chapter",
            "asset",
            "package",
        }:
            self.target = self.window.project.project().id
        self.definitions.clear()
        for row in self.service.definitions():
            self.definitions.addItem(row.title, row.id)
        self.title.setText(
            "Pipeline verwenden · " + self.window.project.catalog.get(self.target).title
        )
        self.pages.setCurrentIndex(0)
        self.show()

    def create(self):
        identifier = self.definitions.currentData()
        if not identifier:
            self.notice.setText("Zuerst unter Skripte & Pipelines eine Definition anlegen.")
            return
        identity = []
        service = self.service

        def forward():
            if identity:
                LifecycleService(self.window.project).restore(identity[0])
            else:
                identity.append(service.use(identifier, [self.target]).id)

        def backward():
            LifecycleService(self.window.project).change(identity, "archived")

        if self.window.perform(
            lambda: self.window.commands.execute(Command("Pipeline verwenden", forward, backward))
        ):
            self.window.refresh()
            self.window.processing.content_changed()
            self.open(identity[0])

    def open(self, identifier, *, source=None, target=None, force=False):
        if not force and not self.confirm_discard():
            return False
        self.current = self.window.project.catalog.get(identifier)
        self.connections = deepcopy(self.current.data["connections"])
        self.title.setText("Verwendung: " + self.current.title)
        self.targets.clear()
        from ..application.search_service import SearchService

        states = SearchService(self.window.project)
        for row in self.window.project.cards():
            if (
                row.kind not in {"project", "global", "act", "chapter", "asset", "package"}
                or states.state(row) != "active"
            ):
                continue
            item = QListWidgetItem(self.window.project.breadcrumb(row.id), self.targets)
            item.setData(Qt.UserRole, row.id)
            item.setCheckState(
                Qt.Checked
                if row.id in self.current.data["targets"] or row.id == target
                else Qt.Unchecked
            )
        self.predecessors.clear()
        for row in self.service.usages():
            if row.id != identifier:
                self.predecessors.addItem(row.title, row.id)
        value, _ = self.service.files.definition(self.current.data["definition_id"])
        self.inputs.clear()
        self.inputs.addItems(list(value["inputs"]))
        if source:
            self.predecessors.setCurrentIndex(self.predecessors.findData(source))
        self.fill_outputs()
        self.render_edges()
        self.pages.setCurrentIndex(1)
        self.show()

    def fill_outputs(self):
        self.outputs.clear()
        identifier = self.predecessors.currentData()
        if identifier:
            try:
                row = self.window.project.catalog.get(identifier)
                value, _ = self.service.files.definition(row.data["definition_id"])
                self.outputs.addItems(list(output_ports(value, self.service.descriptions())))
            except StudioError as error:
                self.notice.setText(str(error))

    def add_connection(self):
        if (
            self.predecessors.currentData()
            and self.outputs.currentText()
            and self.inputs.currentText()
        ):
            self.connections.append(
                {
                    "usage": self.predecessors.currentData(),
                    "out": self.outputs.currentText(),
                    "in": self.inputs.currentText(),
                }
            )
            self.render_edges()
            self.notice.setText(
                "Ergebnisverbindung vorgemerkt. Originalzuordnungen für diesen "
                "Eingabeweg ausdrücklich abwählen und anschließend speichern."
            )

    def render_edges(self):
        self.edges.clear()
        for edge in self.connections:
            row = self.window.project.catalog.get(edge["usage"])
            self.edges.addItem(f"{row.title}: {edge['out']} → {edge['in']}")

    def remove_connection(self):
        row = self.edges.currentRow()
        if row >= 0:
            self.connections.pop(row)
            self.render_edges()

    def save(self):
        if not self.current:
            return False
        if not self.dirty:
            return True
        before = {key: deepcopy(self.current.data[key]) for key in ("targets", "connections")}
        after = self.value()
        identifier, service = self.current.id, self.service
        initial = [True]

        def update(value, expected):
            record = service.catalog.get(identifier)
            if initial[0]:
                self.window.project._check_revision(record, self.current.revision_no)
            if any(record.data[key] != expected[key] for key in expected):
                raise StudioError("conflict", "Zuordnung wurde inzwischen geändert.")
            service.update_usage(identifier, **value, expected_revision=record.revision_no)
            initial[0] = False

        if self.window.perform(
            lambda: self.window.commands.execute(
                Command(
                    "Eingabezuordnung ändern",
                    lambda: update(after, before),
                    lambda: update(before, after),
                )
            )
        ):
            self.window.refresh()
            self.window.processing.content_changed()
            self.open(identifier, force=True)
            self.notice.setText("Zuordnung gespeichert. Der Ausführungsplan wird erneut geprüft.")
            return True
        return False

    def reorder(self, identifier, direction):
        service = self.service
        before = [r.id for r in service.usages()]
        index = before.index(identifier)
        target = index + direction
        if not 0 <= target < len(before):
            return
        after = list(before)
        after[index], after[target] = after[target], after[index]
        if self.window.perform(
            lambda: self.window.commands.execute(
                Command(
                    "Verarbeitung umsortieren",
                    lambda: service.reorder(after),
                    lambda: service.reorder(before),
                )
            )
        ):
            self.window.refresh()
            self.window.processing.content_changed()
