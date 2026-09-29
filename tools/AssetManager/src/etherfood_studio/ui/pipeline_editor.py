"""Recipe editor reusing project Canvas items, gestures and local command history."""

from copy import deepcopy

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QKeySequence, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QGraphicsPathItem,
    QInputDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..application.commands import Command, Commands
from ..application.asset_service import AssetService
from ..application.pipeline_outputs import OUTPUT_STATES, recipe_outputs
from ..application.pipeline_actions import PipelineActions, condition
from ..application.pipeline_exchange import PipelineExchange
from ..application.pipeline_service import PipelineService
from ..application.profile_service import ProfileService
from ..domain.models import StudioError
from ..domain.pipeline_recipes import blockers, step, validate_recipe
from ..domain.tool_contract import compatible, is_workflow
from ..storage.blob_store import BlobStore
from .canvas.edges import EdgeItem, curve
from .canvas.items import CardItem, WorkflowIconItem
from .canvas.view import Canvas
from .common import button, label, show_error
from .presentation import kind_icon
from .appearance import appearance


class PipelineCanvas(Canvas):
    def __init__(self):
        self.legacy_edges = []
        super().__init__()
        self.setObjectName("pipeline_canvas")
        self.setAccessibleName("Technischer Datenfluss: Bild-Ausgang auf Bild-Eingang ziehen")

    def render_recipe(self, recipe, positions, manifests, selected=None, legacy=None,
                      assets=(), bindings=(), outputs=None, asset_origins=None):
        legacy = legacy or {}
        self.rendering = True
        self.cancel_connection()
        self.scene().blockSignals(True)
        self.edges_by_id.clear()
        self.legacy_edges.clear()
        self.scene().clear()
        self.items_by_id.clear()
        self.recipe_edges, self.asset_edges = {}, {}
        self.output_nodes = {}
        defaults, depths, rows = {}, {}, {}
        if is_workflow(recipe):
            for node in validate_recipe(recipe, manifests):
                parents = [
                    edge["from"] for edge in recipe["connections"] if edge["to"] == node["id"]
                ]
                depth = max(
                    (depths[parent] + 1 for parent in parents),
                    default=(0 if node["operation"] == "source" else 1),
                )
                depths[node["id"]] = depth
                defaults[node["id"]] = {"x": depth * 350, "y": rows.get(depth, 0) * 170}
                rows[depth] = rows.get(depth, 0) + 1
        for index, node in enumerate(recipe["steps"]):
            if node["operation"] == "source" and assets:
                continue
            manifest = manifests.get(node["operation"], {})
            title = manifest.get("name", "Fehlendes Werkzeug: " + node["operation"])
            original = legacy.get("nodes", {}).get(node["id"], {})
            if original:
                title = original.get("label") or original.get("text", "").split("\n")[0] \
                    or original.get("file") or title
            ports = (
                ", ".join(manifest.get("inputs", {}))
                + " → "
                + ", ".join(manifest.get("outputs", {}))
            )
            summary = ("aktiv" if node["enabled"] else "aus · Durchreichen") + " · " + ports
            position = positions.get(
                node["id"], defaults.get(node["id"], {"x": index * 310, "y": index % 2 * 170})
            )
            if node["operation"] == "source":
                card = WorkflowIconItem(node["id"], "Asset-Eingang", "asset",
                                        "Asset links auswählen", self)
            else:
                card = CardItem(node["id"], title, "pipeline", summary, self,
                                position.get("w", 270), position.get("h", 105))
            if original:
                card.setToolTip("Legacy-Karte · technische Zuordnung gesondert prüfen\n" +
                                "\n".join(f"{k}: {v}" for k, v in original.items()))
            card.texts[0] = (
                card.texts[0][0],
                "TEILABLAUF" if node["operation"].startswith("flow:") else "SKRIPTBAUSTEIN",
            )
            card.resize(card.rect().width(), card.rect().height())
            card.setPos(position.get("x", 0), position.get("y", 0))
            for port in card.ports.values():
                port.setToolTip("Bild-Ausgang dieses Schrittes → "
                                "Bild-Eingang eines anderen Schrittes")
            self.scene().addItem(card)
            self.items_by_id[node["id"]] = card
            card.setSelected(node["id"] == selected)
        for index, asset in enumerate(assets):
            key = "asset_" + asset.id
            card = WorkflowIconItem(key, asset.title, "asset",
                (asset_origins or {}).get(asset.id, "Verbunden") if asset.id in bindings
                else "Port mit Skript verbinden", self)
            position = positions.get(key, {"x": 0, "y": index * 180})
            card.setPos(position["x"], position["y"])
            self.scene().addItem(card)
            self.items_by_id[key] = card
            card.setSelected(key == selected)
        if outputs is None:
            outputs = [{"id": "output_" + node["id"], "node": node["id"], "kind": "gif",
                        "title": "GIF-Vorschauen", "state": "active",
                        "paths": [node["parameters"]["directory"]]}
                       for node in recipe["steps"] if node["operation"] == "gif"]
        right = max((card.x() + card.rect().width() for card in self.items_by_id.values()),
                    default=300) + 60
        for index, output in enumerate(outputs):
            key = output["id"]
            title = output["paths"][0] if output["kind"] == "gif" and output["paths"] \
                else output["title"]
            state = OUTPUT_STATES[output["state"]]
            summary = output["paths"][0] if output["paths"] and output["state"] == "active" \
                else state
            kind = "pipeline" if output["state"] == "internal" else "act"
            card = WorkflowIconItem(key, title, kind, summary, self)
            card.setOpacity(1 if output["state"] in {"active", "internal"} else 0.5)
            card.setToolTip(output["title"] + " · " + state + "\n" +
                            "\n".join(output["paths"]))
            position = positions.get(key, {"x": right + index % 2 * 225,
                                           "y": index // 2 * 170})
            card.setPos(position["x"], position["y"])
            self.scene().addItem(card)
            self.items_by_id[key] = card
            card.setSelected(key == selected)
            self.output_nodes[key] = output["node"]
        self.add_output_edges(outputs)
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
            if edge["from"] not in self.items_by_id:
                for asset in assets:
                    if asset.id in bindings:
                        key = f"asset_{asset.id}_{index}"
                        self.add_flow_edge(key, "asset_" + asset.id, edge["to"], "Asset → Skript")
                        self.recipe_edges[key] = index
                        self.asset_edges[key] = asset.id
            else:
                self.add_flow_edge(
                    str(index), edge["from"], edge["to"], edge["out"] + " → " + edge["in"]
                )
                self.recipe_edges[str(index)] = index
        self.rendering = False
        self.scene().blockSignals(False)
        self.update_edges()

    def add_flow_edge(self, key, source, target, caption):
        item = EdgeItem({"id": key, "kind": "depends_on", "source_id": source,
                        "target_id": target}, self)
        for text in item.caption.childItems():
            text.setText(caption)
            item.caption.setRect(text.boundingRect().adjusted(0, 0, 10, 6))
        item.setToolTip(caption)
        item.caption.setVisible(bool(caption))
        self.scene().addItem(item)
        self.edges_by_id[key] = item

    def add_output_edges(self, outputs, node_ids=None, prefix="", *, active=True):
        if not active:
            return
        for output in outputs:
            if output["state"] not in {"active", "internal"}:
                continue
            source = (node_ids or {}).get(output["node"], output["node"])
            parent = next((row for row in outputs if row.get("profile") == output.get("parent")
                           and row["node"] == output["node"] and row["state"] == "internal"), None)
            if parent:
                source = prefix + parent["id"]
            key = prefix + output["id"]
            self.add_flow_edge(key, source, key, "")

    def update_edges(self):
        if self.rendering:
            return
        for edge, line in self.legacy_edges:
            start = self.items_by_id[edge["from"]].sceneBoundingRect().center()
            end = self.items_by_id[edge["to"]].sceneBoundingRect().center()
            line.setPath(curve(start, end))
        super().update_edges()


class PipelineEditor(QDialog):
    entry_open_requested = Signal(str)
    saved = Signal()

    def __init__(
        self,
        project,
        identifier,
        parent=None,
        *,
        commands=None,
        draft_recipe=None,
        draft_title=None,
        draft_save=None,
        draft_manifests=None,
    ):
        super().__init__(parent)
        self.project, self.service = project, PipelineService(project)
        self.draft_save = draft_save
        if draft_recipe is None:
            self.identifier, self.record = identifier, self.service.recipe(identifier)
        else:
            from types import SimpleNamespace

            self.identifier = project.project().id
            self.record = SimpleNamespace(
                id=self.identifier, title=draft_title, data={"recipe": draft_recipe}, revision_no=1
            )
        self.commands, self.history = commands or Commands(project), Commands(project)
        self.changed, self.filling, self.selected = False, False, None
        self.initial_view = True
        self.manifests = {**self.service.manifests(), **(draft_manifests or {})}
        self.saved_layout = {} if draft_save else project.catalog.layout(identifier)
        self.state = {"title": self.record.title, "recipe": deepcopy(self.record.data["recipe"]),
                      "positions": deepcopy(self.saved_layout.get("pipeline_nodes", {})),
                      "legacy": deepcopy(self.saved_layout.get("pipeline_legacy", {}))}
        self.state["bindings"] = [] if draft_save else self.service.bound_assets(identifier)
        self.inherited = {} if draft_save else self.service.inherited_assets(identifier)
        known = {r.id for r in project.cards() if r.kind == "asset"}
        self.state["inputs"] = sorted((set(self.state["bindings"]) | set(self.inherited) | {
            key.removeprefix("asset_") for key in self.state["positions"]
            if key.startswith("asset_")}) & known)
        self.baseline = deepcopy(self.state)
        self.setObjectName("pipeline_editor")
        self.setWindowTitle("Ablaufeditor · " + self.record.title)
        self.resize(1480, 850)
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
            ("Zuweisungen …", "pipeline_assign", self.assign),
            ("Dry-run / Ausführen …", "pipeline_build", self.run_pipeline),
            ("Exportieren …", "pipeline_export", self.export),
            ("Werkzeugpakete / Python …", "pipeline_plugins", self.plugins),
        ):
            action = button(text, name, call)
            action.setEnabled(
                not draft_save
                or name not in {"pipeline_assign", "pipeline_build", "pipeline_export"}
            )
            actions.addWidget(action)
        root.addLayout(actions)
        self.package_actions = QHBoxLayout()
        root.addLayout(self.package_actions)
        view_actions = QHBoxLayout()
        view_actions.addWidget(button("Alles anzeigen", "workflow_fit", self.fit_steps))
        view_actions.addWidget(button("100 %", "workflow_actual_size", self.actual_size))
        view_actions.addStretch()
        root.addLayout(view_actions)
        root.addWidget(label("Asset einblenden → Port auf ein Skript ziehen → Ausgabeziel wählen. "
                             "Skripte lassen sich über ihre Ports miteinander verbinden."))
        splitter = QSplitter()
        library = QWidget()
        library_layout = QVBoxLayout(library)
        library_layout.addWidget(label("Assets im Projekt"))
        self.asset_choices = QComboBox()
        self.asset_choices.setObjectName("pipeline_asset_choices")
        for asset in project.cards():
            if asset.kind == "asset":
                self.asset_choices.addItem(kind_icon("asset"), asset.title, asset.id)
        library_layout.addWidget(self.asset_choices)
        library_layout.addWidget(button("Asset einblenden", "pipeline_add_asset", self.add_asset))
        library_layout.addWidget(label("Skripte · Doppelklick zum Einfügen"))
        self.script_search = QLineEdit()
        self.script_search.setPlaceholderText("Baustein oder Teilablauf suchen …")
        self.script_search.textChanged.connect(self.filter_scripts)
        library_layout.addWidget(self.script_search)
        self.script_library = QListWidget()
        self.script_library.setObjectName("pipeline_script_library")
        self.script_library.setIconSize(QSize(32, 32))
        self.script_library.itemClicked.connect(self.choose_script)
        self.script_library.itemDoubleClicked.connect(self.insert_script)
        library_layout.addWidget(self.script_library, 1)
        splitter.addWidget(library)
        self.canvas = PipelineCanvas()
        self.canvas.selected.connect(self.select_step)
        self.canvas.open_requested.connect(self.open_step)
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
        self.form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(self.properties)
        side_layout.addWidget(area, 1)
        side_layout.addWidget(button("Ressource hinzufügen …", "pipeline_resource",
                                      self.add_resource))
        if is_workflow(self.state["recipe"]):
            side_layout.addWidget(
                button(
                    "Assetreferenzen / Masken …", "workflow_asset_resources", self.asset_resources
                )
            )
        self.target_label = label("Zielprofile (keine Auswahl = Anforderungen des Assets):")
        side_layout.addWidget(self.target_label)
        self.targets = QListWidget()
        self.targets.setMaximumHeight(180)
        self.targets.itemChanged.connect(self.targets_changed)
        side_layout.addWidget(self.targets)
        self.legacy_button = button("Legacy-Zuordnungen geprüft", "pipeline_legacy_checked",
                                     self.clear_legacy)
        side_layout.addWidget(self.legacy_button)
        splitter.addWidget(side)
        splitter.setSizes([240, 800, 400])
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
        appearance().changed.connect(self.refresh_icons)

    def refresh_icons(self):
        for index in range(self.script_library.count()):
            self.script_library.item(index).setIcon(kind_icon("pipeline"))
        for index in range(self.operations.count()):
            self.operations.setItemIcon(index, kind_icon("pipeline"))
        for index in range(self.asset_choices.count()):
            self.asset_choices.setItemIcon(index, kind_icon("asset"))

    def safe(self, call):
        try:
            return call()
        except (StudioError, OSError, ValueError, KeyError, TypeError) as error:
            show_error(self, error)
            return None

    def fill_operations(self):
        self.operations.clear()
        self.script_library.clear()
        for key, manifest in self.manifests.items():
            if (
                is_workflow(self.state["recipe"])
                and key != "source"
                and not key.startswith(("tool:", "flow:"))
            ):
                continue
            title = manifest["name"]
            if key.startswith(("tool:", "flow:")):
                title += " · " + manifest["version"]
            self.operations.addItem(kind_icon("pipeline"), title, key)
            if key != "source":
                item = QListWidgetItem(kind_icon("pipeline"), title)
                item.setData(Qt.UserRole, key)
                item.setToolTip(manifest["description"] + "\n" + key)
                self.script_library.addItem(item)
        preferred = next((node["operation"] for node in self.state["recipe"]["steps"]
                          if node["operation"].startswith("python:") and
                          node["operation"] in self.manifests), "graphics")
        self.operations.setCurrentIndex(self.operations.findData(preferred))
        if self.operations.currentIndex() < 0 and self.operations.count():
            self.operations.setCurrentIndex(min(1, self.operations.count() - 1))
        self.filter_scripts(self.script_search.text())

    def filter_scripts(self, text):
        for index in range(self.script_library.count()):
            item = self.script_library.item(index)
            item.setHidden(text.casefold() not in (item.text() + item.toolTip()).casefold())

    def choose_script(self, item):
        self.operations.setCurrentIndex(self.operations.findData(item.data(Qt.UserRole)))

    def insert_script(self, item):
        self.choose_script(item)
        self.add_step(None, 330, len(self.state["recipe"]["steps"]) * 150)

    def add_asset(self):
        identifier = self.asset_choices.currentData()
        if not identifier or identifier in self.state["inputs"]:
            return
        def change(state):
            state["positions"]["asset_" + identifier] = {"x": 0, "y": len(state["inputs"]) * 180}
            state["inputs"].append(identifier)
        self.safe(lambda: self.mutate("Asset einblenden", change))

    def showEvent(self, event):
        super().showEvent(event)
        if self.initial_view:
            self.initial_view = False
            QTimer.singleShot(0, lambda: self.fit_steps(minimum=0.75))

    def fit_steps(self, *, minimum=0):
        bounds = self.canvas.scene().itemsBoundingRect().adjusted(-40, -40, 40, 40)
        self.canvas.fitInView(bounds, Qt.KeepAspectRatio)
        if self.canvas.transform().m11() > 1:
            self.canvas.resetTransform()
            self.canvas.centerOn(bounds.center())
        elif self.canvas.transform().m11() < minimum:
            self.canvas.resetTransform()
            self.canvas.scale(minimum, minimum)
            visible = self.canvas.mapToScene(self.canvas.viewport().rect()).boundingRect()
            self.canvas.centerOn(
                bounds.left() + visible.width() / 2, bounds.top() + visible.height() / 2
            )

    def actual_size(self):
        self.canvas.resetTransform()
        item = self.canvas.items_by_id.get(self.selected)
        if item:
            self.canvas.centerOn(item)

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
            self.inherited = (
                {} if self.draft_save else self.service.inherited_assets(self.identifier)
            )
            inputs = [self.project.catalog.get(key) for key in
                      dict.fromkeys([*self.state["inputs"], *self.inherited])]
            bindings = set(self.state["bindings"]) | set(self.inherited)
            definitions = [AssetService(self.project).definition(asset.id) for asset in inputs
                           if asset.id in bindings and "asset_definition" in asset.data]
            profiles = ProfileService(self.project).profiles()
            outputs = recipe_outputs(recipe, self.manifests, profiles, definitions)
            self.canvas.render_recipe(recipe, self.state["positions"], self.manifests,
                                       self.selected, self.state["legacy"], inputs,
                                       bindings, outputs, self.inherited)
            self.targets.clear()
            has_graphics = any(self.manifests.get(node["operation"], {}).get("profile_targets")
                               for node in recipe["steps"] if node["enabled"])
            self.target_label.setVisible(has_graphics)
            self.targets.setVisible(has_graphics)
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
            self.status.setText(
                saved + f"{len(bindings)} Assets verbunden · " + detail)
            self.legacy_button.setVisible(bool(recipe["legacy_unresolved"]))
            self.show_package_actions()
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

    def open_step(self, identifier):
        self.select_step(identifier)
        node = next(
            (node for node in self.state["recipe"]["steps"] if node["id"] == identifier), None
        )
        if node and node["operation"].startswith(("tool:", "flow:")):
            self.entry_open_requested.emit(node["operation"])

    def show_properties(self):
        while self.form.rowCount():
            self.form.removeRow(0)
        selected = self.canvas.output_nodes.get(self.selected, self.selected or "")
        if selected.startswith("asset_"):
            asset = self.project.catalog.get(selected.removeprefix("asset_"))
            self.form.addRow(label(asset.title + "\nPort auf ein Skript ziehen, um dieses Asset "
                                   "mit der Pipeline zu verbinden."))
            return
        node = next((v for v in self.state["recipe"]["steps"] if v["id"] == selected), None)
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
            if node["operation"].startswith(("tool:", "flow:")):
                self.form.addRow(
                    button(
                        "Baustein / Teilablauf öffnen",
                        "workflow_open_entry",
                        lambda: self.entry_open_requested.emit(node["operation"]),
                    )
                )
                self.form.addRow(
                    label("Paket " + manifest["package_id"] + " · " + manifest["version"])
                )
                for port, kind in manifest["inputs"].items():
                    self.form.addRow(label("Eingang: " + port + " · " + kind))
                for name, output in self.state["recipe"].get("outputs", {}).items():
                    if output["node"] != node["id"]:
                        continue
                    folder = QLineEdit(output.get("directory", "Ergebnisse/" + name))
                    folder.setObjectName("workflow_output_directory_" + output["port"])
                    folder.editingFinished.connect(
                        lambda n=name, w=folder: self.output_changed(n, "directory", w.text())
                    )
                    self.form.addRow("Ordner · " + output["port"], folder)
                    publish = QCheckBox("Dateien veröffentlichen")
                    publish.setChecked(output.get("publish", True))
                    publish.clicked.connect(
                        lambda checked, n=name: self.output_changed(n, "publish", checked)
                    )
                    self.form.addRow(publish)
            for key, definition in manifest["parameters"].items():
                if not condition(node["parameters"], definition.get("visible_if", {})):
                    continue
                self.add_parameter(node, key, definition)
            for action in PipelineActions(self.project).for_step(node, "step"):
                self.form.addRow(button(action["name"], "pipeline_action_" + action["id"],
                    lambda checked=False, a=action["id"]: self.package_action(node, a)))

    def show_package_actions(self):
        while self.package_actions.count():
            item = self.package_actions.takeAt(0)
            item.widget().deleteLater()
        actions = PipelineActions(self.project).for_recipe(self.state["recipe"], "recipe")
        for node, action in actions:
            self.package_actions.addWidget(button(action["name"], "pipeline_" + action["id"],
                lambda checked=False, n=node, a=action["id"]: self.package_action(n, a)))

    def package_action(self, node, action_id):
        from .package_actions import invoke_step

        def run():
            values = invoke_step(self.project, node, action_id, self, recipe_id=self.identifier)
            if values is not None and values != node["parameters"]:
                def change(state):
                    target = next(n for n in state["recipe"]["steps"] if n["id"] == node["id"])
                    target["parameters"] = values
                self.mutate("Paketaktion", change)
            self.render()
        self.safe(run)

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
            bindings = spec.get("bindings", {}) if kind == "resource" else {}
            choices[1:1] = list(bindings)
            for choice in choices:
                if choice in bindings:
                    caption = bindings[choice]
                elif kind == "resource" and choice:
                    caption = self.state["recipe"]["resources"][choice]["name"]
                else:
                    caption = spec.get("choice_labels", {}).get(
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
        widget.setToolTip(spec.get("description", ""))
        disabled = bool(spec.get("disabled_if")) and condition(
            node["parameters"], spec["disabled_if"])
        widget.setEnabled(not disabled)
        self.form.addRow(spec.get("label", key), widget)
        if kind in {"number", "integer", "boolean", "choice", "resource"}:
            allowed = QCheckBox("Lokale Asset-Abweichung erlauben")
            allowed.setEnabled(not disabled)
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

    def output_changed(self, name, field, value):
        self.safe(
            lambda: self.mutate(
                "Ausgabe ändern",
                lambda state: state["recipe"]["outputs"][name].update({field: value}),
            )
        )

    def add_step(self, source=None, x=0, y=0):
        def change(state):
            operation = self.operations.currentData()
            node = step(operation, self.manifests[operation])
            state["recipe"]["steps"].append(node)
            if is_workflow(state["recipe"]):
                for port, spec in (
                    self.manifests[operation].get("ports", {}).get("outputs", {}).items()
                ):
                    name = "out_" + node["id"].replace("-", "")[:12] + "_" + port[:30]
                    state["recipe"]["outputs"][name] = {
                        "node": node["id"],
                        "port": port,
                        **{k: v for k, v in spec.items() if k != "required"},
                    }
            state["positions"][node["id"]] = {"x": x, "y": y}
            if source:
                actual = self.source_node(state, source)
                previous = next(n for n in state["recipe"]["steps"] if n["id"] == actual)
                left = self.manifests[previous["operation"]]["outputs"]
                right = self.manifests[operation]["inputs"]
                choices = [
                    (out, into)
                    for out, kind in left.items()
                    for into, expected in right.items()
                    if compatible(kind, expected)
                ]
                if len(choices) == 1:
                    out, into = choices[0]
                    state["recipe"]["connections"].append(
                        {"from": actual, "out": out, "to": node["id"], "in": into}
                    )
            self.selected = node["id"]
        self.safe(lambda: self.mutate("Schritt hinzufügen", change))

    def connect_steps(self, source, target):
        ports = ("image", "image")
        if is_workflow(self.state["recipe"]):
            nodes = {node["id"]: node for node in self.state["recipe"]["steps"]}
            left = (
                {"image": "image"}
                if source.startswith("asset_")
                else self.manifests.get(nodes.get(source, {}).get("operation"), {}).get(
                    "outputs", {}
                )
            )
            right = self.manifests.get(nodes.get(target, {}).get("operation"), {}).get("inputs", {})
            choices = {
                out + " (" + kind + ") → " + into + " (" + expected + ")": (out, into)
                for out, kind in left.items()
                for into, expected in right.items()
                if compatible(kind, expected)
            }
            if not choices:
                self.status.setText("Keine kompatiblen Ein-/Ausgänge zwischen diesen Bausteinen.")
                return
            selected = next(iter(choices))
            if len(choices) > 1:
                selected, accepted = QInputDialog.getItem(
                    self, "Anschlüsse verbinden", "Dateifluss", list(choices), 0, False
                )
                if not accepted:
                    return
            ports = choices[selected]
        def change(state):
            actual = self.source_node(state, source)
            edge = {"from": actual, "out": ports[0], "to": target, "in": ports[1]}
            if not source.startswith("asset_") or edge not in state["recipe"]["connections"]:
                state["recipe"]["connections"].append(edge)
        self.safe(lambda: self.mutate("Asset / Skript verbinden", change))

    @staticmethod
    def source_node(state, identifier):
        if not identifier.startswith("asset_"):
            return identifier
        asset_id = identifier.removeprefix("asset_")
        if asset_id not in state["inputs"]:
            raise StudioError("validation", "Asset zuerst einblenden.")
        if asset_id not in state["bindings"]:
            state["bindings"] = sorted([*state["bindings"], asset_id])
        node = next((n for n in state["recipe"]["steps"] if n["operation"] == "source"), None)
        if node is None:
            raise StudioError("validation", "Zuerst einen Asset-Eingang hinzufügen.")
        return node["id"]

    def reconnect(self, edge_id, source, target):
        if edge_id not in self.canvas.recipe_edges:
            return
        index = self.canvas.recipe_edges[edge_id]
        previous_asset = self.canvas.asset_edges.get(edge_id)
        def change(state):
            actual = self.source_node(state, source)
            if previous_asset and source.startswith("asset_") and \
                    source != "asset_" + previous_asset:
                state["bindings"] = [key for key in state["bindings"] if key != previous_asset]
            state["recipe"]["connections"][index].update({"from": actual, "to": target})
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
        selected_edges = {item.identifier for item in self.canvas.scene().selectedItems()
                          if isinstance(item, EdgeItem)}
        edges = {self.canvas.recipe_edges[key] for key in selected_edges
                 if key in self.canvas.recipe_edges and key not in self.canvas.asset_edges}
        unbind = {key.removeprefix("asset_") for key in keys if key.startswith("asset_")}
        unbind.update(self.canvas.asset_edges[key] for key in selected_edges
                      if key in self.canvas.asset_edges)
        def change(state):
            if unbind & (set(self.inherited) - set(state["bindings"])):
                raise StudioError("validation", "Diese Assets erben eine Regel. "
                                  "Die Zuweisung unter Zuweisungen / Regeln ändern.")
            state["bindings"] = [key for key in state["bindings"] if key not in unbind]
            state["inputs"] = [key for key in state["inputs"] if "asset_" + key not in keys]
            recipe = state["recipe"]
            recipe["steps"] = [n for n in recipe["steps"] if n["id"] not in keys]
            if is_workflow(recipe):
                recipe["outputs"] = {
                    k: v for k, v in recipe["outputs"].items() if v["node"] not in keys
                }
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
        if self.draft_save:

            def save_draft():
                self.draft_save(deepcopy(self.state["recipe"]))
                self.baseline = deepcopy(self.state)
                self.changed = True
                self.render()
                return True

            return bool(self.safe(save_draft))
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
                self.service.set_bound_assets(record.id, expected["bindings"], value["bindings"])
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
            self.saved.emit()
            return True
        return bool(self.safe(commit))

    def asset_resources(self):
        from .reference_materials import ReferenceMaterialsDialog

        assets = {
            self.project.catalog.get(identifier).title + " · " + identifier[:8]: identifier
            for identifier in set(self.state["inputs"]) | set(self.inherited)
        }
        if not assets:
            self.status.setText("Zuerst ein Asset im Ablauf einblenden.")
            return
        selected, accepted = QInputDialog.getItem(
            self, "Assetreferenzen / Masken", "Asset", list(assets), 0, False
        )
        if accepted:
            self.safe(lambda: ReferenceMaterialsDialog(self.project, assets[selected], self).exec())

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

    def assign(self):
        from .pipeline_auxiliary import AssignmentDialog
        if self.save():
            self.safe(lambda: AssignmentDialog(self.project, self.identifier, self).exec())
            self.state["bindings"] = self.service.bound_assets(self.identifier)
            self.state["inputs"] = sorted(set(self.state["inputs"]) | set(self.state["bindings"]))
            self.baseline = deepcopy(self.state)
            self.render()

    def run_pipeline(self):
        from .pipeline_auxiliary import PipelineRunDialog
        if self.save():
            self.safe(lambda: PipelineRunDialog(self.project, self.identifier, self).exec())

    def export(self):
        from .pipeline_exchange_dialogs import export_pipeline
        if self.save():
            if is_workflow(self.state["recipe"]):
                from ..application.tool_exchange import ToolExchange

                path, _ = QFileDialog.getSaveFileName(
                    self,
                    "Ablauf mit allen Werkzeugpaketen exportieren",
                    "ablauf.zip",
                    "ZIP (*.zip)",
                )
                if path:
                    self.safe(lambda: ToolExchange(self.project).export(self.identifier, path))
                return
            self.safe(lambda: export_pipeline(self.project, self.identifier, self))

    def plugins(self):
        if not is_workflow(self.state["recipe"]):
            from .pipeline_exchange_dialogs import manage_plugins

            self.safe(lambda: manage_plugins(self.project, self))
            self.manifests = self.service.manifests()
            self.fill_operations()
            self.render()
            return
        from .processing import ProcessingDialog

        dialog = ProcessingDialog(self.project, self)
        self.safe(dialog.exec)
        dialog.deleteLater()
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
