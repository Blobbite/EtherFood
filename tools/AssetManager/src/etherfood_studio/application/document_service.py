"""Revisioned Markdown and safe attachments, without generated story content."""

import hashlib
from pathlib import Path

from ..domain.models import MAX_TEXT, Record, StudioError
from ..storage.blob_store import BlobStore, file_hash
from ..storage.paths import real_path
from .project_service import ProjectService

TEMPLATES = {
    "Freie Notiz": "# Notiz\n\n",
    "Aktbeschreibung": "# Aktbeschreibung\n\n## Ziel\n\n## Offene Fragen\n",
    "Kapitelanforderung": "# Kapitelanforderung\n\n## Anforderungen\n\n## Nachweise\n",
    "Asset-Briefing": "# Asset-Briefing\n\n## Verwendungszweck\n\n## Noch zu klären\n",
    "Testnotiz": "# Testnotiz\n\n## Prüfschritte\n\n## Tatsächliches Ergebnis\n\nNicht geprüft.\n",
    "Entscheidung": "# Entscheidung\n\nStatus: Entwurf\n\n## Anlass\n\n## Begründung\n",
}


class DocumentService:
    def __init__(self, project: ProjectService) -> None:
        self.project = project
        self.catalog = project.catalog
        self.blobs = BlobStore(self.catalog, project.config.roots["WORKSPACE_ROOT"], project.config)

    def documents(self, owner_id: str) -> list[Record]:
        return [row for row in self.catalog.records()
                if row.kind == "document" and row.owner_id == owner_id]

    def create(self, owner_id: str, title: str, body: str = "", *,
               template: str = "Freie Notiz", generated: bool = False) -> Record:
        self.catalog.get(owner_id)
        if any(row.title.casefold() == title.strip().casefold()
               for row in self.documents(owner_id)):
            raise StudioError("conflict", "Dokumenttitel existiert; Revision ausdrücklich wählen.")
        self._validate_body(body)
        if template not in TEMPLATES:
            raise StudioError("validation", "Dokumentvorlage nicht vorhanden.")
        return self.catalog.create("document", title, owner_id, {
            "body": body or TEMPLATES[template],
            "document_type": "generated" if generated else "manual",
            "attachments": [], "template": template,
        })

    @staticmethod
    def _validate_body(body: str) -> None:
        if not isinstance(body, str) or len(body.encode("utf-8")) > MAX_TEXT:
            raise StudioError("validation", "Markdown überschreitet die Grenze von 1 MiB.")

    def save(self, identifier: str, body: str, expected_revision: int) -> Record:
        self._validate_body(body)
        record = self.catalog.get(identifier)
        self.project._check_revision(record, expected_revision)
        if record.kind != "document" or record.data.get("document_type") != "manual":
            raise StudioError("validation", "Generierte Berichte sind hier schreibgeschützt.")
        return self.catalog.save(record, data=record.data | {"body": body})

    def attach(self, identifier: str, source: Path, expected_revision: int) -> Record:
        record = self.catalog.get(identifier)
        self.project._check_revision(record, expected_revision)
        if record.kind != "document" or record.data["document_type"] != "manual":
            raise StudioError("validation", "Anhang benötigt ein manuelles Dokument.")
        imported = self.blobs.import_file(source)
        attachments = [*record.data["attachments"], imported]
        return self.catalog.save(record, data=record.data | {"attachments": attachments})

    def attachment_path(self, identifier: str, index: int) -> Path:
        attachment = self.catalog.get(identifier).data["attachments"][index]
        path = self.blobs.path_for(attachment["sha256"])
        if not path.is_file() or file_hash(path) != attachment["sha256"]:
            raise StudioError("integrity", "Anhang fehlt oder ist beschädigt.")
        return path

    def import_markdown(self, owner_id: str, source: Path, *, identifier: str | None = None,
                        expected_revision: int | None = None) -> Record:
        path = real_path(source)
        if path.suffix.lower() not in {".md", ".markdown"} or path.stat().st_size > MAX_TEXT:
            raise StudioError("validation", "Eine Markdown-Datei bis 1 MiB auswählen.")
        try:
            raw = path.read_bytes()
            body = raw.decode("utf-8")
        except UnicodeError as exc:
            raise StudioError("validation", "Markdown muss UTF-8 sein.") from exc
        with self.catalog.transaction():
            if identifier:
                record = self.catalog.get(identifier)
                if record.owner_id != owner_id:
                    raise StudioError("validation", "Dokument gehört zu einer anderen Karte.")
                record = self.save(identifier, body, expected_revision)
            else:
                record = self.create(owner_id, path.stem, body)
            provenance = {"original_name": path.name, "sha256": hashlib.sha256(raw).hexdigest()}
            return self.catalog.save(record, data=record.data | {"provenance": provenance})

    def search(self, query: str, *, scope_id: str | None = None,
               document_type: str | None = None) -> list[Record]:
        scope = self.project.descendants(scope_id) if scope_id else None
        needle = query.casefold()
        return [row for row in self.catalog.records() if row.kind == "document"
                and (scope is None or row.owner_id in scope)
                and (document_type is None or row.data.get("document_type") == document_type)
                and needle in (row.title + "\n" + row.data.get("body", "")).casefold()]
