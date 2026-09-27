"""Backward-compatible note classification and finite, safe presentation options."""

from .models import Record, StudioError

NOTE_COLORS = {
    "yellow": ("Gelb", "#fff1ad"), "blue": ("Blau", "#cfe6ff"),
    "green": ("Grün", "#d5edcd"), "pink": ("Rosa", "#f9d2e1"),
    "orange": ("Orange", "#ffe0b3"), "purple": ("Lila", "#e4d7fc"),
}
NOTE_TEMPLATES = {"Freie Notiz", "Testnotiz"}


def is_note(record: Record) -> bool:
    return (record.kind == "document" and record.data.get("document_type") == "manual"
            and record.data.get("template", "Freie Notiz") in NOTE_TEMPLATES)


def validate_note_style(data: dict) -> None:
    color = data.get("note_color", "yellow")
    if not isinstance(color, str) or color not in NOTE_COLORS:
        raise StudioError("validation", "Unbekannte Notizfarbe.")
    if not isinstance(data.get("note_pinned", False), bool):
        raise StudioError("validation", "Anheften muss ein Wahrheitswert sein.")
