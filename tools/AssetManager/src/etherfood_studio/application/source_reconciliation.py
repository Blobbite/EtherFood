"""Import changed registered current source copies; historical revision bytes stay immutable."""

from pathlib import Path
from tempfile import TemporaryDirectory

from ..domain.assets import require
from ..domain.models import StudioError
from ..storage.blob_store import BlobStore, file_hash
from ..storage.paths import safe_target
from .asset_service import AssetService
from .source_import import SourceImportService, SourceSpec


class SourceReconciliation:
    def __init__(self, project):
        self.project, self.catalog = project, project.catalog
        self.root = self.catalog.path.parent

    def known(self):
        from .search_service import SearchService

        states = SearchService(self.project)
        result, self.issues = [], []
        for asset in self.project.cards():
            if asset.kind != "asset" or states.state(asset) != "active":
                continue
            files = list(
                self.catalog.db.execute("SELECT * FROM managed_files WHERE owner_id=?", (asset.id,))
            )
            for identifier in asset.data.get("active_sources", {}).values():
                try:
                    source = self.catalog.get(identifier)
                    for row in files:
                        if row["path"].startswith(("source/", "spritesheets/")) and row[
                            "path"
                        ].endswith("--" + identifier[:12] + ".png"):
                            relative = (
                                self.project.files.path(asset.id) / row["path"]
                            ).relative_to(self.root)
                            result.append((source, safe_target(self.root, relative.as_posix())))
                except (StudioError, OSError, ValueError) as error:
                    self.issues.append(
                        {"source_id": identifier, "asset_id": asset.id, "reason": str(error)}
                    )
        return result

    def stamp(self):
        result = []
        for source, path in self.known():
            try:
                st = path.stat()
                stamp = (st.st_mtime_ns, st.st_size, st.st_ino)
            except OSError:
                stamp = None
            result.append((source.id, str(path), stamp))
        return tuple(result) + tuple((i["source_id"], i["reason"], None) for i in self.issues)

    def reconcile(self, *, cancelled=lambda: False):
        imports = SourceImportService(AssetService(self.project))
        store = BlobStore(self.catalog, self.root)
        known = self.known()
        changed, issues = [], list(self.issues)
        for source, path in known:
            if cancelled():
                break
            try:
                require(path.is_file(), "Aktuelle Quelldatei fehlt: " + path.name)
                digest = file_hash(path)
                if digest == source.data["sha256"]:
                    continue
                with TemporaryDirectory(prefix="studio-source-") as folder:
                    selected = Path(folder) / Path(source.data["original_name"]).name
                    raw = path.read_bytes()
                    selected.write_bytes(raw)
                    require(file_hash(selected) == digest, "Quelle wird noch geschrieben.")
                    asset = self.catalog.get(source.owner_id)
                    spec = SourceSpec(
                        selected,
                        imports.validate_revision(source),
                        *source.data["grid"],
                        source.data["frames"],
                        source.data["external_tool"],
                    )
                    plan = imports.prepare(asset.id, asset.revision_no, [spec], cancelled=cancelled)
                    with self.catalog.transaction():
                        require(file_hash(path) == digest, "Quelle wird noch geschrieben.")
                        # Restore the historical copy after validating the new bytes.
                        self.catalog.file_changes().write(
                            path, previous=digest, source=store.path_for(source.data["sha256"])
                        )
                        imported = imports.import_plan(
                            plan, replace_active=True, cancelled=cancelled
                        )
                        changed.extend(row.id for row in imported)
            except (StudioError, OSError, ValueError) as error:
                issues.append(
                    {"source_id": source.id, "asset_id": source.owner_id, "reason": str(error)}
                )
        return {"changed": changed, "issues": issues}
