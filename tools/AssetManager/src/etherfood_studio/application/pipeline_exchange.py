"""Bounded declarative recipe exchange; no extraction or imported code execution."""

from copy import deepcopy
from dataclasses import dataclass
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import tempfile
import unicodedata
import zipfile
import zlib

from PIL import Image

from ..domain.assets import require
from ..domain.graphics import validate_profiles
from ..domain.models import StudioError, new_id
from ..domain.pipeline_recipes import BUILTINS, blockers, step, template, validate_recipe
from ..storage.blob_store import BlobStore, file_hash
from ..storage.paths import real_path
from ..storage.sqlite_repository import canonical
from .pipeline_service import PipelineService
from .plugin_service import PluginService
from .profile_service import ProfileService

MAX_RECIPE = 2 * 1024 * 1024
MAX_RESOURCE = 32 * 1024 * 1024
MAX_PACKAGE = 128 * 1024 * 1024
EXPORT_CONTRACT = "studio-pipeline-export-v1"
DIGEST = re.compile(r"[a-f0-9]{64}")
NODE_ID = re.compile(r"[a-zA-Z0-9_-]{1,80}")
RESOURCE_FORMATS = {"pyimg-reference-colors", "pyimg-fixed-palette", "pyimg-material-colors"}
SECRET_FIELDS = {"password", "credentials", "access_token", "refresh_token", "api_key",
                 "authorization", "approved_hash", "code_path", "private_key"}
ALIASES = {
    "SpritesheetFram8-Pipline": ("0-SpritesheetFram8-Pipline", "prepare8"),
    "SpritesheetFram16-Pipline": ("0-SpritesheetFram16-Pipline", "prepare16"),
    "SpritesheetFramReduce-Pipline": ("1-SpritesheetFramReduce-Pipline", "frames"),
    "SpritesheetResolution-Pipline": ("2-SpritesheetResolution-Pipline", "graphics"),
    "SpritesheetColor-Pipline": ("3-SpritesheetColor-Pipline", "color"),
    "SourceColor-Pipline": ("SourceColor-Pipline", "source_color"),
}


def read_json(raw):
    require(isinstance(raw, (str, bytes)), "JSON benötigt Text oder Bytes.")
    try:
        encoded = raw.encode("utf-8") if isinstance(raw, str) else raw
        require(0 < len(encoded) <= MAX_RECIPE, "JSON-Rezept überschreitet 2 MiB oder ist leer.")

        def invalid(value):
            raise ValueError("Nicht endliche JSON-Zahl: " + value)

        def unique(pairs):
            result = {}
            for key, value in pairs:
                require(key not in result, "Doppelter JSON-Schlüssel: " + key)
                result[key] = value
            return result

        data = json.loads(encoded.decode("utf-8"), parse_constant=invalid, object_pairs_hook=unique)
        pending = [(data, 0)]
        while pending:
            value, depth = pending.pop()
            require(depth <= 48, "JSON ist zu tief verschachtelt.")
            if isinstance(value, float):
                require(math.isfinite(value), "JSON enthält eine nicht endliche Zahl.")
            if isinstance(value, dict):
                pending.extend((v, depth + 1) for v in value.values())
            elif isinstance(value, list):
                pending.extend((v, depth + 1) for v in value)
        return data
    except (ValueError, TypeError, RecursionError, OverflowError) as exc:
        raise StudioError("validation", "Ungültiges JSON-Rezept.", str(exc)) from exc


def portable(value):
    if isinstance(value, str):
        text = value.strip()
        require("\x00" not in text and not text.startswith(("/", "\\", "file:", "~")) and
                re.match(r"^[A-Za-z]:", text) is None,
                "Private absolute Pfade dürfen nicht Teil eines Rezepts sein.")
    elif isinstance(value, dict):
        for key, item in value.items():
            require(isinstance(key, str) and key.casefold() not in SECRET_FIELDS,
                    "Zugangsdaten und lokale Freigaben dürfen nicht exportiert werden.")
            portable(key)
            portable(item)
    elif isinstance(value, list):
        for item in value:
            portable(item)


def _read_file(path, limit):
    path = real_path(path)
    require(path.is_file() and 0 < path.stat().st_size <= limit,
            "Importdatei fehlt, ist leer oder überschreitet die Größenbegrenzung.")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    require(len(raw) <= limit, "Datei wurde vergrößert und überschreitet die Größenbegrenzung.")
    return raw


