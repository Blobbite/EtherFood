"""Catalog-backed Markdown with protected automatic sections and relative local links."""

import hashlib
import json
import os
from pathlib import Path
from urllib.parse import quote
from uuid import NAMESPACE_URL, uuid5

from ..domain.assets import require
from ..domain.models import MAX_TEXT, StudioError
from ..domain.notes import is_note
from ..storage.blob_store import file_hash
from ..storage.paths import safe_target
from .project_files import component

START = "<!-- STUDIO:AUTO START -->"
END = "<!-- STUDIO:AUTO END -->"
KINDS = {"project": "Projekt", "global": "Projektweit", "act": "Akt",
         "chapter": "Kapitel", "package": "Asset-Paket", "asset": "Asset",
         "pipeline": "Pipeline", "note": "Notizbereich"}


def text(value):
    value = str(value).replace("\n", " ").replace("\r", " ")
    for char in "\\`*_{}[]<>|":
        value = value.replace(char, "\\" + char)
    return value


def generated(body, content):
    """Only our explicitly delimited block is replaced; all other text is verbatim."""
    require(body.count(START) == body.count(END) == 1 and body.index(START) < body.index(END),
            "Automatische Dokumentation benötigt genau einen STUDIO:AUTO-Abschnitt. "
            "Eigene Texte außerhalb der Markierungen schreiben.")
    before, remaining = body.split(START)
    _, after = remaining.split(END)
    return before + START + "\n" + content.strip("\n").rstrip() + "\n" + END + after


def manual_part(body):
    return generated(body, "")


def read_markdown(path):
    with path.open("rb") as stream:
        raw = stream.read(MAX_TEXT + 1)
    require(len(raw) <= MAX_TEXT, "Markdown ist größer als 1 MiB: " + path.name)
    try:
        return raw.decode("utf-8"), hashlib.sha256(raw).hexdigest()
    except UnicodeError as error:
        raise StudioError("validation", "Markdown benötigt UTF-8: " + path.name) from error


