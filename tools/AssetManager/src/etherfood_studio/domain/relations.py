"""Typed relationships: ownership, reuse and prerequisites are independent."""

from .models import Record, StudioError

CARD_KINDS = frozenset({"project", "global", "act", "chapter", "asset", "package", "note",
                        "pipeline"})
PARENTS = {
    "pipeline": {"project"},
    "global": {"project"}, "act": {"project"}, "chapter": {"act"},
    "asset": {"global", "act", "chapter", "package"},
    "package": {"global", "act", "chapter", "package"},
    "note": {"global", "act", "chapter", "package", "asset"},
}


def validate_relation(source: Record, target: Record, kind: str, edges: list[dict]) -> None:
    if source.id == target.id or source.archived or target.archived:
        raise StudioError("validation", "Selbstbezüge und archivierte Karten sind unzulässig.")
    if source.kind not in CARD_KINDS or target.kind not in CARD_KINDS:
        raise StudioError("validation", "Verbindungen benötigen Projektkarten.")
    if kind == "belongs_to":
        if target.kind not in PARENTS.get(source.kind, set()):
            raise StudioError("validation", "Dieser Kartentyp passt nicht zur gewählten Ebene.")
    elif kind == "uses":
        if source.kind not in {"global", "act", "chapter", "package"} \
                or target.kind not in {"asset", "package"}:
            raise StudioError("validation", "Verwendung benötigt eine Ebene und ein Asset/Paket.")
    elif kind != "depends_on":
        raise StudioError("validation", "Unbekannter Verbindungstyp.")
    if kind in {"belongs_to", "depends_on"}:
        pending = [target.id]
        seen = set()
        while pending:
            node = pending.pop()
            if node == source.id:
                raise StudioError("validation", "Die Verbindung würde einen Zyklus erzeugen.")
            if node not in seen:
                seen.add(node)
                pending.extend(edge["target_id"] for edge in edges
                               if edge["kind"] == kind and edge["source_id"] == node)
