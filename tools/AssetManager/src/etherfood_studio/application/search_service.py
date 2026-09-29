"""Separate project and tool searches returning stable identities, never copied objects."""

from dataclasses import dataclass

from ..domain.models import StudioError
from .document_service import DocumentService
from .workspace_files import WorkspaceFiles


@dataclass(frozen=True)
class SearchHit:
    id: str
    kind: str
    title: str
    location: str
    state: str
    edge_id: str | None = None


class SearchService:
    def __init__(self, project):
        self.project, self.catalog = project, project.catalog

    def state(self, record):
        seen = set()
        while record:
            if record.id in seen:
                return "archived"
            seen.add(record.id)
            row = self.catalog.db.execute(
                "SELECT state FROM lifecycle WHERE id=?", (record.id,)
            ).fetchone()
            if row:
                return row[0]
            if record.archived:
                return "archived"
            record = self.catalog.get(record.owner_id) if record.owner_id else None
        return "active"

    def query(self, text, *, area="project", state="active"):
        needle = text.casefold().strip()
        results = []
        files = WorkspaceFiles(self.project)
        kinds = (
            {"script", "pipeline_definition"}
            if area == "tools"
            else {
                "project",
                "global",
                "act",
                "chapter",
                "asset",
                "package",
                "note",
                "task",
                "issue",
                "document",
                "pipeline_usage",
            }
        )
        for record in self.catalog.records(include_archived=True):
            if record.kind not in kinds:
                continue
            actual = self.state(record)
            if actual != state:
                continue
            path = record.data.get("path", "")
            values = [record.title, path, record.data.get("description", "")]
            if record.kind == "document":
                values.append(DocumentService.search_text(record))
            elif record.kind in {"script", "pipeline_definition"}:
                try:
                    values.append(files.text(record.id)[0])
                except (StudioError, OSError):
                    values.append("Datei fehlt oder ist nicht lesbar")
            else:
                values.extend(str(record.data.get(key, "")) for key in ("body", "text", "status"))
            if needle in "\n".join(values).casefold():
                results.append(
                    SearchHit(
                        record.id,
                        record.kind,
                        record.title,
                        path or self.project.breadcrumb(record.id),
                        actual,
                    )
                )
        if area == "project":
            for edge in self.catalog.relations(include_inactive=True):
                if edge["kind"] != "uses":
                    continue
                target = self.catalog.get(edge["target_id"])
                owner = self.catalog.get(edge["source_id"])
                lifecycle = self.catalog.db.execute(
                    "SELECT state FROM lifecycle WHERE id=?", (edge["id"],)
                ).fetchone()
                actual = lifecycle[0] if lifecycle else self.state(owner)
                if actual == "active":
                    actual = self.state(target)
                location = self.project.breadcrumb(owner.id)
                if actual == state and needle in (target.title + "\n" + location).casefold():
                    results.append(
                        SearchHit(
                            target.id, "reference", target.title, location, actual, edge["id"]
                        )
                    )
        return sorted(results, key=lambda r: (r.title.casefold(), r.location, r.id))
