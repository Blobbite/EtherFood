"""Asset configuration and append-only external observations, never source-file import."""

from ..domain.assets import AssetDefinition, VariantKey, require
from ..domain.models import Record, StudioError, new_id
from .project_service import ProjectService
from .profile_service import ProfileService


class AssetService:
    def __init__(self, project: ProjectService) -> None:
        self.project = project

    def asset(self, identifier: str) -> Record:
        record = self.project.catalog.get(identifier)
        require(record.kind == "asset" and not record.archived, "Aktives Asset auswählen.")
        return record

    def definition(self, identifier: str) -> AssetDefinition:
        data = self.asset(identifier).data.get("asset_definition")
        require(data is not None, "Zuerst die Asset-Anforderungen festlegen.")
        return self.parse_definition(data)

    def parse_definition(self, data: dict) -> AssetDefinition:
        return AssetDefinition.from_data(data, profiles=ProfileService(self.project).profiles())

    def creation_data(self, data: dict) -> dict:
        if self.project.project().data.get("workflow_editor_version"):
            data = {**data, "schema_version": 2, "graphics": [], "frames": []}
        definition = self.parse_definition(data)
        return {"asset_definition": definition.to_data(), "workflow": definition.workflow}

    def create(self, title: str, owner_id: str, data: dict) -> Record:
        return self.project.create_card("asset", title, owner_id, self.creation_data(data))

    def template(self, identifier: str) -> AssetDefinition:
        """Copy configuration only, never identity, sources, evidence or approvals."""
        data = self.definition(identifier).to_data()
        for pose in data["poses"]:
            pose["id"] = new_id()
        return self.parse_definition(data)

    def configure(self, identifier: str, data: dict, expected_revision: int) -> Record:
        definition = self.parse_definition(data)
        with self.project.catalog.transaction():
            record = self.asset(identifier)
            if record.revision_no != expected_revision:
                raise StudioError("conflict", "Asset wurde inzwischen geändert; erneut öffnen.")
            values = {**record.data, "asset_definition": definition.to_data(),
                      "workflow": definition.workflow}
            if values == record.data:
                return record
            return self.project.catalog.save(record, data=values)

    def observations(self, identifier: str) -> list[dict]:
        return self.asset(identifier).data.get("inventory_sources", [])

    def matrix(self, identifier: str) -> dict[VariantKey, str]:
        # Presence describes an inventory observation, not current validity or approval.
        observations = self.observations(identifier)
        hashes_by_key = {}
        for row in observations:
            key = VariantKey(**row["variant"])
            hashes_by_key.setdefault(key, set()).add(row["sha256"])
        matrix = self.definition(identifier).matrix(set(hashes_by_key))
        for key, hashes in hashes_by_key.items():
            if len(hashes) > 1 and matrix[key] == "found":
                matrix[key] = "conflict"
        return matrix

    def append_observations(self, record: Record, observations: list[dict]) -> tuple[int, int]:
        """Keep independent originals; no variant (including 8 frames) is replaced in place."""
        current = list(record.data.get("inventory_sources", []))
        identities = {(row["root_id"], row["path"], row["sha256"],
                       VariantKey(**row["variant"])) for row in current}
        added = 0
        for row in observations:
            identity = (row["root_id"], row["path"], row["sha256"], VariantKey(**row["variant"]))
            if identity not in identities:
                require(row["provenance"]["kind"] in ("unknown", "original", "derived"),
                        "Unbekannte Herkunft.")
                require(row["provenance"]["kind"] != "derived" or
                        bool(row["provenance"].get("source_sha256")),
                        "Ableitung benötigt eine explizite Quellbindung.")
                current.append(row)
                identities.add(identity)
                added += 1
        if added:
            self.project.catalog.save(record, data={**record.data, "inventory_sources": current})
        return added, len(observations) - added
