"""Post-its are existing manual documents, with optional presentation metadata."""

from ..domain.models import Record, StudioError
from ..domain.notes import (
    is_note, validate_note_length, validate_note_position, validate_note_style,
)
from .document_service import DocumentService


class NoteService(DocumentService):
    def position(self, identifier: str) -> dict | None:
        return self.catalog.layout(identifier).get("note_board")

    def place(self, identifier: str, position: dict) -> None:
        """Move a post-it without changing its content revision or its Canvas position."""
        validate_note_position(position)
        with self.catalog.transaction():
            record = self.catalog.get(identifier)
            if not is_note(record) or record.archived:
                raise StudioError("validation", "Keine bearbeitbare Notiz auf dieser Pinnwand.")
            self.project.require_active_card(record.owner_id)
            layout = self.catalog.layout(identifier)
            if layout.get("note_board") != position:
                self.catalog.save_layout(identifier, layout | {"note_board": position})

    def notes(self, scope_id: str, query: str = "", color: str | None = None) -> list[Record]:
        rows = [row for row in self.search(query, scope_id=scope_id) if is_note(row)
                and (color is None or row.data.get("note_color", "yellow") == color)]
        return sorted(rows, key=lambda row: (not row.data.get("note_pinned", False),
                                             row.title.casefold(), row.id))

    def write(self, owner_id: str, title: str, body: str, *, identifier: str | None = None,
              expected_revision: int | None = None, color: str = "yellow",
              pinned: bool = False, position: dict | None = None) -> Record:
        self._validate_body(body)
        style = {"note_color": color, "note_pinned": pinned}
        validate_note_style(style)
        if position is not None:
            validate_note_position(position)
        with self.catalog.transaction():
            self.project.require_active_card(owner_id)
            if identifier:
                record = self.catalog.get(identifier)
                self.project._check_revision(record, expected_revision)
                if not is_note(record) or record.archived or record.owner_id != owner_id:
                    raise StudioError("validation", "Keine bearbeitbare Notiz in diesem Bereich.")
                validate_note_length(body, record.data["body"])
                if any(row.id != record.id and row.title.casefold() == title.strip().casefold()
                       for row in self.documents(owner_id)):
                    raise StudioError("conflict", "Dokumenttitel existiert bereits.")
                data = record.data | style | {"body": body}
                if data != record.data or title.strip() != record.title:
                    record = self.catalog.save(record, title=title, data=data)
            else:
                validate_note_length(body)
                record = self.create(owner_id, title, body)
                record = self.catalog.save(record, data=record.data | style | {"body": body})
            if position is not None:
                self.place(record.id, position)
            return record
