"""Declarative discovery and local, hash-bound consent; never import extension code here."""

from importlib.metadata import PackageNotFoundError, version
import json
import math
from pathlib import Path
import re

from ..domain.assets import CAPABILITIES, require
from ..domain.models import StudioError
from ..domain.pipeline_recipes import validate_parameters
from ..storage.blob_store import BlobStore, file_hash
from ..storage.paths import real_path
from ..storage.sqlite_repository import canonical

MAX_MANIFEST = 65536
MAX_CODE = 1024 * 1024
PLUGIN_ID = re.compile(r"python:[a-z0-9_-]{1,64}")
DIGEST = re.compile(r"[a-f0-9]{64}")


def read_manifest(raw: bytes) -> dict:
    require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_MANIFEST,
            "Manifest überschreitet 64 KiB oder ist leer.")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "Doppeltes Manifestfeld: " + key)
            result[key] = value
        return result

    def invalid(value):
        raise ValueError("Nicht endliche JSON-Zahl: " + value)

    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=invalid)
        validate_manifest(data)
    except (ValueError, TypeError, RecursionError, OverflowError) as exc:
        raise StudioError("validation", "Ungültiges JSON-Erweiterungsmanifest.", str(exc)) from exc
    return data


def validate_manifest(data: dict) -> None:
    fields = {"contract", "id", "name", "version", "description", "parameters", "inputs",
              "outputs", "capabilities", "entry_point", "dependencies"}
    require(isinstance(data, dict) and set(data) == fields and
            data["contract"] == "studio-python-step-v1", "Unbekannter Erweiterungsvertrag.")
    for key in ("id", "name", "version", "description", "entry_point"):
        require(isinstance(data[key], str) and 0 < len(data[key].strip()) <= 512 and
                "\x00" not in data[key], "Ungültiges Manifestfeld: " + key)
    require(PLUGIN_ID.fullmatch(data["id"]) is not None and
            re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]{0,127}", data["entry_point"]) is not None,
            "Erweiterung benötigt eine stabile ID und einen einfachen Funktionsnamen.")
    require(data["inputs"] == data["outputs"] == {"image": "image"},
            "Vertrag v1 unterstützt RGBA-Bilder gleicher Geometrie, keine freien Dateipfade.")
    caps = data["capabilities"]
    require(isinstance(caps, list) and len(caps) <= len(CAPABILITIES) and
            all(isinstance(v, str) and v in CAPABILITIES for v in caps) and
            len(set(caps)) == len(caps), "Unbekannte oder doppelte Erweiterungsfähigkeit.")
    require(isinstance(data["parameters"], dict) and len(data["parameters"]) <= 32,
            "Zu viele oder ungültige Parameter.")
    for key, spec in data["parameters"].items():
        require(isinstance(key, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,63}", key) is not None,
                "Ungültiger Parametername.")
        require(isinstance(spec, dict) and isinstance(spec.get("type"), str) and
                spec["type"] in {"number", "integer", "boolean", "choice", "string"} and
                "default" in spec, "Ungültige Parameterdefinition.")
        expected = {"type", "default"}
        if spec["type"] in {"integer", "number"}:
            expected |= {"minimum", "maximum"}
        elif spec["type"] == "choice":
            expected.add("choices")
        require(set(spec) == expected, "Nicht unterstützte oder fehlende Parameterfelder.")
        if spec["type"] in {"integer", "number"}:
            types = {int} if spec["type"] == "integer" else {int, float}
            require(all(type(spec[k]) in types and abs(spec[k]) <= 10 ** 12 and
                        math.isfinite(spec[k]) for k in ("minimum", "maximum")) and
                    spec["minimum"] <= spec["maximum"], "Ungültige Parametergrenzen.")
        if spec["type"] == "choice":
            values = spec["choices"]
            require(isinstance(values, list) and 1 <= len(values) <= 128 and
                    all(isinstance(v, str) and 0 < len(v) <= 512 for v in values) and
                    len(set(values)) == len(values), "Ungültige oder doppelte Auswahleinträge.")
    try:
        validate_parameters({k: v["default"] for k, v in data["parameters"].items()},
                            data["parameters"])
    except (TypeError, ValueError, OverflowError) as exc:
        raise StudioError("validation", "Ungültiger Parameter-Standardwert.", str(exc)) from exc
    deps = data["dependencies"]
    require(isinstance(deps, list) and len(deps) <= 16 and
            all(isinstance(v, str) and len(v) <= 200 and re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9_.-]*==[A-Za-z0-9][A-Za-z0-9_.+-]*", v) for v in deps),
            "Abhängigkeiten benötigen genaue Versionen, keine URLs oder Installationsbefehle.")
    names = [re.sub(r"[-_.]+", "-", value.split("==")[0]).lower() for value in deps]
    require(len(set(names)) == len(names), "Abhängigkeit mehrfach angegeben.")
    try:
        require(len(canonical(data).encode("utf-8")) <= MAX_MANIFEST, "Manifest ist zu groß.")
    except (ValueError, TypeError, RecursionError) as exc:
        raise StudioError("validation", "Manifest ist kein gültiges UTF-8-JSON.", str(exc)) from exc


