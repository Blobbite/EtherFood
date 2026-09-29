"""Read-only status projection for the dashboard; no editable success flag."""

from ..domain.workflows import Evidence, StepStatus, resolve
from .asset_service import AssetService
from .project_service import ProjectService
from .source_import import SourceImportService

STATE_NAMES = {
    "not_started": "Noch nicht begonnen", "waiting_external": "Externe Eingabe fehlt",
    "ready": "Bereit, noch nicht geprüft", "running": "In Arbeit", "blocked": "Blockiert",
    "failed": "Fehlgeschlagen", "cancelled": "Abgebrochen", "passed": "Nachweis vorhanden",
    "stale": "Nachweis veraltet", "not_required": "Nicht erforderlich",
}
STEP_NAMES = {
    "document": "Dokumentation",
    "source": "Quelldaten",
    "mask": "Materialmaske",
    "color": "Farben",
    "frames": "Frame-Ableitung",
    "scale": "Grafikstufen",
    "checks": "Technische Prüfung",
    "review": "Sichtabnahme",
    "godot": "Godot-Test",
    "runtime": "Spielintegration",
    "dependencies": "Abhängigkeiten",
    "processing": "Verarbeitung",
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
        materials = True
        source_rows = None
        if record.data.get("asset_definition"):
            definition = AssetService(self.project).parse_definition(
                record.data["asset_definition"])
            kind = definition.workflow
            materials = "supports_materials" in definition.capabilities
            if not record.archived:
                sources = SourceImportService(AssetService(self.project))
                source_rows = sources.matrix(identifier)
                fingerprint = sources.fingerprint(identifier)
                if fingerprint:
                    inputs["source"] = fingerprint
        evidence = {key: Evidence(**value)
                    for key, value in record.data.get("evidence", {}).items()}
        result = resolve(kind, inputs, evidence, supports_materials=materials,
                         current_build_id=record.data.get("current_build_id"))
        if record.archived and "source" in result:
            result["source"] = StepStatus("source", "blocked", "Asset ist archiviert.")
        if source_rows is not None and not inputs.get("source"):
            required = [row for row in source_rows if row["required"]]
            missing = [row for row in required if row["state"] != "imported"]
            poses = {p.id: p.display_name for p in definition.poses}
            detail = ", ".join(f"{poses.get(r['key'].pose_id, 'Bild')} "
                               f"{r['key'].direction or 'ohne Richtung'}" for r in missing[:8])
            result["source"] = StepStatus("source", "waiting_external",
                f"{len(required) - len(missing)}/{len(required)} benötigte Quellen importiert. "
                f"Externe Lieferung fehlt oder ist ungeprüft: {detail}.")
        if record.data.get("asset_definition", {}).get("schema_version") == 2:
            source = result["source"]
            ready = source.state == "passed"
            result = {
                "source": source,
                "processing": StepStatus(
                    "processing",
                    "ready" if ready else "blocked",
                    (
                        "Pipelineverwendungen und deren Ergebnisse prüfen."
                        if ready
                        else "Zuerst die benötigten Originalquellen bereitstellen."
                    ),
                ),
            }
            for key, description in (
                ("review", "Sichtabnahme bleibt ein gesonderter Nachweis."),
                ("godot", "Noch keine Godot-Freigabe."),
                ("runtime", "Noch nicht ins Spiel übernommen."),
            ):
                result[key] = StepStatus(key, "blocked", description)
        blockers = [edge["target_id"] for edge in self.project.catalog.relations()
                    if edge["kind"] == "depends_on" and edge["source_id"] == identifier]
        if blockers:
            reason = "Voraussetzung noch nicht abgenommen: " + ", ".join(
                self.project.catalog.get(target).title for target in blockers
            )
            result["dependencies"] = StepStatus("dependencies", "blocked", reason, tuple(blockers))
        return result

    def summary(self, identifier: str) -> str:
        record = self.project.catalog.get(identifier)
        if record.archived:
            return "Inhalt archiviert · Zum Bearbeiten wiederherstellen."
        if record.kind == "pipeline_usage":
            return "Pipelineverwendung · Eingaben im Projekt · Bearbeiten über Rechtsklick"
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