def _resource_bytes(resource, raw, *, export=False):
    require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_RESOURCE,
            "Ressource überschreitet 32 MiB oder ist leer.")
    suffix = PurePosixPath(resource["name"]).suffix.lower()
    require(suffix in {".png", ".json"},
            "Nur deklarative JSON-/PNG-Ressourcen; Python-Code gesondert registrieren.")
    if suffix == ".json":
        data = read_json(raw)
        require(isinstance(data, dict), "Deklarative Ressource muss ein JSON-Objekt sein.")
        require("format" not in data or isinstance(data["format"], str),
                "Ungültige Ressourcenformat-Kennung.")
        require(data.get("contract") != "studio-python-step-v1",
                "Python-Manifeste gehören in die gesonderte Erweiterungsverwaltung.")
        # Only these legacy provenance fields are descriptive, not processing inputs.
        changed = False
        if export and data.get("format") in RESOURCE_FORMATS:
            references = data.get("references", [])
            derivation = data.get("derivation", {})
            require(isinstance(references, list) and isinstance(derivation, dict),
                    "Ungültige Farbprofil-Herkunftsdaten.")
            masks = derivation.get("reference_masks", [])
            require(isinstance(masks, list), "Ungültige Masken-Herkunftsdaten.")
            for reference in references + masks:
                require(isinstance(reference, dict), "Ungültiger Herkunftseintrag.")
                if "path" in reference:
                    value = reference["path"]
                    require(isinstance(value, str) and value.strip(), "Ungültiger Herkunftspfad.")
                    name = value.replace("\\", "/").rsplit("/", 1)[-1]
                    require(name not in {"", ".", ".."}, "Ungültiger Herkunftsdateiname.")
                    changed |= name != value
                    reference["path"] = name
        portable(data)
        return canonical(data).encode("utf-8") if changed else raw
    try:
        with Image.open(BytesIO(raw)) as image:
            require(image.format == "PNG" and getattr(image, "n_frames", 1) == 1 and
                    image.width * image.height <= 32_000_000,
                    "Ressource muss ein statisches PNG mit höchstens 32 Millionen Pixeln sein.")
            # Provenance paths must not leak through PNG text chunks either.
            for value in image.info.values():
                if isinstance(value, str):
                    portable(value)
            image.verify()
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise StudioError("validation", "Ungültige PNG-Ressource.", str(exc)) from exc
    return raw


def _profile_merge(incoming, current):
    """Clone dependent profiles too; never repoint an existing local Pixel-Low profile."""
    merged = deepcopy(current)
    reserved, mapping = set(current) | set(incoming), {}
    ordered = sorted(incoming, key=lambda key: incoming[key]["parent"] is not None)
    for key in ordered:
        value = deepcopy(incoming[key])
        if value["parent"] is not None:
            value["parent"] = mapping[value["parent"]]
        destination = key
        if key in current and current[key] != value:
            while destination in reserved:
                destination = key[:48] + "_" + new_id()[:8]
        reserved.add(destination)
        mapping[key] = destination
        value["key"] = destination
        merged[destination] = value
    validate_profiles(list(merged.values()))
    return merged, mapping


def _position(data):
    require(isinstance(data, dict) and set(data) <= {"x", "y", "w", "h"},
            "Ungültige Pipeline-Layoutdaten.")
    for key, value in data.items():
        require(type(value) in {int, float} and math.isfinite(value) and abs(value) <= 1_000_000,
                "Layoutposition muss eine begrenzte, endliche Zahl sein.")
        if key in {"w", "h"}:
            require(1 <= value <= 10000, "Ungültige Kartengröße.")


