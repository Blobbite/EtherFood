"""Real Qt acceptance events for Markdown, image playback, editing and revision safety."""

import time
import json
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from PySide6.QtCore import QSettings, Qt, QUrl
from PySide6.QtGui import QTextCursor, QMovie
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QInputDialog, QMessageBox, QPlainTextEdit,
    QPushButton, QStyleOptionViewItem,
)

from etherfood_studio.application.document_service import DocumentService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.ui.documents.editor import DocumentEditor
from etherfood_studio.ui.documents.insert_dialogs import ReferenceDialog
from etherfood_studio.ui.documents.markdown_syntax import headings
from etherfood_studio.ui.documents.media_source import MediaLimits
from etherfood_studio.ui.appearance import appearance


@pytest.fixture
def panel(qt_app, tmp_path):
    previous_settings = appearance().settings
    appearance().configure(QSettings(str(tmp_path / 'preferences.ini'), QSettings.IniFormat))
    project = ProjectService.new(tmp_path, 'Markdown-Abnahme')
    widget = DocumentEditor()
    widget.bind(DocumentService(project))
    widget.show_card(project.project().id)
    widget.create_document('Prüfdokument')
    widget.resize(1100, 900)
    widget.show()
    qt_app.processEvents()
    yield widget
    widget.dirty = False
    widget.close()
    widget.deleteLater()
    qt_app.processEvents()
    project.catalog.close()
    appearance().settings = previous_settings


def wait_for(predicate, timeout=3000):
    end = time.monotonic() + timeout / 1000
    while not predicate() and time.monotonic() < end:
        QTest.qWait(10)
    assert predicate()


def image_file(panel, name, fmt='PNG'):
    path = panel.service.path(panel.current.id).parent / name
    first = Image.new('RGBA', (40, 20), (255, 0, 0, 255))
    if fmt == 'GIF':
        second = Image.new('RGBA', (40, 20), (0, 0, 255, 255))
        first.save(path, format=fmt, save_all=True, append_images=[second],
                   duration=[140, 260], loop=0)
    else:
        first.convert('RGB').save(path, format=fmt)
    return path


CONTRACTS = json.loads((Path(__file__).parents[1] / 'fixtures/markdown/contracts.json').read_text())


@pytest.mark.parametrize('identifier', list(CONTRACTS))
def test_all_fixture_sources_survive_view_changes_exactly(panel, identifier):
    source = CONTRACTS[identifier]['source']
    assert CONTRACTS[identifier]['expected']
    panel.editor.setPlainText(source)
    assert panel.save()
    before = panel.service.catalog.export_snapshot()
    panel.editor.set_mode('code')
    panel.editor.set_mode('md')
    assert panel.editor.toPlainText() == source and not panel.dirty
    assert panel.service.catalog.export_snapshot() == before


def test_m01_m02_m04_rendered_basics_and_far_references_preserve_revision(panel):
    source = '# Titel\n\n**Fett _innen_** [Fern][ref]\n\n- [ ] Aufgabe\n\n' + 'Text\n\n' * 30
    source += '[ref]: https://example.org "Hinweis"\n'
    panel.editor.setPlainText(source)
    assert panel.save()
    before = panel.service.catalog.export_snapshot()
    for mode in ['code', 'md', 'code', 'md']:
        panel.editor.set_mode(mode)
    html = ''.join(b.view.toHtml() for b in panel.editor.blocks)
    assert 'https://example.org' in html
    assert panel.editor.toPlainText() == source and not panel.dirty
    assert panel.service.catalog.export_snapshot() == before


@pytest.mark.parametrize('fmt,name', [('PNG', 'A.png'), ('JPEG', 'B.jpg'), ('WEBP', 'C.webp')])
def test_m08_actual_raster_formats_scaled_without_source_change(panel, fmt, name):
    image_file(panel, name, fmt)
    source = f'![Alternativtext]({name})\n'
    panel.editor.setPlainText(source)
    assert panel.save()
    revision = panel.current.revision_no
    item = next(iter(panel.editor.media.resources.values()))
    wait_for(lambda: item.state != 'loading')
    assert item.state == 'ready' and item.image.width() == 40
    assert panel.editor.media.image(item.key, 1000).width() == 40
    assert panel.editor.media.image(item.key, 20).width() <= 24
    assert panel.editor.toPlainText() == source and not panel.dirty
    assert panel.current.revision_no == revision


