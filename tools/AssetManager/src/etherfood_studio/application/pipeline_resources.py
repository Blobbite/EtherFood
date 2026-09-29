"""Declared asset resources resolved and frozen before a run, without processing code."""

from ..domain.assets import require
from ..domain.models import StudioError
from ..storage.blob_store import BlobStore, file_hash
from .mask_service import MaskService
from .reference_service import ReferenceService


def freeze_bindings(project, declarations):
    """Bindings preserve legacy asset profiles/masks as explicit definition data."""
    catalog, root = project.catalog, project.catalog.path.parent
    store = BlobStore(catalog, root)
    result = {}
    for name, declaration in declarations.items():
        if "binding" not in declaration:
            continue
        require(
            declaration["binding"] in {"color_profile", "source_mask", "declared_mask"},
            "Unbekannte Ressourcenbindung: " + name,
        )
        values = result[name] = {}
        for asset in project.cards():
            if asset.kind != "asset":
                continue
            for identifier in asset.data.get("active_sources", {}).values():
                source = catalog.get(identifier)
                try:
                    if declaration["binding"] == "color_profile":
                        record = ReferenceService(project).profile(asset.id, declaration["mode"])
                        data = record.data
                    elif declaration["binding"] == "source_mask":
                        record = MaskService(project).for_source(asset.id, identifier)
                        data = record.data
                    else:
                        from PIL import Image, UnidentifiedImageError
                        from ..pipelines.image_processing import legacy_modules

                        exact = legacy_modules()[-1]
                        matching = []
                        for item in declaration["candidates"]:
                            path = store.path_for(item["sha256"])
                            require(
                                path.is_file() and file_hash(path) == item["sha256"],
                                "Deklarierte Maskenressource fehlt oder ist verändert.",
                            )
                            try:
                                with Image.open(path) as image:
                                    if (
                                        image.format == "PNG"
                                        and image.info.get(exact.MASK_SOURCE)
                                        == source.data["sha256"]
                                    ):
                                        matching.append(item)
                            except UnidentifiedImageError:
                                continue
                        require(
                            len(matching) == 1,
                            "Genau eine quellgebundene Maske benötigt; "
                            + str(len(matching))
                            + " gefunden.",
                        )
                        data = matching[0]
                    path = store.path_for(data["sha256"])
                    raw = path.read_bytes()
                    require(
                        len(raw) == data["length"] and file_hash(path) == data["sha256"],
                        "Gebundene Ressource fehlt oder ist verändert.",
                    )
                    values[identifier] = {"raw": raw, "sha256": data["sha256"]}
                except (StudioError, OSError, ValueError, KeyError) as error:
                    values[identifier] = {"issue": str(error)}
    return result


def resolve_resources(snapshot, inputs, names=None):
    resources = {
        key: raw
        for key, raw in snapshot.get("resources", {}).items()
        if names is None or key in names
    }
    identifiers = {
        item["metadata"].get("source_revision") for values in inputs.values() for item in values
    }
    for name, bindings in snapshot.get("bindings", {}).items():
        if names is not None and name not in names:
            continue
        selected = [
            bindings.get(key, {"issue": "Quellzuordnung der Ressourcenbindung fehlt."})
            for key in identifiers
        ]
        require(
            selected and not any("issue" in value for value in selected),
            name + ": " + "; ".join(value.get("issue", "") for value in selected),
        )
        require(
            len({value["sha256"] for value in selected}) == 1,
            "Sammelschritt benötigt eine eindeutige Ressourcenbindung: " + name,
        )
        resources[name] = selected[0]["raw"]
    return resources