class ProjectDocuments:
    def __init__(self, files):
        self.files, self.project = files, files.project
        self.catalog, self.root = files.catalog, files.root

    def ensure(self, cards):
        self.records = {r.id: r for r in self.catalog.records(include_archived=True)}
        records = self.records
        self.sections = {}
        for card in cards:
            roles = ("section", "index") if card.kind == "project" else ("section",)
            for role in roles:
                identifier = str(uuid5(NAMESPACE_URL, "etherfood-document:" + card.id + role))
                title = "Startseite" if role == "index" else card.title[:240] + " · Dokumentation"
                if identifier in records:
                    existing = records[identifier]
                    require(existing.kind == "document" and existing.owner_id == card.id and
                            existing.data.get("automation") == role,
                            "Grunddokument-ID kollidiert mit einem vorhandenen Datensatz.")
                if identifier not in records:
                    tail = "\n\n## Beschreibung\n\n"
                    if card.kind == "act":
                        tail += "## Ziel\n\n## Offene Fragen\n\n"
                    elif card.kind == "chapter":
                        tail += "## Anforderungen\n\n## Nachweise\n\n"
                    elif card.kind == "asset":
                        tail += "## Verwendungszweck\n\n"
                    records[identifier] = self.catalog.create("document", title, card.id, {
                            "body": START + "\n" + END + (tail if role == "section" else "\n"),
                            "document_type": "manual" if role == "section" else "generated",
                            "automation": role, "attachments": [], "template": "Dokumentation",
                            "initial_manual": tail if role == "section" else "\n",
                        }, identifier=identifier)
                elif records[identifier].title != title:
                    records[identifier] = self.catalog.save(records[identifier], title=title)
                self.sections[(card.id, role)] = identifier
        self.records = dict(sorted(records.items()))

    def desired_name(self, document, cards):
        card = cards[document.owner_id]
        role = document.data.get("automation")
        if role == "index":
            return "Index.md"
        if role == "section":
            return ("Projekt" if card.kind == "project" else component(card.title)) + ".md"
        return "Dokumente/" + component(document.title) + "--" + document.id[:8] + ".md"

    def sync(self, change, cards):
        self.ensure(cards)
        self.cards = {r.id: r for r in cards}
        self.visible = self.project.content_scope()
        docs = [r for r in self.records.values()
                if r.kind == "document" and r.owner_id in self.cards]
        old = {r["id"]: dict(r) for r in self.catalog.db.execute("SELECT * FROM document_files")}
        self.paths = {}
        for doc in docs:
            name = self.desired_name(doc, self.cards)
            prior = old.get(doc.id)
            target = self.files.path(doc.owner_id) / name
            if prior and prior["owner_id"] == doc.owner_id and \
                    prior["path"].startswith(str(Path(name).with_suffix("")) + "--"):
                name = prior["path"]  # Keep a previously disambiguated name stable.
            elif target.exists() and (not prior or prior["owner_id"] != doc.owner_id or
                                      prior["path"] != name):
                name = str(Path(name).with_suffix("")) + "--" + doc.id[:8] + ".md"
            self.paths[doc.id] = self.files.path(doc.owner_id) / name
        for doc in docs:
            prior = old.get(doc.id)
            body, previous = doc.data["body"], None
            source = None
            if prior:
                source = safe_target(self.root, str(self.files.path(prior["owner_id"])
                                     .relative_to(self.root) / prior["path"]))
                if source.is_file():
                    external, previous = read_markdown(source)
                    if previous != prior["sha256"]:
                        require(body == prior["body"] or body == external,
                                "Dokument gleichzeitig extern und in Studio geändert: " +
                                source.name + ". Beide Fassungen bleiben erhalten.")
                        body = external
            role = doc.data.get("automation")
            if role:
                content = self.index(doc) if role == "index" else self.section(doc)
                body = generated(body, content)
            require(len(body.encode("utf-8")) <= MAX_TEXT, "Dokument überschreitet 1 MiB.")
            if body != doc.data["body"]:
                doc = self.catalog.save(doc, data=doc.data | {"body": body})
                self.records[doc.id] = doc
            target = safe_target(self.root, str(self.paths[doc.id].relative_to(self.root)))
            if source and source != target and source.exists():
                change.move(source, target)
            content = body.encode("utf-8")
            digest = hashlib.sha256(content).hexdigest()
            if not target.exists() or file_hash(target) != digest:
                change.write(target, content=content, previous=previous)
            self.catalog.db.execute(
                "INSERT INTO document_files VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
                "owner_id=excluded.owner_id,path=excluded.path,sha256=excluded.sha256,"
                "body=excluded.body", (doc.id, doc.owner_id,
                    str(target.relative_to(self.files.path(doc.owner_id))), digest, body))
        self.asset_indexes(change, cards)

    def link(self, base, target, label):
        relative = os.path.relpath(target, base.parent).replace(os.sep, "/")
        return "[" + text(label) + "](" + quote(relative, safe="/.-_") + ")"

    def card_link(self, base, card):
        return self.link(base, self.paths[self.sections[(card.id, "section")]], card.title)

    def document_links(self, doc):
        others = [r for r in self.records.values() if not r.archived and r.kind == "document" and
                  r.owner_id == doc.owner_id and r.id != doc.id and r.id in self.paths]
        return ["- " + self.link(self.paths[doc.id], self.paths[r.id], r.title) for r in others]

    def section(self, doc):
        card, base = self.cards[doc.owner_id], self.paths[doc.id]
        lines = ["# " + text(card.title), "", "Bereich: " + KINDS[card.kind] +
                 (" · Archiviert" if card.id not in self.visible else ""), ""]
        if card.owner_id:
            lines += ["Übergeordnet: " + self.card_link(base, self.cards[card.owner_id]), ""]
        children = [r for r in self.cards.values()
                    if r.owner_id == card.id and r.id in self.visible]
        lines += ["## Inhalt", ""]
        lines += ["- " + self.card_link(base, r) + " · " + KINDS[r.kind] for r in children]
        if not children:
            lines += ["Noch keine untergeordneten Bereiche."]
        if card.kind in {"global", "act", "chapter", "package"}:
            directory = "" if card.kind == "package" else "Assets/"
            lines += ["", self.link(base, self.files.path(card.id) / directory / "index.md",
                                   "Assets nach Typ")]
        if card.kind == "asset":
            lines += self.asset_section(card, base)
        elif card.kind == "pipeline":
            lines += ["", "## Verarbeitungsschritte", ""]
            lines += ["- " + text(n["operation"]) + ("" if n["enabled"] else " · deaktiviert")
                      for n in card.data["recipe"]["steps"]]
            lines += ["", "Ausgaben werden bei den verarbeiteten Assets abgelegt."]
        edges = [e for e in self.catalog.relations() if e["source_id"] == card.id and
                 e["kind"] != "belongs_to" and e["target_id"] in self.visible]
        if edges:
            lines += ["", "## Verweise", ""]
            lines += ["- " + self.card_link(base, self.cards[e["target_id"]]) +
                      (" · Verwendung" if e["kind"] == "uses" else " · Voraussetzung")
                      for e in edges]
        lines += ["", "## Dokumente", "", *self.document_links(doc)]
        lines += self.planning(card.id, base)
        return "\n".join(lines)

    def planning(self, owner, base):
        lines = []
        for kind, title in (("task", "Aufgaben"), ("issue", "Issues / Probleme")):
            rows = [r for r in self.records.values()
                    if not r.archived and r.kind == kind and r.owner_id == owner]
            if rows:
                lines += ["", "## " + title, "", "| Eintrag | Status |", "| --- | --- |"]
                lines += ["| " + text(r.title) + " | " + text(r.data.get("status", "offen")) +
                          " |" for r in rows]
        return lines

    def index(self, doc):
        base = self.paths[doc.id]
        lines = ["# " + text(self.project.project().title) + " – Startseite", "",
                 self.card_link(base, self.project.project()), ""]
        for kind, heading in (("global", "Projektweit"), ("act", "Akte und Kapitel"),
                              ("pipeline", "Pipelines")):
            lines += ["## " + heading, ""]
            for card in self.cards.values():
                if card.kind == kind and card.id in self.visible:
                    lines += ["- " + self.card_link(base, card)]
                    if kind == "act":
                        lines += ["  - " + self.card_link(base, child)
                                  for child in self.cards.values() if child.kind == "chapter"
                                  and child.owner_id == card.id and child.id in self.visible]
        lines += ["", "## Asset-Typen", ""]
        groups = {}
        for card in self.cards.values():
            if card.kind == "asset" and card.id in self.visible:
                groups.setdefault(self.files.asset_type(card), []).append(card)
        for label, assets in sorted(groups.items()):
            lines += ["### " + text(label), ""]
            lines += ["- " + self.card_link(base, card) for card in assets]
        lines += ["", "## Dokumentation und Planung", ""]
        for record in self.records.values():
            if record.archived or record.owner_id not in self.visible or \
                    record.data.get("automation"):
                continue
            if record.kind == "document" and record.id in self.paths:
                lines += ["- " + ("Notiz: " if is_note(record) else "Dokument: ") +
                          self.link(base, self.paths[record.id], record.title)]
            elif record.kind in {"task", "issue"}:
                lines += ["- " + ("Aufgabe: " if record.kind == "task" else "Issue: ") +
                          text(record.title) + " · " + text(record.data.get("status", "offen")) +
                          " · " + self.card_link(base, self.cards[record.owner_id])]
        lines += ["", "## Ordnerstruktur", "", "```text", *self.folder_tree(), "```"]
        return "\n".join(lines)

    def folder_tree(self):
        tree = {}
        paths = {path for identifier, path in self.paths.items()
                 if self.records[identifier].owner_id in self.visible and
                 not self.records[identifier].archived}
        for card in self.cards.values():
            if card.id not in self.visible:
                continue
            directory = self.files.path(card.id)
            if card.kind in {"global", "act", "chapter", "package"}:
                paths.add(directory / ("" if card.kind == "package" else "Assets") / "index.md")
            elif card.kind == "asset":
                paths.add(directory.parent / "index.md")
                current = self.results(card.id)
                if current:
                    for artifact in current["artifacts"]:
                        paths.add(directory / artifact["image_path"])
                        paths.add((directory / artifact["image_path"]).parent / "index.md")
                        if artifact.get("preview_path"):
                            paths.add(directory / artifact["preview_path"])
                            paths.add((directory / artifact["preview_path"]).parent / "index.md")
            elif card.kind == "pipeline":
                paths.add(directory / "rezept.json")
        for path in sorted(paths):
            branch = tree
            for part in path.relative_to(self.root).parts:
                branch = branch.setdefault(part, {})

        def render(branch, prefix=""):
            result = []
            for index, (name, children) in enumerate(sorted(branch.items())):
                last = index == len(branch) - 1
                result.append(prefix + ("└── " if last else "├── ") + name +
                              ("/" if children else ""))
                result.extend(render(children, prefix + ("    " if last else "│   ")))
            return result
        return render(tree)

    def asset_section(self, card, base):
        lines = ["", "Asset-Typ: " + text(self.files.asset_type(card)), "", "## Bildausgaben", ""]
        current = self.results(card.id)
        if not current:
            return lines + ["Noch keine geprüften Pipeline-Ausgaben veröffentlicht."]
        profiles = sorted({str(Path(a["image_path"]).parent) for a in current["artifacts"]})
        profiles += sorted({str(Path(a["preview_path"]).parent) for a in current["artifacts"]
                            if a.get("preview_path")})
        lines += ["- " + self.link(base, self.files.path(card.id) / profile / "index.md",
                                  Path(profile).name) for profile in profiles]
        return lines + ["", "Letzter vollständig veröffentlichter Lauf: `" + current["run_id"] +
                        "`. Aktuelle Gültigkeit im Asset-Arbeitsbereich prüfen."]

    def results(self, owner):
        name = "Ergebnisse/aktuell.json"
        path = self.files.path(owner) / name
        expected = self.files.files.get((owner, name))
        if not expected or not path.is_file() or file_hash(path) != expected:
            return None
        result = json.loads(path.read_text(encoding="utf-8"))
        if result.get("contract") == "studio-workflow-publication-v1":
            result["artifacts"] = [
                {**item, "image_path": item["path"]} for item in result["artifacts"]
            ]
        return result

    def markdown(self, change, owner, name, body):
        body = START + "\n" + body.rstrip() + "\n" + END + "\n"
        target = safe_target(self.root, str(self.files.path(owner).relative_to(self.root) / name))
        previous = self.files.files.get((owner, name))
        if target.exists() and previous:
            external, actual = read_markdown(target)
            body = generated(external, body.split(START)[1].split(END)[0])
            # Preserve external prose, and adopt precisely the bytes just read.
            self.files.files[(owner, name)] = actual
            self.catalog.db.execute("UPDATE managed_files SET sha256=? WHERE owner_id=? AND path=?",
                                    (actual, owner, name))
        raw = body.encode("utf-8")
        self.files.file(change, owner, name, hashlib.sha256(raw).hexdigest(), content=raw)

    def asset_indexes(self, change, cards):
        for scope in cards:
            if scope.kind not in {"global", "act", "chapter", "package"}:
                continue
            directory = "" if scope.kind == "package" else "Assets/"
            groups = {}
            for card in cards:
                if card.owner_id == scope.id and card.kind in {"asset", "package"} and \
                        card.id in self.visible:
                    groups.setdefault(self.files.asset_type(card), []).append(card)
            # Keep empty former type indexes truthful after moves/type changes.
            prefix = directory
            groups.update({Path(name).parent.name: groups.get(Path(name).parent.name, [])
                           for owner, name in self.files.files if owner == scope.id and
                           name.startswith(prefix) and name.endswith("/index.md") and
                           len(Path(name[len(prefix):]).parts) == 2})
            base = self.files.path(scope.id) / directory / "index.md"
            body = "# Assets nach Typ\n\n" + self.card_link(base, scope) + "\n\n"
            for label, rows in sorted(groups.items()):
                name = directory + label + "/index.md"
                target = self.files.path(scope.id) / name
                body += "- " + self.link(base, target, label) + f" ({len(rows)})\n"
                content = "# " + text(label) + "\n\n" + self.link(
                    target, base, "Asset-Typen") + "\n\n"
                content += "\n".join("- " + self.card_link(target, row) for row in rows)
                self.markdown(change, scope.id, name, content)
            self.markdown(change, scope.id, directory + "index.md", body)
        for card in cards:
            if card.kind != "asset":
                continue
            current = self.results(card.id)
            if not current:
                continue
            groups = {}
            for artifact in current["artifacts"]:
                groups.setdefault(str(Path(artifact["image_path"]).parent), []).append(artifact)
                if artifact.get("preview_path"):
                    groups.setdefault(str(Path(artifact["preview_path"]).parent), []).append(
                        {**artifact, "image_path": artifact["preview_path"]})
            for directory, artifacts in groups.items():
                base = self.files.path(card.id) / directory / "index.md"
                body = "# " + text(Path(directory).name) + "\n\n"
                body += self.card_link(base, card) + "\n\n| Datei | Vorschau |\n| --- | --- |\n"
                for artifact in artifacts:
                    target = self.files.path(card.id) / artifact["image_path"]
                    link = self.link(base, target, target.name)
                    body += "| " + link + " | !" + link + " |\n"
                self.markdown(change, card.id, directory + "/index.md", body)