def test_m09_actual_gif_frames_pause_resume_and_cleanup(panel):
    image_file(panel, 'idle.gif', 'GIF')
    panel.editor.setPlainText('![Idle](idle.gif)')
    item = next(iter(panel.editor.media.resources.values()))
    wait_for(lambda: item.movie is not None)
    assert item.movie.cacheMode() == QMovie.CacheNone and item.movie.loopCount() == -1
    view = panel.editor.blocks[0].view
    first = item.image.pixelColor(10, 10)
    first_visible = view.grab().toImage()
    wait_for(lambda: item.image.pixelColor(10, 10) != first)
    assert view.grab().toImage() != first_visible
    assert item.movie.nextFrameDelay() in {140, 260}
    panel.editor.media.action(item, 'pause', panel)
    frame, number = item.image.copy(), item.movie.currentFrameNumber()
    paused_visible = view.grab().toImage()
    QTest.qWait(350)
    assert item.state == 'paused' and item.movie.currentFrameNumber() == number
    assert item.image == frame
    assert view.grab().toImage() == paused_visible
    panel.editor.media.action(item, 'pause', panel)
    wait_for(lambda: item.movie.currentFrameNumber() != number)
    panel.editor.media.stop()
    assert not panel.editor.media.resources and item.movie is None


def test_m09_reduced_motion_starts_paused(panel):
    image_file(panel, 'idle.gif', 'GIF')
    panel.editor.motion_setting('reduced_motion', True)
    panel.editor.setPlainText('![Idle](idle.gif)')
    item = next(iter(panel.editor.media.resources.values()))
    wait_for(lambda: item.state != 'loading')
    assert item.state == 'paused'


def test_m10_linked_image_does_not_open_outer_target_when_loaded(panel, monkeypatch):
    image_file(panel, 'A.png')
    calls = []
    panel.editor.local_link = lambda url: calls.append(url.toString())
    panel.editor.setPlainText('[![Bild](A.png)](anderes.md#ziel)')
    item = next(iter(panel.editor.media.resources.values()))
    wait_for(lambda: item.state == 'ready')
    assert calls == []
    from PySide6.QtCore import QPoint
    view = panel.editor.blocks[0].view
    cursor = QTextCursor(view.document())
    point = view.cursorRect(cursor).topLeft() + QPoint(12, 8)
    assert view.anchorAt(point) == 'anderes.md#ziel'
    QTest.mouseClick(view.viewport(), Qt.LeftButton, Qt.NoModifier, point)
    assert calls == ['anderes.md#ziel']


def test_m11_no_network_on_render_or_mode_switch(panel, monkeypatch):
    calls = []
    monkeypatch.setattr('etherfood_studio.ui.documents.media.download', lambda *a,
        **k: calls.append(a))
    panel.editor.setPlainText('![Extern](https://example.org/no-fetch.png)')
    for mode in ['code', 'md']:
        panel.editor.set_mode(mode)
    QTest.qWait(30)
    assert calls == []
    assert next(iter(panel.editor.media.resources.values())).state == 'permission'


def test_m13_m14_svg_file_and_explicit_code_preview_are_static_and_lossless(panel):
    raw = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60">'
           '<rect width="100" height="60" fill="red"/></svg>')
    path = panel.service.path(panel.current.id).parent / 'symbol.svg'
    path.write_text(raw)
    source = '![SVG](symbol.svg)\n\n```svg\n' + raw + '\n```\n'
    panel.editor.setPlainText(source)
    item = next(iter(panel.editor.media.resources.values()))
    wait_for(lambda: item.state != 'loading')
    assert item.state == 'ready' and item.image.pixelColor(10, 10).red() == 255
    block = panel.editor.blocks[-1]
    toggle = next(b for b in block.code_controls.findChildren(QPushButton)
                  if b.text() == 'SVG-Vorschau')
    QTest.mouseClick(toggle, Qt.LeftButton)
    wait_for(lambda: len(panel.editor.media.resources) == 2 and
             all(r.state == 'ready' for r in panel.editor.media.resources.values()))
    assert panel.editor.toPlainText() == source and path.read_text() == raw


