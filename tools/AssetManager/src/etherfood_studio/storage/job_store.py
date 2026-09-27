"""Local execution evidence, deliberately excluded from portable catalog snapshots."""

import json

from ..domain.models import StudioError, utc_now
from ..pipelines.processes import identity
from .sqlite_repository import canonical

ACTIVE = ("running", "cancelling")
TERMINAL = ("succeeded", "failed", "cancelled", "interrupted")


class JobStore:
    def __init__(self, catalog):
        self.catalog = catalog

    def recover(self) -> None:
        with self.catalog.transaction():
            for row in self.rows():
                if row["status"] in ACTIVE and identity(row["owner_pid"]) != row["owner_stamp"]:
                    self.finish(row["id"], {"status": "interrupted",
                                           "reason": "Anwendung vor Abschluss beendet"})

    def reserve(self, request, limit: int) -> None:
        with self.catalog.transaction():
            self.recover()
            active = [r for r in self.rows() if r["status"] in ACTIVE]
            if any(r["resource_key"] == request.resource_key for r in active):
                raise StudioError("conflict",
                                  "Für diesen Ergebnisbereich läuft bereits ein Auftrag.")
            if len(active) >= limit:
                raise StudioError("busy", "Parallelitätsgrenze erreicht; Abschluss abwarten.")
            self.catalog.db.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,NULL,?)", (
                request.job_id, canonical(request.to_data()), "running", request.resource_key,
                request.owner_pid, request.owner_stamp, utc_now(),
            ))

    def rows(self) -> list[dict]:
        return [{**dict(r), "request": json.loads(r["request"]),
                 "result": json.loads(r["result"]) if r["result"] else None}
                for r in self.catalog.db.execute("SELECT * FROM jobs ORDER BY created_at DESC,id")]

    def get(self, identifier: str) -> dict:
        row = next((r for r in self.rows() if r["id"] == identifier), None)
        if row is None:
            raise StudioError("validation", "Auftrag nicht gefunden.")
        return row

    def event(self, identifier: str, event: dict) -> None:
        with self.catalog.transaction():
            seq = self.catalog.db.execute(
                "SELECT COALESCE(MAX(seq),0) FROM job_events WHERE job_id=?", (identifier,),
            ).fetchone()[0]
            if event.get("job_id") != identifier or event.get("seq") != seq + 1:
                raise StudioError("integrity", "Ungültige Reihenfolge der Auftragsereignisse.")
            self.catalog.db.execute("INSERT INTO job_events VALUES (?,?,?)",
                                    (identifier, event["seq"], canonical(event)))

    def events(self, identifier: str) -> list[dict]:
        return [json.loads(r[0]) for r in self.catalog.db.execute(
            "SELECT data FROM job_events WHERE job_id=? ORDER BY seq", (identifier,),
        )]

    def cancelling(self, identifier: str) -> None:
        with self.catalog.transaction():
            self.catalog.db.execute("UPDATE jobs SET status='cancelling' WHERE id=? "
                                    "AND status='running'", (identifier,))

    def finish(self, identifier: str, result: dict) -> None:
        if result.get("status") not in TERMINAL:
            raise StudioError("integrity", "Ungültiger Abschlusszustand.")
        with self.catalog.transaction():
            # Historical results are never rewritten by late events or a second GUI.
            self.catalog.db.execute("UPDATE jobs SET status=?,result=? WHERE id=? "
                                    "AND status IN ('running','cancelling')",
                                    (result["status"], canonical(result), identifier))
