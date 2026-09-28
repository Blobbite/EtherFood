"""Explicit master selections and immutable soft/fixed/material color profiles."""

from copy import deepcopy

from ..domain.assets import DIRECTIONS, require
from ..domain.materials import COLOR_CONTRACT, REFERENCE_CONTRACT
from ..domain.models import StudioError
from ..pipelines.image_processing import legacy_modules
from .color_context import ColorContext
from .mask_service import MaskService


class ReferenceService(ColorContext):
    def active(self, asset_id):
        identifier = self.asset(asset_id).data.get("reference_selection_id")
        require(identifier, "Zuerst Masterreferenzen auswählen.")
        record = self.revision(identifier, asset_id, REFERENCE_CONTRACT)
        self.validate_selection(record)
        return record

    def validate_selection(self, record):
        legacy_modules()
        from PyImgReferenceSelection import validate_selection

        require(record.data.get("verification") == "verified",
            "Importierte Referenzen erneut auswählen.")
        try:
            validate_selection(record.data["selection"])
            for ref in record.data["selection"]["references"]:
                source = self.source(ref["source_revision"], record.owner_id)
                require(ref["sha256"] == source.data["sha256"] and ref["grid"] == source.data[
                    "grid"]
                        and ref["size"] == [source.data["width"], source.data["height"]]
                        and ref["direction"] == source.data["slot"]["direction"],
                        "Referenzauswahl widerspricht der gebundenen Quelle.")
        except (ValueError, KeyError, TypeError) as error:
            raise StudioError("validation", str(error)) from error

    def select(self, asset_id, source_ids, preview_id, expected_revision):
        self.asset(asset_id, expected_revision)
        require(0 < len(source_ids) <= 32 and len(source_ids) == len(set(source_ids)),
                "Eine bis 32 eindeutige Quellen auswählen.")
        legacy_modules()
        from PyImgReferenceSelection import SAMPLING, SELECTION_FORMAT, validate_selection

        poses = {p.id: p.display_name for p in self.assets.definition(asset_id).poses}
        refs = []
        for identifier in source_ids:
            source = self.source(identifier, asset_id)
            data = source.data
            refs.append({"id": source.id, "source_revision": source.id,
                         "path": source.id + ".png", "pose": poses.get(data["slot"]["pose_id"]),
                         "direction": data["slot"]["direction"], "grid": data["grid"],
                         "frames": data["frames"], "size": [data["width"], data["height"]],
                         "sha256": data["sha256"]})
        selection = {"format": SELECTION_FORMAT, "version": 1, "sampling": SAMPLING,
                     "preview_reference": preview_id, "references": refs}
        try:
            validate_selection(selection)
        except ValueError as error:
            raise StudioError("validation", str(error)) from error
        with self.catalog.transaction():
            asset = self.asset(asset_id, expected_revision)
            for identifier in source_ids:
                self.source(identifier, asset_id)
            previous = asset.data.get("reference_selection_id")
            if previous and self.catalog.get(previous).data.get("selection") == selection \
                    and self.catalog.get(previous).data.get("verification") == "verified":
                return self.catalog.get(previous)
            record = self.catalog.create("profile_revision", "Masterreferenzen", asset_id,
                {"contract": REFERENCE_CONTRACT, "selection": selection,
                 "verification": "verified", "previous": previous})
            self.catalog.save(asset, data={**asset.data, "reference_selection_id": record.id})
            return record

    def greenhero_selection(self, asset_id, expected_revision):
        """Explicit legacy preset: all stand sheets and all their frames, never fabricated."""
        poses = [p for p in self.assets.definition(asset_id).poses if p.export_name == "stand"]
        require(len(poses) == 1, "Die Acht-Richtungs-Vorlage benötigt eine eindeutige Stand-Pose.")
        active = self.sources.active(asset_id)
        by_direction = {k.direction: r.id for k, r in active.items()
                        if k.pose_id == poses[0].id and k.kind == "spritesheet"}
        require(set(DIRECTIONS) <= set(by_direction),
            "Alle acht Stand-Sheets müssen importiert sein.")
        ids = [by_direction[d] for d in DIRECTIONS]
        return self.select(asset_id, ids, by_direction["S"], expected_revision)

    def generate(self, asset_id, mode, expected_revision):
        self.asset(asset_id, expected_revision)
        require(mode in {"soft", "fixed", "material"}, "Unbekannter Farbmodus.")
        selection = self.active(asset_id)
        refs = selection.data["selection"]["references"]
        masks = MaskService(self.project)
        definitions, bindings = None, {}
        if mode == "material":
            definitions = masks.definitions(asset_id)
            bindings = {r["id"]: masks.for_source(asset_id, r["source_revision"]) for r in refs}
        legacy_modules()
        from PyImgReferenceSelection import make_profile

        try:
            profile = make_profile(selection.data["selection"],
                lambda ref: self.blob(self.source(ref["source_revision"], asset_id).data), mode,
                definitions=definitions.data["definitions"] if definitions else None,
                resolve_mask=lambda ref: self.blob(bindings[ref["id"]].data))
        except (ValueError, OSError) as error:
            raise StudioError("validation", str(error)) from error
        # Provenance is part of this color resource only, not of unrelated graphics branches.
        profile["studio_provenance"] = {"selection_id": selection.id,
            "material_revision": definitions.id if definitions else None,
            "mask_revisions": {key: value.id for key, value in bindings.items()}}
        blob = self.json_blob(profile)
        with self.catalog.transaction():
            asset = self.asset(asset_id, expected_revision)
            self.validate_selection(selection)
            if definitions:
                require(masks.definitions(asset_id).id == definitions.id,
                    "Materialdefinition geändert.")
                for source_id, mask in bindings.items():
                    require(masks.for_source(asset_id, source_id).id == mask.id,
                        "Referenzmaske geändert.")
            record = self.catalog.create("profile_revision", "Farbprofil · " + mode, asset_id,
                {"contract": COLOR_CONTRACT, **blob, "mode": mode, "verification": "verified",
                 **profile["studio_provenance"]})
            profiles = dict(asset.data.get("color_profiles", {}))
            profiles[mode] = record.id
            self.catalog.save(asset, data={**asset.data, "color_profiles": profiles})
            return record

    def profile(self, asset_id, mode):
        identifier = self.asset(asset_id).data.get("color_profiles", {}).get(mode)
        require(identifier, "Noch kein " + mode + "-Farbprofil für dieses Asset erzeugt.")
        record = self.revision(identifier, asset_id, COLOR_CONTRACT)
        require(record.data.get("verification") == "verified" and record.data["mode"] == mode,
                "Farbprofil ist nicht verifiziert.")
        require(self.active(asset_id).id == record.data["selection_id"],
                "Farbprofil veraltet: Referenzauswahl geändert; Profil neu erzeugen.")
        if mode == "material":
            masks = MaskService(self.project)
            require(masks.definitions(asset_id).id == record.data["material_revision"],
                    "Farbprofil veraltet: Materialdefinition geändert.")
            for source_id, mask_id in record.data["mask_revisions"].items():
                require(masks.for_source(asset_id, source_id).id == mask_id,
                        "Farbprofil veraltet: Referenzmaske geändert; Profil neu erzeugen.")
        self.read_profile(record, mode)
        return record

    def configure_step(self, asset_id, recipe_id, step_id, mode, expected_revision):
        """Explicit shared-recipe edit; each asset resolves its own managed resources."""
        from .pipeline_service import PipelineService

        self.profile(asset_id, mode)
        service = PipelineService(self.project)
        record = service.recipe(recipe_id)
        recipe = deepcopy(record.data["recipe"])
        node = next((n for n in recipe["steps"] if n["id"] == step_id), None)
        require(node and node["operation"] in {"color", "source_color"}, "Farbschritt auswählen.")
        node["parameters"]["mode"] = mode
        roles = {"soft": ["reference"], "fixed": ["palette"], "material": ["materials", "mask"]}[
            mode]
        node["parameters"].update({role: "@asset" for role in roles})
        return service.save(recipe_id, recipe, expected_revision)