def test_m15_m16_table_images_and_lossless_overlong_row(panel):
    image_file(panel, 'A.png')
    panel.editor.setPlainText('|A|B|\n|:-|-:|\n|![Bild](A.png)|`a \\| b`<br>Text|')
    block = panel.editor.blocks[0]
    item = next(iter(panel.editor.media.resources.values()))
    wait_for(lambda: item.state == 'ready')
    table = block.table_editor.table
    delegate = table.itemDelegate()
    index = table.model().index(1, 0)
    doc = delegate.document(QStyleOptionViewItem(), index)
    assert 'studio-media:' in doc.toHtml()
    source = '|A|\n|-|\n|eins|ZUSÄTZLICH|\n'
    panel.editor.setPlainText(source)
    assert panel.editor.blocks[0].table_editor is None
    assert 'ZUSÄTZLICH' in panel.editor.blocks[0].view.toPlainText()
    assert 'prüfbedürftig' in panel.editor.blocks[0].view.toPlainText()


def test_m17_m18_table_keyboard_cancel_breaks_align_and_undo(panel, monkeypatch):
    source = '|A|B|\n|---|---|\n|001|1.0|\n|2026-09-29|=1+1|\n'
    editor = panel.editor
    editor.setPlainText(source)
    table = editor.blocks[0].table_editor.table
    table.setCurrentCell(1, 0)
    QTest.keyClick(table, Qt.Key_F2)
    field = table.findChild(QPlainTextEdit)
    assert field is not None
    QTest.keyClicks(field, 'abbrechen')
    QTest.keyClick(field, Qt.Key_Escape)
    assert editor.toPlainText() == source
    QTest.qWait(10)
    table.editItem(table.item(1, 0))
    QTest.qWait(10)
    field = next(f for f in table.findChildren(QPlainTextEdit) if f.isVisible())
    field.selectAll()
    QTest.keyClicks(field, 'a|b')
    QTest.keyClick(field, Qt.Key_Return, Qt.ShiftModifier)
    QTest.keyClicks(field, 'c')
    QTest.keyClick(field, Qt.Key_Return)
    assert 'a\\|b<br>c' in editor.toPlainText()
    editor.blocks[0].table_editor.align_column('center')
    assert ':---:' in editor.toPlainText()
    assert '1.0' in editor.toPlainText() and '=1+1' in editor.toPlainText()
    assert panel.save()
    saved = editor.toPlainText()
    reopened = ProjectService.open(panel.service.catalog.path.parent)
    try:
        assert reopened.catalog.get(panel.current.id).data['body'] == saved
    finally:
        reopened.catalog.close()
    editor.undo()
    editor.undo()
    assert editor.toPlainText() == source
    editor.redo()
    editor.redo()
    assert editor.toPlainText() == saved


def test_m17_nonempty_removal_confirmation_preserves_cancelled_content(panel, monkeypatch):
    source = '|A|B|\n|---|---|\n|Daten|001|'
    panel.editor.setPlainText(source)
    widget = panel.editor.blocks[0].table_editor
    widget.table.selectRow(1)
    prompts = []
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: prompts.append(args[2])
        or QMessageBox.No)
    widget.remove_rows()
    assert 'Daten' in prompts[0] and panel.editor.toPlainText() == source
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.Yes)
    widget.remove_rows()
    assert 'Daten' not in panel.editor.toPlainText()
    panel.editor.undo()
    assert panel.editor.toPlainText() == source


def test_m19_code_crlf_selection_and_shared_undo(panel):
    source = '# 🧩\r\n\r\nText\r\n'
    editor = panel.editor
    editor.setPlainText(source)
    editor.set_mode('code')
    editor.select_source(source.index('Text'), source.index('Text') + 4)
    editor.format_selection('bold')
    assert editor.toPlainText() == source.replace('Text', '**Text**')
    editor.set_mode('md')
    editor.undo()
    assert editor.toPlainText() == source
    editor.set_mode('code')
    editor.redo()
    assert editor.toPlainText() == source.replace('Text', '**Text**')


def test_m20_cancelled_insert_dialog_has_no_text_or_attachment_side_effects(panel):
    before = panel.service.catalog.export_snapshot()
    source = panel.editor.toPlainText()
    dialog = ReferenceDialog(panel.editor, image=True)
    path = image_file(panel, 'source.png')
    dialog.set_file(path)
    dialog.copy_file.setChecked(True)
    dialog.reject()
    dialog.release_temporary()
    dialog.deleteLater()
    assert panel.service.catalog.export_snapshot() == before
    assert panel.editor.toPlainText() == source


