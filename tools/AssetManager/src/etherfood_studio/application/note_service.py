"""Post-its are existing manual documents, with optional presentation metadata."""

from ..domain.models import Record, StudioError
from ..domain.notes import is_note, validate_note_style
from .document_service import DocumentService


class NoteService(DocumentService):
    def notes(self, scope_id: str, query: str = "", color: str | None = None) -> list[Record]:
        rows = [row for row in self.search(query, scope_id=scope_id) if is_note(row)
                and (color is None or row.data.get("note_color", "yellow") == color)]
        return sorted(rows, key=lambda row: (not row.data.get("note_pinned", False),
                                             row.title.casefold(), row.id))

    def write(self, owner_id: str, title: str, body: str, *, identifier: str | None = None,
              expected_revision: int | None = None, color: str = "yellow",
              pinned: bool = False) -> Record:
        self._validate_body(body)
        style = {"note_color": color, "note_pinned": pinned}
        validate_note_style(style)
        with self.catalog.transaction():
            self.project.require_active_card(owner_id)
            if identifier:
                record = self.catalog.get(identifier)
                self.project._check_revision(record, expected_revision)
                if not is_note(record) or record.archived or record.owner_id != owner_id:
                    raise StudioError("validation", "Keine bearbeitbare Notiz in diesem Bereich.")
                if any(row.id != record.id and row.title.casefold() == title.strip().casefold()
                       for row in self.documents(owner_id)):
                    raise StudioError("conflict", "Dokumenttitel existiert bereits.")
                data = record.data | style | {"body": body}
                if data == record.data and title.strip() == record.title:
                    return record
                return self.catalog.save(record, title=title, data=data)
            record = self.create(owner_id, title, body)
            return self.catalog.save(record, data=record.data | style | {"body": body})
