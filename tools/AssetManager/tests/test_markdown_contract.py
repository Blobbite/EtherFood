"""M01–M07, M13–M16, M18/M21: exact syntax, safe resources and source patches."""

from pathlib import Path

import pytest

from etherfood_studio.application.document_resources import (
    FileGrant, project_target, read_image_file,
)
from etherfood_studio.application.document_service import DocumentService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.domain.models import StudioError
from etherfood_studio.ui.documents.markdown_source import MarkdownTable, escape_cell
from etherfood_studio.ui.documents.markdown_syntax import (
    headings, link_spans, parser, preserved_edit, render,
)
from etherfood_studio.ui.documents.svg_source import sanitize_svg


def test_m01_m02_blocks_escapes_and_inline_scope():
    source = ('Titel\n=====\n\nAbschnitt\n---\n\n---\n\n'
              '**Fett _innen_** ~~weg~~ `**Code**` \\*Text\\*\n'
              'weich\nbleibt Absatz  \nhart\\\nnoch hart\n\n'
              '> Zitat\n>\n> > Kind\n\n3) Drei\n4) Vier\n\n'
              '~~~python\n**kein Fett**\n```\n~~~\n\n    eingerückt\n')
    html, _ = render(source)
    assert '<h1' in html and '<h2' in html and '<hr' in html
    assert '<strong>Fett <em>innen</em></strong>' in html
    assert '<s>weg</s>' in html and '<code>**Code**</code>' in html
    assert '*Text*' in html and 'weich\nbleibt Absatz<br' in html
    assert '<ol start="3">' in html and html.count('<blockquote>') == 2
    assert '**kein Fett**\n```' in html and '<pre><code>eingerückt\n' in html


def test_m04_references_are_global_first_valid_definition_wins():
    source = ('[Fern][ A   B ] [a b][] [A B] [fehlt]\n\n' + 'Absatz\n\n' * 40
              + '[a b]: <dokumente/NPC Beschreibung.md> "Titel"\n[A B]: falsch.md\n')
    html, _ = render(source)
    assert html.count('href="dokumente/NPC%20Beschreibung.md"') == 3
    assert html.count('title="Titel"') == 3
    assert '[fehlt]' in html and 'href="falsch.md"' not in html


def test_links_balanced_targets_wiki_and_media_short_forms():
    source = ('[A](a(b).md "Titel") https://example.org/a(b). <https://example.org>\n'
              '[[NPC#animationen|Text]] ![[bilder/npc.gif]]\n'
              '`[[Code]]` \\[[maskiert]] ![[bild.png|300]]\n')
    html, _ = render(source)
    assert 'href="a(b).md"' in html
    assert 'href="https://example.org/a(b)"' in html
    assert 'href="studio-wiki:NPC%23animationen"' in html
    assert 'src="bilder/npc.gif"' in html
    assert 'studio-wiki:Code' not in html and 'studio-wiki:maskiert' not in html
    assert '![[bild.png|300]]' in html
    spans = link_spans(source)
    assert source[spans[0][0]:spans[0][1]] == '[A](a(b).md "Titel")'


def test_m06_heading_collisions_check_all_previously_assigned_ids():
    source = '# A\n# A-1\n# A\n# A\n# Ä **Ö** _Ü_\n# !!!\n# !!!\n# A\u0308\n'
    assert [h.identifier for h in headings(source)] == [
        'a', 'a-1', 'a-2', 'a-3', 'ä-ö-ü', 'abschnitt', 'abschnitt-1', 'ä']


@pytest.mark.parametrize('raw,edited,expected', [
    ('A\r\nB\r\nC', 'A\nBX\nC', 'A\r\nBX\r\nC'),
    ('\ufeff# 🧩\r\n\r\nEnde\r\n', '\ufeff# 🧩\n\nNeu\nEnde\n', '\ufeff# 🧩\r\n\r\nNeu\r\nEnde\r\n'),
    ('A\r\nB\nC', 'A\nB\nC', 'A\r\nB\nC'),
])
def test_m01_minimal_edit_retains_unmodified_line_endings(raw, edited, expected):
    start, end, value = preserved_edit(raw, edited)
    assert raw[:start] + value + raw[end:] == expected


def test_m15_m18_table_values_and_breaks_stay_text():
    source = '| A | B |\n|:-|-:|\n|001|1.0|\n|2026-09-29|=1+1|\n|`A \\| B`|x|\n'
    table = MarkdownTable.parse(source)
    assert table.rows[1] == ['001', '1.0']
    assert table.rows[2] == ['2026-09-29', '=1+1']
    table.edit(3, 1, 'a|b\\|c\nneu')
    assert 'a\\|b\\|c<br>neu' in table.text()
    assert escape_cell('a\\|b') == ' a\\|b '
    html, _ = render('|A|\n|-|\n|a<br>b<br/>c<br />d<script>x</script>|')
    assert html.count('<br') == 3 and '&lt;script&gt;' in html


