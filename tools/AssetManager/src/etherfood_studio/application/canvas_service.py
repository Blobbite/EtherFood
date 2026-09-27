"""Atomic creation at a canvas endpoint; reuse the existing ownership rules."""

from ..domain.assets import default_definition
from ..domain.models import Record, StudioError
from ..domain.relations import CARD_KINDS, PARENTS
from .asset_service import AssetService
from .commands import Command, Commands
from .document_service import DocumentService
from .issue_service import IssueService
from .note_service import NoteService


class CanvasService:
    def __init__(self, commands: Commands) -> None:
        self.commands = commands
        self.project = commands.project

    def owner(self, source: str) -> Record:
        record = self.project.catalog.get(source)
        if record.archived:
            raise StudioError("validation", "Archivierte Quelle ist gesperrt.")
        identifier = record.id if record.kind in CARD_KINDS else record.owner_id
        return self.project.require_active_card(identifier)

    def kinds(self, source: str) -> list[str]:
        owner = self.owner(source)
        return ["note", "document", "task", "issue"] + [
            kind for kind in ("asset", "package", "chapter", "act")
            if owner.kind in PARENTS[kind]
        ]

    def create(self, source: str, expected_revision: int, kind: str, title: str,
               x: float, y: float) -> Record:
        catalog = self.project.catalog
        owner = self.owner(source)
        self.project._check_revision(catalog.get(source), expected_revision)
        if kind not in self.kinds(source):
            raise StudioError("validation", "Dieser Kartentyp passt nicht unter die Quelle.")
        catalog.validate_layout({"x": x, "y": y})
        identity: list[Record] = []
        relations: list[dict] = []

        def forward() -> None:
            self.project.require_active_card(owner.id)
            if identity:
                current = catalog.get(identity[0].id)
                self.project._check_revision(current, identity[0].revision_no)
                identity[0] = self.project.archive(current.id, False, current.revision_no)
                return
            self.project._check_revision(catalog.get(source), expected_revision)
            if self.owner(source).id != owner.id:
                raise StudioError("conflict", "Die Quelle wurde inzwischen umgeordnet.")
            if kind == "note":
                record = NoteService(self.project).write(owner.id, title, "")
            elif kind == "document":
                record = DocumentService(self.project).create(
                    owner.id, title, template="Dokumentation")
            elif kind in {"task", "issue"}:
                record = IssueService(self.project).create(owner.id, title, issue=kind == "issue")
            elif kind == "asset":
                record = AssetService(self.project).create(
                    title, owner.id, default_definition().to_data())
            else:
                record = self.project.create_card(kind, title, owner.id)
            catalog.save_layout(record.id, {"x": x, "y": y})
            identity.append(record)
            relations.extend(self.project.affected_relations(record.id))

        def backward() -> None:
            current = catalog.get(identity[0].id)
            self.project._check_revision(current, identity[0].revision_no)
            children = [row for row in catalog.records() if row.owner_id == current.id]
            if children or self.project.affected_relations(current.id) != relations:
                raise StudioError("conflict", "Neue Inhalte/Verwendungen vorhanden; "
                                  "die Erstellung kann nicht mehr zurückgenommen werden.")
            identity[0] = self.project.archive(current.id, True, current.revision_no)

        self.commands.execute(Command("Canvas-Inhalt anlegen", forward, backward))
        return identity[0]
