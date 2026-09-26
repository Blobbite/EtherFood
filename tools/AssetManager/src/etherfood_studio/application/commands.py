"""Undoable local commands, deliberately excluding external deployments."""

from dataclasses import dataclass
from typing import Callable

from ..domain.models import StudioError
from .project_service import ProjectService


@dataclass
class Command:
    title: str
    forward: Callable[[], None]
    backward: Callable[[], None]


class Commands:
    def __init__(self, project: ProjectService) -> None:
        self.project = project
        self.done: list[Command] = []
        self.undone: list[Command] = []

    def execute(self, command: Command) -> None:
        with self.project.catalog.transaction():
            command.forward()
        self.done.append(command)
        self.undone.clear()

    def undo(self) -> None:
        if not self.done:
            return
        command = self.done[-1]
        with self.project.catalog.transaction():
            command.backward()
        self.done.pop()
        self.undone.append(command)

    def redo(self) -> None:
        if not self.undone:
            return
        command = self.undone[-1]
        with self.project.catalog.transaction():
            command.forward()
        self.undone.pop()
        self.done.append(command)

    def layout(self, identifier: str, data: dict) -> None:
        before = self.project.catalog.layout(identifier)
        self.execute(Command("Ansicht ändern",
                             lambda: self.project.catalog.save_layout(identifier, data),
                             lambda: self.project.catalog.save_layout(identifier, before)))

    def layouts(self, values: dict[str, dict]) -> None:
        before = {key: self.project.catalog.layout(key) for key in values}

        def write(layouts: dict[str, dict]) -> None:
            for key, value in layouts.items():
                self.project.catalog.save_layout(key, value)

        self.execute(Command("Anordnung ändern", lambda: write(values), lambda: write(before)))

    def create_card(self, kind: str, title: str, parent: str, data: dict | None = None) -> str:
        identity = []

        def forward() -> None:
            if identity:
                record = self.project.catalog.get(identity[0])
                self.project.archive(record.id, False, record.revision_no)
            else:
                identity.append(self.project.create_card(kind, title, parent, data).id)

        def backward() -> None:
            record = self.project.catalog.get(identity[0])
            self.project.archive(record.id, True, record.revision_no)

        self.execute(Command("Karte anlegen", forward, backward))
        return identity[0]

    def link(self, source: str, target: str, kind: str) -> str:
        identity = []

        def forward() -> None:
            edge = self.project.relate(source, target, kind,
                                       identifier=identity[0] if identity else None)
            if not identity:
                identity.append(edge)

        self.execute(Command("Verbindung anlegen", forward,
                             lambda: self.project.unlink(identity[0])))
        return identity[0]

    def unlink(self, identifier: str) -> None:
        edge = next((row for row in self.project.catalog.relations()
                     if row["id"] == identifier), None)
        if edge is None or edge["kind"] == "belongs_to":
            raise StudioError("validation", "Hierarchie stattdessen ausdrücklich umordnen.")
        self.execute(Command("Verbindung lösen", lambda: self.project.unlink(identifier),
                             lambda: self.project.relate(edge["source_id"], edge["target_id"],
                                                         edge["kind"], identifier=identifier)))

    def move(self, identifier: str, parent: str) -> None:
        old = self.project.catalog.get(identifier).owner_id

        def move_to(target: str) -> None:
            current = self.project.catalog.get(identifier)
            self.project.move(identifier, target, current.revision_no)

        self.execute(Command("Karte umordnen", lambda: move_to(parent), lambda: move_to(old)))

    def relink(self, identifier: str, source: str, target: str) -> None:
        edge = next((row for row in self.project.catalog.relations()
                     if row["id"] == identifier), None)
        if edge is None:
            raise StudioError("validation", "Verbindung nicht gefunden.")
        if (source, target) == (edge["source_id"], edge["target_id"]):
            return
        if edge["kind"] == "belongs_to":
            if source != edge["source_id"]:
                raise StudioError("validation", "Nur das Eltern-Ziel der Hierarchie umhängen.")
            self.move(source, target)
            return
        self.execute(Command(
            "Verbindung umhängen", lambda: self.project.relink(identifier, source, target),
            lambda: self.project.relink(identifier, edge["source_id"], edge["target_id"]),
        ))
