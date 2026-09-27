"""Qt-free, immutable job envelope and explicit adapter lifecycle (studio-job-v1)."""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Protocol

from ..domain.models import StudioError
from ..storage.blob_store import file_hash
from ..storage.paths import safe_target
from ..storage.sqlite_repository import canonical


@dataclass(frozen=True)
class InputFile:
    revision_id: str
    source: str
    name: str
    sha256: str
    length: int


@dataclass(frozen=True)
class BuildRequest:
    job_id: str
    owner_id: str
    adapter: str
    parameters: str
    inputs: tuple[InputFile, ...]
    outputs: tuple[str, ...]
    argv: tuple[str, ...]
    tool_hashes: tuple[tuple[str, str], ...]
    resource_key: str
    timeout: float
    owner_pid: int
    owner_stamp: str
    schema_version: str = "studio-job-v1"

    def to_data(self) -> dict:
        return asdict(self)

    @classmethod
    def from_data(cls, data: dict) -> "BuildRequest":
        if data.get("schema_version") != "studio-job-v1":
            raise StudioError("validation", "Unbekannter Auftragsvertrag.")
        return cls(**{**data, "inputs": tuple(InputFile(**v) for v in data["inputs"]),
                      "outputs": tuple(data["outputs"]), "argv": tuple(data["argv"]),
                      "tool_hashes": tuple(tuple(v) for v in data["tool_hashes"])})


@dataclass(frozen=True)
class CommandPlan:
    argv: tuple[str, ...]
    outputs: tuple[str, ...]
    tool_hashes: tuple[tuple[str, str], ...]


class PipelineAdapter(Protocol):
    identifier: str

    def validate(self, parameters: dict) -> None: ...
    def plan(self, workspace: Path, parameters: dict) -> CommandPlan: ...
    def execute(self, request: BuildRequest, workspace: Path) -> tuple[str, ...]: ...
    def verify(self, request: BuildRequest, workspace: Path) -> list[dict]: ...


def verify_files(root: Path, expected: tuple[str, ...], manifest: list[dict] | None = None
                 ) -> list[dict]:
    actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() or p.is_symlink()}
    if actual != set(expected):
        raise StudioError("integrity",
                          "Ausgabeordner enthält fehlende oder nicht erfasste Dateien.")
    if manifest is not None and (len(manifest) != len(expected) or
                                {r["path"] for r in manifest} != set(expected)):
        raise StudioError("integrity", "Ergebnisliste ist unvollständig.")
    results = []
    for name in expected:
        path = safe_target(root, name)
        if not path.is_file():
            raise StudioError("integrity", "Erwartete Ausgabe fehlt.", name)
        item = {"path": name, "length": path.stat().st_size, "sha256": file_hash(path)}
        if manifest is not None and item not in manifest:
            raise StudioError("integrity", "Cachedatei stimmt nicht mit Ergebnisdigest überein.")
        results.append(item)
    return results


def write_json(path: Path, value: dict, *, exclusive: bool = True) -> None:
    with path.open("x" if exclusive else "w", encoding="utf-8") as stream:
        stream.write(canonical(value) + "\n")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
