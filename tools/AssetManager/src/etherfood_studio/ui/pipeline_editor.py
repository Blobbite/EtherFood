"""Recipe editor reusing project Canvas items, gestures and local command history."""

from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QKeySequence, QPen
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout,
    QGraphicsPathItem, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox,
    QScrollArea, QSpinBox,
    QSplitter, QVBoxLayout, QWidget,
)

from ..application.commands import Command, Commands
from ..application.pipeline_exchange import PipelineExchange
from ..application.pipeline_service import PipelineService
from ..application.profile_service import ProfileService
from ..domain.models import StudioError
from ..domain.pipeline_recipes import blockers, step, validate_recipe
from ..storage.blob_store import BlobStore
from .canvas.edges import EdgeItem, curve
from .canvas.items import CardItem
from .canvas.view import Canvas
from .common import button, label, show_error
from .presentation import kind_icon


class PipelineCanvas(Canvas):
    def __init__(self):
        self.legacy_edges = []
        super().__init__()
        self.setObjectName("pipeline_canvas")
        self.setAccessibleName("Technischer Datenfluss: Bild-Ausgang auf Bild-Eingang ziehen")

    def render_recipe(self, recipe, positions, manifests, selected=None, legacy=None):
        legacy = legacy or {}
        self.rendering = True
        self.cancel_connection()
        self.scene().blockSignals(True)
        self.edges_by_id.clear()
        self.legacy_edges.clear()
        self.scene().clear()
        self.items_by_id.clear()
        for index, node in enumerate(recipe["steps"]):
            manifest = manifests.get(node["operation"], {})
            title = manifest.get("name", "Fehlendes Werkzeug: " + node["operation"])
            original = legacy.get("nodes", {}).get(node["id"], {})
            if original:
                title = original.get("label") or original.get("text", "").split("\n")[0] \
                    or original.get("file") or title
            ports = "Quelle → Bild" if node["operation"] == "source" else "Bild → Bild"
            summary = ("aktiv" if node["enabled"] else "aus · Durchreichen") + " · " + ports
            position = positions.get(node["id"], {"x": index * 310, "y": index % 2 * 170})
            card = CardItem(node["id"], title, "pipeline", summary, self,
                            position.get("w", 270), position.get("h", 105))
            if original:
                card.setToolTip("Legacy-Karte · technische Zuordnung gesondert prüfen\n" +
                                "\n".join(f"{k}: {v}" for k, v in original.items()))
            card.texts[0] = (card.texts[0][0], "VERARBEITUNGSSCHRITT")
            card.resize(card.rect().width(), card.rect().height())
            card.setPos(position.get("x", 0), position.get("y", 0))
            for port in card.ports.values():
                port.setToolTip("Bild-Ausgang dieses Schrittes → "
                                "Bild-Eingang eines anderen Schrittes")
            self.scene().addItem(card)
            self.items_by_id[node["id"]] = card
            card.setSelected(node["id"] == selected)
        for edge in legacy.get("edges", []):
            if edge["from"] not in self.items_by_id or edge["to"] not in self.items_by_id:
                continue
            line = QGraphicsPathItem()
            line.setPen(QPen(QColor("#888888"), 1, Qt.DashLine))
            line.setZValue(-2)
            line.setAcceptedMouseButtons(Qt.NoButton)
            line.setToolTip("Nur visuelle Legacy-Verbindung · kein Datenfluss")
            self.scene().addItem(line)
            self.legacy_edges.append((edge, line))
        for index, edge in enumerate(recipe["connections"]):
            item = EdgeItem({"id": str(index), "kind": "depends_on", "source_id": edge["from"],
                             "target_id": edge["to"]}, self)
            for text in item.caption.childItems():
                text.setText("Bild → Bild")
                item.caption.setRect(text.boundingRect().adjusted(0, 0, 10, 6))
            item.setToolTip("Technischer Datenfluss: Bild → Bild (keine Projektzuordnung)")
            self.scene().addItem(item)
            self.edges_by_id[str(index)] = item
        self.rendering = False
        self.scene().blockSignals(False)
        self.update_edges()

    def update_edges(self):
        if self.rendering:
            return
        for edge, line in self.legacy_edges:
            start = self.items_by_id[edge["from"]].sceneBoundingRect().center()
            end = self.items_by_id[edge["to"]].sceneBoundingRect().center()
            line.setPath(curve(start, end))
        super().update_edges()


