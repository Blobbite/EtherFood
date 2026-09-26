"""Copy, verify and register immutable content without replacing originals."""

import hashlib
import mimetypes
import os
from pathlib import Path
import shutil
import tempfile
from typing import Callable

from ..config import Configuration
from ..domain.models import StudioError, new_id
from .operation_journal import OperationJournal
from .paths import make_directory, real_path, safe_target
from .sqlite_repository import Catalog


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class BlobStore:
    def __init__(self, catalog: Catalog, workspace: Path,
                 config: Configuration | None = None) -> None:
        self.catalog = catalog
        self.root = real_path(workspace)
        self.config = config or Configuration()
        self.journal = OperationJournal(catalog)

    def path_for(self, digest: str) -> Path:
        if len(digest) != 64 or set(digest) - set("0123456789abcdef"):
            raise StudioError("validation", "Ungültiger Blob-Digest.")
        return safe_target(self.root, f".asset-studio/objects/{digest[:2]}/{digest}")

    def import_file(self, source: Path, *, cancelled: Callable[[], bool] = lambda: False,
                    after_copy: Callable[[], None] = lambda: None) -> dict:
        original = real_path(source)
        if not original.is_file():
            raise StudioError("validation", "Importquelle ist keine Datei.")
        size = original.stat().st_size
        if size > self.config.max_file_bytes:
            raise StudioError("validation", "Datei überschreitet die Importgrenze.")
        if shutil.disk_usage(self.root).free < size * 2 + 1024 * 1024:
            raise StudioError("storage", "Nicht genügend freier Speicher für eine geprüfte Kopie.")
        if cancelled():
            raise StudioError("cancelled", "Import abgebrochen.")
        if original.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
            try:
                from PIL import Image
            except ImportError as exc:
                raise StudioError("unavailable", "Pillow für Bildimporte erforderlich.") from exc
            try:
                with Image.open(original) as image:
                    if image.width * image.height > self.config.max_pixels:
                        raise StudioError("validation", "Bild überschreitet die Pixelgrenze.")
                    image.verify()
            except (OSError, Image.DecompressionBombError) as exc:
                raise StudioError("validation", "Bilddatei konnte nicht geprüft werden.") from exc
        identifier = new_id()
        staging = make_directory(self.root, ".asset-studio/staging")
        data = {"original_name": original.name, "length": size,
                "media_type": mimetypes.guess_type(original.name)[0] or "application/octet-stream"}
        self.journal.record(identifier, "planned", data)
        fd, temporary = tempfile.mkstemp(prefix=identifier + "-", dir=staging)
        data["temporary"] = str(Path(temporary).relative_to(self.root))
        self.journal.record(identifier, "copying", data)
        try:
            with os.fdopen(fd, "wb") as output, original.open("rb") as incoming:
                copied = 0
                while chunk := incoming.read(1024 * 1024):
                    if cancelled():
                        raise StudioError("cancelled", "Import abgebrochen; Journal bleibt.")
                    copied += len(chunk)
                    if copied > self.config.max_file_bytes or copied > size:
                        raise StudioError("integrity", "Quelle während des Imports verändert.")
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            staged = safe_target(self.root, data["temporary"])
            digest = file_hash(staged)
            if copied != size or file_hash(original) != digest:
                raise StudioError("integrity", "Quellbytes während des Imports geändert.")
            data["sha256"] = digest
            make_directory(self.root, f".asset-studio/objects/{digest[:2]}")
            target = self.path_for(digest)
            # Exclusive copy stays on the destination filesystem. No source rename/hardlink.
            # Serialize publication through the catalog writer: a duplicate import must
            # never inspect a second writer's half-published file.
            with self.catalog.transaction():
                target = self.path_for(digest)
                try:
                    with target.open("xb") as output, staged.open("rb") as incoming:
                        shutil.copyfileobj(incoming, output)
                        output.flush()
                        os.fsync(output.fileno())
                except FileExistsError:
                    pass
                if target.stat().st_size != size or file_hash(target) != digest:
                    raise StudioError("integrity", "Vorhandener Blob beschädigt.")
                self.journal.record(identifier, "copied", data)
            after_copy()
            if cancelled():
                raise StudioError("cancelled", "Import vor Registrierung abgebrochen.")
            with self.catalog.transaction():
                self.catalog.db.execute("INSERT OR IGNORE INTO blobs VALUES (?,?,?)",
                                        (digest, size, data["media_type"]))
                self.journal.record(identifier, "registered", data)
            staged.unlink()  # Only this operation's verified temporary copy.
            return data | {"operation_id": identifier}
        except (OSError, StudioError) as exc:
            self.journal.record(identifier, "interrupted", data | {"error": str(exc)})
            if isinstance(exc, StudioError):
                raise
            raise StudioError("storage", "Import unterbrochen; Quelle bleibt erhalten.", str(exc)) \
                from exc

    def integrity(self) -> list[str]:
        findings = []
        for row in self.catalog.db.execute("SELECT * FROM blobs"):
            path = self.path_for(row["sha256"])
            if not path.is_file() or path.stat().st_size != row["length"] \
                    or file_hash(path) != row["sha256"]:
                findings.append(f'Blob beschädigt/fehlt: {row["sha256"]}')
        for entry in self.journal.entries():
            if entry["state"] != "registered":
                findings.append(f'Import unvollständig: {entry["id"]} ({entry["state"]})')
        staging = safe_target(self.root, ".asset-studio/staging")
        if staging.exists():
            findings.extend(f"Temporäre Datei: {path.name}" for path in staging.iterdir())
        objects = safe_target(self.root, ".asset-studio/objects")
        known = {row[0] for row in self.catalog.db.execute("SELECT sha256 FROM blobs")}
        if objects.exists():
            for bucket in objects.iterdir():
                real_path(bucket)
                for path in bucket.iterdir():
                    real_path(path)
                    if path.name not in known:
                        findings.append(f"Nicht registrierter Blob: {path.name}")
        return findings
