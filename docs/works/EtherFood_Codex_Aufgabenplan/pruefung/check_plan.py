#!/usr/bin/env python3
"""Read-only integrity and structure check for the EtherFood planning package.

This validates planning files only. It never runs application or asset tests.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


def validate(root: Path, *, structure_only: bool = False) -> dict:
    errors: list[str] = []
    model = json.loads((root / 'tasks.json').read_text(encoding='utf-8'))
    tasks = model.get('tasks', [])
    ids = [t['id'] for t in tasks]
    known = set(ids)
    if len(tasks) != 48 or len(known) != 48:
        errors.append('Expected exactly 48 unique tasks.')
    if ids != [f'T{i:03}' for i in range(1, 49)]:
        errors.append('Task IDs must be contiguous and ordered.')
    if model.get('recommended_order') != ids:
        errors.append('Recommended order differs from task order.')
    numbers = {t['id']: t['number'] for t in tasks}
    requirement_ids = {r['id'] for r in model.get('requirements', [])}
    expected_files: set[Path] = set()
    words: list[int] = []
    for t in tasks:
        rel = Path(t['path'])
        if rel.is_absolute() or '..' in rel.parts or rel.name != 'p.md':
            errors.append(f'Unsafe or invalid task path: {rel}')
            continue
        p = root / rel
        expected_files.add(p)
        if not p.is_file():
            errors.append(f'Missing task: {rel}')
            continue
        text = p.read_text(encoding='utf-8')
        words.append(len(text.split()))
        if f'task_id: {t["id"]}' not in text:
            errors.append(f'Wrong task frontmatter: {rel}')
        for heading in ('## Ziel', '## Kontext und Bestandsgrenzen',
                        '## Verbindliche Tests', '## Abnahmekriterien',
                        '## Nicht Bestandteil dieser Aufgabe', '## Abschluss und Übergabe'):
            if heading not in text:
                errors.append(f'Missing heading {heading}: {rel}')
        if len(re.findall(r'^\d+\. ', text, re.M)) < 6:
            errors.append(f'Too few implementation steps: {rel}')
        if len(re.findall(r'^- \[ \] ', text, re.M)) < 8:
            errors.append(f'Too few test/acceptance checks: {rel}')
        if len(text.split()) < 300:
            errors.append(f'Task unexpectedly short: {rel}')
        for dep in t['depends_on']:
            if dep not in known:
                errors.append(f'Unknown dependency {dep} in {t["id"]}')
            elif numbers[dep] >= t['number']:
                errors.append(f'Forward/cyclic dependency {dep} in {t["id"]}')
        if not t.get('requirements') or not set(t['requirements']) <= requirement_ids:
            errors.append(f'Invalid requirement mapping: {t["id"]}')
    if set((root / 'aufgaben').glob('*/p.md')) != expected_files:
        errors.append('Task file set differs from tasks.json.')
    for r in model.get('requirements', []):
        if not r.get('tasks') or not set(r['tasks']) <= known:
            errors.append(f'Uncovered requirement {r.get("id")}')
        for tid in r.get('tasks', []):
            task = next((t for t in tasks if t['id'] == tid), None)
            if task and r['id'] not in task['requirements']:
                errors.append(f'Asymmetric requirement mapping: {r["id"]}/{tid}')
    # Remove fenced examples and quoted source extracts before link validation.
    fence = re.compile(r'(?ms)^(`{3,}|~{3,})[^\n]*\n.*?^\1[ \t]*$')
    link_count = 0
    for p in root.rglob('*.md'):
        text = fence.sub('', p.read_text(encoding='utf-8'))
        for href in re.findall(r'\[[^\]\n]*\]\(([^\)\n]+)\)', text):
            href = href.strip()
            if href.startswith('#') or urlsplit(href).scheme:
                continue
            target = unquote(href.split('#', 1)[0])
            if not target:
                continue
            resolved = (p.parent / target).resolve()
            if root.resolve() not in (resolved, *resolved.parents):
                errors.append(f'Link outside package: {p.relative_to(root)} -> {href}')
            elif not resolved.exists():
                errors.append(f'Broken link: {p.relative_to(root)} -> {href}')
            link_count += 1
    source_refs = model.get('sources', [])
    for source in source_refs:
        if not (root / source['path']).is_file():
            errors.append(f'Missing source excerpt: {source["id"]}')
    checked_hashes = 0
    if not structure_only:
        manifest_path = root / 'MANIFEST.json'
        if not manifest_path.is_file():
            errors.append('MANIFEST.json is missing.')
        else:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            entries = manifest['files']
            listed = {e['path'] for e in entries}
            actual = {str(p.relative_to(root)).replace('\\', '/') for p in root.rglob('*')
                      if p.is_file() and p.name != 'MANIFEST.json'}
            if listed != actual:
                errors.append('Manifest file list differs from actual package.')
            for entry in entries:
                p = root / entry['path']
                if not p.is_file():
                    errors.append(f'Manifest file missing: {entry["path"]}')
                    continue
                data = p.read_bytes()
                if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
                    errors.append(f'Checksum mismatch: {entry["path"]}')
                checked_hashes += 1
    return {'ok': not errors, 'errors': errors, 'tasks': len(tasks),
            'requirements': len(model.get('requirements', [])),
            'source_excerpts': len(source_refs), 'local_links_checked': link_count,
            'hashes_checked': checked_hashes, 'minimum_task_words': min(words, default=0),
            'maximum_task_words': max(words, default=0), 'total_task_words': sum(words),
            'scope': 'planning_package_only'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--structure-only', action='store_true', help='Skip manifest hash checks.')
    parser.add_argument('--json', action='store_true', help='Print a machine-readable result.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        result = validate(root, structure_only=args.structure_only)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'Planprüfung fehlgeschlagen: {exc}', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result['ok']:
        print(f"OK: {result['tasks']} Aufgaben, {result['requirements']} Anforderungen, "
              f"{result['local_links_checked']} Links, {result['hashes_checked']} Dateihashes geprüft.")
        print('Dies prüft nur den Aufgabenplan, keine implementierte Anwendung.')
    else:
        print('\n'.join(result['errors']), file=sys.stderr)
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