class PipelineEditor(QDialog):
    def __init__(self, project, identifier, parent=None, *, commands=None):
        super().__init__(parent)
        self.project, self.service = project, PipelineService(project)
        self.identifier, self.record = identifier, self.service.recipe(identifier)
        self.commands, self.history = commands or Commands(project), Commands(project)
        self.changed, self.filling, self.selected = False, False, None
        self.manifests = self.service.manifests()
        self.saved_layout = project.catalog.layout(identifier)
        self.state = {"title": self.record.title, "recipe": deepcopy(self.record.data["recipe"]),
                      "positions": deepcopy(self.saved_layout.get("pipeline_nodes", {})),
                      "legacy": deepcopy(self.saved_layout.get("pipeline_legacy", {}))}
        self.baseline = deepcopy(self.state)
        self.setObjectName("pipeline_editor")
        self.setWindowTitle("Projekt-Pipeline · " + self.record.title)
        self.resize(1320, 850)
        root = QVBoxLayout(self)
        head = QHBoxLayout()
        self.name, self.category = QLineEdit(self.record.title), QLineEdit()
        self.category.setMinimumWidth(260)
        self.name.setObjectName("pipeline_name")
        self.enabled = QCheckBox("Pipeline aktiv")
        self.name.editingFinished.connect(self.header_changed)
        self.category.editingFinished.connect(self.header_changed)
        self.enabled.clicked.connect(self.header_changed)
        head.addWidget(label("Name"))
        head.addWidget(self.name, 1)
        head.addWidget(label("Kategorie"))
        head.addWidget(self.category)
        head.addWidget(self.enabled)
        root.addLayout(head)
        actions = QHBoxLayout()
        for text, name, call in (
            ("Speichern", "pipeline_save", self.save),
            ("Rückgängig", "pipeline_undo", self.undo),
            ("Wiederholen", "pipeline_redo", self.redo),
            ("Projektprofile …", "pipeline_profiles", self.profiles),
            ("Zuweisungen …", "pipeline_assign", self.assign),
            ("Dry-run / Ausführen …", "pipeline_build", self.run_pipeline),
            ("Exportieren …", "pipeline_export", self.export),
            ("Python-Erweiterungen …", "pipeline_plugins", self.plugins),
        ):
            actions.addWidget(button(text, name, call))
        root.addLayout(actions)
        root.addWidget(label("Nur technische Bildverbindungen. Layoutänderungen erzeugen keine "
                             "Bilder. Vor der Ausführung speichern und den Dry-run prüfen."))
        splitter = QSplitter()
        self.canvas = PipelineCanvas()
        self.canvas.selected.connect(self.select_step)
        self.canvas.open_requested.connect(self.select_step)
        self.canvas.moved.connect(lambda key, x, y: self.move_nodes({key: {"x": x, "y": y}}))
        self.canvas.moved_many.connect(self.move_nodes)
        self.canvas.resized.connect(lambda key, w, h: self.move_nodes({key: {"w": w, "h": h}}))
        self.canvas.connection_requested.connect(self.connect_steps)
        self.canvas.reconnect_requested.connect(self.reconnect)
        self.canvas.create_requested.connect(lambda key, x, y: self.add_step(key, x, y))
        self.canvas.setContextMenuPolicy(Qt.CustomContextMenu)
        self.canvas.customContextMenuRequested.connect(self.context_menu)
        splitter.addWidget(self.canvas)
        side = QWidget()
        side_layout = QVBoxLayout(side)
        row = QHBoxLayout()
        self.operations = QComboBox()
        self.fill_operations()
        row.addWidget(self.operations, 1)
        row.addWidget(button("+ Schritt", "pipeline_add_step", lambda: self.add_step()))
        side_layout.addLayout(row)
        side_layout.addWidget(button("Auswahl entfernen", "pipeline_remove_step",
                                      self.remove_selected))
        self.properties = QWidget()
        self.form = QFormLayout(self.properties)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(self.properties)
        side_layout.addWidget(area, 1)
        side_layout.addWidget(button("Ressource hinzufügen …", "pipeline_resource",
                                      self.add_resource))
        side_layout.addWidget(label("Zielprofile (keine Auswahl = Anforderungen des Assets):"))
        self.targets = QListWidget()
        self.targets.setMaximumHeight(180)
        self.targets.itemChanged.connect(self.targets_changed)
        side_layout.addWidget(self.targets)
        self.legacy_button = button("Legacy-Zuordnungen geprüft", "pipeline_legacy_checked",
                                     self.clear_legacy)
        side_layout.addWidget(self.legacy_button)
        splitter.addWidget(side)
        splitter.setSizes([850, 390])
        root.addWidget(splitter, 1)
        self.status = label("", "pipeline_status")
        root.addWidget(self.status)
        for shortcut, call in ((QKeySequence.StandardKey.Save, self.save),
                               (QKeySequence.StandardKey.Undo, self.undo),
                               (QKeySequence.StandardKey.Redo, self.redo)):
            action = QAction(self)
            action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(call)
            self.addAction(action)
        self.render()

    def safe(self, call):
        try:
            return call()
        except (StudioError, OSError, ValueError, KeyError, TypeError) as error:
            show_error(self, error)
            return None

    def fill_operations(self):
        self.operations.clear()
        for key, manifest in self.manifests.items():
            self.operations.addItem(kind_icon("pipeline"), manifest["name"], key)
        self.operations.setCurrentIndex(self.operations.findData("graphics"))

    def mutate(self, title, change):
        if self.filling:
            return
        before, after = deepcopy(self.state), deepcopy(self.state)
        change(after)
        validate_recipe(after["recipe"], self.manifests)
        self.project.catalog.validate_layout({"pipeline_nodes": after["positions"]})
        if after != before:
            self.history.execute(Command(title, lambda: self.set_state(after),
                                          lambda: self.set_state(before)))
        return True

    def set_state(self, state):
        self.state = deepcopy(state)
        self.render()

    def render(self):
        self.filling = True
        try:
            self.name.setText(self.state["title"])
            recipe = self.state["recipe"]
            self.category.setText(recipe["category"])
            self.enabled.setChecked(recipe["enabled"])
            self.canvas.render_recipe(recipe, self.state["positions"], self.manifests,
                                       self.selected, self.state["legacy"])
            self.targets.clear()
            has_graphics = any(node["operation"] == "graphics"
                               for node in recipe["steps"])
            self.targets.setEnabled(has_graphics)
            self.targets.setToolTip(
                "Zielprofile werden von einem Grafikprofile-Schritt verarbeitet."
                if not has_graphics else "Projektweite Grafikziele wählen")
            for key, profile in ProfileService(self.project).profiles().items():
                suffix = " · deaktiviert" if not profile["enabled"] else ""
                item = QListWidgetItem(profile["name"] + suffix)
                item.setData(Qt.UserRole, key)
                item.setCheckState(Qt.Checked if key in recipe["profiles"] else Qt.Unchecked)
                self.targets.addItem(item)
            reasons = blockers(recipe, self.manifests)
            reasons += PipelineExchange(self.project).dependency_blockers(
                recipe, verify_content=False)
            saved = "Ungespeichert · " if self.state != self.baseline else "Gespeichert · "
            detail = "Blockiert: " + "; ".join(reasons) if reasons else \
                "Rezept validiert; Dry-run erforderlich"
            self.status.setText(saved + detail)
            self.legacy_button.setVisible(bool(recipe["legacy_unresolved"]))
            self.show_properties()
        finally:
            self.filling = False

    def header_changed(self):
        def change(state):
            state["title"] = self.name.text().strip()
            state["recipe"].update(category=self.category.text().strip(),
                                   enabled=self.enabled.isChecked())
        return self.safe(lambda: self.mutate("Pipeline ändern", change))

    def targets_changed(self):
        values = [self.targets.item(i).data(Qt.UserRole) for i in range(self.targets.count())
                  if self.targets.item(i).checkState() == Qt.Checked]
        self.safe(lambda: self.mutate("Zielprofile ändern",
                                      lambda s: s["recipe"].update(profiles=values)))

    def select_step(self, identifier):
        self.selected = identifier
        self.show_properties()

    def show_properties(self):
        while self.form.rowCount():
            self.form.removeRow(0)
        node = next((v for v in self.state["recipe"]["steps"] if v["id"] == self.selected), None)
        if not node:
            self.form.addRow(label("Einen Verarbeitungsschritt auswählen."))
            return
        manifest = self.manifests.get(node["operation"])
        notice = manifest["description"] if manifest else \
            "Werkzeug fehlt; separat registrieren oder Schritt ersetzen."
        self.form.addRow(label(notice))
        enabled = QCheckBox("Schritt aktiv")
        enabled.setChecked(node["enabled"])
        def toggle_step(checked):
            def change(state):
                target = next(n for n in state["recipe"]["steps"] if n["id"] == node["id"])
                target["enabled"] = checked
            self.safe(lambda: self.mutate("Schritt aktivieren", change))
        enabled.clicked.connect(toggle_step)
        self.form.addRow(enabled)
        if manifest:
            for key, definition in manifest["parameters"].items():
                if node["operation"] in {"color", "source_color"}:
                    modes = {"soft": {"mode", "reference", "strength", "max_distance"},
                             "fixed": {"mode", "palette"},
                             "material": {"mode", "materials", "mask"}}
                    visible = modes[node["parameters"]["mode"]]
                    if key not in visible:
                        continue
                self.add_parameter(node, key, definition)

    def add_parameter(self, node, key, spec):
        kind, value = spec["type"], node["parameters"][key]
        if kind in {"integer", "number"}:
            small_integer = kind == "integer" and \
                -2 ** 31 <= spec["minimum"] <= spec["maximum"] < 2 ** 31
            widget = QSpinBox() if small_integer else QDoubleSpinBox()
            if not small_integer:
                decimals = 15 if node["operation"].startswith("python:") else 4
                widget.setDecimals(0 if kind == "integer" else decimals)
            widget.setRange(spec["minimum"], spec["maximum"])
            widget.setValue(value)
            widget.editingFinished.connect(
                lambda: self.parameter_changed(node["id"], key,
                    int(widget.value()) if kind == "integer" else widget.value()))
        elif kind in {"choice", "resource"}:
            widget = QComboBox()
            choices = spec["choices"] if kind == "choice" else \
                ["", *self.state["recipe"]["resources"]]
            if kind == "resource" and key == "mask":
                choices.insert(1, "@source")
            for choice in choices:
                from ..domain.pipeline_recipes import TIMING_MODES
                if choice == "@source":
                    caption = "Nach Quellbindung (importierte Masken)"
                else:
                    caption = self.state["recipe"]["resources"][choice]["name"] \
                        if kind == "resource" and choice else TIMING_MODES.get(
                            choice, choice or "Nicht konfiguriert")
                widget.addItem(caption, choice)
            widget.setCurrentIndex(widget.findData(value))
            widget.activated.connect(
                lambda: self.parameter_changed(node["id"], key, widget.currentData()))
        elif kind == "boolean":
            widget = QCheckBox()
            widget.setChecked(value)
            widget.clicked.connect(lambda checked: self.parameter_changed(node["id"], key, checked))
        else:
            widget = QLineEdit(value)
            widget.editingFinished.connect(
                lambda: self.parameter_changed(node["id"], key, widget.text()))
        widget.setObjectName("pipeline_parameter_" + key)
        automatic_fps = key == "fps" and node["operation"] == "frames" and \
            node["parameters"]["timing"] == "keep_duration"
        if automatic_fps:
            widget.setEnabled(False)
            widget.setToolTip("Wird aus Quelldauer und Zielframes berechnet. "
                              "Dieser Wert bleibt für den Modus FPS beibehalten gespeichert.")
        caption = {"frames": "Zielframes", "fps": "Wiedergabe-FPS", "timing": "Timing-Modus",
                   "mode": "Farbmodus", "reference": "Referenzprofil", "palette": "Festpalette",
                   "materials": "Materialprofil", "mask": "Labelmaske", "strength": "Stärke",
                   "max_distance": "Max. Farbdistanz"}.get(key, key)
        self.form.addRow(caption, widget)
        if kind in {"number", "integer", "boolean", "choice", "resource"}:
            allowed = QCheckBox("Lokale Asset-Abweichung erlauben")
            allowed.setEnabled(not automatic_fps)
            token = node["id"] + "." + key
            allowed.setChecked(token in self.state["recipe"]["overridable"])
            def toggle(checked):
                def change(state):
                    values = set(state["recipe"]["overridable"])
                    values.add(token) if checked else values.discard(token)
                    state["recipe"]["overridable"] = sorted(values)
                self.safe(lambda: self.mutate("Parameter freigeben", change))
            allowed.clicked.connect(toggle)
            self.form.addRow(allowed)

    def parameter_changed(self, identifier, key, value):
        def change(state):
            target = next(n for n in state["recipe"]["steps"] if n["id"] == identifier)
            target["parameters"][key] = value
        self.safe(lambda: self.mutate("Parameter ändern", change))

    def add_step(self, source=None, x=0, y=0):
        def change(state):
            operation = self.operations.currentData()
            node = step(operation, self.manifests[operation])
            state["recipe"]["steps"].append(node)
            state["positions"][node["id"]] = {"x": x, "y": y}
            if source:
                state["recipe"]["connections"].append({"from": source, "out": "image",
                                                        "to": node["id"], "in": "image"})
            self.selected = node["id"]
        self.safe(lambda: self.mutate("Schritt hinzufügen", change))

    def connect_steps(self, source, target):
        self.safe(lambda: self.mutate("Technische Verbindung", lambda state:
            state["recipe"]["connections"].append({"from": source, "out": "image",
                                                    "to": target, "in": "image"})))

    def reconnect(self, edge_id, source, target):
        def change(state):
            state["recipe"]["connections"][int(edge_id)].update({"from": source, "to": target})
        self.safe(lambda: self.mutate("Datenfluss umhängen", change))

    def move_nodes(self, values):
        def change(state):
            for key, value in values.items():
                if not isinstance(value, dict):
                    value = {"x": value[0], "y": value[1]}
                old = state["positions"].get(key)
                if old is None:
                    card = self.canvas.items_by_id[key]
                    old = {"x": card.pos().x(), "y": card.pos().y()}
                state["positions"][key] = old | value
        self.safe(lambda: self.mutate("Knotenlayout ändern", change))

    def remove_selected(self):
        keys = self.canvas.selected_ids()
        edges = {int(item.identifier) for item in self.canvas.scene().selectedItems()
                 if isinstance(item, EdgeItem)}
        def change(state):
            recipe = state["recipe"]
            recipe["steps"] = [n for n in recipe["steps"] if n["id"] not in keys]
            recipe["connections"] = [e for i, e in enumerate(recipe["connections"])
                                      if i not in edges and e["from"] not in keys
                                      and e["to"] not in keys]
            recipe["overridable"] = [v for v in recipe["overridable"]
                                     if v.split(".")[0] not in keys]
            state["positions"] = {k: v for k, v in state["positions"].items() if k not in keys}
            legacy = state["legacy"]
            if legacy:
                legacy["nodes"] = {k: v for k, v in legacy["nodes"].items() if k not in keys}
                for node in legacy["nodes"].values():
                    if node.get("group") in keys:
                        node.pop("group")
                legacy["edges"] = [e for e in legacy["edges"]
                                   if e["from"] not in keys and e["to"] not in keys]
                legacy["mappings"] = [m for m in legacy["mappings"] if m["node"] not in keys]
        self.safe(lambda: self.mutate("Schritt/Verbindung entfernen", change))

    def context_menu(self, point):
        menu = QMenu(self)
        menu.addAction("Schritt hinzufügen", lambda: self.add_step(None,
            self.canvas.mapToScene(point).x(), self.canvas.mapToScene(point).y()))
        menu.addAction("Auswahl entfernen", self.remove_selected)
        menu.exec(self.canvas.viewport().mapToGlobal(point))

    def undo(self):
        self.safe(self.history.undo)

    def redo(self):
        self.safe(self.history.redo)

    def save(self):
        if not self.header_changed():
            return False
        if self.state == self.baseline:
            return True
        def commit():
            before, after = deepcopy(self.baseline), deepcopy(self.state)
            current = self.service.recipe(self.identifier)
            self.project._check_revision(current, self.record.revision_no)
            positions = self.project.catalog.layout(self.identifier).get("pipeline_nodes", {})
            legacy = self.project.catalog.layout(self.identifier).get("pipeline_legacy", {})
            if positions != before["positions"] or legacy != before["legacy"]:
                raise StudioError("conflict", "Knotenlayout wurde inzwischen geändert.")
            def write(expected, value):
                record = self.service.recipe(self.identifier)
                if record.data["recipe"] != expected["recipe"] or record.title != expected["title"]:
                    raise StudioError("conflict", "Pipeline wurde inzwischen geändert.")
                self.service.save(record.id, value["recipe"], record.revision_no)
                record = self.service.recipe(record.id)
                if record.title != value["title"]:
                    self.project.rename(record.id, value["title"], record.revision_no)
                layout = self.project.catalog.layout(record.id)
                if value["positions"]:
                    layout["pipeline_nodes"] = value["positions"]
                else:
                    layout.pop("pipeline_nodes", None)
                if value["legacy"]:
                    layout["pipeline_legacy"] = value["legacy"]
                else:
                    layout.pop("pipeline_legacy", None)
                self.project.catalog.save_layout(record.id, layout)
            self.commands.execute(Command("Pipeline speichern", lambda: write(before, after),
                                           lambda: write(after, before)))
            self.record = self.service.recipe(self.identifier)
            self.baseline = deepcopy(self.state)
            self.changed = True
            self.render()
            return True
        return bool(self.safe(commit))

    def add_resource(self):
        from pathlib import Path
        from ..domain.models import new_id

        name, _ = QFileDialog.getOpenFileName(self, "Deklarative Bild-/Farbressource", "",
                                              "Bilder und Farbprofile (*.png *.json)")
        if not name:
            return
        def add():
            path = Path(name)
            if path.stat().st_size > 32 * 1024 * 1024:
                raise StudioError("validation", "Ressource überschreitet 32 MiB.")
            store = BlobStore(self.project.catalog, self.project.catalog.path.parent)
            blob = store.import_file(path)
            key = "resource_" + new_id()[:8]
            self.mutate("Ressource hinzufügen", lambda state: state["recipe"]["resources"].update({
                key: {"name": path.name, "sha256": blob["sha256"], "length": blob["length"]}}))
        self.safe(add)

    def clear_legacy(self):
        if QMessageBox.question(self, "Legacy-Prüfung", "Sind Karten und technischer Datenfluss "
            "bewusst zugeordnet? Fehlende Werkzeuge bleiben weiterhin blockiert."
        ) == QMessageBox.Yes:
            self.safe(lambda: self.mutate("Legacy-Prüfung bestätigen",
                lambda state: state["recipe"].update(legacy_unresolved=[])))

    def profiles(self):
        from .pipeline_auxiliary import ProfileDialog
        self.safe(lambda: ProfileDialog(self.project, self).exec())
        self.render()

    def assign(self):
        from .pipeline_auxiliary import AssignmentDialog
        if self.save():
            self.safe(lambda: AssignmentDialog(self.project, self.identifier, self).exec())

    def run_pipeline(self):
        from .pipeline_auxiliary import PipelineRunDialog
        if self.save():
            self.safe(lambda: PipelineRunDialog(self.project, self.identifier, self).exec())

    def export(self):
        from .pipeline_exchange_dialogs import export_pipeline
        if self.save():
            self.safe(lambda: export_pipeline(self.project, self.identifier, self))

    def plugins(self):
        from .pipeline_exchange_dialogs import manage_plugins
        self.safe(lambda: manage_plugins(self.project, self))
        self.manifests = self.service.manifests()
        self.fill_operations()
        self.render()

    def reject(self):
        if not self.header_changed():
            return
        if self.state != self.baseline:
            answer = QMessageBox.question(self, "Ungespeicherte Pipeline",
                "Änderungen speichern? Nein verwirft nur den Entwurf.",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if answer == QMessageBox.Cancel or answer == QMessageBox.Yes and not self.save():
                return
        super().reject()

    def closeEvent(self, event):
        event.ignore()
        self.reject()
