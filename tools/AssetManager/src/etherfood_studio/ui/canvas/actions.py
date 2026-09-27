"""Pointer endpoint creation and arrangements affect only the intended selection."""

import math
from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QInputDialog, QMenu

from ...application.canvas_service import CanvasService
from ..presentation import kind_icon

if TYPE_CHECKING:
    from ..main_window import MainWindow


class CanvasActions:
    def __init__(self, window: "MainWindow") -> None:
        self.window = window

    def create_at(self, source: str, x: float, y: float) -> None:
        window = self.window
        if not window.project:
            return
        window.perform(lambda: self._create_at(source, x, y))

    def _create_at(self, source: str, x: float, y: float) -> None:
        window = self.window
        service = CanvasService(window.commands)
        owner = service.owner(source)
        source_record = window.project.catalog.get(source)
        menu = QMenu(window)
        menu.addSection("Neu unter: " + owner.title)
        names = {"note": "Notiz", "document": "Dokumentation", "task": "Aufgabe",
                 "issue": "Issue", "asset": "Asset", "package": "Ordner / Paket",
                 "chapter": "Kapitel", "act": "Akt"}
        choices = {}
        for kind in service.kinds(source):
            action = menu.addAction(kind_icon(kind), names[kind] + " …")
            action.setObjectName("canvas_create_" + kind)
            choices[action] = kind
        point = window.canvas.mapFromScene(QPointF(x, y))
        chosen = menu.exec(window.canvas.viewport().mapToGlobal(point))
        kind = choices.get(chosen)
        menu.deleteLater()
        if not kind:
            return
        title, accepted = QInputDialog.getText(window, names[kind] + " anlegen", "Name")
        if not accepted or not window.prepare_content_change():
            return
        record = service.create(source, source_record.revision_no, kind, title, x, y)
        window.refresh()
        window.canvas.focus_card(record.id, center=False)
        window.statusBar().showMessage(
            names[kind] + " angelegt und zugeordnet · Doppelklick: bearbeiten · "
            "Strg+Z: rückgängig", 9000)

    def add_arrangements(self, menu: QMenu, anchor: str | None = None) -> None:
        selected = self.window.canvas.selected_ids()
        if len(selected) < 2:
            return
        anchor = anchor or sorted(selected)[0]
        menu.addSeparator()
        submenu = QMenu("Auswahl anordnen", menu)
        menu.addMenu(submenu)
        for mode, title in (("circle", "Kreis um diese Karte"), ("line", "Linie ab dieser Karte")):
            action = submenu.addAction(title)
            action.setObjectName("canvas_arrange_" + mode)
            action.triggered.connect(lambda checked=False, value=mode: self.arrange(anchor, value))

    def arrange(self, anchor: str, mode: str) -> None:
        window = self.window
        canvas = window.canvas
        if mode not in {"circle", "line"} or anchor not in canvas.items_by_id:
            return
        selected = canvas.selected_ids()
        peers = [canvas.items_by_id[key] for key in selected if key != anchor]
        peers.sort(key=lambda item: (item.y(), item.x(), item.identifier))
        if not peers:
            return
        box = canvas.items_by_id[anchor].sceneBoundingRect()
        diameter = max(math.hypot(item.rect().width(), item.rect().height()) for item in peers)
        radius = (math.hypot(box.width(), box.height()) + diameter) / 2 + 40
        if len(peers) > 1:
            radius = max(radius, (diameter + 40) / (2 * math.sin(math.pi / len(peers))))
        positions = {}
        next_x = box.right() + 40
        for index, item in enumerate(peers):
            size = item.rect().size()
            if mode == "circle":
                angle = 2 * math.pi * index / len(peers)
                point = box.center() + QPointF(math.cos(angle), math.sin(angle)) * radius
                x, y = point.x() - size.width() / 2, point.y() - size.height() / 2
            else:
                x, y = next_x, box.center().y() - size.height() / 2
                next_x += size.width() + 40
            positions[item.identifier] = {"x": x, "y": y}
        self.move_many(positions)
        canvas.select_many(selected)

    def move_many(self, positions: dict[str, dict]) -> None:
        window = self.window
        if not window.project or not positions:
            return
        selected = window.canvas.selected_ids()
        values = {}
        for identifier, point in positions.items():
            layout = window.project.catalog.layout(identifier) | point
            if "manual" in layout:
                layout["manual"] = point.copy()
            values[identifier] = layout
        if window.perform(lambda: window.commands.layouts(values)):
            window.refresh()
            window.canvas.select_many(selected)
