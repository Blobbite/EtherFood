"""Stable records, explicit limits and structured user-facing errors."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

KINDS = frozenset(
    {
        "project",
        "global",
        "act",
        "chapter",
        "asset",
        "package",
        "note",
        "document",
        "task",
        "issue",
        "pipeline",
        "pipeline_assignment",
        "pose",
        "source_revision",
        "script",
        "pipeline_definition",
        "pipeline_usage",
        "profile_revision",
        "mask_revision",
        "build",
        "check",
        "review",
        "approval",
        "deployment",
        "candidate",
        "export",
        "test_run",
    }
)
IMMUTABLE = frozenset({
    "source_revision", "profile_revision", "mask_revision", "build", "check", "review",
    "approval", "deployment", "candidate", "export", "test_run",
})
UNTRUSTED_IMPORT = IMMUTABLE - {"source_revision", "profile_revision", "mask_revision"}
MAX_TEXT = 1024 * 1024
MAX_SNAPSHOT = 64 * 1024 * 1024


class StudioError(Exception):
    """A safe message plus a stable error code and optional technical detail."""

    def __init__(self, code: str, message: str, detail: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.detail = detail


def new_id() -> str:
    return str(uuid4())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class Record:
    id: str
    kind: str
    title: str
    owner_id: str | None
    data: dict[str, Any] = field(default_factory=dict)
    revision_no: int = 1
    archived: bool = False
    created_at: str = ""
    updated_at: str = ""
