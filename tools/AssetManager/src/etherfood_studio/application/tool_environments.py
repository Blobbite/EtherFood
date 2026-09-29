"""Project-local Python environments; inspection never installs a dependency."""

import ast
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

from ..domain.assets import require
from ..domain.models import StudioError
from ..storage.blob_store import file_hash
from ..storage.paths import safe_target
from ..storage.sqlite_repository import canonical


class ToolEnvironments:
    def __init__(self, project):
        self.root = project.catalog.path.parent

    @staticmethod
    def identity(manifest):
        value = {
            "python": manifest["python"],
            "dependencies": sorted(manifest["dependencies"]),
            "runtime": platform.python_version(),
            "platform": sys.platform,
            "machine": platform.machine(),
        }
        return hashlib.sha256(canonical(value).encode()).hexdigest()

    def directory(self, manifest):
        return safe_target(self.root, ".asset-studio/environments/" + self.identity(manifest))

    @staticmethod
    def python(directory):
        return directory / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

    def diagnostics(self, manifest):
        if manifest["python"] != f"{sys.version_info.major}.{sys.version_info.minor}":
            return [
                {
                    "kind": "python",
                    "message": "Python "
                    + manifest["python"]
                    + " benötigt; Studio verwendet "
                    + platform.python_version()
                    + ".",
                }
            ]
        receipt = self.directory(manifest) / "studio-environment.json"
        if not receipt.is_file():
            return [
                {
                    "kind": "environment",
                    "message": "Python-Umgebung noch nicht eingerichtet. Benötigt: "
                    + (", ".join(manifest["dependencies"]) or "Python-Standardbibliothek")
                    + ".",
                }
            ]
        try:
            self.verify(manifest)
            return []
        except (
            StudioError,
            OSError,
            ValueError,
            KeyError,
            TypeError,
            subprocess.SubprocessError,
        ) as error:
            return [
                {
                    "kind": "environment",
                    "message": "Umgebung fehlt oder ist verändert: "
                    + str(error)
                    + "\nBenötigter Bibliotheksbestand: "
                    + (", ".join(manifest["dependencies"]) or "Python-Standardbibliothek"),
                }
            ]

    def receipt(self, manifest):
        directory = self.directory(manifest)
        receipt = json.loads((directory / "studio-environment.json").read_text())
        require(
            receipt["id"] == self.identity(manifest)
            and receipt["executable_hash"] == file_hash(self.python(directory)),
            "Python-Umgebung passt nicht zum Paket.",
        )
        return receipt

    def executable(self, manifest):
        self.receipt(manifest)
        return self.python(self.directory(manifest))

    def verify(self, manifest):
        receipt = self.receipt(manifest)
        actual = self.installed(self.python(self.directory(manifest)))
        require(
            actual == receipt["installed"], "Bibliotheken wurden außerhalb des Studios geändert."
        )
        return receipt

    def import_diagnostics(self, manifest, files):
        """Check module availability without importing the package or executing its code."""
        if not (self.directory(manifest) / "studio-environment.json").is_file():
            return []
        local = {
            part
            for name in manifest["files"]
            for part in (name.split("/")[0].removesuffix(".py"), Path(name).stem)
        }
        imports = {}
        for name, raw in files.items():
            if not name.endswith(".py"):
                continue
            try:
                tree = ast.parse(raw)
                parents = {
                    child: parent
                    for parent in ast.walk(tree)
                    for child in ast.iter_child_nodes(parent)
                }
                for node in ast.walk(tree):
                    names = (
                        [alias.name for alias in node.names]
                        if isinstance(node, ast.Import)
                        else (
                            [node.module]
                            if isinstance(node, ast.ImportFrom) and not node.level and node.module
                            else []
                        )
                    )
                    for module in names:
                        root = module.split(".")[0]
                        if root not in local | sys.stdlib_module_names | {"etherfood_studio"}:
                            parent, conditional = node, False
                            while parent in parents:
                                parent = parents[parent]
                                conditional |= isinstance(
                                    parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.If, ast.Try)
                                )
                            if root not in imports or not conditional:
                                imports[root] = (name, node.lineno, conditional)
            except (SyntaxError, UnicodeError, ValueError):
                continue
        if not imports:
            return []
        code = "import json,pkgutil; print(json.dumps([m.name for m in pkgutil.iter_modules()]))"
        result = subprocess.run(
            [str(self.executable(manifest)), "-I", "-B", "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        available = set(json.loads(result.stdout))
        return [
            {
                "kind": "import",
                "path": imports[name][0],
                "line": imports[name][1],
                "conditional": imports[name][2],
                "message": "Python-Modul fehlt in dieser Umgebung: "
                + name
                + (" (bedingter Import; benötigt bei Aufruf)." if imports[name][2] else ".")
                + " Hilfsdatei ergänzen oder Bibliothek im Manifest festlegen.",
            }
            for name in sorted(imports.keys() - available)
        ]

    @staticmethod
    def installed(python):
        code = (
            "import importlib.metadata as m,json; "
            "print(json.dumps(sorted((d.metadata['Name'].lower(),d.version) "
            "for d in m.distributions())))"
        )
        result = subprocess.run(
            [str(python), "-I", "-B", "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        return json.loads(result.stdout)

    def prepare(self, manifest, *, on_output=lambda text: None):
        require(
            manifest["python"] == f"{sys.version_info.major}.{sys.version_info.minor}",
            "Dieses Paket benötigt einen anderen Python-Interpreter.",
        )
        directory = self.directory(manifest)
        directory.parent.mkdir(parents=True, exist_ok=True)
        lock = directory.with_suffix(".lock")
        try:
            lock.mkdir()
        except FileExistsError as error:
            raise StudioError("conflict", "Diese Umgebung wird bereits eingerichtet.") from error
        temporary = Path(tempfile.mkdtemp(prefix="prepare-", dir=directory.parent))
        try:
            # Venv launchers contain absolute paths. Build at the final location under a lock.
            if directory.exists():
                try:
                    return self.verify(manifest)
                except (
                    StudioError,
                    OSError,
                    ValueError,
                    KeyError,
                    TypeError,
                    subprocess.SubprocessError,
                ):
                    on_output("Unvollständige oder veränderte Umgebung wird neu eingerichtet.")
                    shutil.rmtree(directory)
            directory.mkdir()
            on_output("Isolierte Python-Umgebung wird erstellt …")
            self.command([sys.executable, "-I", "-m", "venv", str(directory)], on_output)
            python = self.python(directory)
            report = temporary / "install.json"
            if manifest["dependencies"]:
                on_output("Bibliotheken: " + ", ".join(manifest["dependencies"]))
                self.command(
                    [
                        str(python),
                        "-I",
                        "-m",
                        "pip",
                        "--isolated",
                        "install",
                        "--disable-pip-version-check",
                        "--only-binary=:all:",
                        "--report",
                        str(report),
                        *manifest["dependencies"],
                    ],
                    on_output,
                )
            resolved = json.loads(report.read_text()) if report.exists() else {"install": []}
            lock_lines = []
            for item in resolved["install"]:
                meta = item["metadata"]
                info = item["download_info"]["archive_info"]
                hashes = info.get("hashes", {})
                if not hashes and info.get("hash", "").startswith("sha256="):
                    hashes = {"sha256": info["hash"].split("=", 1)[1]}
                require("sha256" in hashes, "Bibliotheksdownload hat keinen SHA-256-Nachweis.")
                lock_lines.append(
                    f"{meta['name']}=={meta['version']} --hash=sha256:{hashes['sha256']}"
                )
            (directory / "requirements.lock").write_text("\n".join(sorted(lock_lines)) + "\n")
            receipt = {
                "id": self.identity(manifest),
                "installed": self.installed(python),
                "executable_hash": file_hash(python),
                "requirements": lock_lines,
            }
            (directory / "studio-environment.json").write_text(canonical(receipt) + "\n")
            return receipt
        except BaseException:
            shutil.rmtree(directory, ignore_errors=True)
            raise
        finally:
            shutil.rmtree(temporary, ignore_errors=True)
            lock.rmdir()

    @staticmethod
    def command(argv, on_output):
        result = subprocess.run(argv, capture_output=True, text=True, timeout=600)
        on_output(result.stdout + result.stderr)
        require(result.returncode == 0, "Einrichtung fehlgeschlagen: " + result.stderr[-5000:])
