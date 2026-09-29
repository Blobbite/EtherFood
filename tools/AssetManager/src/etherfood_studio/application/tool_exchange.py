"""Portable complete workflow bundles, including nested packages and resources."""

from dataclasses import dataclass
import hashlib
from pathlib import Path
import tempfile

from ..domain.assets import require
from ..domain.pipeline_recipes import BUILTINS, blockers, validate_recipe
from ..domain.tool_contract import is_workflow, package_manifests, resolve_local
from ..storage.blob_store import BlobStore
from ..storage.tool_archives import archive_bytes, json_bytes, read_archive, read_json
from .pipeline_service import PipelineService
from .tool_packages import ToolPackageService


@dataclass(frozen=True)
class WorkflowPreview:
    title: str
    recipe: dict
    packages: tuple
    resources: dict
    issues: tuple
    root_package: str | None = None


class ToolExchange:
    def __init__(self, project):
        self.project = project
        self.packages = ToolPackageService(project)
        self.store = BlobStore(project.catalog, project.catalog.path.parent)

    def dependencies(self, recipe):
        pending = [recipe]
        found = {}
        while pending:
            for node in pending.pop()["steps"]:
                if not node["operation"].startswith(("tool:", "flow:")):
                    continue
                digest = node["operation"].split(":")[1]
                if digest in found:
                    continue
                package = self.packages.details(digest)
                found[digest] = package
                pending.extend(flow["recipe"] for flow in package["manifest"]["flows"])
        return found

    def export(self, recipe_id, path):
        record = PipelineService(self.project).recipe(recipe_id)
        recipe = record.data["recipe"]
        require(is_workflow(recipe), "Für diesen Export zuerst den alten Ablauf umwandeln.")
        packages = self.dependencies(recipe)
        self.write(path, record.title, recipe, packages)

    def export_package(self, digest, path):
        package = self.packages.details(digest)
        packages = {digest: package}
        for flow in package["manifest"]["flows"]:
            packages.update(self.dependencies(resolve_local(flow["recipe"], digest)))
        self.write(path, package["manifest"]["name"], None, packages, root_package=digest)

    def write(self, path, title, recipe, packages, *, root_package=None):
        files = {}
        for digest, package in packages.items():
            files["packages/" + digest + ".zip"] = archive_bytes(
                {"manifest.json": json_bytes(package["manifest"]), **self.packages.contents(digest)}
            )
        resources = dict(recipe["resources"]) if recipe else {}
        for package in packages.values():
            for flow in package["manifest"]["flows"]:
                for key, value in flow["recipe"]["resources"].items():
                    require(
                        key not in resources or resources[key] == value,
                        "Ressourcenkonflikt: " + key,
                    )
                    resources[key] = value
        for value in resources.values():
            raw = self.store.path_for(value["sha256"]).read_bytes()
            require(
                hashlib.sha256(raw).hexdigest() == value["sha256"], "Ressource wurde verändert."
            )
            files["resources/" + value["sha256"]] = raw
        data = {"title": title, "packages": sorted(packages), "resources": resources}
        if root_package:
            files["toolkit.json"] = json_bytes(
                {**data, "contract": "studio-tool-bundle-v1", "root_package": root_package}
            )
        else:
            files["workflow.json"] = json_bytes(
                {**data, "contract": "studio-workflow-bundle-v1", "recipe": recipe}
            )
        with Path(path).open("xb") as stream:
            stream.write(archive_bytes(files))

    def preview(self, path):
        contents = read_archive(path)
        toolkit = "toolkit.json" in contents
        entry = "toolkit.json" if toolkit else "workflow.json"
        require(entry in contents, "Paketbeschreibung fehlt im Archiv.")
        data = read_json(contents.pop(entry))
        field = "root_package" if toolkit else "recipe"
        contract = "studio-tool-bundle-v1" if toolkit else "studio-workflow-bundle-v1"
        require(
            isinstance(data, dict)
            and set(data) == {"contract", "title", field, "packages", "resources"}
            and data["contract"] == contract,
            "Unbekannter Ablaufpaketvertrag.",
        )
        require(
            isinstance(data["title"], str)
            and 0 < len(data["title"]) <= 256
            and isinstance(data["packages"], list)
            and len(data["packages"]) <= 128
            and all(
                isinstance(value, str)
                and len(value) == 64
                and all(c in "0123456789abcdef" for c in value)
                for value in data["packages"]
            )
            and len(set(data["packages"])) == len(data["packages"])
            and isinstance(data["resources"], dict),
            "Ungültige Paketliste.",
        )
        require(
            data["root_package"] in data["packages"] if toolkit else is_workflow(data["recipe"]),
            "Paketeinstieg fehlt oder ist ungültig.",
        )
        packages, issues, manifests = [], [], dict(BUILTINS)
        for digest in data["packages"]:
            name = "packages/" + digest + ".zip"
            if name not in contents:
                issues.append("Werkzeugpaket fehlt: " + digest)
                continue
            files = read_archive(contents.pop(name))
            require("manifest.json" in files, "Manifest fehlt in Werkzeugpaket: " + digest)
            manifest = read_json(files.pop("manifest.json"))
            package = self.packages.inspect_content(manifest, files)
            require(package.digest == digest, "Paketkennung stimmt nicht mit Inhalt überein.")
            packages.append(package)
            manifests.update(package_manifests(manifest, digest))
            issues.extend(item["message"] for item in package.issues)
        resources = {}
        for name, value in data["resources"].items():
            key = "resources/" + value["sha256"]
            raw = contents.get(key)
            if raw is None:
                issues.append("Ressource fehlt: " + name)
                continue
            require(
                len(raw) == value["length"] and hashlib.sha256(raw).hexdigest() == value["sha256"],
                "Ressource passt nicht zum Manifest: " + name,
            )
            resources[value["sha256"]] = raw
        extra = set(contents) - {"resources/" + value for value in resources}
        require(not extra, "Nicht deklarierte Dateien im Ablaufpaket.")
        for package in packages:
            for flow in package.manifest["flows"]:
                recipe = resolve_local(flow["recipe"], package.digest)
                validate_recipe(recipe, manifests)
                issues.extend(blockers(recipe, manifests))
        if not toolkit:
            validate_recipe(data["recipe"], manifests)
            issues.extend(blockers(data["recipe"], manifests))
        return WorkflowPreview(
            data["title"],
            data.get("recipe"),
            tuple(packages),
            resources,
            tuple(dict.fromkeys(issues)),
            data.get("root_package"),
        )

    def register(self, preview):
        service = PipelineService(self.project)
        with self.project.catalog.transaction():
            for package in preview.packages:
                self.packages.register(package)
            with tempfile.TemporaryDirectory(prefix="studio-workflow-import-") as directory:
                for digest, content in preview.resources.items():
                    require(
                        hashlib.sha256(content).hexdigest() == digest,
                        "Importvorschau wurde verändert.",
                    )
                    path = Path(directory) / digest
                    path.write_bytes(content)
                    self.store.import_file(path)
            if preview.root_package:
                return self.packages.details(preview.root_package)
            return self.project.create_card(
                "pipeline",
                preview.title,
                service.project_id,
                {"project_id": service.project_id, "recipe": preview.recipe},
            )
