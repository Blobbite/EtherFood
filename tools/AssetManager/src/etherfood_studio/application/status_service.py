"""Read-only status projection for the dashboard; no editable success flag."""

from ..domain.workflows import StepStatus, resolve
from .project_service import ProjectService


class StatusService:
    def __init__(self, project: ProjectService) -> None:
        self.project = project

    def status(self, identifier: str) -> dict[str, StepStatus]:
        record = self.project.catalog.get(identifier)
        kind = record.data.get("workflow", "document")
        inputs = {}
        documents = [row for row in self.project.catalog.records()
                     if row.kind == "document" and row.owner_id == identifier
                     and row.data.get("document_type") == "manual" and row.data.get("body")]
        if documents:
            inputs["document"] = ";".join(
                f"{row.id}:{row.revision_no}" for row in documents
            )
        result = resolve(kind, inputs)
        # Real pipeline/import evidence is integrated in later packages, never invented.
        blockers = [edge["target_id"] for edge in self.project.catalog.relations()
                    if edge["kind"] == "depends_on" and edge["source_id"] == identifier]
        if blockers:
            reason = "Voraussetzung noch nicht abgenommen: " + ", ".join(
                self.project.catalog.get(target).title for target in blockers
            )
            result["dependencies"] = StepStatus("dependencies", "blocked", reason, tuple(blockers))
        return result

    def summary(self, identifier: str) -> str:
        statuses = list(self.status(identifier).values())
        for state in ("blocked", "failed", "waiting_external", "not_started", "stale", "ready"):
            found = next((row for row in statuses if row.state == state), None)
            if found:
                return f"{found.state}: {found.reason}"
        return "Nicht abgenommen"
