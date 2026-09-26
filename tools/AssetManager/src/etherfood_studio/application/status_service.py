"""Read-only status projection for the dashboard; no editable success flag."""

from ..domain.workflows import StepStatus, resolve
from .project_service import ProjectService

STATE_NAMES = {
    "not_started": "Noch nicht begonnen", "waiting_external": "Externe Eingabe fehlt",
    "ready": "Bereit, noch nicht geprüft", "running": "In Arbeit", "blocked": "Blockiert",
    "failed": "Fehlgeschlagen", "cancelled": "Abgebrochen", "passed": "Nachweis vorhanden",
    "stale": "Nachweis veraltet", "not_required": "Nicht erforderlich",
}
STEP_NAMES = {
    "document": "Dokumentation", "source": "Quelldaten", "mask": "Materialmaske",
    "color": "Farben", "frames": "Frame-Ableitung", "scale": "Grafikstufen",
    "checks": "Technische Prüfung", "review": "Sichtabnahme", "godot": "Godot-Test",
    "runtime": "Spielintegration", "dependencies": "Abhängigkeiten",
}


def status_reason(status: StepStatus) -> str:
    if status.reason.startswith("Voraussetzungen fehlen:"):
        return "Voraussetzungen fehlen: " + ", ".join(
            STEP_NAMES.get(key, key) for key in status.predecessors
        )
    return status.reason


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
        dependency = next((row for row in statuses if row.id == "dependencies"), None)
        if dependency:
            return "Blockiert · " + dependency.reason
        for state in ("failed", "cancelled", "stale", "waiting_external", "not_started",
                      "running", "ready", "blocked"):
            found = next((row for row in statuses if row.state == state), None)
            if found:
                summary = f"{STEP_NAMES[found.id]} · {STATE_NAMES[found.state]}"
                reason = status_reason(found)
                return summary if reason.rstrip(".") == STATE_NAMES[found.state] \
                    else summary + ": " + reason
        return "Nicht abgenommen"
