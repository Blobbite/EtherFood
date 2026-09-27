"""Local tasks and precise findings; these never grant pipeline approval."""

from dataclasses import asdict, dataclass

from ..domain.models import Record, StudioError
from ..domain.checklists import validate_checklist
from .project_service import ProjectService

TASK_STATES = ("open", "in_progress", "blocked", "done")
PRIORITIES = ("low", "normal", "high", "critical")


@dataclass(frozen=True)
class Finding:
    asset_id: str | None = None
    build_id: str | None = None
    pose: str | None = None
    direction: str | None = None
    graphics_profile: str | None = None
    frame_count: int | None = None
    frame_index: int | None = None
    time_ms: float | None = None
    screenshot_sha256: str | None = None


class IssueService:
    def __init__(self, project: ProjectService) -> None:
        self.project = project
        self.catalog = project.catalog

    def create(self, owner_id: str, title: str, body: str = "", *, issue: bool = False,
               priority: str = "normal", approval_needed: bool = False, assignee: str = "",
               finding: Finding | None = None, checklist: list[dict] | None = None) -> Record:
        self.catalog.get(owner_id)
        if priority not in PRIORITIES:
            raise StudioError("validation", "Unbekannte Priorität.")
        self._validate_body(body)
        items = validate_checklist(checklist if checklist is not None else [])
        location = asdict(finding or Finding())
        for field, kind in (("asset_id", "asset"), ("build_id", "build")):
            if location[field] and self.catalog.get(location[field]).kind != kind:
                raise StudioError("validation", "Fundstelle verweist auf den falschen Datentyp.")
        for field in ("frame_count", "frame_index", "time_ms"):
            if location[field] is not None and location[field] < 0:
                raise StudioError("validation", "Negative Frame-/Zeitwerte sind unzulässig.")
        digest = location["screenshot_sha256"]
        if digest and not self.catalog.db.execute(
            "SELECT sha256 FROM blobs WHERE sha256=?", (digest,),
        ).fetchone():
            raise StudioError("validation", "Screenshot muss zuerst sicher importiert werden.")
        return self.catalog.create("issue" if issue else "task", title, owner_id, {
            "body": body, "status": "open", "priority": priority, "assignee": assignee,
            "approval_needed": approval_needed, "approval_confirmed": False, "finding": location,
            "checklist": items,
        })

    @staticmethod
    def _validate_body(body: str) -> None:
        if len(body.encode("utf-8")) > 1024 * 1024:
            raise StudioError("validation", "Beschreibung ist größer als 1 MiB.")

    def update(self, identifier: str, title: str, body: str, expected_revision: int,
               *, priority: str = "normal", assignee: str = "",
               checklist: list[dict] | None = None) -> Record:
        record = self.catalog.get(identifier)
        self.project._check_revision(record, expected_revision)
        if record.kind not in {"task", "issue"} or priority not in PRIORITIES:
            raise StudioError("validation", "Ungültige Aufgabe oder Priorität.")
        self._validate_body(body)
        data = record.data | {"body": body, "priority": priority, "assignee": assignee.strip()}
        if checklist is not None:
            data["checklist"] = validate_checklist(checklist)
        if title.strip() == record.title and data == record.data:
            return record
        # An approval covers the reviewed contents, never subsequent edits.
        data["approval_confirmed"] = False
        if data["status"] == "done" and (data["approval_needed"] or
                any(not item["done"] for item in data.get("checklist", []))):
            data["status"] = "open"
        return self.catalog.save(record, title=title, data=data)

    def set_status(self, identifier: str, status: str, expected_revision: int,
                   *, approval_confirmed: bool = False) -> Record:
        record = self.catalog.get(identifier)
        self.project._check_revision(record, expected_revision)
        if record.kind not in {"task", "issue"} or status not in TASK_STATES:
            raise StudioError("validation", "Unzulässiger Aufgabenstatus.")
        if status == "done" and any(not item["done"] for item in
                                   validate_checklist(record.data.get("checklist", []))):
            raise StudioError("validation", "Zuerst alle To-do-Punkte erledigen.")
        if status == "done" and record.data["approval_needed"] and not approval_confirmed:
            raise StudioError("validation", "Benötigte Abnahme wurde nicht bestätigt.")
        return self.catalog.save(record, data=record.data | {
            "status": status, "approval_confirmed": approval_confirmed,
        })

    def search(self, query: str = "", *, scope_id: str | None = None,
               status: str | None = None, kind: str | None = None,
               asset_type: str | None = None) -> list[Record]:
        scope = self.project.descendants(scope_id) if scope_id else None
        if scope is not None:
            scope.update(edge["target_id"] for edge in self.catalog.relations()
                         if edge["kind"] == "uses" and edge["source_id"] in scope)
        results = []
        for row in self.catalog.records():
            if row.kind not in {"task", "issue"} or (kind is not None and row.kind != kind):
                continue
            owner = self.catalog.get(row.owner_id)
            if (scope is not None and row.owner_id not in scope) or owner.archived:
                continue
            if status and row.data["status"] != status:
                continue
            if asset_type and owner.data.get("workflow") != asset_type:
                continue
            text = "\n".join(item["text"] for item in row.data.get("checklist", []))
            if query.casefold() in (row.title + "\n" + row.data["body"] + "\n" + text).casefold():
                results.append(row)
        return results
