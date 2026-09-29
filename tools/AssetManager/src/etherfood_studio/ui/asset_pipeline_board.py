"""Focused view of one asset's shared recipes, rules, scripts and output folders."""

import json
import os

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import QGraphicsItem, QHBoxLayout, QPlainTextEdit, QVBoxLayout, QWidget

from ..application.pipeline_outputs import OUTPUT_STATES
from ..domain.pipeline_recipes import validate_recipe
from .canvas.items import CardItem, WorkflowIconItem
from .common import button, label
from .pipeline_editor import PipelineCanvas


RULE_STATES = {"active": "Wirksam", "superseded": "Übersteuert", "disabled": "Deaktiviert",
               "blocked": "Konflikt / blockiert", "archived": "Archiviert"}


class AssetPipelineCanvas(PipelineCanvas):
    def begin_connection(self, *args, **kwargs):
        pass  # This is a projection; shared recipe edits belong to its dashboard.

    def update_edges(self):
        super().update_edges()
        for edge in self.edges_by_id.values():
            for handle in edge.handles.values():
                handle.hide()


class AssetPipelineBoard(QWidget):
    recipe_selected = Signal(str)
    recipe_open = Signal(str)
    folder_open = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("asset_pipeline_board")
        self.entries, self.flow_ids = {}, ()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        controls = QHBoxLayout()
        self.caption = label("", "asset_pipeline_board_caption")
        controls.addWidget(self.caption, 1)
        controls.addWidget(button("+", "asset_pipeline_zoom_in",
                                  lambda: self.canvas.scale(1.2, 1.2)))
        controls.addWidget(button("−", "asset_pipeline_zoom_out",
                                  lambda: self.canvas.scale(1 / 1.2, 1 / 1.2)))
        controls.addWidget(button("Board einpassen", "asset_pipeline_fit", self.fit))
        layout.addLayout(controls)
        self.canvas = AssetPipelineCanvas()
        self.canvas.setObjectName("asset_pipeline_canvas")
        self.canvas.setAccessibleName("Pipelines, Regeln und Ausgabeordner dieses Assets")
        self.canvas.setMinimumHeight(300)
        self.canvas.selected.connect(self.select)
        self.canvas.open_requested.connect(self.open)
        layout.addWidget(self.canvas, 1)
        self.details = QPlainTextEdit()
        self.details.setObjectName("asset_pipeline_node_details")
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(110)
        layout.addWidget(self.details)

    def add_card(self, key, title, kind, summary, position, entry, *, icon=True, enabled=True):
        card = WorkflowIconItem(key, title, kind, summary, self.canvas) if icon else \
            CardItem(key, title, kind, summary, self.canvas, 250, 105)
        card.setFlag(QGraphicsItem.ItemIsMovable, False)
        card.grip.hide()
        for port in card.ports.values():
            port.setAcceptedMouseButtons(Qt.NoButton)
            port.setToolTip("Gespeicherter Datenfluss · Änderungen im Projekt-Dashboard")
        card.setOpacity(1 if enabled else 0.5)
        card.setPos(*position)
        card.setToolTip(entry["text"])
        self.canvas.scene().addItem(card)
        self.canvas.items_by_id[key] = card
        self.entries[key] = entry
        return card

    def render(self, asset, rows, manifests):
        canvas = self.canvas
        canvas.rendering = True
        canvas.scene().blockSignals(True)
        canvas.cancel_connection()
        canvas.edges_by_id.clear()
        canvas.items_by_id.clear()
        canvas.legacy_edges.clear()
        canvas.scene().clear()
        canvas.recipe_edges, canvas.asset_edges = {}, {}
        self.entries = {}
        previous = self.flow_ids
        self.flow_ids = tuple(row["recipe"].id for row in rows)
        asset_key = "asset_" + asset.id
        self.add_card(asset_key, asset.title, "asset", "Dieses Asset", (0, 0),
                      {"text": asset.title + "\nNur dieses Asset ist in diesem Board sichtbar."})
        top = 0
        for row in rows:
            top += self.add_recipe(row, manifests, asset_key, top)
        canvas.rendering = False
        canvas.scene().blockSignals(False)
        canvas.update_edges()
        count = sum(row["state"] == "active" for row in rows)
        rules = sum(len(row["rules"]) for row in rows)
        self.caption.setText(f"{asset.title} · {count} wirksame Pipelines · "
                             f"{rules} passende Zuweisungsregeln")
        self.details.setPlainText(
            "Symbol auswählen: Regeln, Parameter und Ordner ansehen. "
            "Pipeline doppelklicken: gemeinsames Projekt-Dashboard öffnen."
            if rows else "Noch keine passende Pipeline-Zuweisung. "
            "Oben eine Projektpipeline auswählen und unter Zuweisungen / Regeln zuordnen.")
        if previous != self.flow_ids or not previous:
            QTimer.singleShot(0, self.fit)

    def add_recipe(self, row, manifests, asset_key, top):
        recipe, data = row["recipe"], row["data"]
        effective = row["state"] == "active"
        prefix = "recipe_" + recipe.id
        rule_text = []
        for rule in row["rules"]:
            scope = "dieses Asset" if rule["asset_id"] else rule["type_id"] or "alle Asset-Typen"
            capabilities = ", ".join(rule["capabilities"])
            rule_text.append(rule["origin"] + ": " + scope +
                             (" · Fähigkeiten: " + capabilities if capabilities else ""))
        text = (recipe.title + " · " + data["category"] + "\n" +
                RULE_STATES[row["state"]] + ": " + row["reason"] + "\n" + "\n".join(rule_text))
        if row["binding"]:
            text += "\nLokale Abweichungen: " + json.dumps(
                row["binding"]["assignment"].data["overrides"], ensure_ascii=False)
        caption = RULE_STATES[row["state"]]
        if effective:
            rule = row["binding"]["assignment"].data
            caption = "Direkt zugewiesen" if rule["asset_id"] else \
                "Typregel · " + rule["type_id"] if rule["type_id"] else \
                "Fähigkeitsregel" if rule["capabilities"] else "Projektstandard"
        self.add_card(prefix, recipe.title, "pipeline", caption, (280, top),
                      {"recipe_id": recipe.id, "text": text}, enabled=effective)
        canvas = self.canvas
        canvas.add_flow_edge(prefix, asset_key, prefix, "")
        if row["state"] in {"superseded", "archived", "blocked"}:
            return 210
        levels, counts, nodes = {}, {}, {}
        for node in validate_recipe(data, manifests):
            if node["operation"] == "source":
                levels[node["id"]], nodes[node["id"]] = -1, prefix
                continue
            level = max((levels[e["from"]] + 1 for e in data["connections"]
                         if e["to"] == node["id"]), default=0)
            index = counts.get(level, 0)
            levels[node["id"]], counts[level] = level, index + 1
            key = prefix + "_" + node["id"]
            nodes[node["id"]] = key
            title = manifests.get(node["operation"], {}).get("name", node["operation"])
            state = "Aktiv" if node["enabled"] else "Deaktiviert · Durchreichen"
            details = text + "\n\n" + title + " · " + state + "\n" + json.dumps(
                node["parameters"], ensure_ascii=False, indent=2)
            self.add_card(key, title, "pipeline", state, (560 + level * 285, top + index * 140),
                          {"recipe_id": recipe.id, "text": details}, icon=False,
                          enabled=effective and node["enabled"])
        for index, edge in enumerate(data["connections"]):
            canvas.add_flow_edge(prefix + "_edge_" + str(index),
                                 nodes[edge["from"]], nodes[edge["to"]], "Bild → Bild")
        right = 560 + (max(levels.values(), default=0) + 1) * 285
        for index, output in enumerate(row["outputs"]):
            key = prefix + "_" + output["id"]
            status = OUTPUT_STATES[output["state"]] if effective else RULE_STATES[row["state"]]
            paths = output["paths"]
            details = output["title"] + " · " + status + "\nOrdner beim Asset:\n" + \
                ("\n".join(paths) if paths else "Kein eigener Ausgabeordner angefordert")
            if output.get("parent"):
                details += "\nInterne Voraussetzung: " + output["parent"]
            summary = paths[0] if paths and effective and output["state"] == "active" else status
            kind = "pipeline" if output["state"] == "internal" else "act"
            self.add_card(key, output["title"], kind, summary,
                          (right + (index % 2) * 225, top + (index // 2) * 170),
                          {"recipe_id": recipe.id, "paths": paths, "text": details},
                          enabled=effective and output["state"] in {"active", "internal"})
        canvas.add_output_edges(row["outputs"], nodes, prefix + "_", active=effective)
        return max(210, max(counts.values(), default=1) * 140 + 50,
                   ((len(row["outputs"]) + 1) // 2) * 170 + 50)

    def fit(self):
        if self.canvas.items_by_id:
            bounds = self.canvas.scene().itemsBoundingRect().adjusted(-30, -30, 30, 30)
            self.canvas.fitInView(bounds, Qt.KeepAspectRatio)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.fit)

    def select(self, identifier):
        entry = self.entries.get(identifier, {})
        self.details.setPlainText(entry.get("text", ""))
        if entry.get("recipe_id"):
            self.recipe_selected.emit(entry["recipe_id"])

    def open(self, identifier):
        entry = self.entries.get(identifier, {})
        if entry.get("paths"):
            self.folder_open.emit(os.path.commonpath(entry["paths"]))
        elif entry.get("recipe_id"):
            self.recipe_open.emit(entry["recipe_id"])