def test_m22_late_media_cannot_appear_in_another_document(panel, monkeypatch):
    image_file(panel, 'A.png')
    from etherfood_studio.ui.documents import media
    original = media.read_image_file
    def delayed(*args):
        time.sleep(0.15)
        return original(*args)
    monkeypatch.setattr(media, 'read_image_file', delayed)
    panel.editor.setPlainText('![A](A.png)')
    other = panel.service.create(panel.owner_id, 'Anderes', '# Anderes', template='Dokumentation')
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.Discard)
    panel.open_document(other.id)
    QTest.qWait(250)
    assert panel.current.id == other.id and panel.editor.toPlainText() == '# Anderes'
    assert not panel.editor.media.resources


def test_m23_structured_edit_conflict_keeps_draft_and_readonly_guards(panel, monkeypatch):
    panel.editor.setPlainText('|A|\n|---|\n|1|\n\n- [ ] Aufgabe\n')
    assert panel.save()
    current = panel.current
    panel.service.save(current.id, 'Parallel', current.revision_no)
    panel.editor.blocks[0].table_editor.table.item(1, 0).setText('Mein Wert')
    errors = []
    monkeypatch.setattr('etherfood_studio.ui.documents.editor.show_error', lambda p,
        e: errors.append(e.code))
    assert not panel.save() and errors == ['conflict']
    before = panel.editor.toPlainText()
    panel.editor.setReadOnly(True)
    panel.editor.blocks[0].table_editor.insert_row()
    panel.editor.format_selection('bold')
    panel.editor.undo()
    assert panel.editor.toPlainText() == before


def test_m05_m06_real_link_click_and_missing_anchor_hint(panel, monkeypatch):
    other = panel.service.create(panel.owner_id, 'Andere Datei', '# Start\n\n## Ziel\n',
        template='Dokumentation')
    target = panel.service.path(other.id).name
    source = f'[Öffnen](<{target}#ziel>)\n\n# Eigen\n'
    panel.editor.setPlainText(source)
    panel.save()
    view = panel.editor.blocks[0].view
    cursor = view.document().find('Öffnen')
    cursor.setPosition(cursor.selectionStart() + 2)
    QTest.qWait(10)
    point = view.cursorRect(cursor).center()
    assert view.anchorAt(point)
    QTest.mouseClick(view.viewport(), Qt.LeftButton, pos=point)
    assert panel.current.id == other.id
    hints = []
    monkeypatch.setattr(QMessageBox, 'information', lambda *args: hints.append(args[2]))
    panel.follow_link(QUrl('#nicht-vorhanden'))
    assert hints and 'nicht-vorhanden' in hints[-1]
    block = next(b for b in panel.editor.blocks if 'Ziel' in b.view.toPlainText())
    menu = panel.editor.context_menu(block, block.view)
    next(a for a in menu.actions() if a.text() == 'Abschnittslink kopieren').trigger()
    assert QApplication.clipboard().text() == '#ziel'
    menu.deleteLater()


def test_m07_ambiguous_wiki_link_asks_and_cancel_does_not_navigate(panel, monkeypatch):
    project = panel.service.project
    a = project.create_card('act', 'A', project.project().id)
    b = project.create_card('act', 'B', project.project().id)
    one = panel.service.create(a.id, 'NPC', '# Eins', template='Dokumentation')
    two = panel.service.create(b.id, 'NPC', '# Zwei', template='Dokumentation')
    original = panel.current.id
    choices = []
    monkeypatch.setattr(QInputDialog, 'getItem', lambda *args: choices.append(args[3]) or ('',
        False))
    panel.follow_link(QUrl('studio-wiki:NPC'))
    assert len(choices[0]) == 2 and panel.current.id == original
    chosen = str(panel.service.path(two.id).relative_to(panel.service.catalog.path.parent))
    monkeypatch.setattr(QInputDialog, 'getItem', lambda *args: (chosen, True))
    panel.follow_link(QUrl('studio-wiki:NPC'))
    assert panel.current.id == two.id