def dependency_issues(manifest: dict) -> list[str]:
    """Read installed distribution metadata, never import modules or install packages."""
    validate_manifest(manifest)
    result = []
    for dependency in manifest["dependencies"]:
        name, expected = dependency.split("==")
        try:
            installed = version(name)
        except PackageNotFoundError:
            installed = None
        if installed != expected:
            result.append("Abhängigkeit fehlt/abweichend: " + dependency)
    return result


class PluginService:
    def __init__(self, project):
        self.catalog = project.catalog
        self.root = self.catalog.path.parent
        self.store = BlobStore(self.catalog, self.root)

    def manifests(self):
        result = {}
        for row in self.catalog.db.execute("SELECT identifier, manifest FROM pipeline_plugins"):
            manifest = read_manifest(row["manifest"].encode("utf-8"))
            require(manifest["id"] == row["identifier"], "Manifest-ID widerspricht Registrierung.")
            result[manifest["id"]] = manifest
        return result

    def register(self, manifest_path: Path, code_path: Path):
        manifest_path, code_path = real_path(manifest_path), real_path(code_path)
        require(manifest_path.is_file() and code_path.is_file(),
                "Manifest und Python-Code müssen reguläre Dateien sein.")
        require(manifest_path.stat().st_size <= MAX_MANIFEST and
                code_path.stat().st_size <= MAX_CODE,
                "Manifest oder Python-Datei überschreitet die Größenbegrenzung.")
        with manifest_path.open("rb") as stream:
            data = read_manifest(stream.read(MAX_MANIFEST + 1))
        require(code_path.suffix.lower() == ".py", "Explizit eine Python-Quelldatei auswählen.")
        require(code_path.stat().st_size > 0, "Python-Quelldatei ist leer.")
        before = file_hash(code_path)
        blob = self.store.import_file(code_path)
        require(blob["length"] <= MAX_CODE and blob["sha256"] == before,
                "Python-Datei wurde während der Registrierung geändert; erneut prüfen.")
        path = str(self.store.path_for(blob["sha256"]).relative_to(self.root))
        with self.catalog.transaction():
            row = self.catalog.db.execute("SELECT * FROM pipeline_plugins WHERE identifier=?",
                                          (data["id"],)).fetchone()
            if row:
                require(row["code_hash"] != blob["sha256"] or
                        row["manifest"] != canonical(data), "Diese Erweiterung ist registriert.")
                self.catalog.db.execute(
                    "UPDATE pipeline_plugins SET manifest=?, code_path=?, code_hash=?, "
                    "approved_hash=NULL WHERE identifier=?",
                    (canonical(data), path, blob["sha256"], data["id"]))
            else:
                self.catalog.db.execute("INSERT INTO pipeline_plugins VALUES (?,?,?,?,NULL)",
                    (data["id"], canonical(data), path, blob["sha256"]))
        return self.details(data["id"])

    def details(self, identifier):
        require(isinstance(identifier, str) and PLUGIN_ID.fullmatch(identifier) is not None,
                "Ungültige Erweiterungs-ID.")
        row = self.catalog.db.execute("SELECT * FROM pipeline_plugins WHERE identifier=?",
                                      (identifier,)).fetchone()
        require(row is not None, "Python-Erweiterung fehlt: " + identifier)
        values = dict(row)
        values["manifest"] = read_manifest(values["manifest"].encode("utf-8"))
        require(values["manifest"]["id"] == identifier and
                isinstance(values["code_hash"], str) and
                DIGEST.fullmatch(values["code_hash"]) is not None,
                "Beschädigte Erweiterungsregistrierung.")
        expected = str(self.store.path_for(values["code_hash"]).relative_to(self.root))
        require(values["code_path"] == expected,
                "Python-Erweiterungen dürfen nur registrierte unveränderliche Kopien verwenden.")
        return values

    def approve(self, identifier, code_hash):
        with self.catalog.transaction():
            row = self.details(identifier)
            require(row["code_hash"] == code_hash,
                    "Codeversion geändert; erneut prüfen.")
            self._verify_code(row)
            self.catalog.db.execute(
                "UPDATE pipeline_plugins SET approved_hash=? WHERE identifier=?",
                (code_hash, identifier))

    def revoke(self, identifier):
        with self.catalog.transaction():
            self.details(identifier)
            self.catalog.db.execute("UPDATE pipeline_plugins SET approved_hash=NULL "
                                    "WHERE identifier=?", (identifier,))

    def _verify_code(self, row):
        path = self.store.path_for(row["code_hash"])
        require(path.is_file() and 0 < path.stat().st_size <= MAX_CODE and
                file_hash(path) == row["code_hash"],
                "Codekopie fehlt oder wurde verändert; erneut prüfen und registrieren.")

    def trusted(self, identifier):
        row = self.details(identifier)
        require(row["approved_hash"] == row["code_hash"],
                "Python-Code ist nicht für diese Version freigegeben: " + identifier)
        self._verify_code(row)
        issues = dependency_issues(row["manifest"])
        require(not issues, "; ".join(issues))
        return row
