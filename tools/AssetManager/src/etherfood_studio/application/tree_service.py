"""Tree drops distinguish ownership from shared usage; no default Qt tree mutation."""

from dataclasses import dataclass

from ..domain.models import Record, StudioError
from ..domain.relations import validate_relation
from .commands import Commands


@dataclass(frozen=True)
class TreeDrag:
    record: Record
    edge: dict | None = None


class TreeService:
    def __init__(self, commands: Commands) -> None:
        self.commands = commands
        self.project = commands.project
        self.catalog = self.project.catalog

    def capture(self, identifier: str, edge_id: str | None = None) -> TreeDrag:
        record = self.catalog.get(identifier)
        edge = next((row for row in self.catalog.relations() if row["id"] == edge_id), None)
        if edge_id and (not edge or edge["kind"] != "uses" or edge["target_id"] != identifier):
            raise StudioError("conflict", "Verwendungs-Verweis ist nicht mehr aktuell.")
        return TreeDrag(record, edge)

    def validate(self, drag: TreeDrag, target_id: str, copy: bool = False) -> str:
        record = self.catalog.get(drag.record.id)
        self.project._check_revision(record, drag.record.revision_no)
        target = self.project.require_active_card(target_id)
        self.project.require_active_card(record.id if record.kind in {"asset", "package"}
                                         else record.owner_id or record.id)
        if record.archived:
            raise StudioError("validation", "Archivierte Inhalte können nicht verschoben werden.")
        if not copy and drag.edge is None:
            self.project.validate_move(record.id, target_id)
            return "move"
        edges = self.catalog.relations()
        if drag.edge:
            current = next((row for row in edges if row["id"] == drag.edge["id"]), None)
            if current != drag.edge:
                raise StudioError("conflict", "Verwendung wurde zwischenzeitlich geändert.")
            self.project.require_active_card(drag.edge["source_id"])
        remaining = [edge for edge in edges if copy or not drag.edge
                     or edge["id"] != drag.edge["id"]]
        validate_relation(target, record, "uses", remaining)
        if any(edge["source_id"] == target_id and edge["target_id"] == record.id
               and edge["kind"] == "uses" for edge in remaining):
            raise StudioError("conflict", "Diese Verwendung existiert am Ziel bereits.")
        return "link" if copy else "relink"

    def apply(self, drag: TreeDrag, target_id: str, copy: bool = False) -> None:
        with self.catalog.transaction():
            action = self.validate(drag, target_id, copy)
            if action == "move":
                self.commands.move(drag.record.id, target_id, drag.record.revision_no)
            elif action == "link":
                self.commands.link(target_id, drag.record.id, "uses")
            else:
                self.commands.relink(drag.edge["id"], target_id, drag.record.id)