def test_m20_accepted_image_import_uses_attachment_service_and_survives_reopen(panel, tmp_path,
    monkeypatch):
    outside = tmp_path.parent / (tmp_path.name + '-outside.png')
    Image.new('RGB', (20, 10), 'blue').save(outside)
    original = panel.editor.toPlainText()
    def accept(dialog):
        dialog.set_file(outside)
        dialog.copy_file.setChecked(True)
        dialog.label.setText('Übernommenes Bild')
        dialog.accept()
        return QDialog.Accepted
    monkeypatch.setattr(ReferenceDialog, 'exec', accept)
    try:
        panel.editor.reference_dialog(image=True)
        assert len(panel.current.data['attachments']) == 1
        assert '.asset-studio/objects/' in panel.editor.toPlainText()
        assert str(outside) not in panel.editor.toPlainText() and outside.exists()
        assert panel.save()
        value = panel.editor.toPlainText()
        panel.editor.undo()
        assert panel.editor.toPlainText() == original
        panel.editor.redo()
        assert panel.editor.toPlainText() == value
        panel.refresh_documents(panel.current.id)
        wait_for(lambda: all(r.state != 'loading' for r in panel.editor.media.resources.values()))
        assert all(r.state == 'ready' for r in panel.editor.media.resources.values())
    finally:
        outside.unlink(missing_ok=True)


def test_m20_cancelled_clipboard_image_removes_temporary_preview(panel):
    from PySide6.QtGui import QImage
    image = QImage(20, 20, QImage.Format_RGB32)
    image.fill(Qt.red)
    dialog = ReferenceDialog(panel.editor, image=True)
    dialog.set_clipboard_image(image)
    temporary = dialog.temporary
    assert temporary.is_file()
    dialog.show()
    cancel = dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.Cancel)
    QTest.mouseClick(cancel, Qt.LeftButton)
    assert not temporary.exists()
    assert not panel.current.data['attachments']
    dialog.deleteLater()


def test_m17_tsv_preview_cancel_then_insert_is_one_undo_step(panel, monkeypatch):
    source = '|A|B|\n|---|---|\n|Alt|001|'
    panel.editor.setPlainText(source)
    widget = panel.editor.blocks[0].table_editor
    widget.table.setCurrentCell(1, 0)
    QApplication.clipboard().setText('Neu\t1.0\nDatum\t=1+1')
    prompts = []
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: prompts.append(args[2])
        or QMessageBox.No)
    widget.paste_cells()
    assert 'Alt' in prompts[0] and 'Neu' in prompts[0] and panel.editor.toPlainText() == source
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.Yes)
    widget.paste_cells()
    assert '| Neu | 1.0 |' in panel.editor.toPlainText() and '=1+1' in panel.editor.toPlainText()
    assert len(panel.editor._undo) == 1
    panel.editor.undo()
    assert panel.editor.toPlainText() == source


def test_m24_repeated_media_open_close_releases_reserved_memory_and_keeps_events_live(panel):
    image_file(panel, 'a.gif', 'GIF')
    image_file(panel, 'b.gif', 'GIF')
    media = panel.editor.media
    for _ in range(3):
        panel.editor.setPlainText('![A](a.gif) ![B](b.gif)')
        wait_for(lambda: len(media.resources) == 2 and all(r.state != 'loading'
            for r in media.resources.values()))
        assert all(r.movie is not None for r in media.resources.values())
        panel.editor.set_mode('code')
        QTest.keyClicks(panel.editor.code_source, 'Text')
        assert 'Text' in panel.editor.toPlainText()
        panel.editor.set_mode('md')
        media.stop()
        wait_for(lambda: not media.running)
        assert media.memory_used == 0 and not media.resources


def test_m04_duplicate_definition_in_later_block_cannot_override_global_reference(panel):
    panel.editor.setPlainText('[r]: zuerst.md\n\nAbsatz\n\n[Später][r]\n\n[r]: falsch.md\n')
    html = ''.join(b.view.toHtml() for b in panel.editor.blocks)
    assert 'href="zuerst.md"' in html and 'href="falsch.md"' not in html


def test_m11_m12_local_permission_cache_block_and_selection_use_real_server(panel, monkeypatch):
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    raw = BytesIO()
    Image.new('RGB', (40, 20), 'red').save(raw, format='PNG')
    hits = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            hits.append(self.path)
            self.send_response(200)
            self.send_header('Content-Length', str(len(raw.getvalue())))
            self.end_headers()
            self.wfile.write(raw.getvalue())
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    source = f'http://127.0.0.1:{server.server_port}/image'
    try:
        panel.editor.setPlainText(f'|Bild|Text|\n|---|---|\n|![Test]({source})|Unverändert|\n')
        media = panel.editor.media
        item = media.ensure(source)
        assert item.state == 'permission' and hits == []
        prompts = []
        monkeypatch.setattr(QMessageBox, 'question', lambda *args: prompts.append(args[1])
            or QMessageBox.Yes)
        media.action(item, 'allow', panel)
        wait_for(lambda: item.state != 'loading')
        assert item.state == 'permission' and hits == []
        assert 'Lokaler Medienserver' in item.reason
        media.action(item, 'allow', panel)
        wait_for(lambda: item.state == 'ready')
        assert hits == ['/image'] and len(prompts) == 2
        panel.editor.blocks[0].table_editor.table.item(1, 1).setText('Geändert')
        panel.editor.set_mode('code')
        field = panel.editor.code_source
        field.selectAll()
        selection = field.textCursor().selectedText()
        field.setFocus()
        media.changed.emit(item.key)
        assert field.hasFocus() and field.textCursor().selectedText() == selection
        panel.editor.set_mode('md')
        QTest.qWait(20)
        assert hits == ['/image']
        media.set_policy('block')
        assert item.state == 'blocked' and item.image.isNull() and media.memory_used == 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)