def _validate_layout(layout, recipe):
    require(isinstance(layout, dict) and
            set(layout) <= {"pipeline_nodes", "pipeline_legacy"}, "Unbekannte Layoutfelder.")
    ids = {node["id"] for node in recipe["steps"]}
    positions = layout.get("pipeline_nodes", {})
    require(isinstance(positions, dict) and set(positions) <= ids,
            "Layout verweist auf unbekannte Schritte.")
    for position in positions.values():
        _position(position)
    if "pipeline_legacy" not in layout:
        return
    legacy = layout["pipeline_legacy"]
    require(isinstance(legacy, dict) and set(legacy) == {"nodes", "edges", "mappings"} and
            isinstance(legacy["nodes"], dict) and set(legacy["nodes"]) <= ids and
            isinstance(legacy["edges"], list) and len(legacy["edges"]) <= 512 and
            isinstance(legacy["mappings"], list) and len(legacy["mappings"]) <= 128,
            "Ungültige Legacy-Layoutdaten.")
    for node in legacy["nodes"].values():
        require(isinstance(node, dict) and
                set(node) <= {"type", "label", "text", "file", "color", "group"} and
                all(isinstance(v, str) and len(v) <= 16384 for v in node.values()),
                "Ungültige Legacy-Karteninformation.")
        if "group" in node:
            require(node["group"] in legacy["nodes"], "Legacy-Gruppe fehlt.")
    seen = set()
    for edge in legacy["edges"]:
        require(isinstance(edge, dict) and {"id", "from", "to"} <= set(edge) and
                set(edge) <= {"id", "from", "to", "from_side", "to_side", "label", "color"} and
                all(isinstance(v, str) and len(v) <= 512 for v in edge.values()) and
                edge["from"] in legacy["nodes"] and edge["to"] in legacy["nodes"] and
                edge["id"] not in seen, "Ungültige visuelle Legacy-Verbindung.")
        seen.add(edge["id"])
    for mapping in legacy["mappings"]:
        require(isinstance(mapping, dict) and set(mapping) ==
                {"node", "original", "resolved", "operation"} and
                all(isinstance(v, str) and len(v) <= 1024 for v in mapping.values()) and
                mapping["node"] in ids, "Ungültiges Legacy-Zuordnungsprotokoll.")
    portable(legacy)


def _remap_layout(layout, ids):
    result = deepcopy(layout)
    if "pipeline_nodes" in result:
        result["pipeline_nodes"] = {ids[key]: value
                                    for key, value in result["pipeline_nodes"].items()}
    legacy = result.get("pipeline_legacy")
    if legacy:
        legacy["nodes"] = {ids[key]: value for key, value in legacy["nodes"].items()}
        for node in legacy["nodes"].values():
            if "group" in node:
                node["group"] = ids[node["group"]]
        for edge in legacy["edges"]:
            edge.update(id=new_id(), **{"from": ids[edge["from"]], "to": ids[edge["to"]]})
        for mapping in legacy["mappings"]:
            mapping["node"] = ids[mapping["node"]]
    return result


@dataclass(frozen=True)
class PipelineImport:
    document: str
    resources: tuple[tuple[str, bytes], ...]
    warnings: tuple[str, ...]
    layout: str = "{}"


