#!/usr/bin/env python3
"""Python-Werkzeuge im eigenen Ordner auswählen und starten (Standardbibliothek)."""
from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import tokenize
import unicodedata

AREA = 'PyImageAnimi'
HELP_FILE = 'PyImageAnimiHelp.py'
SELF = Path(__file__).resolve()


def tree(path):
    with tokenize.open(path) as source:
        return ast.parse(source.read())


def descriptions(folder):
    """Nur literale Hilfedaten lesen, niemals Werkzeugcode importieren."""
    result = {}
    try:
        for node in tree(folder / HELP_FILE).body:
            if isinstance(node, ast.Assign):
                if any(isinstance(t, ast.Name) and t.id == 'SCRIPT_DESCRIPTIONS'
                       for t in node.targets):
                    result.update(ast.literal_eval(node.value))
                if any(isinstance(t, ast.Name) and t.id == 'SCRIPT_CATALOG'
                       for t in node.targets) and isinstance(node.value, ast.Dict):
                    for key, value in zip(node.value.keys, node.value.values):
                        if isinstance(value, ast.Call):
                            for kw in value.keywords:
                                if kw.arg == 'description':
                                    result.setdefault(ast.literal_eval(key), ast.literal_eval(kw.value))
    except (OSError, SyntaxError, ValueError, TypeError, UnicodeError):
        pass
    return result


def discover(folder):
    known = descriptions(folder)
    entries = []
    for path in sorted(folder.iterdir(), key=lambda p: (p.name.casefold(), p.name)):
        if path.suffix != '.py' or not path.is_file():
            continue
        description = known.get(path.name)
        if path.resolve() == SELF:
            description = 'dieses Menü; Auswahl aktualisieren'
        elif not description:
            try:
                doc = ast.get_docstring(tree(path)) or ''
                description = next((line.strip() for line in doc.splitlines() if line.strip()), '')
            except (OSError, SyntaxError, UnicodeError):
                description = ''
        entries.append((path, description or 'Python-Skript starten; keine Kurzbeschreibung vorhanden'))
    return entries


def cell_width(char):
    return 0 if unicodedata.combining(char) else (2 if unicodedata.east_asian_width(char) in 'WF' else 1)


def fit(text, width):
    text = ' '.join(''.join(c if c.isprintable() else ' ' for c in text).split())
    if sum(map(cell_width, text)) <= width:
        return text
    out, used = '', 0
    for char in text:
        size = cell_width(char)
        if used + size > max(0, width - 1):
            break
        out += char
        used += size
    return out + ('…' if width else '')


def line(entry, prefix=''):
    path, description = entry
    width = max(1, shutil.get_terminal_size((100, 24)).columns - 1)
    return fit(f'{prefix}{path.stem} --> für {description}', width)


@contextmanager
def keyboard():
    """Terminalmodus auch bei Fehlern und Ctrl-C zuverlässig zurücksetzen."""
    if os.name == 'nt':
        import ctypes
        import msvcrt
        kernel = ctypes.windll.kernel32
        handle = kernel.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if not kernel.GetConsoleMode(handle, ctypes.byref(mode)):
            raise OSError('Kein Windows-Konsolenterminal')
        if not kernel.SetConsoleMode(handle, mode.value | 4):
            raise OSError('Terminal unterstützt keine ANSI-Ausgabe')
        def read():
            char = msvcrt.getwch()
            if char in ('\x00', '\xe0'):
                return {'H': 'up', 'P': 'down'}.get(msvcrt.getwch(), '')
            if char == '\x03':
                raise KeyboardInterrupt
            return char
        try:
            yield read
        finally:
            kernel.SetConsoleMode(handle, mode.value)
    else:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        def read():
            char = os.read(fd, 1).decode('ascii', 'ignore')
            if char != '\x1b':
                return char
            sequence = b''
            while select.select([fd], [], [], 0.08)[0]:
                sequence += os.read(fd, 1)
                if len(sequence) >= 2:
                    break
            return {b'[A': 'up', b'OA': 'up', b'[B': 'down', b'OB': 'down'}.get(sequence, '\x1b' if not sequence else '')
        try:
            tty.setcbreak(fd)
            yield read
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def arrow_choice(entries, index):
    with keyboard() as read:
        try:
            print('\x1b[?25l', end='', flush=True)
            while True:
                rows = max(1, shutil.get_terminal_size((100, 24)).lines - 4)
                start = max(0, min(index - rows + 1, len(entries) - rows))
                width = max(1, shutil.get_terminal_size((100, 24)).columns - 1)
                print('\x1b[H\x1b[2J' + fit(AREA + ' | Hoch/Runter, Enter, Q/Escape', width))
                for i in range(start, min(len(entries), start + rows)):
                    print(line(entries[i], '> ' if i == index else '  '))
                print(fit(f'{index + 1}/{len(entries)} | --plain: Nummernauswahl', width), flush=True)
                key = read()
                if key in ('q', 'Q', '\x1b', '\x04'):
                    return None
                if key in ('\r', '\n'):
                    return index
                if key == 'up':
                    index = (index - 1) % len(entries)
                if key == 'down':
                    index = (index + 1) % len(entries)
        finally:
            print('\x1b[?25h', end='', flush=True)


