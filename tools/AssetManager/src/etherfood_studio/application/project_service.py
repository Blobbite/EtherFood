"""Project lifecycle and card operations shared by CLI, UI and tests."""

import json
from pathlib import Path

from ..config import Configuration
from ..domain.models import Record, StudioError
from ..domain.relations import CARD_KINDS, validate_relation
from ..storage.paths import real_path, safe_target, validate_roots
from ..storage.sqlite_repository import Catalog, canonical

CATALOG_NAME = "project.studio.sqlite"
SETTINGS_NAME = "project.studio-local.json"


class ProjectService:
    def __init__(self, catalog: Catalog, config: Configuration | None = None) -> None:
        self.catalog = catalog
        self.config = config or Configuration({"WORKSPACE_ROOT": catalog.path.parent})

    @classmethod
    def new(cls, directory: Path, title: str,
            roots: dict[str, Path] | None = None) -> "ProjectService":
        root = real_path(directory)
        if not root.is_dir() or any(root.iterdir()):
            raise StudioError("validation", "Für ein neues Projekt einen leeren Ordner wählen.")
        if not title.strip() or len(title.strip()) > 256:
            raise StudioError("validation", "Projektname fehlt oder ist zu lang.")
        mapping = dict(roots or {}) | {"WORKSPACE_ROOT": root}
        validate_roots(mapping)
        catalog = Catalog(safe_target(root, CATALOG_NAME), create=True)
        service = cls(catalog, Configuration(mapping))
        try:
            with catalog.transaction():
                project = catalog.create("project", title)
                service.create_card("global", "Projektweite Inhalte", project.id)
            settings = {"schema_version": 1, "roots": {k: str(v) for k, v in mapping.items()}}
            with safe_target(root, SETTINGS_NAME).open("x", encoding="utf-8") as output:
                output.write(canonical(settings) + "\n")
        except Exception:
            catalog.close()
            raise
        return service

    @classmethod
    def open(cls, directory: Path) -> "ProjectService":
        root = real_path(directory)
        config = Configuration.load(safe_target(root, SETTINGS_NAME))
        validate_roots(config.roots, require_available=False)
        stored = config.roots.get("WORKSPACE_ROOT")
        if stored is None or real_path(stored, must_exist=False) != root:
            raise StudioError("unavailable", "Projektwurzel passt nicht zur lokalen Konfiguration.")
        catalog = Catalog(safe_target(root, CATALOG_NAME))
        service = cls(catalog, config)
        try:
            service.validate_structure()
        except Exception:
            catalog.close()
            raise
        return service

    def unavailable_roots(self) -> list[str]:
        return [alias for alias, path in self.config.roots.items() if not path.is_dir()]

    def cards(self, *, include_archived: bool = False) -> list[Record]:
        return sorted((record for record in self.catalog.records(include_archived=include_archived)
                       if record.kind in CARD_KINDS),
                      key=lambda row: (row.data.get("order", 0), row.created_at, row.id))

    def project(self) -> Record:
        projects = [record for record in self.cards() if record.kind == "project"]
        if len(projects) != 1:
            raise StudioError("integrity", "Katalog benötigt genau ein Projekt.")
        return projects[0]

    def create_card(self, kind: str, title: str, parent_id: str,
                    data: dict | None = None) -> Record:
        if kind not in CARD_KINDS - {"project"}:
            raise StudioError("validation", "Ungültiger Kartentyp.")
        with self.catalog.transaction():
            if kind == "global" and any(row.kind == "global" for row in self.cards()):
                raise StudioError("conflict", "Projektweiter Rahmen existiert bereits.")
            record = self.catalog.create(kind, title, parent_id, {"order": 0, **(data or {})})
            parent = self.catalog.get(parent_id)
            validate_relation(record, parent, "belongs_to", self.catalog.relations())
            self.catalog.add_relation(record.id, parent.id, "belongs_to")
            return record

    def rename(self, identifier: str, title: str, expected_revision: int) -> Record:
        record = self.catalog.get(identifier)
        self._check_revision(record, expected_revision)
        return self.catalog.save(record, title=title)

    @staticmethod
    def _check_revision(record: Record, expected: int) -> None:
        if record.revision_no != expected:
            raise StudioError("conflict", "Neuere Änderung vorhanden; bitte neu laden.")

    def move(self, identifier: str, parent_id: str, expected_revision: int) -> Record:
        with self.catalog.transaction():
            record, target = self.catalog.get(identifier), self.catalog.get(parent_id)
            self._check_revision(record, expected_revision)
            validate_relation(record, target, "belongs_to", self.catalog.relations())
            relation_id = None
            for edge in self.catalog.relations():
                if edge["source_id"] == identifier and edge["kind"] == "belongs_to":
                    relation_id = edge["id"]
                    self.catalog.remove_relation(edge["id"])
            self.catalog.add_relation(identifier, parent_id, "belongs_to", identifier=relation_id)
            return self.catalog.save(record, owner_id=parent_id)

    def reorder(self, identifier: str, order: int, expected_revision: int) -> Record:
        record = self.catalog.get(identifier)
        self._check_revision(record, expected_revision)
        return self.catalog.save(record, data=record.data | {"order": order})

    def relate(self, source: str, target: str, kind: str,
               *, identifier: str | None = None) -> str:
        if kind == "belongs_to":
            raise StudioError("validation", "Hierarchie über die Umordnen-Aktion ändern.")
        with self.catalog.transaction():
            edges = self.catalog.relations()
            validate_relation(self.catalog.get(source), self.catalog.get(target), kind, edges)
            if any(edge["source_id"] == source and edge["target_id"] == target
                   and edge["kind"] == kind for edge in edges):
                raise StudioError("conflict", "Verbindung existiert bereits.")
            return self.catalog.add_relation(source, target, kind, identifier=identifier)

    def unlink(self, identifier: str) -> None:
        edge = next((row for row in self.catalog.relations() if row["id"] == identifier), None)
        if edge is None or edge["kind"] == "belongs_to":
            raise StudioError("validation", "Hierarchie nicht lösen, sondern Karte umordnen.")
        self.catalog.remove_relation(identifier)

    def affected_relations(self, identifier: str) -> list[dict]:
        return [edge for edge in self.catalog.relations()
                if identifier in (edge["source_id"], edge["target_id"])]

    def usage_description(self, identifier: str) -> str:
        record = self.catalog.get(identifier)
        owner = self.breadcrumb(record.owner_id) if record.owner_id else "Projektwurzel"
        edges = self.catalog.relations()
        used_by = [self.catalog.get(edge["source_id"]) for edge in edges
                   if edge["kind"] == "uses" and edge["target_id"] == identifier]
        uses = [self.catalog.get(edge["target_id"]) for edge in edges
                if edge["kind"] == "uses" and edge["source_id"] == identifier]
        lines = ["Eigentümer / Herkunft: " + owner]
        if record.kind in {"asset", "package"}:
            lines.append(f"Verwendet in {len(used_by)} Ort(en) · dieselbe ID, keine Kopien:")
            lines.extend("• " + self.breadcrumb(row.id) + (" [Archiv]" if row.archived else "")
                         for row in used_by)
            if not used_by:
                lines.append("Noch keine zusätzlichen Verweise.")
            lines.append("Verwaltungskarte: Grafikimport und Vorschau folgen in späteren Paketen.")
        if uses:
            lines.append("Verwendet vorhandene Karten:")
            lines.extend("↪ " + row.title + (" [Archiv]" if row.archived else "") for row in uses)
        return "\n".join(lines)

    def relink(self, identifier: str, source: str, target: str) -> None:
        """Retarget a non-ownership edge atomically without changing its identity."""
        with self.catalog.transaction():
            edges = self.catalog.relations()
            edge = next((row for row in edges if row["id"] == identifier), None)
            if edge is None or edge["kind"] == "belongs_to":
                raise StudioError("validation", "Hierarchie ausdrücklich umordnen.")
            remaining = [row for row in edges if row["id"] != identifier]
            validate_relation(self.catalog.get(source), self.catalog.get(target),
                              edge["kind"], remaining)
            if any(row["source_id"] == source and row["target_id"] == target
                   and row["kind"] == edge["kind"] for row in remaining):
                raise StudioError("conflict", "Verbindung existiert bereits.")
            self.catalog.remove_relation(identifier)
            self.catalog.add_relation(source, target, edge["kind"], identifier=identifier)

    def archive(self, identifier: str, archived: bool, expected_revision: int) -> Record:
        record = self.catalog.get(identifier)
        if record.kind in {"project", "global"}:
            raise StudioError("validation", "Projektrahmen kann nicht archiviert werden.")
        self._check_revision(record, expected_revision)
        return self.catalog.save(record, archived=archived)

    def descendants(self, identifier: str) -> set[str]:
        found = {identifier}
        previous = set()
        while previous != found:
            previous = set(found)
            found.update(row.id for row in self.cards(include_archived=True)
                         if row.owner_id in previous)
        return found

    def breadcrumb(self, identifier: str) -> str:
        names = []
        seen = set()
        while identifier:
            if identifier in seen:
                raise StudioError("integrity", "Zyklische Hierarchie im Katalog.")
            seen.add(identifier)
            record = self.catalog.get(identifier)
            names.append(record.title)
            identifier = record.owner_id
        return " / ".join(reversed(names))

    def validate_structure(self) -> None:
        self.project()
        cards = self.cards(include_archived=True)
        if len([row for row in cards if row.kind == "global"]) != 1:
            raise StudioError("integrity", "Projektweiter Rahmen fehlt oder ist mehrfach vorhanden")
        edges = self.catalog.relations()
        from dataclasses import replace

        for card in cards:
            self.catalog.layout(card.id)
            self.breadcrumb(card.id)
            parents = [e for e in edges
                       if e["kind"] == "belongs_to" and e["source_id"] == card.id]
            if card.kind != "project" and (
                len(parents) != 1 or parents[0]["target_id"] != card.owner_id
            ):
                raise StudioError("integrity", "Kartenbesitzer und Hierarchie widersprechen sich.")
        for edge in edges:
            validate_relation(replace(self.catalog.get(edge["source_id"]), archived=False),
                              replace(self.catalog.get(edge["target_id"]), archived=False),
                              edge["kind"], [other for other in edges if other != edge])

    def import_snapshot(self, content: str) -> None:
        with self.catalog.transaction():
            self.catalog.import_snapshot(content)
            self.validate_structure()

    def demo(self) -> dict[str, str]:
        """Create clearly labelled synthetic structure, never game canon."""
        with self.catalog.transaction():
            global_card = next(row for row in self.cards() if row.kind == "global")
            act = self.create_card("act", "Demo: Akt 1", self.project().id)
            one = self.create_card("chapter", "Demo: Kapitel 1", act.id)
            two = self.create_card("chapter", "Demo: Kapitel 2", act.id)
            hero = self.create_card("asset", "Demo: globaler Held", global_card.id,
                                    {"workflow": "animated"})
            effect = self.create_card("asset", "Demo: globaler Effekt", global_card.id,
                                      {"workflow": "effect"})
            temple = self.create_card("package", "Demo: Tempelpaket", one.id,
                                      {"workflow": "static"})
            for chapter in (one, two):
                self.relate(chapter.id, hero.id, "uses")
                self.relate(chapter.id, effect.id, "uses")
            return {"act": act.id, "one": one.id, "two": two.id, "hero": hero.id,
                    "effect": effect.id, "temple": temple.id}