class PipelineExchange:
    def __init__(self, project):
        self.project = project
        self.pipelines = PipelineService(project)
        self.store = BlobStore(project.catalog, project.catalog.path.parent)

    def _document(self, data):
        fields = {"contract", "name", "recipe", "profiles"}
        require(isinstance(data, dict) and fields <= set(data) <= fields | {"layout"} and
                data["contract"] == EXPORT_CONTRACT and isinstance(data["name"], str) and
                0 < len(data["name"].strip()) <= 256, "Unbekannter Pipeline-Exportvertrag.")
        portable(data)
        try:
            validate_recipe(data["recipe"], self.pipelines.manifests())
            profiles = validate_profiles(data["profiles"])
            require(set(data["recipe"]["profiles"]) <= set(profiles), "Exportprofile fehlen.")
            for node in data["recipe"]["steps"]:
                require(re.fullmatch(r"[a-zA-Z0-9_:-]{1,128}", node["operation"]) is not None,
                        "Ungültige Werkzeug-ID.")
                require(len(node["parameters"]) <= 32 and
                        all(isinstance(k, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,63}", k)
                            and type(v) in {str, bool, int, float}
                            for k, v in node["parameters"].items()), "Ungültige Schrittparameter.")
            _validate_layout(data.get("layout", {}), data["recipe"])
        except (TypeError, ValueError, KeyError, OverflowError) as exc:
            raise StudioError("validation", "Ungültige Pipeline-Struktur.", str(exc)) from exc
        require(len(canonical(data).encode("utf-8")) <= MAX_RECIPE, "Export ist zu groß.")
        return profiles

    def _resources(self, recipe, resources):
        require(isinstance(resources, tuple) and len(resources) <= 128,
                "Ungültige Importressourcen.")
        available = {}
        for entry in resources:
            require(isinstance(entry, tuple) and len(entry) == 2, "Ungültige Paketressource.")
            digest, raw = entry
            require(isinstance(digest, str) and DIGEST.fullmatch(digest) is not None and
                    digest not in available and isinstance(raw, bytes) and
                    0 < len(raw) <= MAX_RESOURCE and hashlib.sha256(raw).hexdigest() == digest,
                    "Importressource ist doppelt, verändert oder zu groß.")
            available[digest] = raw
        require(sum(map(len, available.values())) <= MAX_PACKAGE, "Importpaket ist zu groß.")
        expected = {}
        for resource in recipe["resources"].values():
            digest = resource["sha256"]
            require(digest not in expected or expected[digest]["length"] == resource["length"],
                    "Gleicher Ressourcendigest mit widersprüchlicher Länge.")
            expected[digest] = resource
            require(PurePosixPath(resource["name"]).suffix.lower() in {".png", ".json"},
                    "Python-Code und nicht deklarative Ressourcen separat verwalten.")
            if digest in available:
                require(len(available[digest]) == resource["length"],
                        "Ressourcengröße stimmt nicht.")
                _resource_bytes(resource, available[digest])
        require(set(available) <= set(expected),
                "Paket enthält nicht deklarierte Ressourcen oder Code.")
        return expected, available

    def export(self, identifier, path: Path, *, package=False):
        record = self.pipelines.recipe(identifier)
        recipe = deepcopy(record.data["recipe"])
        resources = {}
        for resource in recipe["resources"].values():
            source = self.store.path_for(resource["sha256"])
            raw = _read_file(source, MAX_RESOURCE)
            require(len(raw) == resource["length"] and
                    hashlib.sha256(raw).hexdigest() == resource["sha256"],
                    "Ressource fehlt oder ist beschädigt.")
            raw = _resource_bytes(resource, raw, export=True)
            digest = hashlib.sha256(raw).hexdigest()
            resource.update(sha256=digest, length=len(raw))
            resources[digest] = raw
        data = {"contract": EXPORT_CONTRACT, "name": record.title, "recipe": recipe,
                "profiles": list(ProfileService(self.project).profiles().values())}
        layout = self.project.catalog.layout(record.id)
        layout = {k: deepcopy(v) for k, v in layout.items()
                  if k in {"pipeline_nodes", "pipeline_legacy"}}
        if layout:
            data["layout"] = layout
        self._document(data)
        payload = canonical(data).encode("utf-8")
        require(sum(map(len, resources.values())) + len(payload) <= MAX_PACKAGE,
                "Export ist zu groß.")
        path = real_path(path, must_exist=False)
        require(path.parent.is_dir() and not path.exists(),
                "Exportziel existiert oder Ordner fehlt; anderen Namen wählen.")
        # Exclusive creation prevents an existing foreign file from being overwritten.
        if package:
            with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("recipe.json", payload)
                for digest, raw in sorted(resources.items()):
                    archive.writestr("resources/" + digest + ".dat", raw)
        else:
            with path.open("xb") as stream:
                stream.write(payload)

    def _archive(self, path):
        resources, document = {}, None
        try:
            # Bound the central directory before ZipFile allocates an entry for every record.
            with path.open("rb") as stream:
                stream.seek(max(0, path.stat().st_size - 65557))
                tail = stream.read(65557)
            position = tail.rfind(b"PK\x05\x06")
            require(position >= 0 and len(tail) - position >= 22,
                    "ZIP-Endverzeichnis fehlt oder ist beschädigt.")
            end = struct.unpack("<4s4H2IH", tail[position:position + 22])
            require(end[1] == end[2] == 0 and end[3] == end[4] <= 129 and
                    end[5] <= MAX_RECIPE and len(tail) - position == 22 + end[7],
                    "Zu viele Paketeinträge oder nicht unterstütztes ZIP-/Mehrteilformat.")
            with zipfile.ZipFile(path) as archive:
                entries = archive.infolist()
                require(len(entries) <= 129 and
                        len({v.filename.casefold() for v in entries}) == len(entries),
                        "Zu viele oder doppelte Paketeinträge.")
                require(sum(v.file_size for v in entries) <= MAX_PACKAGE,
                        "Entpackgröße überschreitet 128 MiB.")
                for item in entries:
                    name = PurePosixPath(item.filename)
                    mode = stat.S_IFMT(item.external_attr >> 16)
                    require(item.filename == item.orig_filename and str(name) == item.filename and
                            mode in {0, stat.S_IFREG} and not item.is_dir() and
                            item.compress_type in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED} and
                            not item.flag_bits & 1 and
                            (item.filename == "recipe.json" or re.fullmatch(
                                r"resources/[a-f0-9]{64}\.dat", item.filename) is not None),
                            "Unsicherer oder unbekannter Paketeintrag: " + item.filename)
                    limit = MAX_RECIPE if item.filename == "recipe.json" else MAX_RESOURCE
                    require(0 < item.file_size <= limit, "Paketeintrag überschreitet Größenlimit.")
                    with archive.open(item) as stream:
                        raw = stream.read(limit + 1)
                    require(len(raw) == item.file_size, "Ungültige entpackte Dateigröße.")
                    if item.filename == "recipe.json":
                        document = raw
                    else:
                        require(hashlib.sha256(raw).hexdigest() == name.stem,
                                "Paketressource hat falschen Inhaltshash.")
                        resources[name.stem] = raw
        except (zipfile.BadZipFile, zlib.error, RuntimeError, NotImplementedError, EOFError) as exc:
            raise StudioError("validation", "Ungültiges oder nicht unterstütztes Paket.",
                              str(exc)) from exc
        require(document is not None, "Rezept fehlt im Paket.")
        return read_json(document), tuple(sorted(resources.items()))

    def preview(self, path: Path) -> PipelineImport:
        path = real_path(path)
        require(path.is_file() and 0 < path.stat().st_size <= MAX_PACKAGE,
                "Importdatei fehlt, ist leer oder überschreitet 128 MiB.")
        if path.suffix.lower() == ".canvas":
            return self.legacy(read_json(_read_file(path, MAX_RECIPE)))
        if zipfile.is_zipfile(path):
            data, resources = self._archive(path)
        else:
            data, resources = read_json(_read_file(path, MAX_RECIPE)), ()
        return self._preview(data, resources)

    def _preview(self, data, resources):
        profiles = self._document(data)
        expected, available = self._resources(data["recipe"], resources)
        warnings = blockers(data["recipe"], self.pipelines.manifests())
        for digest, resource in expected.items():
            if digest in available:
                continue
            path = self.store.path_for(digest)
            if (not path.is_file() or path.stat().st_size != resource["length"] or
                    file_hash(path) != digest):
                warnings.append("Ressource fehlt/ist beschädigt: " + resource["name"])
            else:
                _resource_bytes(resource, _read_file(path, MAX_RESOURCE))
        current = ProfileService(self.project).profiles()
        _, mapping = _profile_merge(profiles, current)
        warnings += ["Profilkonflikt: " + key + " wird einschließlich Bezügen als Kopie importiert"
                     for key in profiles if key != mapping[key]]
        if not data["recipe"]["profiles"] and any(k != v for k, v in mapping.items()):
            warnings.append("Wegen Profilkonflikten werden importierte Profile ausdrücklich "
                            "gewählt; die bisherige automatische Asset-Profilauswahl entfällt.")
        if self._name_exists(data["name"]):
            warnings.append("Namenskonflikt: einen eigenen Namen für die Kopie eingeben.")
        plugins = PluginService(self.project)
        for operation in {n["operation"] for n in data["recipe"]["steps"]
                          if n["operation"].startswith("python:")}:
            warnings.append("Python-Code separat registrieren und hashgebunden freigeben: " +
                            operation)
            if operation in plugins.manifests():
                try:
                    plugins.trusted(operation)
                except StudioError as exc:
                    warnings.append(str(exc))
        return PipelineImport(canonical(data), resources, tuple(warnings),
                              canonical(data.get("layout", {})))

    def dependency_blockers(self, recipe, *, verify_content=True):
        """Reusable card/editor status checks; only active processing dependencies are required."""
        validate_recipe(recipe, self.pipelines.manifests())
        required, reasons = set(), []
        for node in recipe["steps"]:
            if not node["enabled"]:
                continue
            operation, values = node["operation"], node["parameters"]
            if operation in {"color", "source_color"}:
                roles = {"soft": ["reference"], "fixed": ["palette"],
                         "material": ["materials", "mask"]}[values["mode"]]
                required.update(values[role] for role in roles
                                if not (role == "mask" and values[role] == "@source"))
            elif operation == "graphics" and values["palette"]:
                required.add(values["palette"])
            elif operation.startswith("python:"):
                try:
                    PluginService(self.project).trusted(operation)
                except (StudioError, OSError) as exc:
                    reasons.append(str(exc))
        for key in sorted(required):
            resource = recipe["resources"].get(key)
            if resource is None:
                reasons.append("Ressource nicht konfiguriert: " + (key or "leerer Verweis"))
                continue
            try:
                path = self.store.path_for(resource["sha256"])
                require(path.is_file() and path.stat().st_size == resource["length"],
                        "Ressource fehlt oder hat eine abweichende Größe.")
                if not verify_content:
                    continue  # Canvas status must not decode/hash images during dragging.
                raw = _read_file(path, MAX_RESOURCE)
                require(len(raw) == resource["length"] and
                        hashlib.sha256(raw).hexdigest() == resource["sha256"],
                        "Ressourceninhalt wurde verändert.")
                _resource_bytes(resource, raw)
            except (StudioError, OSError) as exc:
                reasons.append("Ressource fehlt/ist ungültig: " + resource["name"] + ": " +
                               str(exc))
        return reasons

    def _name_exists(self, title):
        key = unicodedata.normalize("NFC", title.strip()).casefold()
        return any(unicodedata.normalize("NFC", r.title).casefold() == key
                   for r in self.pipelines.recipes())

    def accept(self, plan: PipelineImport, title: str):
        require(isinstance(plan, PipelineImport) and isinstance(title, str) and
                0 < len(title.strip()) <= 256, "Pipeline-Name fehlt oder ist zu lang.")
        data = read_json(plan.document)
        profiles = self._document(data)
        self._resources(data["recipe"], plan.resources)
        layout = read_json(plan.layout)
        require(layout == data.get("layout", {}), "Layout der Importvorschau wurde verändert.")
        recipe = deepcopy(data["recipe"])
        with self.project.catalog.transaction():
            require(not self._name_exists(title),
                    "Pipeline-Name ist bereits vergeben; Kopie umbenennen.")
            current = ProfileService(self.project).profiles()
            merged, mapping = _profile_merge(profiles, current)
            if recipe["profiles"]:
                recipe["profiles"] = [mapping[key] for key in recipe["profiles"]]
            elif any(k != v for k, v in mapping.items()):
                recipe["profiles"] = list(mapping.values())
            ids = {node["id"]: new_id() for node in recipe["steps"]}
            for node in recipe["steps"]:
                node["id"] = ids[node["id"]]
            for edge in recipe["connections"]:
                edge["from"], edge["to"] = ids[edge["from"]], ids[edge["to"]]
            recipe["overridable"] = [ids[token.split(".", 1)[0]] + "." + token.split(".", 1)[1]
                                     for token in recipe["overridable"]]
            layout = _remap_layout(layout, ids)
            validate_recipe(recipe, self.pipelines.manifests())
            _validate_layout(layout, recipe)
            with tempfile.TemporaryDirectory(prefix="studio-pipeline-import-") as temporary:
                for digest, raw in plan.resources:
                    path = Path(temporary) / digest
                    path.write_bytes(raw)
                    self.store.import_file(path)
            ProfileService(self.project).save(list(merged.values()),
                                             self.project.project().revision_no)
            record = self.pipelines.create(title.strip())
            record = self.pipelines.save(record.id, recipe, record.revision_no)
            if layout:
                self.project.catalog.save_layout(record.id, layout)
            return record

    def legacy(self, data):
        require(isinstance(data, dict) and isinstance(data.get("nodes"), list) and
                1 <= len(data["nodes"]) <= 127 and isinstance(data.get("edges", []), list) and
                len(data.get("edges", [])) <= 512, "Ungültiges Legacy-Canvas.")
        recipe = template("empty")
        recipe["enabled"] = False
        positions, nodes, edges, mappings, old_ids, warnings = {}, {}, [], [], {}, []
        for index, old in enumerate(data["nodes"]):
            require(isinstance(old, dict) and isinstance(old.get("id"), str) and
                    NODE_ID.fullmatch(old["id"]) is not None and old["id"] not in old_ids,
                    "Ungültige oder doppelte Legacy-Karten-ID.")
            identifier = new_id()
            old_ids[old["id"]] = identifier
            info = {key: old[key] for key in ("type", "label", "text", "file", "color", "group")
                    if key in old}
            require(all(isinstance(v, str) and len(v) <= 16384 for v in info.values()),
                    "Ungültiger Legacy-Kartentext.")
            position = {k: old.get(k, 0) for k in ("x", "y")}
            position.update({key: old[source] for key, source in (("w", "width"), ("h", "height"))
                             if source in old})
            _position(position)
            reference = info.get("file", "").replace("\\", "/")
            operation, resolved = self._legacy_tool(reference, info.get("label", ""))
            if reference:
                if reference.startswith("/") or re.match(r"^[A-Za-z]:", reference):
                    reference = reference.rsplit("/", 1)[-1]
                    resolved = resolved.rsplit("/", 1)[-1]
                    warnings.append("Privater absoluter Legacy-Dateipfad entfernt.")
                info["file"] = resolved
                mappings.append({"node": identifier, "original": reference,
                                 "resolved": resolved, "operation": operation or ""})
                warnings.append("Legacy-Dateizuordnung: " + reference + " → " + resolved)
            if operation:
                node = step(operation, BUILTINS[operation])
                warnings.append("Bekannter Schritt: " + operation +
                                " (noch ohne technischen Datenfluss)")
            else:
                node = {"operation": "unresolved:" + identifier, "enabled": False, "parameters": {}}
                recipe["legacy_unresolved"].append(
                    f"Karte {index + 1} zuordnen: " + info.get("label", "Unbekannt")[:100])
            node["id"] = identifier
            recipe["steps"].append(node)
            positions[identifier], nodes[identifier] = position, info
        for info in nodes.values():
            if "group" in info:
                require(info["group"] in old_ids, "Legacy-Gruppenkarte fehlt.")
                info["group"] = old_ids[info["group"]]
        seen = set()
        for old in data.get("edges", []):
            require(isinstance(old, dict) and isinstance(old.get("id"), str) and
                    old["id"] not in seen and isinstance(old.get("fromNode"), str) and
                    isinstance(old.get("toNode"), str) and old["fromNode"] in old_ids and
                    old["toNode"] in old_ids, "Ungültige visuelle Legacy-Verbindung.")
            seen.add(old["id"])
            edge = {"id": new_id(), "from": old_ids[old["fromNode"]],
                    "to": old_ids[old["toNode"]]}
            edge_fields = (("from_side", "fromSide"), ("to_side", "toSide"),
                           ("label", "label"), ("color", "color"))
            edge.update({key: old[source] for key, source in edge_fields if source in old})
            edges.append(edge)
        recipe["legacy_unresolved"].append("Legacy-Zuordnungen und technischen Datenfluss prüfen")
        layout = {"pipeline_nodes": positions,
                  "pipeline_legacy": {"nodes": nodes, "edges": edges, "mappings": mappings}}
        document = {"contract": EXPORT_CONTRACT, "name": "Legacy-Canvas", "recipe": recipe,
                    "profiles": list(ProfileService(self.project).profiles().values()),
                    "layout": layout}
        preview = self._preview(document, ())
        warnings.append("Visuelle Verbindungen bleiben Layoutdaten, KEIN ausführbarer Datenfluss.")
        return PipelineImport(preview.document, (), tuple(warnings) + preview.warnings,
                              preview.layout)

    @staticmethod
    def _legacy_tool(reference, label):
        require(len(reference) <= 1024 and ".." not in PurePosixPath(reference).parts,
                "Unsicherer Legacy-Dateiverweis.")
        parts = reference.split("/")
        operation = None
        for historical, (current, candidate) in ALIASES.items():
            starter = "PyPiplineStart-" + historical.removesuffix("-Pipline") + ".py"
            known = {historical + ".canvas", starter}
            if parts[-1] in known or label.strip().removeprefix("🐍").strip() in known:
                operation = candidate
            parts = [current if part == historical else part for part in parts]
        return operation, "/".join(parts)