def plain_choice(entries):
    for i, entry in enumerate(entries, 1):
        print(line(entry, f'{i}. '))
    while True:
        try:
            answer = input('Nummer + Enter | Q/Escape: ').strip()
        except EOFError:
            return None
        if answer.lower() == 'q' or answer == '\x1b':
            return None
        if answer.isdecimal() and 1 <= int(answer) <= len(entries):
            return int(answer) - 1
        print('Bitte eine gültige Nummer eingeben.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=f'{AREA}: Python-Skripte auswählen.',
        epilog='Hoch/Runter: Auswahl; Enter: Start; Q/Escape: Ende. Nach dem Lauf Enter drücken. '
               'Ohne interaktive Eingabe wird nur die Liste angezeigt. Arbeitsordner bleibt erhalten.')
    parser.add_argument('--plain', action='store_true', help='Nummernauswahl erzwingen')
    parser.add_argument('--list', action='store_true', help='Nur Skriptliste anzeigen')
    parser.add_argument('--dir', type=Path, default=SELF.parent, metavar='ORDNER', help='Anderer Skriptordner')
    args = parser.parse_args(argv)
    folder = args.dir.resolve()
    plain = args.plain or not sys.stdout.isatty() or (os.name != 'nt' and os.environ.get('TERM') in ('dumb', ''))
    index = 0
    while True:
        try:
            entries = discover(folder)
        except OSError as exc:
            print(f'Skriptordner kann nicht gelesen werden: {exc}', file=sys.stderr)
            return 1
        if not entries:
            print('Keine Python-Skripte gefunden.')
            return 0
        if args.list or (not sys.stdin.isatty() and not args.plain):
            for entry in entries:
                print(line(entry))
            return 0
        if plain:
            choice = plain_choice(entries)
        else:
            try:
                choice = arrow_choice(entries, min(index, len(entries) - 1))
            except (OSError, ImportError) as exc:
                print(f'Nummernauswahl wird verwendet: {exc}')
                plain = True
                continue
        if choice is None:
            return 0
        index = choice
        path = entries[choice][0]
        if path.resolve() == SELF:
            continue
        print(f'\nStarte {path.name}', flush=True)
        try:
            child = subprocess.Popen([sys.executable, str(path)])
            try:
                code = child.wait()
            except KeyboardInterrupt:
                # Ctrl-C erreicht im gemeinsamen Terminal auch das Kind.
                if child.poll() is None:
                    child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
                print('\nSkript abgebrochen.')
            else:
                print('Erfolgreich beendet (Exit-Code 0).' if code == 0
                      else f'Skript mit Fehler/Abbruch beendet (Exit-Code {code}).')
        except OSError as exc:
            print(f'Skript konnte nicht gestartet werden: {exc}')
        try:
            input('Enter zurück zur aktualisierten Auswahl: ')
        except EOFError:
            return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\nMenü beendet.')
        raise SystemExit(130)
    except BrokenPipeError:
        raise SystemExit(0)