def test_m15_escaped_final_pipe_is_a_cell_and_only_edited_cell_changes():
    source = 'A | B\r\n--- | ---\r\nx | a\\|\r\n'
    table = MarkdownTable.parse(source)
    left, right = table.cell_range(1, 1)
    assert source[left:right] == ' a\\|'
    table.edit(1, 1, 'b|')
    assert table.text() == source.replace(' a\\|', ' b\\| ')


def test_m07_paths_win_and_duplicate_wiki_names_remain_ambiguous(tmp_path):
    project = ProjectService.new(tmp_path, 'Wiki')
    try:
        service = DocumentService(project)
        act = project.create_card('act', 'Akt', project.project().id)
        a = service.create(project.project().id, 'NPC', '# A', template='Dokumentation')
        b = service.create(act.id, 'NPC', '# B', template='Dokumentation')
        other = service.create(act.id, 'Basis', '# Basis', template='Dokumentation')
        # An exact existing relative path precedes a global name match.
        exact = service.path(b.id).stem
        assert service.link_candidates(other.id, exact, wiki=True)[0]['id'] == b.id
        third = project.create_card('act', 'Anderer Akt', project.project().id)
        base = service.create(third.id, 'Basis', '# C', template='Dokumentation')
        assert {x['id'] for x in service.link_candidates(base.id, 'NPC', wiki=True)} == {a.id, b.id}
        before = a.revision_no
        assert service.save(a.id, a.data['body'], before).revision_no == before
    finally:
        project.catalog.close()


def test_m21_project_paths_decode_once_reject_escape_and_symlinks(tmp_path):
    root = tmp_path / 'Projekt'
    root.mkdir()
    folder = root / 'dokumente'
    folder.mkdir()
    base = folder / 'Basis.md'
    assert project_target(root, base, '../Bild%20%C3%84.png') == root / 'Bild Ä.png'
    assert project_target(root, base, '/bilder/test.png') == root / 'bilder/test.png'
    assert project_target(root, base, '%252e%252e/test.png') == folder / '%2e%2e/test.png'
    for target in ('../../secret.png', 'file:///etc/passwd', '//server/datei',
        'https://example.org/x'):
        with pytest.raises(StudioError):
            project_target(root, base, target)
    (folder / 'link').symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(StudioError):
        project_target(root, base, 'link/secret.png')
    file = tmp_path / 'one.png'
    file.write_bytes(b'original')
    grant = FileGrant.select(file, 100)
    file.write_bytes(b'changed')
    with pytest.raises(StudioError):
        read_image_file(file, 100, grant.digest)


SVG = (b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60">'
       b'<defs><linearGradient id="g"><stop offset="0" stop-color="red"/>'
       b'<stop offset="1" stop-color="blue"/></linearGradient></defs>'
       b'<g transform="translate(5 5)"><rect width="90" height="50" fill="url(#g)"/>'
       b'<text x="10" y="20">Text</text></g></svg>')


def test_m13_m14_safe_svg_preview_copy_does_not_modify_original():
    original = bytes(SVG)
    result = sanitize_svg(SVG)
    assert b'linearGradient' in result and b'transform=' in result and b'Text' in result
    assert SVG == original


@pytest.mark.parametrize('body', [
    '<script>alert(1)</script>', '<rect onload="x"/>', '<foreignObject/>',
    '<image href="https://example.org/a.png"/>', '<use href="file:///etc/passwd"/>',
    '<rect fill="url(https://example.org/a)"/>', '<style>@import "x";</style>',
    '<defs><g id="a"><use href="#a"/></g></defs><use href="#a"/>',
    '<use href="#missing"/>', '<animate attributeName="x"/>',
])
def test_m13_active_external_cyclic_or_unsupported_svg_is_visibly_rejected(body):
    with pytest.raises(StudioError):
        sanitize_svg(('<svg xmlns="http://www.w3.org/2000/svg">' + body + '</svg>').encode())


def test_m13_entities_are_rejected_before_xml_parsing():
    with pytest.raises(StudioError):
        sanitize_svg(b'<!DOCTYPE svg [<!ENTITY x SYSTEM "file:///etc/passwd">]><svg>&x;</svg>')


def test_table_link_spans_preserve_duplicate_cells_and_escaped_pipes():
    source = '|A|B|\n|-|-|\n|[A \\| B](a.md)|[A \\| B](a.md)|\n'
    spans = link_spans(source)
    assert len(spans) == 2 and spans[0][1] < spans[1][0]
    assert all(source[a:b] == '[A \\| B](a.md)' for a, b, _ in spans)


def test_single_cell_patch_does_not_normalize_optional_outer_pipes():
    source = '  A | B\r\n :- | -:\r\n **Eins** | 001\r\n'
    model = MarkdownTable.parse(source)
    assert model.text() == source
    model.edit(1, 1, '1.0')
    changed = model.text()
    assert changed.startswith('  A | B\r\n :- | -:\r\n **Eins** |')
    assert changed.endswith(' 1.0 \r\n')
