"""Local-only roots and correlated diagnostics, never telemetry."""

from dataclasses import dataclass, field
import json
import logging
from pathlib import Path

from .domain.models import StudioError

ALIASES = ("TOOL_ROOT", "WORKSPACE_ROOT", "VERSIONS_ROOT", "GODOT_ROOT")


@dataclass(frozen=True)
class Configuration:
    roots: dict[str, Path] = field(default_factory=dict)
    max_file_bytes: int = 64 * 1024 * 1024
    max_pixels: int = 32_000_000

    @classmethod
    def load(cls, path: Path) -> "Configuration":
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if value.get("schema_version") != 1 or not isinstance(value.get("roots"), dict):
                raise ValueError("Unbekannte lokale Konfiguration")
            if set(value["roots"]) - set(ALIASES):
                raise ValueError("Unbekannter Wurzelalias")
            return cls({key: Path(item) for key, item in value["roots"].items()})
        except (OSError, ValueError, TypeError) as exc:
            raise StudioError("validation", "Lokale Konfiguration nicht lesbar.", str(exc)) from exc


def job_logger(job_id: str) -> logging.LoggerAdapter:
    return logging.LoggerAdapter(logging.getLogger("etherfood_studio"), {"job_id": job_id})
