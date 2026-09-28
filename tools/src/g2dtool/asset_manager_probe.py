"""Inspect Asset Studio inside its own interpreter without installing anything."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
import argparse
import importlib
import importlib.metadata
import importlib.util
import json
import os
import re
import sys


def environment_checks(venv: Path) -> list[dict[str, str | bool]]:
    """Check the actual interpreter, not just the presence of an executable."""

    return [
        _check(
            ".venv interpreter",
            sys.prefix != sys.base_prefix and Path(sys.prefix).resolve() == venv.resolve(),
            f"Interpreter prefix: {sys.prefix}; expected: {venv}",
        ),
        _check("Python", sys.version_info >= (3, 11), sys.version.split()[0]),
        _check("pip", importlib.util.find_spec("pip") is not None, "Required inside .venv"),
    ]


def package_checks(studio: Path, *, core: bool) -> list[dict[str, str | bool]]:
    """Compare installed packages with the existing version-pinned manifest."""

    import tomllib

    with (studio / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)["project"]
    requirements = [f'{project["name"]}=={project["version"]}', *project["dependencies"]]
    for extra in (("test",) if core else ("test", "gui")):
        requirements.extend(project["optional-dependencies"][extra])
    checks = []
    for requirement in dict.fromkeys(requirements):
        match = re.fullmatch(r"([A-Za-z0-9._-]+)==([A-Za-z0-9.+!-]+)", requirement)
        if match is None:
            raise ValueError(f"Expected an exact, reviewed package pin: {requirement}")
        name, expected = match.groups()
        try:
            observed = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            observed = "missing"
        checks.append(_check(name, observed == expected, f"{observed}; required: {expected}"))
    spec = importlib.util.find_spec("etherfood_studio")
    expected_source = studio / "src" / "etherfood_studio" / "__init__.py"
    matches = bool(
        spec and spec.origin and Path(spec.origin).resolve() == expected_source.resolve()
    )
    checks.append(_check("Studio checkout", matches, str(expected_source)))
    return checks


def runtime_checks(*, core: bool) -> list[dict[str, str | bool]]:
    """Report Python and native-library import failures separately from package pins."""

    modules = ["etherfood_studio.cli", "PIL.Image", "pytest", "jsonschema"]
    if not core:
        modules.append("PySide6.QtWidgets")
    checks = []
    for module in modules:
        try:
            importlib.import_module(module)
        except (ImportError, OSError) as exc:
            checks.append(_check(module, False, str(exc)))
        else:
            checks.append(_check(module, True, "Import succeeded"))
    return checks


def platform_checks() -> list[dict[str, str | bool]]:
    """Probe the selected Qt platform in a disposable process, without core dumps."""

    if os.name == "posix":
        import resource

        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    return [_check("Qt platform", True, app.platformName())]


def _check(name: str, ok: bool, detail: str) -> dict[str, str | bool]:
    return {"name": name, "ok": ok, "detail": detail}


def main(arguments: Sequence[str] | None = None) -> int:
    """Emit a small JSON diagnostic payload for the Control parent process."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("environment", "packages", "runtime", "platform"))
    parser.add_argument("--venv", type=Path, required=True)
    parser.add_argument("--studio", type=Path, required=True)
    parser.add_argument("--core", action="store_true")
    args = parser.parse_args(arguments)
    try:
        if args.mode == "environment":
            checks = environment_checks(args.venv)
        elif args.mode == "packages":
            checks = package_checks(args.studio, core=args.core)
        elif args.mode == "runtime":
            checks = runtime_checks(core=args.core)
        else:
            checks = platform_checks()
    except (OSError, ValueError, KeyError, ImportError) as exc:
        checks = [_check(args.mode, False, str(exc))]
    print(json.dumps(checks))
    return 0 if all(check["ok"] for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
