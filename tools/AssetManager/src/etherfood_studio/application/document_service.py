"""Revisioned Markdown and safe attachments, without generated story content."""

import hashlib
import os
from pathlib import Path

from ..domain.models import MAX_TEXT, Record, StudioError
from ..storage.blob_store import BlobStore, file_hash
from ..storage.paths import real_path
from .project_service import ProjectService

TEMPLATES = {
    "Dokumentation": "# Dokumentation\n\n",
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
        rows = [row for row in self.catalog.records()
                if row.kind == "document" and row.owner_id == owner_id]
        return sorted(rows, key=lambda r: ({"index": 0, "section": 1}.get(
            r.data.get("automation"), 2), r.title.casefold(), r.id))

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
        if record.data["body"] == body:
            return record
        if record.data.get("automation"):
            from .project_documents import START, END, generated
            content = record.data["body"].split(START)[1].split(END)[0]
            if generated(body, content) != body:
                raise StudioError("validation", "Der STUDIO:AUTO-Abschnitt wird automatisch "
                                  "gepflegt. Eigene Texte unterhalb der Markierungen bearbeiten.")
        return self.catalog.save(record, data=record.data | {"body": body})

    def attach(self, identifier: str, source: Path, expected_revision: int) -> Record:
        record = self.catalog.get(identifier)
        self.project._check_revision(record, expected_revision)
        if record.kind != "document" or record.data["document_type"] != "manual":
            raise StudioError("validation", "Anhang benötigt ein manuelles Dokument.")
        imported = self.blobs.import_file(source)
        attachments = [*record.data["attachments"], imported]
        return self.catalog.save(record, data=record.data | {"attachments": attachments})

    def rename(self, identifier: str, title: str, expected_revision: int) -> Record:
        record = self.catalog.get(identifier)
        self.project._check_revision(record, expected_revision)
        if record.data.get("automation"):
            raise StudioError("validation", "Das Grunddokument gehört fest zum Bereich.")
        if record.kind != "document" or record.data.get("document_type") != "manual":
            raise StudioError("validation", "Generierte Berichte sind hier schreibgeschützt.")
        if any(row.id != identifier and row.title.casefold() == title.strip().casefold()
               for row in self.documents(record.owner_id)):
            raise StudioError("conflict", "Dokumenttitel existiert bereits.")
        return self.catalog.save(record, title=title)

    def attachment_path(self, identifier: str, index: int) -> Path:
        attachment = self.catalog.get(identifier).data["attachments"][index]
        path = self.blobs.path_for(attachment["sha256"])
        if not path.is_file() or file_hash(path) != attachment["sha256"]:
            raise StudioError("integrity", "Anhang fehlt oder ist beschädigt.")
        return path

    def attachment_text(self, identifier: str, index: int) -> str:
        attachment = self.catalog.get(identifier).data["attachments"][index]
        path = self.attachment_path(identifier, index)
        extension = Path(attachment["original_name"]).suffix.lower()
        if extension not in {".md", ".txt", ".json", ".csv", ".log"}:
            return "Binär-/Skriptanhang sicher gespeichert. Automatisches Öffnen ist deaktiviert."
        if path.stat().st_size > MAX_TEXT:
            return "Anhang ist für die Textvorschau zu groß. Original bleibt erhalten."
        return path.read_text(encoding="utf-8", errors="replace")

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
                record = self.create(owner_id, path.stem, body, template="Dokumentation")
            provenance = {"original_name": path.name, "sha256": hashlib.sha256(raw).hexdigest()}
            return self.catalog.save(record, data=record.data | {"body": body,
                                                                "provenance": provenance})

    def search(self, query: str, *, scope_id: str | None = None,
               document_type: str | None = None) -> list[Record]:
        scope = self.project.content_scope(scope_id)
        needle = query.casefold()
        return [row for row in self.catalog.records() if row.kind == "document"
                and not self.catalog.get(row.owner_id).archived
                and row.owner_id in scope
                and (document_type is None or row.data.get("document_type") == document_type)
                and needle in self.search_text(row).casefold()]

    @staticmethod
    def search_text(record):
        body = record.data.get("body", "")
        if record.data.get("automation"):
            from .project_documents import manual_part
            body = manual_part(body)
        return record.title + "\n" + body

    def path(self, identifier):
        row = self.catalog.db.execute(
            "SELECT * FROM document_files WHERE id=?", (identifier,)).fetchone()
        if not row:
            record = self.catalog.get(identifier)
            return self.project.files.path(record.owner_id) / (record.id + ".md")
        return self.project.files.path(row["owner_id"]) / row["path"]

    def resolve_link(self, base, relative):
        """Only indexed Markdown and hash-verified local images, never arbitrary file reads."""
        from .document_resources import project_target

        root = self.catalog.path.parent
        try:
            candidate = project_target(root, base, relative)
            for row in self.catalog.db.execute("SELECT * FROM document_files"):
                if candidate == self.project.files.path(row["owner_id"]) / row["path"]:
                    return {"kind": "document", "id": row["id"], "path": candidate}
            for row in self.catalog.db.execute("SELECT * FROM managed_files"):
                if candidate == self.project.files.path(row["owner_id"]) / row["path"] and \
                        candidate.suffix in {".md", ".png", ".gif"} and candidate.is_file() and \
                        file_hash(candidate) == row["sha256"]:
                    return {"kind": "image" if candidate.suffix in {".png", ".gif"} else "index",
                            "path": candidate}
            for row in self.catalog.db.execute("SELECT path,sha256 FROM current_files"):
                if candidate == root / row["path"] and candidate.is_file() and \
                        file_hash(candidate) == row["sha256"]:
                    from PIL import Image
                    try:
                        with Image.open(candidate) as image:
                            if image.format in {"PNG", "JPEG", "WEBP", "GIF"}:
                                return {"kind": "image", "path": candidate}
                    except (OSError, ValueError):
                        pass
        except (StudioError, OSError, ValueError):
            pass
        return None

    def link_candidates(self, identifier, target, *, wiki=False, base=None):
        """Exact project paths win; a wiki name never silently chooses among duplicates."""
        from urllib.parse import unquote, urlsplit
        from .document_resources import project_target

        base = base or self.path(identifier)
        path = urlsplit(target).path
        if not path:
            return [{"kind": "document", "id": identifier, "path": base}] if identifier else [
                {"kind": "index", "path": base}]
        names = [path]
        if wiki and not Path(unquote(path)).suffix:
            names += [path + ".md", path + ".markdown"]
        for name in names:
            resolved = self.resolve_link(base, name)
            if resolved:
                return [resolved]
            candidate = project_target(self.catalog.path.parent, base, name)
            if candidate.is_file() and candidate.suffix.lower() in {".md", ".markdown"}:
                return [{"kind": "index", "path": candidate}]
        if wiki and "/" not in path and "\\" not in path:
            stem = Path(unquote(path)).stem.casefold()
            return [{"kind": "document", "id": row.id, "path": self.path(row.id)}
                    for row in self.catalog.records() if row.kind == "document" and not row.archived
                    and (row.title.casefold() == stem or self.path(row.id).stem.casefold() == stem)]
        candidate = project_target(self.catalog.path.parent, base, path)
        if candidate.is_file() and candidate.suffix.lower() in {".md", ".markdown"}:
            return [{"kind": "index", "path": candidate}]
        return []

    def image_file(self, identifier, target, grants=None, *, base=None):
        """Return a checked path and expected digest for the asynchronous media reader."""
        from urllib.parse import unquote, urlsplit
        from .document_resources import project_target

        parts = urlsplit(target)
        if parts.scheme == "file":
            selected = Path(unquote(parts.path)).absolute()
            grant = (grants or {}).get(str(selected))
            if not grant or parts.netloc:
                raise StudioError("permission",
                    "Externe Datei gezielt über Zugriff erlauben auswählen.")
            return real_path(selected), grant.digest
        path = project_target(self.catalog.path.parent, base or self.path(identifier), target)
        attachments = self.catalog.get(identifier).data["attachments"] if identifier else []
        for item in attachments:
            if path == self.blobs.path_for(item["sha256"]):
                return path, item["sha256"]
        for row in self.catalog.db.execute("SELECT * FROM managed_files"):
            if path == self.project.files.path(row["owner_id"]) / row["path"]:
                return path, row["sha256"]
        for row in self.catalog.db.execute("SELECT path,sha256 FROM current_files"):
            if path == self.catalog.path.parent / row["path"]:
                return path, row["sha256"]
        if not path.is_file():
            raise StudioError("missing", "Bildquelle fehlt. Quelle ändern oder erneut versuchen.")
        return path, None
