"""Shared catalog/blob checks for color services; no alternative storage or runner."""

import json
import os
from pathlib import Path
import shutil
import tempfile

from ..domain.assets import require
from ..domain.models import StudioError
from ..pipelines.image_processing import legacy_modules
from ..storage.blob_store import BlobStore, file_hash
from ..storage.sqlite_repository import canonical
from ..storage.paths import safe_target
from .asset_service import AssetService
from .source_import import SourceImportService


class ColorContext:
    def __init__(self, project):
        self.project, self.catalog = project, project.catalog
        self.assets = AssetService(project)
        self.sources = SourceImportService(self.assets)
        self.store = BlobStore(self.catalog, self.catalog.path.parent, project.config)

    def asset(self, identifier, expected_revision=None):
        record = self.project.require_active_card(identifier)
        require(record.kind == "asset", "Aktives Asset auswählen.")
        self.assets.definition(identifier)
        if expected_revision is not None and record.revision_no != expected_revision:
            raise StudioError("conflict", "Asset wurde inzwischen geändert; erneut öffnen.")
        return record

    def revision(self, identifier, owner, contract):
        record = self.catalog.get(identifier)
        kind = "mask_revision" if contract == "studio-mask-revision-v1" else "profile_revision"
        require(record.kind == kind and record.owner_id == owner and record.data.get(
            "contract") == contract,
                "Revision gehört nicht zu diesem Asset oder Vertrag.")
        return record

    def source(self, identifier, owner, *, current=True):
        record = self.catalog.get(identifier)
        require(record.kind == "source_revision" and record.owner_id == owner,
                "Master-/Maskenquelle gehört nicht zu diesem Asset.")
        key = self.sources.validate_revision(record)
        require(record.data.get("verification") == "verified",
                "Quellenrevision ist nicht geprüft; Quelle erneut importieren.")
        self.blob(record.data)
        if current:
            active = self.sources.active(owner).get(key)
            require(active is not None and active.id == identifier,
                    "Quellbindung ist veraltet; aktive Quelle und Maske/Referenz erneut wählen.")
        return record

    def blob(self, data):
        path = self.store.path_for(data["sha256"])
        require(path.is_file() and path.stat().st_size == data["length"]
                and file_hash(path) == data["sha256"], "Gebundene Datei fehlt oder ist beschädigt.")
        return path

    def json_blob(self, value):
        with tempfile.TemporaryDirectory(prefix="studio-color-") as temporary:
            path = Path(temporary) / "profile.json"
            path.write_text(canonical(value), encoding="utf-8")
            blob = self.store.import_file(path)
        return {k: blob[k] for k in ("sha256", "length")}

    def records(self, owner, contract):
        kind = {"studio-mask-review-v1": "review", "studio-mask-revision-v1": "mask_revision"}.get(
            contract, "profile_revision")
        return sorted((r for r in self.catalog.records() if r.owner_id == owner
                       and r.kind == kind and r.data.get("contract") == contract),
                      key=lambda r: (r.created_at, r.id))

    def export_file(self, data, target, suffix):
        """Publish an independent copy exclusively; never replace a source or existing export."""
        target = Path(target)
        require(target.suffix.lower() == suffix, "Exportdatei benötigt die Endung " + suffix)
        target = safe_target(target.parent, target.name)
        source = self.blob(data)
        fd, name = tempfile.mkstemp(prefix=".studio-export-", dir=target.parent)
        temporary = Path(name)
        try:
            with os.fdopen(fd, "wb") as output, source.open("rb") as incoming:
                shutil.copyfileobj(incoming, output)
                output.flush()
                os.fsync(output.fileno())
            require(file_hash(temporary) == data["sha256"], "Exportkopie ist beschädigt.")
            # Link only our newly written temporary copy, never an original or stored blob.
            os.link(temporary, target, follow_symlinks=False)
        except FileExistsError as error:
            raise StudioError("conflict",
                "Ausgabedatei existiert bereits; anderen Namen wählen.") from error
        finally:
            temporary.unlink(missing_ok=True)
        return target

    def read_profile(self, record, mode):
        soft, exact = legacy_modules()[-2:]
        loader = {"soft": soft.load_profile, "fixed": exact.load_palette,
                  "material": exact.load_material_profile}[mode]
        try:
            return loader(self.blob(record.data))
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise StudioError("validation", str(error)) from error
