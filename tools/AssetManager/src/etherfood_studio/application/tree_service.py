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
        edge = next(
            (row for row in self.catalog.relations(include_inactive=True) if row["id"] == edge_id),
            None,
        )
        if edge_id and (not edge or edge["kind"] != "uses" or edge["target_id"] != identifier):
            raise StudioError("conflict", "Verwendungs-Verweis ist nicht mehr aktuell.")
        return TreeDrag(record, edge)

    def validate(self, drag: TreeDrag, target_id: str, copy: bool = False) -> str:
        record = self.catalog.get(drag.record.id)
        self.project._check_revision(record, drag.record.revision_no)
        target = self.project.require_active_card(target_id)
        from .lifecycle_service import LifecycleService

        life = LifecycleService(self.project)
        inactive = life.state(drag.edge["id"] if drag.edge else record.id)
        if inactive:
            if copy:
                raise StudioError("validation", "Ablagen werden wiederhergestellt, nicht kopiert.")
            from dataclasses import replace

            restored = replace(record, archived=False)
            if drag.edge:
                self.project.require_active_card(record.id)
                remaining = [e for e in self.catalog.relations() if e["id"] != drag.edge["id"]]
                validate_relation(target, restored, "uses", remaining)
                if any(
                    e["source_id"] == target.id
                    and e["target_id"] == record.id
                    and e["kind"] == "uses"
                    for e in remaining
                ):
                    raise StudioError("conflict", "Verwendung existiert am Ziel bereits.")
            elif record.kind in {"document", "task", "issue"}:
                if target.id in life.subtree(record.id):
                    raise StudioError("validation", "Ungültiges Wiederherstellungsziel.")
            else:
                validate_relation(
                    restored,
                    target,
                    "belongs_to",
                    [e for e in self.catalog.relations() if e["source_id"] != record.id],
                )
                if target.id in life.subtree(record.id):
                    raise StudioError("validation", "Ziel liegt im eigenen Teilbaum.")
            return "restore"
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
            if action == "restore":
                from .lifecycle_service import LifecycleService

                LifecycleService(self.project).command(
                    self.commands,
                    [drag.edge["id"] if drag.edge else drag.record.id],
                    target=target_id,
                )
            elif action == "move":
                self.commands.move(drag.record.id, target_id, drag.record.revision_no)
            elif action == "link":
                self.commands.link(target_id, drag.record.id, "uses")
            else:
                self.commands.relink(drag.edge["id"], target_id, drag.record.id)
