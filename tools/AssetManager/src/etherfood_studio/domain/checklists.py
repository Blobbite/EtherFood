"""Small revisioned task checklists, independent of asset approvals."""

from uuid import UUID

from .assets import require


def validate_checklist(value: list[dict]) -> list[dict]:
    require(isinstance(value, list) and len(value) <= 200,
            "Eine To-do-Liste darf höchstens 200 Punkte enthalten.")
    result, identifiers = [], set()
    for item in value:
        require(isinstance(item, dict) and set(item) == {"id", "text", "done"},
                "Ungültiger To-do-Eintrag.")
        identifier, text, done = item["id"], item["text"], item["done"]
        require(isinstance(identifier, str), "To-do-ID muss eine UUID sein.")
        try:
            UUID(identifier)
        except (ValueError, AttributeError):
            require(False, "To-do-ID muss eine UUID sein.")
        require(identifier not in identifiers, "Doppelte To-do-ID.")
        require(isinstance(text, str) and 0 < len(text.strip()) <= 500,
                "To-do-Text benötigt 1 bis 500 Zeichen.")
        require(type(done) is bool, "To-do-Zustand muss wahr oder falsch sein.")
        identifiers.add(identifier)
        result.append({"id": identifier, "text": text.strip(), "done": done})
    return result