def test_m24_shared_decode_budget_blocks_extra_images_before_allocation(panel):
    from dataclasses import replace
    image_file(panel, 'a.gif', 'GIF')
    image_file(panel, 'b.gif', 'GIF')
    media = panel.editor.media
    media.limits = replace(media.limits, memory=25000)
    panel.editor.setPlainText('![A](a.gif) ![B](b.gif)')
    wait_for(lambda: all(r.state != 'loading' for r in media.resources.values()))
    assert sorted(r.state for r in media.resources.values()) == ['blocked', 'ready']
    assert 0 < media.memory_used <= media.limits.memory
    ready = next(r for r in media.resources.values() if r.state == 'ready')
    media.action(ready, 'hide', panel)
    assert media.memory_used == 0


def test_m15_table_link_context_can_remove_link_without_losing_text_or_other_cells(panel):
    source = '|A|B|\n|-|-|\n|[Link][r]|001|\n\n[r]: andere.md\n'
    panel.editor.setPlainText(source)
    widget = panel.editor.blocks[0].table_editor
    widget.table.setCurrentCell(1, 0)
    menu = widget.context_menu()
    link_menu = next(a.menu() for a in menu.actions() if a.text().startswith('Link:'))
    next(a for a in link_menu.actions() if a.text() == 'Verknüpfung entfernen').trigger()
    assert panel.editor.toPlainText() == source.replace('[Link][r]', 'Link')
    panel.editor.undo()
    assert panel.editor.toPlainText() == source
    menu.deleteLater()


@pytest.mark.parametrize('kind,prefix', [('list', '- '), ('todo', '- [ ] '), ('quote', '> ')])
def test_m19_multiline_formatting_is_one_source_edit_with_original_line_endings(panel, kind,
    prefix):
    source = 'Eins\r\nZwei\r\n'
    panel.editor.setPlainText(source)
    panel.editor.set_mode('code')
    panel.editor.select_source(0, len(source))
    panel.editor.format_selection(kind)
    assert panel.editor.toPlainText() == prefix + 'Eins\r\n' + prefix + 'Zwei\r\n'
    panel.editor.set_mode('md')
    panel.editor.undo()
    assert panel.editor.toPlainText() == source


def test_m05_code_control_click_respects_crlf_and_drag_selection(panel):
    source = '😀 Vorwort\r\n\r\n[Ziel](andere.md)\r\n'
    panel.editor.setPlainText(source)
    panel.editor.set_mode('code')
    field = panel.editor.code_source
    opened = []
    panel.editor.blocks[0].view.local_link = lambda url: opened.append(url.toString()) or True
    cursor = field.document().find('Ziel')
    cursor.setPosition(cursor.selectionStart() + 1)
    point = field.cursorRect(cursor).center()
    QTest.mouseClick(field.viewport(), Qt.LeftButton, Qt.NoModifier, point)
    assert not opened
    QTest.mouseClick(field.viewport(), Qt.LeftButton, Qt.ControlModifier, point)
    assert opened == ['andere.md']
    QTest.mousePress(field.viewport(), Qt.LeftButton, Qt.ControlModifier, point)
    from PySide6.QtCore import QPoint
    QTest.mouseMove(field.viewport(), point + QPoint(35, 0))
    QTest.mouseRelease(field.viewport(), Qt.LeftButton, Qt.ControlModifier, point + QPoint(35, 0))
    assert opened == ['andere.md'] and panel.editor.toPlainText() == source


