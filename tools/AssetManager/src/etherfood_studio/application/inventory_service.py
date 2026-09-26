"""Review and atomic metadata adoption; the selected source tree is never modified."""

from dataclasses import dataclass
import hashlib
import json
import re
from threading import Event

from ..domain.assets import require
from ..domain.models import StudioError, new_id
from ..storage.inventory_files import (
    ScanLimits, check_cancel, inside_reference, read_bytes, stamp,
)
from .asset_service import AssetService
from .document_service import DocumentService
from .inventory_scan import Candidate, ScanResult


@dataclass(frozen=True)
class PreparedInventory:
    scan: ScanResult
    selected: tuple[Candidate, ...]
    stamps: tuple[tuple[str, tuple], ...]
    provenance: dict


def prepare_adoption(scan: ScanResult, selected_paths: list[str], *, provenance: dict | None = None,
                     limits: ScanLimits | None = None,
                     cancel: Event | None = None) -> PreparedInventory:
    """Slow revalidation runs outside the catalog/GUI thread; no writes on cancel."""
    limits, cancel = limits or ScanLimits(), cancel or Event()
    require(bool(selected_paths) and len(set(selected_paths)) == len(selected_paths),
            "Mindestens eine eindeutige Datei bewusst auswählen.")
    candidates = {c.path: c for c in scan.candidates}
    require(all(p in candidates for p in selected_paths), "Auswahl gehört nicht zu diesem Scan.")
    selected = tuple(candidates[p] for p in selected_paths)
    require(all(c.state in {"proposal", "duplicate"} for c in selected),
            "Unklare oder nicht erforderliche Zuordnung kann nicht übernommen werden.")
    require(len({c.variant for c in selected}) == len(selected),
            "Mehrere Dateien derselben Variante gewählt; Auswahlkonflikt zuerst auflösen.")
    provenance = dict(provenance or {"kind": "unknown"})
    require(set(provenance) <= {"kind", "source_sha256"} and
            provenance.get("kind") in {"unknown", "original", "derived"}, "Ungültige Herkunft.")
    if provenance["kind"] == "derived":
        require(isinstance(provenance.get("source_sha256"), str) and
                bool(re.fullmatch(r"[0-9a-f]{64}", provenance["source_sha256"])),
                "Ableitung benötigt eine ausdrücklich angegebene Quell-SHA256.")
    else:
        require("source_sha256" not in provenance, "Quellbindung nur bei Ableitungen angeben.")
    provenance["assertion"] = "user_declared" if provenance["kind"] != "unknown" else "unknown"
    stamps = []
    references = [(c.path, c.sha256) for c in selected]
    references.extend((r["path"], r["sha256"]) for r in (*scan.reports, *scan.pages))
    for relative, expected in references:
        check_cancel(cancel)
        path = inside_reference(scan.root, scan.root, relative)
        before = stamp(path)
        actual = hashlib.sha256(read_bytes(path, limits.max_bytes, cancel)).hexdigest()
        if actual != expected or stamp(path) != before:
            raise StudioError("conflict", "Bestand seit Vorschau geändert; erneut erfassen.",
                              relative)
        stamps.append((relative, before))
    # Historical bindings must still match, including inputs not chosen for adoption.
    for report in scan.reports:
        if report["state"] != "historical_bound":
            continue
        for link in (*report["sources"], *report["outputs"]):
            path = inside_reference(scan.root, scan.root, link["path"])
            before = stamp(path)
            actual = hashlib.sha256(read_bytes(path, limits.max_bytes, cancel)).hexdigest()
            require(actual == link["expected_sha256"] and stamp(path) == before,
                    "Historische Berichtbindung inzwischen veraltet; erneut erfassen.")
            stamps.append((link["path"], before))
    check_cancel(cancel)
    return PreparedInventory(scan, selected, tuple(stamps), provenance)


class InventoryService:
    def __init__(self, assets: AssetService) -> None:
        self.assets = assets

    def adopt(self, identifier: str, expected_revision: int, prepared: PreparedInventory,
              *, cancel: Event | None = None) -> dict:
        cancel = cancel or Event()
        catalog, scan = self.assets.project.catalog, prepared.scan
        with catalog.transaction():
            check_cancel(cancel)
            record = self.assets.asset(identifier)
            require(record.revision_no == expected_revision,
                    "Asset seit Scan geändert; Anforderungen und Bestand erneut öffnen.")
            require(self.assets.definition(identifier) == scan.definition,
                    "Bestand gehört zu anderen Asset-Anforderungen.")
            for relative, expected in prepared.stamps:
                path = inside_reference(scan.root, scan.root, relative)
                require(stamp(path) == expected, "Bestand seit Prüfung geändert; erneut erfassen.")
            root_id = catalog.inventory_root(scan.root)
            observations = []
            for candidate in prepared.selected:
                observations.append({
                    "schema_version": 1, "id": new_id(), "root_id": root_id,
                    "path": candidate.path, "sha256": candidate.sha256,
                    "variant": candidate.variant.to_data(), "grid": list(candidate.grid),
                    "size": [candidate.width, candidate.height], "provenance": prepared.provenance,
                    "verification": "inventory_only", "approval": "not_granted",
                    "historical_reports": [{k: r[k] for k in ("path", "sha256", "state")}
                        for r in scan.reports
                        if r["state"] == "historical_bound" and any(
                            v["path"] == candidate.path and v["expected_sha256"] == candidate.sha256
                            for v in (*r["sources"], *r["outputs"]))],
                    "comparison_pages": [{k: p[k] for k in ("path", "sha256")}
                                         for p in scan.pages],
                })
            added, duplicate = self.assets.append_observations(record, observations)
            summary = {
                "adopted": added, "already_present": duplicate,
                "not_selected": len(scan.candidates) - len(prepared.selected),
                "needs_review": sum(c.state in {"needs_review", "duplicate"}
                                    for c in scan.candidates) + len(scan.problems),
                "skipped_files": scan.skipped, "source_files_changed": False,
                "approval": "not_granted",
            }
            if added:
                selected_paths = {c.path for c in prepared.selected}
                elements = [{"path": c.path,
                             "decision": "übernommen/vorhanden" if c.path in selected_paths
                             else "manuell klären" if c.state in {"needs_review", "duplicate"}
                             else "ausgelassen", "finding": c.state, "notes": c.notes}
                            for c in scan.candidates]
                text = ("# Lesende Bestandserfassung\n\nNur externe Katalogverweise übernommen. "
                        "Keine Quellkopie, Pixelprüfung, Freigabe oder Godot-Integration.\n\n"
                        "Übernommen / schon vorhanden / nicht gewählt / Klärfälle:\n\n" +
                        json.dumps(summary, ensure_ascii=False, indent=2) +
                        "\n\nWurzel-ID: " + root_id + "\n\nElemente und Klärfälle:\n\n" +
                        json.dumps({"elements": elements, "problems": scan.problems,
                                    "historical_reports": scan.reports,
                                    "comparison_pages": scan.pages}, ensure_ascii=False, indent=2))
                DocumentService(self.assets.project).create(
                    identifier, "Bestandserfassung " + new_id()[:8], text, generated=True,
                )
            check_cancel(cancel)
            return summary
