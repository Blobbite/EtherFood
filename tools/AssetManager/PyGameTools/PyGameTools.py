#!/usr/bin/env python3
"""PyGameTools installieren: interne Pipeline-Dateien, eigene venv, sechs Pipeline-Wrapper."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import venv

SOURCE = Path(__file__).resolve().parent
COMMANDS = {
    "PyPiplineStart-SourceColor": "Pipline/SourceColor-Pipline/PyPiplineStart-SourceColor.py",
    "PyPiplineStart-SpritesheetColor":
        "Pipline/3-SpritesheetColor-Pipline/PyPiplineStart-SpritesheetColor.py",
    "PyPiplineStart-SpritesheetResolution":
        "Pipline/2-SpritesheetResolution-Pipline/PyPiplineStart-SpritesheetResolution.py",
    "PyPiplineStart-SpritesheetFram16":
        "Pipline/0-SpritesheetFram16-Pipline/PyPiplineStart-SpritesheetFram16.py",
    "PyPiplineStart-SpritesheetFram8":
        "Pipline/0-SpritesheetFram8-Pipline/PyPiplineStart-SpritesheetFram8.py",
    "PyPiplineStart-SpritesheetFramReduce":
        "Pipline/1-SpritesheetFramReduce-Pipline/PyPiplineStart-SpritesheetFramReduce.py",
}
LEGACY_PATHS = {
    relative.replace("Pipline/0-", "Pipline/").replace("Pipline/1-", "Pipline/")
        .replace("Pipline/2-", "Pipline/").replace("Pipline/3-", "Pipline/"): command
    for command, relative in COMMANDS.items() if "Pipline/SourceColor-" not in relative
}
LEGACY_COMMANDS = {
    "PyPiplineStart-SpritsheetAll": (
        "Pipline/SpritesheetAll-Pipline/PyPiplineStart-SpritsheetAll.py",
        "PyPiplineStart-SpritesheetResolution",
    ),
}
INTERNAL_FILES = (
    "Pipline/PiplineToos/PyImgColorPipeline.py",
    "Pipline/PiplineToos/PyImgColorMatch.py",
    "Pipline/PiplineToos/PyImgFixedColors.py",
    "Pipline/PiplineToos/PyImgGif.py",
    "Pipline/PiplineToos/PyImgGrid.py",
    "Pipline/PiplineToos/PySpritesheetPipeline.py",
    "Pipline/PiplineToos/PyImgFrameSelect.py",
    "Pipline/PiplineToos/PyPipelineOutputs.py",
    *(f"Pipline/2-SpritesheetResolution-Pipline/{name}.py" for name in
      ("SComicMid", "SComicLow", "SPixelHigh", "SPixelLow", "PyGraphicsCompare", "PyGraphicsPoseCompare")),
)
FILES = (*COMMANDS.values(), *INTERNAL_FILES)
MARKER = ".pygametools.json"
IDENTITY = {"tool": "PyGameTools", "format": 1}


def atomic_write(path: Path, content: str, mode: int = 0o644):
    fd, temporary = tempfile.mkstemp(prefix=".pygametools-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def managed_install(path: Path) -> bool:
    marker = path / MARKER
    if marker.is_symlink():
        return False
    try:
        return json.loads(marker.read_text(encoding="utf-8")) == IDENTITY
    except (OSError, ValueError):
        return False


def validate_install_dir(path: Path):
    if path == SOURCE or SOURCE.is_relative_to(path) or path == Path.home():
        raise ValueError(f"Ein eigenes Installationsverzeichnis verwenden: {path}")
    if path.exists() and not path.is_dir():
        raise ValueError(f"Installationsziel ist kein Ordner: {path}")
    if path.exists() and any(path.iterdir()) and not managed_install(path):
        raise ValueError(f"Ordner gehört nicht zu PyGameTools: {path}")
    for name in ("app", "venv", MARKER):
        if (path / name).is_symlink():
            raise ValueError(f"Installationsbestandteil ist ein Link: {path / name}")


def wrapper_content(install_dir: Path, relative: str) -> str:
    return (f"#!/bin/sh\n# PyGameTools wrapper: {install_dir}\n"
            f"exec {shlex.quote(str(install_dir / 'venv/bin/python'))} "
            f"{shlex.quote(str(install_dir / 'app' / relative))} \"$@\"\n")


def owned_wrapper(path: Path, install_dir: Path) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    with path.open(encoding="utf-8", errors="replace") as stream:
        return (stream.readline() == "#!/bin/sh\n"
                and stream.readline() == f"# PyGameTools wrapper: {install_dir}\n")


def legacy_entrypoint(relative: str) -> str:
    """Alte installierte Wrapper bis zur Umstellung auf den neuen Namen erhalten."""
    return ("#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "import runpy\n"
            "import sys\n"
            f"target = Path(__file__).resolve().parents[2] / {relative!r}\n"
            "sys.path.insert(0, str(target.parent))\n"
            "runpy.run_path(str(target), run_name='__main__')\n")


def validate_wrappers(bin_dir: Path, install_dir: Path):
    if bin_dir.exists() and not bin_dir.is_dir():
        raise ValueError(f"Wrapperziel ist kein Ordner: {bin_dir}")
    if bin_dir == install_dir or bin_dir.is_relative_to(install_dir):
        raise ValueError("Wrapperordner muss außerhalb des Installationsverzeichnisses liegen.")
    for name in COMMANDS:
        path = bin_dir / name
        if (path.exists() or path.is_symlink()) and not owned_wrapper(path, install_dir):
            raise ValueError(f"Vorhandener fremder Befehl wird nicht ersetzt: {path}")


def prepare(install_dir: Path):
    validate_install_dir(install_dir)
    for relative in (*FILES, "requirements.txt"):
        if not (SOURCE / relative).is_file():
            raise ValueError(f"Installationsquelle fehlt: {SOURCE / relative}")
    install_dir.mkdir(parents=True, exist_ok=True)
    atomic_write(install_dir / MARKER, json.dumps(IDENTITY) + "\n")
    python = install_dir / "venv/bin/python"
    if not python.is_file():
        print("Eigene Python-Umgebung erstellen …", flush=True)
        venv.EnvBuilder(with_pip=True).create(install_dir / "venv")
    subprocess.run([str(python), "-m", "pip", "install", "-r", str(SOURCE / "requirements.txt")], check=True)
    subprocess.run([str(python), "-c", "from PIL import Image; print('Pillow bereit:', Image.__version__)"], check=True)
    # Erst eine vollständige Kopie erstellen, dann den bisherigen Programmbaum ersetzen.
    with tempfile.TemporaryDirectory(prefix=".pygametools-stage-", dir=install_dir) as temporary:
        stage = Path(temporary)
        app = stage / "app"
        for relative in FILES:
            destination = app / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE / relative, destination)
        current = install_dir / "app"
        # --update hat möglicherweise keine Schreibrechte auf /usr/local/bin.
        # Bisherige Wrapper können deshalb zunächst ihren alten Skriptpfad behalten.
        compatibility = [*LEGACY_COMMANDS.values(), *LEGACY_PATHS.items()]
        for old_relative, replacement in compatibility:
            if (current / old_relative).is_file():
                destination = app / old_relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(legacy_entrypoint(COMMANDS[replacement]), encoding="utf-8")
        backup = stage / "previous"
        if current.exists():
            current.rename(backup)
        try:
            app.rename(current)
        except OSError:
            if backup.exists():
                backup.rename(current)
            raise
    print(f"Pipeline-Dateien und Python-Umgebung bereit: {install_dir}", flush=True)


def install_wrappers(install_dir: Path, bin_dir: Path):
    validate_install_dir(install_dir)
    if not managed_install(install_dir):
        raise ValueError("Zuerst PyGameTools.py --prepare als normaler Benutzer ausführen.")
    for relative in FILES:
        if not (install_dir / "app" / relative).is_file():
            raise ValueError(f"Installation unvollständig: {relative}; zuerst --prepare ausführen.")
    if not os.access(install_dir / "venv/bin/python", os.X_OK):
        raise ValueError("Python-Umgebung fehlt; zuerst --prepare ausführen.")
    validate_wrappers(bin_dir, install_dir)
    bin_dir.mkdir(parents=True, exist_ok=True)
    for name, relative in COMMANDS.items():
        atomic_write(bin_dir / name, wrapper_content(install_dir, relative), 0o755)
        print(f"Wrapper: {bin_dir / name}")
    for old_name, (_, replacement) in LEGACY_COMMANDS.items():
        old_wrapper = bin_dir / old_name
        if owned_wrapper(old_wrapper, install_dir):
            old_wrapper.unlink()
            print(f"Befehl umbenannt: {old_name} → {replacement}")
    if str(bin_dir) not in os.environ.get("PATH", "").split(os.pathsep):
        print(f"Diesen Ordner in PATH aufnehmen: {bin_dir}")


def uninstall(install_dir: Path, bin_dir: Path):
    validate_install_dir(install_dir)
    if not managed_install(install_dir):
        raise ValueError(f"Keine von PyGameTools verwaltete Installation: {install_dir}")
    validate_wrappers(bin_dir, install_dir)
    for name in (*COMMANDS, *LEGACY_COMMANDS):
        wrapper = bin_dir / name
        if owned_wrapper(wrapper, install_dir):
            wrapper.unlink()
            print(f"Wrapper entfernt: {wrapper}")
    for name in ("app", "venv"):
        path = install_dir / name
        if path.exists():
            shutil.rmtree(path)
    (install_dir / MARKER).unlink()
    if not any(install_dir.iterdir()):
        install_dir.rmdir()
    print("PyGameTools deinstalliert.")


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--install", action="store_true", help="Vorbereiten und Benutzer-Wrapper installieren")
    mode.add_argument("--prepare", action="store_true", help="Nur Programme und venv als normaler Benutzer vorbereiten")
    mode.add_argument("--apply-system", action="store_true", help="Nur Wrapper installieren; Standard /usr/local/bin")
    mode.add_argument("--update", action="store_true", help="Installierte Pipeline-Dateien und Abhängigkeiten aktualisieren")
    mode.add_argument("--uninstall", action="store_true", help="Eigene Wrapper und Installation entfernen")
    parser.add_argument("--install-dir", type=Path, default=Path.home() / ".local/share/PyGameTools",
                        help="Programm-/venv-Ordner; Standard ~/.local/share/PyGameTools")
    location = parser.add_mutually_exclusive_group()
    location.add_argument("--user-bin", action="store_true", help="Wrapper nach ~/.local/bin (Standard bei --install)")
    location.add_argument("--system-bin", action="store_true", help="Wrapper nach /usr/local/bin")
    location.add_argument("--bin-dir", type=Path, help="Eigener Wrapperordner")
    parser.add_argument("--dry-run", action="store_true", help="Pfade und Schritte anzeigen; nichts installieren")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not any((args.install, args.prepare, args.apply_system, args.update, args.uninstall)):
        parser.print_help()
        return 0
    install_dir = args.install_dir.expanduser().absolute()
    if install_dir.is_symlink():
        parser.error("Installationsverzeichnis darf kein symbolischer Link sein.")
    install_dir = install_dir.resolve()
    system_bin = args.system_bin or (args.apply_system and not args.user_bin and not args.bin_dir)
    bin_dir = (args.bin_dir or (Path("/usr/local/bin") if system_bin else Path.home() / ".local/bin"))
    bin_dir = bin_dir.expanduser().resolve()
    try:
        validate_install_dir(install_dir)
        if args.install or args.apply_system or args.uninstall:
            validate_wrappers(bin_dir, install_dir)
        print(f"Installation: {install_dir}\nWrapperordner: {bin_dir}", flush=True)
        if args.dry_run:
            if args.install or args.prepare or args.update:
                print(f"Plan: {len(FILES)} Pipeline-Dateien kopieren, eigene venv und Pillow vorbereiten.")
            if args.install or args.apply_system or args.uninstall:
                print("Plan: " + ("entfernen: " if args.uninstall else "Wrapper erstellen: ") + ", ".join(COMMANDS))
                for old_name, (_, replacement) in LEGACY_COMMANDS.items():
                    if owned_wrapper(bin_dir / old_name, install_dir):
                        print(f"Plan: alten eigenen Wrapper {old_name} "
                              + ("entfernen." if args.uninstall else f"durch {replacement} ersetzen."))
            if args.uninstall:
                print("Plan: eigene app/ und venv/ entfernen.")
            return 0
        if (args.install or args.prepare or args.update) and os.geteuid() == 0:
            raise ValueError("Vorbereitung und pip als normaler Benutzer ausführen. "
                             "sudo ist nur für --apply-system bzw. --uninstall vorgesehen.")
        if args.install and system_bin:
            raise ValueError("Systemweite Installation in zwei Schritten: --prepare, dann "
                             "sudo python3 PyGameTools.py --apply-system --install-dir " + shlex.quote(str(install_dir)))
        if args.update and not managed_install(install_dir):
            raise ValueError("Noch keine Installation vorhanden; zuerst --install oder --prepare ausführen.")
        if args.install or args.prepare or args.update:
            prepare(install_dir)
        if args.update:
            print("Für neue Befehlsnamen die Wrapper ebenfalls aktualisieren: "
                  "--apply-system (Systeminstallation) oder --install --user-bin (Benutzerinstallation).")
        if args.install or args.apply_system:
            install_wrappers(install_dir, bin_dir)
        if args.uninstall:
            uninstall(install_dir, bin_dir)
        return 0
    except KeyboardInterrupt:
        print("\nAbgebrochen.", file=sys.stderr)
        return 130
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