def test_m20_cancelled_modal_dialog_restores_source_focus_and_selection(panel):
    from PySide6.QtCore import QTimer
    panel.editor.setPlainText('Unverändert')
    panel.editor.select_source(1, 5)
    field = panel.editor.active.source
    selected = field.textCursor().selectedText()
    QTimer.singleShot(20, lambda: QApplication.activeModalWidget().reject())
    panel.editor.reference_dialog(image=True)
    QTest.qWait(20)
    assert field.hasFocus() and field.textCursor().selectedText() == selected
    assert panel.editor.toPlainText() == 'Unverändert'


def test_m09_finite_gif_uses_its_repeat_count(panel):
    path = panel.service.path(panel.current.id).parent / 'finite.gif'
    Image.new('RGB', (12, 12), 'red').save(
        path, format='GIF', save_all=True, append_images=[Image.new('RGB', (12, 12), 'blue')],
        duration=[70, 110], loop=1)
    panel.editor.setPlainText('![Endlich](finite.gif)')
    item = panel.editor.media.ensure('finite.gif')
    wait_for(lambda: item.movie is not None)
    assert item.movie.loopCount() == 1
    wait_for(lambda: item.state == 'paused')
    assert item.movie.state() == QMovie.NotRunning
    frame = item.image.cacheKey()
    QTest.qWait(200)
    assert item.image.cacheKey() == frame


def test_m10_selected_external_file_link_needs_exact_grant_and_does_not_import(panel,
    tmp_path_factory, monkeypatch):
    path = tmp_path_factory.mktemp('markdown-external') / 'extern ä.png'
    Image.new('RGB', (18, 12), 'green').save(path)
    attachments = list(panel.current.data['attachments'])
    def accept(dialog):
        dialog.set_file(path)
        assert not dialog.copy_file.isChecked()
        dialog.accept()
        return QDialog.Accepted
    monkeypatch.setattr(ReferenceDialog, 'exec', accept)
    panel.editor.reference_dialog(image=True)
    source = panel.editor.toPlainText()
    assert 'file:' in source and panel.current.data['attachments'] == attachments
    item = panel.editor.media.ensure(path.as_uri())
    wait_for(lambda: item.state == 'ready')
    assert item.image.width() == 18 and path.is_file()
    assert panel.save()
    panel.editor.media.grants()['files'].clear()
    panel.editor.media.stop()
    panel.editor.rebuild()
    assert panel.editor.media.ensure(path.as_uri()).state == 'permission'
    assert panel.editor.toPlainText() == source


def test_m16_theme_switch_keeps_links_legible_and_source_and_selection_unchanged(panel):
    from etherfood_studio.ui.theme import color
    source = '[Verweis](#ziel)\n\n# Ziel\n\n|A|\n|-|\n|[Zelle](#ziel)|'
    panel.editor.setPlainText(source)
    view = panel.editor.blocks[0].view
    view.selectAll()
    selected = view.textCursor().selectedText()
    for theme in ('light', 'dark', 'light'):
        appearance().set_preferences(theme, 'text', persist=False)
        QTest.qWait(10)
        cursor = view.document().find('Verweis')
        assert cursor.charFormat().foreground().color().name() == color('link')
        assert cursor.charFormat().fontUnderline()
        assert view.textCursor().selectedText() == selected
        assert panel.editor.toPlainText() == source


def test_m20_clipboard_url_stays_text_and_image_drop_opens_shared_dialog(panel, monkeypatch):
    from PySide6.QtCore import QMimeData, QPoint, QPointF
    from PySide6.QtGui import QDragEnterEvent, QDropEvent
    panel.editor.setPlainText('')
    panel.editor.set_mode('code')
    field = panel.editor.code_source
    mime = QMimeData()
    mime.setUrls([QUrl('https://example.org/text')])
    mime.setText('https://example.org/text')
    QApplication.clipboard().setMimeData(mime)
    QTest.keyClick(field, Qt.Key_V, Qt.ControlModifier)
    assert panel.editor.toPlainText() == 'https://example.org/text'
    image = image_file(panel, 'drop.png')
    dropped = QMimeData()
    dropped.setUrls([QUrl.fromLocalFile(str(image))])
    calls = []
    monkeypatch.setattr(panel.editor, 'reference_dialog', lambda **kw: calls.append(kw))
    QApplication.sendEvent(field.viewport(), QDragEnterEvent(
        QPoint(5, 5), Qt.CopyAction, dropped, Qt.LeftButton, Qt.NoModifier))
    QApplication.sendEvent(field.viewport(), QDropEvent(
        QPointF(5, 5), Qt.CopyAction, dropped, Qt.LeftButton, Qt.NoModifier))
    assert calls == [{'image': True, 'file': str(image)}] and image.is_file()


