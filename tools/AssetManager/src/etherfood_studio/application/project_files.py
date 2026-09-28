"""Readable ownership folders and checked asset derivations; never use Canvas coordinates."""

import hashlib
import json
from pathlib import Path
import re
import unicodedata

from ..domain.assets import TYPE_PRESETS, require
from ..domain.models import StudioError
from ..storage.blob_store import BlobStore, file_hash
from ..storage.file_changes import FileChanges
from ..storage.paths import RESERVED, safe_target
from ..storage.sqlite_repository import canonical


def component(title):
    value = unicodedata.normalize("NFC", title)
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .") or "Ohne Namen"
    while len(value.encode("utf-8")) > 100:
        value = value[:-1]
    return "_" + value if RESERVED.match(value) or value.startswith(".") else value


class ProjectFiles:
    def __init__(self, project):
        self.project, self.catalog = project, project.catalog
        self.root = self.catalog.path.parent

    def path(self, identifier):
        record = self.catalog.get(identifier)
        if record.kind == "project":
            return self.root
        row = self.catalog.db.execute("SELECT path FROM card_paths WHERE id=?",
                                      (identifier,)).fetchone()
        require(row is not None, "Kartenablage ist noch nicht angelegt.")
        return safe_target(self.root, row["path"])

    def prepare(self):
        change = FileChanges(self.catalog)
        try:
            self.sync(change)
            change.committed()
            return change
        except Exception:
            change.rollback()
            raise

    @staticmethod
    def asset_type(card):
        definition = card.data.get("asset_definition", {})
        kind = definition.get("type", {})
        identifier = kind.get("id") or card.data.get("asset_type")
        label = kind.get("label") or TYPE_PRESETS.get(identifier, (identifier, ()))[0]
        return component(label or ("Pakete" if card.kind == "package" else "Unsortiert"))

    def folder_parent(self, card, targets, by_id):
        parent = Path(targets[card.owner_id])
        if card.kind == "pipeline":
            return parent / ".pipelines"
        if card.kind in {"asset", "package"}:
            if by_id[card.owner_id].kind != "package":
                parent /= "Assets"
            parent /= self.asset_type(card)
        return parent

    def sync(self, change):
        cards = self.project.cards(include_archived=True)
        if not cards:
            return
        old = {row["id"]: row["path"]
               for row in self.catalog.db.execute("SELECT * FROM card_paths")}
        by_id = {r.id: r for r in cards}
        targets = {}
        pending = list(cards)
        while pending:
            ready = [r for r in pending if r.kind == "project" or r.owner_id in targets]
            require(ready, "Ordnerhierarchie enthält fehlende Eltern oder einen Zyklus.")
            for card in ready:
                pending.remove(card)
                if card.kind == "project":
                    targets[card.id] = ""
                    continue
                name = component(card.title)
                duplicates = [r for r in cards if r.owner_id == card.owner_id and
                              component(r.title).casefold() == name.casefold()]
                if len(duplicates) > 1:
                    name += "--" + card.id[:8]
                parent = self.folder_parent(card, targets, by_id)
                relative = str(Path(parent) / name)
                target = safe_target(self.root, relative)
                previous = old.get(card.id)
                fallback = relative + "--" + card.id[:8]
                if (previous is None or previous == fallback) and target.exists() and \
                        relative not in old.values():
                    relative = fallback
                    target = safe_target(self.root, relative)
                if previous and previous != relative:
                    source = safe_target(self.root, previous)
                    require(source.is_dir(), "Bisherige Kartenablage fehlt: " + previous)
                    change.move(source, target)
                    # An ancestor move carries every owned descendant with it.
                    old = {key: relative + value[len(previous):]
                           if value == previous or value.startswith(previous + "/") else value
                           for key, value in old.items()}
                elif not previous:
                    require(not target.exists(),
                            "Ordner existiert außerhalb des Katalogs: " + relative)
                    change.mkdir(target)
                else:
                    require(target.is_dir(), "Kartenablage fehlt: " + relative)
                targets[card.id] = relative
        self.catalog.db.execute("DELETE FROM card_paths")
        self.catalog.db.executemany("INSERT INTO card_paths VALUES (?,?)",
                                   [(key, value) for key, value in targets.items() if value])
        self.targets = targets
        self.files = {(row["owner_id"], row["path"]): row["sha256"]
                      for row in self.catalog.db.execute("SELECT * FROM managed_files")}
        for card in cards:
            self.json(change, card.id, ".studio-card.json", {
                "contract": "studio-card-folder-v1", "id": card.id, "kind": card.kind,
                "title": card.title, "owner_id": card.owner_id, "archived": card.archived})
            if card.kind == "pipeline":
                self.json(change, card.id, "rezept.json", {"id": card.id,
                    "revision": card.revision_no, "recipe": card.data["recipe"]})
                from .plugin_service import PluginService
                plugins = PluginService(self.project)
                manifests = plugins.manifests()
                copied = set()
                for node in card.data["recipe"]["steps"]:
                    if node["operation"] not in manifests:
                        from ..packages import bundle_for, files, manifests as bundled
                        if node["operation"] in bundled():
                            bundle = bundle_for(node["operation"])
                            if bundle not in copied:
                                for path in files(node["operation"]):
                                    self.copy(change, card.id, "Pakete/studio-" + bundle +
                                              "/" + path.name, path, file_hash(path))
                                copied.add(bundle)
                        continue
                    plugin = plugins.details(node["operation"])
                    manifest = plugin["manifest"]
                    directory = "Pakete/" + component(node["operation"].replace(":", "-"))
                    self.json(change, card.id, directory + "/manifest.json", manifest)
                    self.copy(change, card.id, directory + "/" + manifest.get("source", "step.py"),
                              plugins.store.path_for(plugin["code_hash"]), plugin["code_hash"])
            if card.kind == "asset":
                for name in ("Quellen", "Ergebnisse"):
                    change.mkdir(self.path(card.id) / name)
        for source in self.catalog.records(include_archived=True):
            if source.kind != "source_revision" or source.owner_id not in by_id:
                continue
            data = source.data
            if data.get("verification") != "verified" or "sha256" not in data:
                continue
            blob = BlobStore(self.catalog, self.root).path_for(data["sha256"])
            if not blob.is_file():
                continue  # Unavailable sources keep their existing catalog status on open.
            name = component(Path(data["original_name"]).stem) + "--" + source.id[:12]
            self.copy(change, source.owner_id, "Quellen/" + name + ".png", blob, data["sha256"])
            self.json(change, source.owner_id, "Quellen/" + name + ".json",
                      {"source_id": source.id, **data})
        runs = [r for r in self.catalog.records() if r.kind == "build" and
                r.data.get("contract") == "studio-build-run-v1" and
                r.data.get("published") and r.data.get("status") == "succeeded"]
        latest = {}
        for run in sorted(runs, key=lambda r: (r.created_at, r.id)):
            latest[run.owner_id] = run
        for run in latest.values():
            self.publish(change, run)
        if self.catalog.db.execute(
                "SELECT 1 FROM sqlite_master WHERE name='document_files'").fetchone():
            from .project_documents import ProjectDocuments
            ProjectDocuments(self).sync(change, cards)

    def json(self, change, owner, name, data):
        content = (canonical(data) + "\n").encode("utf-8")
        self.file(change, owner, name, hashlib.sha256(content).hexdigest(), content=content)

    def copy(self, change, owner, name, source, digest):
        self.file(change, owner, name, digest, source=source)

    def file(self, change, owner, name, digest, **kwargs):
        target = safe_target(self.root, str(Path(self.targets[owner]) / name))
        previous = self.files.get((owner, name))
        if previous == digest and target.is_file():
            return
        # Explicit re-registration may select an edited visible package copy itself.
        # Adopt only bytes matching the newly registered immutable content exactly.
        adopted = previous is not None and target.is_file() and file_hash(target) == digest
        if not adopted:
            change.write(target, previous=previous, **kwargs)
        require(file_hash(target) == digest, "Dateikopie wurde während der Ablage verändert.")
        self.catalog.db.execute(
            "INSERT INTO managed_files VALUES (?,?,?) ON CONFLICT(owner_id,path) "
            "DO UPDATE SET sha256=excluded.sha256", (owner, name, digest))
        self.files[(owner, name)] = digest

    def publish(self, change, run):
        from .recipe_results import RecipeResultService

        report = run.data
        snapshot = json.loads(report["plan"]["snapshot"])
        actual = {row["node"]: row for row in report["actual"]}
        prepared = {}
        # Verify every final file before copying any of a historical run's outputs.
        # A corrupt historical cache remains inspectable instead of blocking project open.
        try:
            for variant in report["plan"]["variants"]:
                if not variant["required"]:
                    continue
                build = self.catalog.get(actual[variant["node"]]["build_id"])
                existing = self.catalog.db.execute(
                    "SELECT 1 FROM asset_publications WHERE build_id=?", (build.id,)).fetchone()
                if not existing or run.id in self.catalog.projection_builds:
                    prepared[build.id] = RecipeResultService(self.project).metadata(
                        build, published=bool(existing))
        except (StudioError, OSError, ValueError, KeyError, TypeError):
            if run.id in self.catalog.projection_builds:
                raise
            return
        artifacts = []
        for variant in report["plan"]["variants"]:
            if not variant["required"]:
                continue
            result = actual[variant["node"]]
            require(result["actual"] in {"built", "reused"}, "Unvollständige Bildveröffentlichung.")
            build = self.catalog.get(result["build_id"])
            require(build.owner_id == run.owner_id, "Bild gehört zu einem anderen Asset.")
            existing = self.catalog.db.execute(
                "SELECT path FROM asset_publications WHERE build_id=?", (build.id,)).fetchone()
            if existing:
                relative = existing["path"]
            else:
                artifact = prepared[build.id]
                meta = artifact["metadata"]
                source = self.catalog.get(meta["source_revision"])
                name = component(Path(source.data["original_name"]).stem)
                name += "--" + build.data["input_fingerprint"][:12]
                relative = "Ergebnisse/" + component(meta["profile"]) + "/" + name + ".png"
                directory = safe_target(self.root, artifact["image_path"]).parent
                require(self.files.get((run.owner_id, relative)) in {None, meta["image_sha256"]},
                        "Buildkennung kollidiert mit einer bestehenden Bildausgabe.")
                self.copy(change, run.owner_id, relative, directory / "image.png",
                          meta["image_sha256"])
                metadata_path = str(Path(relative).with_suffix(".json"))
                require(self.files.get((run.owner_id, metadata_path)) in {
                    None, file_hash(directory / "metadata.json")},
                    "Buildkennung kollidiert mit bestehenden Ausgabemetadaten.")
                self.copy(change, run.owner_id, metadata_path, directory / "metadata.json",
                          file_hash(directory / "metadata.json"))
                self.catalog.db.execute("INSERT INTO asset_publications VALUES (?,?,?)",
                                        (build.id, run.owner_id, relative))
            artifacts.append({"variant": variant["key"], "build_id": build.id,
                              "image_path": relative,
                              "metadata_path": str(Path(relative).with_suffix(".json"))})
        self.json(change, run.owner_id, "Ergebnisse/aktuell.json", {
            "contract": "studio-asset-results-v1", "asset_id": run.owner_id,
            "run_id": run.id, "recipe_id": snapshot.get("recipe_id"),
            "recipe_revision": snapshot.get("recipe_revision"), "artifacts": artifacts})
