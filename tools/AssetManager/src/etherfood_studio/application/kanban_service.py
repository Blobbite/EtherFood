"""Read-only Kanban projection of existing tasks, ownership and shared usages."""

from dataclasses import dataclass

from ..domain.models import Record
from .issue_service import IssueService, PRIORITIES
from .project_service import ProjectService


@dataclass(frozen=True)
class TaskGroup:
    id: str
    title: str
    kind: str


@dataclass(frozen=True)
class BoardEntry:
    record: Record
    groups: tuple[TaskGroup, ...]
    location: str
    shared: bool


class KanbanService:
    def __init__(self, project: ProjectService) -> None:
        self.project = project

    def entries(self, scope_id: str, query: str = "", *, kind: str | None = None,
                asset_type: str | None = None) -> list[BoardEntry]:
        cards = self.project.cards()
        positions = {card.id: index for index, card in enumerate(cards)}
        scope = self.project.catalog.get(scope_id)
        root = self.project.project()
        entries = []
        for record in IssueService(self.project).search(
                query, scope_id=scope_id, kind=kind, asset_type=asset_type):
            path = []
            owner = self.project.catalog.get(record.owner_id)
            while owner.owner_id:
                path.insert(0, owner)
                owner = self.project.catalog.get(owner.owner_id)
            shared = scope.kind != "project" and scope_id not in [card.id for card in path]
            if scope.kind != "project" and not shared:
                path = path[next(index for index, card in enumerate(path) if card.id == scope_id):]
            groups = []
            if shared:
                groups.append(TaskGroup("shared", "Verwendete Assets (Herkunft)", "asset"))
            if not path or path[0].kind == "global":
                groups.append(TaskGroup(root.id, "Projektweite Aufgaben", "global"))
                if path:
                    path = path[1:]
            groups.extend(TaskGroup(card.id, card.title, card.kind) for card in path)
            entries.append(BoardEntry(record, tuple(groups),
                                       self.project.breadcrumb(record.owner_id), shared))
        return sorted(entries, key=lambda entry: (
            entry.shared,
            tuple(positions.get(group.id, -1) for group in entry.groups),
            -PRIORITIES.index(entry.record.data["priority"]),
            entry.record.title.casefold(), entry.record.id,
        ))
