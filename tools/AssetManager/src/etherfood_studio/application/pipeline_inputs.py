"""Generic input selection over registered current asset sources, never directory scans."""

from copy import deepcopy

from ..domain.assets import require
from ..domain.models import StudioError
from ..domain.pipeline_contract import compatible
from ..pipelines.image_processing import finish_metadata, validate_metadata
from ..storage.blob_store import BlobStore, file_hash
from ..storage.sqlite_repository import canonical
from .asset_service import AssetService
from .source_import import SourceImportService
from .workspace_files import content_hash


def source_metadata(source, definition):
    data = source.data
    columns, rows = data["grid"]
    width, height = data["width"] // columns, data["height"] // rows
    pose = next((p for p in definition.poses if p.id == data["slot"]["pose_id"]), None)
    result = {
        "kind": data["slot"]["kind"],
        "grid": data["grid"],
        "frames": data["frames"],
        "source_grid": data["grid"],
        "source_indices": list(range(data["frames"])),
        "source_revision": source.id,
        "source_sha256": data["sha256"],
        "slot": data["slot"],
        "profile": "source",
        "logical_size": [width, height],
        "crop_offset": [0, 0],
        "crop_size": [width, height],
        "anchor": list(pose.anchor) if pose else [0.5, 1.0],
    }
    if result["kind"] == "spritesheet":
        require(
            pose is not None and pose.fps and pose.fps > 0,
            "Spritesheet benötigt gültige Pose und positive Timingdaten.",
        )
        result.update(
            fps=pose.fps, loop=pose.loop, duration=data["frames"] / pose.fps, timing_mode="keep_fps"
        )
    return finish_metadata(result, (width, height))


def influences(artifact):
    metadata = deepcopy(artifact["metadata"])
    metadata.pop("source_revision", None)
    return {"sha256": artifact["sha256"], "type": artifact["type"], "metadata": metadata}


def matches(artifact, spec):
    if not compatible(artifact["type"], spec["type"]):
        return False
    if spec.get("animated") and (
        artifact["metadata"].get("kind") != "spritesheet"
        or artifact["metadata"].get("frames", 0) <= 1
    ):
        return False
    if spec.get("extensions") and not any(
        artifact["name"].lower().endswith(ext) for ext in spec["extensions"]
    ):
        return False
    return True


class PipelineInputs:
    def __init__(self, workspace):
        self.workspace = workspace
        self.project, self.catalog = workspace.project, workspace.catalog
        self.assets = AssetService(self.project)
        self.imports = SourceImportService(self.assets)
        self.store = BlobStore(self.catalog, self.catalog.path.parent)

    def artifact(self, source):
        from PIL import Image

        key = self.imports.validate_revision(source)
        definition = self.assets.definition(source.owner_id)
        path = self.store.path_for(source.data["sha256"])
        require(
            path.is_file() and file_hash(path) == source.data["sha256"],
            "Aktuelle Quellbytes fehlen oder wurden verändert: " + source.title,
        )
        for row in self.catalog.db.execute(
            "SELECT path FROM managed_files WHERE owner_id=?", (source.owner_id,)
        ):
            if row[0].startswith(("source/", "spritesheets/")) and row[0].endswith(
                "--" + source.id[:12] + ".png"
            ):
                from ..storage.paths import safe_target

                relative = (self.project.files.path(source.owner_id) / row[0]).relative_to(
                    self.catalog.path.parent
                )
                visible = safe_target(self.catalog.path.parent, relative.as_posix())
                require(
                    visible.is_file() and file_hash(visible) == source.data["sha256"],
                    "Aktuelle Quelle extern geändert oder entfernt; Quellenabgleich erforderlich.",
                )
        metadata = source_metadata(source, definition)
        with Image.open(path) as image:
            require(
                image.format == "PNG"
                and image.size == (source.data["width"], source.data["height"]),
                "Bild und deklarierte Abmessungen widersprechen sich.",
            )
            require(
                image.width * image.height <= self.project.config.max_pixels,
                "Eingabebild überschreitet die Pixelgrenze.",
            )
            validate_metadata(metadata, image.size)
            image.load()
        return {
            "path": str(path.relative_to(self.catalog.path.parent)),
            "name": source.data["original_name"],
            "sha256": source.data["sha256"],
            "length": source.data["length"],
            "source_key": key.token,
            "asset_id": source.owner_id,
            "source_id": source.id,
            "type": "spritesheet" if key.kind == "spritesheet" else "image",
            "metadata": metadata,
        }

    def select(self, usage, definition):
        rows = []
        for asset in self.workspace.scope(usage):
            bindings = asset.data.get("active_sources", {})
            if not bindings:
                rows.append(
                    {
                        "asset_id": asset.id,
                        "state": "nonmatching",
                        "reason": "Keine aktuellen registrierten Quellen.",
                        "inputs": {},
                    }
                )
            for token, identifier in sorted(bindings.items()):
                row = {
                    "asset_id": asset.id,
                    "source_key": token,
                    "source_id": identifier,
                    "state": "matching",
                    "reason": "Passende aktuelle Quelle.",
                    "inputs": {},
                }
                try:
                    source = self.catalog.get(identifier)
                    require(
                        source.owner_id == asset.id and source.kind == "source_revision",
                        "Quelle gehört nicht zum gewählten Asset.",
                    )
                    artifact = self.artifact(source)
                    require(
                        artifact["source_key"] == token, "Quellenzuordnung ist widersprüchlich."
                    )
                    for name, spec in definition["inputs"].items():
                        if matches(artifact, spec):
                            row["inputs"][name] = [artifact]
                        elif spec.get("required", True):
                            row.update(
                                state="nonmatching", reason="Quellart passt nicht zu " + name
                            )
                    if not row["inputs"]:
                        row.update(state="nonmatching", reason="Keine passenden Eingabeanschlüsse.")
                except (StudioError, OSError, ValueError) as error:
                    row.update(state="invalid", reason=str(error))
                row["fingerprint"] = content_hash(
                    canonical(
                        {k: [influences(a) for a in values] for k, values in row["inputs"].items()}
                    ).encode()
                )
                rows.append(row)
        return rows