def test_m12_concurrency_limit_and_block_cancel_actual_queued_downloads(panel):
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from etherfood_studio.ui.documents.media_source import origin
    raw = BytesIO()
    Image.new('RGB', (8, 8), 'red').save(raw, format='PNG')
    release, hits = threading.Event(), []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            hits.append(self.path)
            self.send_response(200)
            self.end_headers()
            release.wait(2)
            try:
                self.wfile.write(raw.getvalue())
            except (BrokenPipeError, ConnectionResetError):
                pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f'http://127.0.0.1:{server.server_port}'
    media = panel.editor.media
    try:
        sources = [base + '/' + str(i) for i in range(6)]
        media.grants()['urls'].update(sources)
        media.grants()['private'].add(origin(base))
        panel.editor.setPlainText(' '.join(f'![Test]({s})' for s in sources))
        wait_for(lambda: len(hits) == 4)
        QTest.qWait(40)
        assert len(hits) == 4 and len(media.running) == 4 and len(media.pending) == 2
        media.set_policy('block')
        release.set()
        wait_for(lambda: not media.running)
        assert len(hits) == 4 and media.memory_used == 0
        assert all(r.state == 'blocked' and r.image.isNull() for r in media.resources.values())
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        worker.join(2)


def test_m03_checkbox_click_undo_save_reopen_and_readonly(panel):
    original = '- [ ] Aufgabe\r\n'
    panel.editor.setPlainText(original)
    assert panel.save()
    checkbox = panel.editor.blocks[0].view.checkboxes[0][0]
    QTest.mouseClick(checkbox, Qt.LeftButton)
    assert panel.editor.toPlainText() == '- [x] Aufgabe\r\n'
    panel.editor.undo()
    assert panel.editor.toPlainText() == original
    panel.editor.redo()
    assert panel.save()
    panel._load(panel.current.id)
    checkbox = panel.editor.blocks[0].view.checkboxes[0][0]
    assert checkbox.isChecked()
    panel.editor.setReadOnly(True)
    QTest.mouseClick(checkbox, Qt.LeftButton)
    assert panel.editor.toPlainText() == '- [x] Aufgabe\r\n' and not panel.dirty


def test_m02_code_copy_preserves_source_line_endings_and_has_horizontal_overflow(panel):
    content = '  print("Beispiel")\r\n' + '# ' + 'lange Zeile ' * 100 + '\r\n'
    source = '~~~~python\r\n' + content + '~~~~\r\n'
    panel.editor.setPlainText(source)
    block = panel.editor.blocks[0]
    copy = next(b for b in block.code_controls.findChildren(QPushButton)
                if b.text() == 'Code kopieren')
    QTest.mouseClick(copy, Qt.LeftButton)
    assert QApplication.clipboard().text() == content
    assert block.view.horizontalScrollBar().maximum() > 0
    assert panel.editor.toPlainText() == source


def test_m06_m07_project_file_view_uses_existing_wiki_resolution_and_target_flash(panel):
    from etherfood_studio.ui.documents.project_links import ProjectMarkdownView
    from urllib.parse import quote
    target = panel.service.create(panel.owner_id, 'Wiki-Ziel', '# Ziel\n',
                                  template='Dokumentation')
    path = panel.service.path(panel.current.id).parent / 'extra.md'
    path.write_text('[[Wiki-Ziel#ziel]]\n', encoding='utf-8')
    dialog = ProjectMarkdownView(panel.service, path, panel)
    dialog.follow(QUrl('studio-wiki:' + quote('Wiki-Ziel#ziel', safe='')))
    assert dialog.path == panel.service.path(target.id)
    assert len(dialog.view.extraSelections()) == 1
    dialog.close()
    dialog.deleteLater()


def test_m13_media_alt_and_code_language_never_enable_qlabel_html(panel):
    from PySide6.QtWidgets import QLabel
    source = ('![<img src="file:///unapproved.png">](missing.png)\n\n'
              '~~~<img src="file:///unapproved.png">\nText\n~~~\n')
    panel.editor.setPlainText(source)
    media_block, code_block = panel.editor.blocks
    labels = (media_block.controls.findChildren(QLabel) +
              code_block.code_controls.findChildren(QLabel))
    assert labels and all(label.textFormat() == Qt.PlainText for label in labels)
    assert panel.editor.toPlainText() == source
