"""Immutable material definitions, source-bound label revisions and explicit visual reviews."""

from pathlib import Path
import tempfile

from PIL import Image

from ..domain.assets import require
from ..domain.materials import MATERIAL_CONTRACT, MASK_CONTRACT, MASK_REVIEW_CONTRACT, finding
from ..domain.models import StudioError
from ..domain.sources import SourceKey
from ..pipelines.image_processing import legacy_modules
from .color_context import ColorContext


class MaskService(ColorContext):
    def definitions(self, asset_id):
        identifier = self.asset(asset_id).data.get("material_definition_id")
        require(identifier, "Zuerst Materialdefinitionen anlegen/importieren.")
        return self.revision(identifier, asset_id, MATERIAL_CONTRACT)

    def save_definitions(self, asset_id, materials, expected_revision):
        self.asset(asset_id, expected_revision)
        exact = legacy_modules()[-1]
        try:
            exact.validate_materials(materials, definitions=True)
        except ValueError as error:
            raise StudioError("validation", str(error)) from error
        definitions = {"format": exact.DEFINITIONS_FORMAT, "version": 1, "materials": materials}
        with self.catalog.transaction():
            asset = self.asset(asset_id, expected_revision)
            previous = asset.data.get("material_definition_id")
            if previous and self.definitions(asset_id).data["definitions"] == definitions:
                return self.definitions(asset_id)
            record = self.catalog.create("profile_revision", "Materialdefinitionen", asset_id,
                {"contract": MATERIAL_CONTRACT, "definitions": definitions, "previous": previous})
            self.catalog.save(asset, data={**asset.data, "material_definition_id": record.id})
            return record

    def inspect(self, path, source, definitions):
        soft, exact = legacy_modules()[-2:]
        slot, data = source.data["slot"], source.data
        try:
            with soft.load_png(self.blob(data)) as image:
                with exact.load_mask(path, image, data["grid"], definitions["materials"],
                                     data["sha256"], validate=False) as labels:
                    results = exact.label_findings(labels, image, definitions["materials"], data[
                        "grid"])
                    if not results:
                        exact.validate_labels(labels, image, definitions["materials"], path,
                            data["grid"])
                    return [finding(row["code"], row["message"], slot, frame=row["frame"],
                                    bounds=row["bounds"], count=row["count"]) for row in results]
        except (ValueError, OSError) as error:
            return [finding("binding", str(error), slot)]

    def import_mask(self, asset_id, source_id, path, expected_revision, *, method="manual_import"):
        self.asset(asset_id, expected_revision)
        require(method in {"manual_import", "template", "legacy_import"},
            "Unbekannte Maskenherkunft.")
        source = self.source(source_id, asset_id)
        definitions = self.definitions(asset_id)
        # Preserve the exact L/P PNG, including index labels and source-binding metadata.
        blob = self.store.import_file(Path(path))
        copied = self.blob(blob)
        with Image.open(copied) as image:
            require(image.format == "PNG" and image.mode in {"L", "P"},
                    "Maske benötigt eine L/P-Label-PNG; RGB ist keine Material-ID.")
        findings = self.inspect(copied, source, definitions.data["definitions"])
        if method == "template" and not findings:
            findings = [finding("draft", "Unbeschriftete Vorlage ist ein Entwurf; "
                                "bearbeitete Maske importieren.", source.data["slot"])]
        with self.catalog.transaction():
            asset = self.asset(asset_id, expected_revision)
            self.source(source_id, asset_id)
            require(self.definitions(asset_id).id == definitions.id,
                "Materialdefinition inzwischen geändert.")
            token = SourceKey(**source.data["slot"]).token
            bindings = dict(asset.data.get("active_masks", {}))
            record = self.catalog.create("mask_revision", Path(path).name, asset_id,
                {"contract": MASK_CONTRACT, "sha256": blob["sha256"], "length": blob["length"],
                 "source_revision": source.id, "source_sha256": source.data["sha256"],
                 "grid": source.data["grid"], "slot": source.data["slot"],
                 "material_revision": definitions.id, "method": method,
                 "previous": bindings.get(token), "verification": "verified",
                 "technical": "failed" if findings else "passed", "findings": findings,
                 "visual": "pending"})
            bindings[token] = record.id
            self.catalog.save(asset, data={**asset.data, "active_masks": bindings})
            return record

    def create_template(self, asset_id, source_id, expected_revision):
        self.asset(asset_id, expected_revision)
        source = self.source(source_id, asset_id)
        exact = legacy_modules()[-1]
        with tempfile.TemporaryDirectory(prefix="studio-mask-") as temporary:
            path = Path(temporary) / "Unbeschriftete Maske.png"
            with Image.new("L", (source.data["width"], source.data["height"])) as mask:
                mask.save(path, pnginfo=exact.mask_metadata(source.data["grid"], source.data[
                    "sha256"]))
            return self.import_mask(asset_id, source_id, path, expected_revision, method="template")

    def status(self, identifier):
        record = self.catalog.get(identifier)
        require(record.kind == "mask_revision" and record.data.get("contract") == MASK_CONTRACT,
                "Maskenrevision auswählen.")
        data = record.data
        result = {"technical": "failed", "visual": "pending", "findings": []}
        try:
            source = self.source(data["source_revision"], record.owner_id)
            definitions = self.definitions(record.owner_id)
            require(definitions.id == data["material_revision"], "Materialdefinition ist veraltet.")
            require(data.get("verification") == "verified",
                "Importierte Maske neu prüfen/importieren.")
            require(data["source_sha256"] == source.data["sha256"] and data[
                "grid"] == source.data["grid"]
                    and data["slot"] == source.data["slot"],
                        "Masken-/Quellbindung widerspricht der Revision.")
            result["findings"] = self.inspect(self.blob(data), source, definitions.data[
                "definitions"])
            if data.get("method") == "template" and not result["findings"]:
                result["findings"] = [finding(
                    "draft", "Unbeschriftete Vorlage ist ein Entwurf; "
                    "bearbeitete Maske importieren.",
                    data["slot"])]
            if not result["findings"]:
                result["technical"] = "passed"
                reviews = self.records(record.owner_id, MASK_REVIEW_CONTRACT)
                if any(r.data.get("binding") == self.review_binding(record) for r in reviews):
                    result["visual"] = "confirmed"
        except (StudioError, OSError, KeyError, ValueError) as error:
            result["technical"] = "stale"
            result["findings"] = [finding("stale", str(error), data.get("slot", {}))]
        return result

    @staticmethod
    def review_binding(record):
        return {key: record.data[key] for key in
                ("source_revision", "source_sha256", "sha256", "material_revision", "grid")} | {
                    "mask_id": record.id}

    def confirm(self, identifier, reviewer, expected_revision):
        require(isinstance(reviewer, str) and 0 < len(reviewer.strip()) <= 128,
                "Namen/Profil für die ausdrückliche Sichtbestätigung angeben.")
        with self.catalog.transaction():
            record = self.catalog.get(identifier)
            self.asset(record.owner_id, expected_revision)
            status = self.status(identifier)
            require(status["technical"] == "passed",
                "Nur technisch gültige aktuelle Masken bestätigen.")
            return self.catalog.create("review", "Masken-Sichtbestätigung", record.owner_id,
                {"contract": MASK_REVIEW_CONTRACT, "binding": self.review_binding(record),
                 "reviewer": reviewer.strip(), "scope": "selected_mask_only"})

    def for_source(self, asset_id, source_id, *, confirmed=True):
        source = self.source(source_id, asset_id)
        token = SourceKey(**source.data["slot"]).token
        identifier = self.asset(asset_id).data.get("active_masks", {}).get(token)
        require(identifier, "Keine Maskenrevision für diese Quelle; zuerst importieren.")
        record = self.revision(identifier, asset_id, MASK_CONTRACT)
        require(record.data["source_revision"] == source_id, "Maskenbindung ist veraltet.")
        status = self.status(record.id)
        require(status["technical"] == "passed", "; ".join(r["message"] for r in status[
            "findings"]))
        require(not confirmed or status["visual"] == "confirmed",
                "Materialmaske ist technisch gültig, aber noch nicht visuell bestätigt.")
        return record

    def activate(self, asset_id, identifier, expected_revision):
        with self.catalog.transaction():
            asset = self.asset(asset_id, expected_revision)
            record = self.revision(identifier, asset_id, MASK_CONTRACT)
            self.source(record.data["source_revision"], asset_id)
            require(self.definitions(asset_id).id == record.data["material_revision"],
                    "Alte Maskenrevision passt nicht zur aktuellen Materialdefinition.")
            bindings = dict(asset.data.get("active_masks", {}))
            bindings[SourceKey(**record.data["slot"]).token] = record.id
            self.catalog.save(asset, data={**asset.data, "active_masks": bindings})
