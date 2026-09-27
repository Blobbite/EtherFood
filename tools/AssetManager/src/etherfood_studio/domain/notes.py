"""Backward-compatible note classification and finite, safe presentation options."""

from .models import Record, StudioError

NOTE_COLORS = {
    "yellow": ("Gelb", "#fff1ad"), "blue": ("Blau", "#cfe6ff"),
    "green": ("Grün", "#d5edcd"), "pink": ("Rosa", "#f9d2e1"),
    "orange": ("Orange", "#ffe0b3"), "purple": ("Lila", "#e4d7fc"),
}
NOTE_TEMPLATES = {"Freie Notiz", "Testnotiz"}
NOTE_WORD_LIMIT = 100
NOTE_POSITION_LIMIT = 100_000


def note_word_count(body: str) -> int:
    """Count whitespace-separated words, ignoring standalone bullet markers."""
    return sum(word not in {"-", "*", "+", "[x]", "[X]", "#", "##"}
               for word in body.replace("[ ]", "[x]").split())


def validate_note_length(body: str, previous: str | None = None) -> None:
    """Keep legacy text intact while bounding new and edited post-it contents."""
    if body != previous and note_word_count(body) > NOTE_WORD_LIMIT:
        raise StudioError("validation", "Notizen sind auf 100 Wörter begrenzt. "
                          "Längere Texte bitte in der Dokumentation aufbewahren.")


def is_note(record: Record) -> bool:
    return (record.kind == "document" and record.data.get("document_type") == "manual"
            and record.data.get("template", "Freie Notiz") in NOTE_TEMPLATES)


def validate_note_style(data: dict) -> None:
    color = data.get("note_color", "yellow")
    if not isinstance(color, str) or color not in NOTE_COLORS:
        raise StudioError("validation", "Unbekannte Notizfarbe.")
    if not isinstance(data.get("note_pinned", False), bool):
        raise StudioError("validation", "Anheften muss ein Wahrheitswert sein.")


def validate_note_position(value: dict) -> None:
    if (not isinstance(value, dict) or set(value) != {"x", "y"}
            or any(isinstance(axis, bool) or not isinstance(axis, (int, float))
                   or not 0 <= axis <= NOTE_POSITION_LIMIT
                   for axis in value.values())):
        raise StudioError("validation", "Ungültige Position auf der Notiz-Pinnwand.")
