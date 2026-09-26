"""Persistent import stages; interrupted operations remain visible."""

import json

from ..domain.models import utc_now
from .sqlite_repository import Catalog, canonical


class OperationJournal:
    def __init__(self, catalog: Catalog) -> None:
        self.catalog = catalog

    def record(self, identifier: str, state: str, data: dict) -> None:
        with self.catalog.transaction():
            self.catalog.db.execute(
                "INSERT INTO operations VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
                "state=excluded.state,data=excluded.data,updated_at=excluded.updated_at",
                (identifier, state, canonical(data), utc_now()),
            )

    def entries(self) -> list[dict]:
        return [dict(row) | {"data": json.loads(row["data"])} for row in
                self.catalog.db.execute("SELECT * FROM operations ORDER BY id")]
