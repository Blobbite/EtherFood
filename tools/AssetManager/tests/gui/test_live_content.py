"""Direct post-it and source-preserving Markdown editing through real Qt widgets."""

import sqlite3

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QSettings, Qt, QUrl
from PySide6.QtGui import QTextTable
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QInputDialog, QListView, QMessageBox, QPushButton

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.note_service import NoteService
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.ui.asset_workspace import AssetWorkspace
from etherfood_studio.ui.documents.live_markdown import LiveMarkdownEditor, markdown_spans
from etherfood_studio.ui.main_window import MainWindow


@pytest.fixture
def window(tmp_path, qt_app):
    value = MainWindow(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat))
    root = tmp_path / "project"
    root.mkdir()
    value.new_project(root, "Direkte Inhalte")
    value.ids = value.project.demo()
    value.refresh()
    value.show()
    qt_app.processEvents()
    yield value
    for _, card in value.notes._cards():
        card.timer.stop()
        card.dirty = False
    value.documents.dirty = False
    value.close()
    qt_app.processEvents()


@pytest.mark.parametrize("entry", ["tree", "canvas", "context", "tab"])
def test_empty_old_container_shows_yellow_editable_postit_without_writing(window, qt_app, entry):
    container = window.project.create_card("note", "Alter Notizbereich", window.ids["one"])
    window.refresh()
    before = window.project.catalog.export_snapshot()
    if entry == "tree":
        item = next(i for i in window.tree.findItems("", Qt.MatchContains | Qt.MatchRecursive)
                    if i.data(0, Qt.UserRole) == container.id)
        window.tree.setCurrentItem(item)
    elif entry == "canvas":
        window.open_canvas_content(container.id)
    elif entry == "context":
        menu = window.navigation.menu(container.id)
        next(a for a in menu.actions() if a.objectName() == "context_open").trigger()
        menu.deleteLater()
    else:
        window.select_card(container.id)
        window.tabs.setCurrentWidget(window.notes)
    qt_app.processEvents()
    card = window.notes.editor
    assert card.isVisible() and card.current is None and card.size().width() == 320
    assert "#fff1ad" in card.styleSheet()
    assert card.parentWidget() is window.notes.notes.viewport()
    assert window.project.catalog.export_snapshot() == before
    assert window.notes.findChild(QPushButton, "note_inline_add_attachment") is None
    QTest.mouseClick(card.editor.viewport(), Qt.LeftButton)
    QTest.keyClicks(card.editor, "Idee direkt auf der Karte")
    assert card.dirty
    QTest.qWait(1050)
    assert not card.dirty and card.current.owner_id == container.id
    assert card.current.data["body"] == "Idee direkt auf der Karte"
    assert window.tabs.currentWidget() == window.notes


def test_note_filter_refresh_keeps_invalid_draft_and_context_color(window, qt_app, monkeypatch):
    window.select_card(window.ids["one"])
    window.tabs.setCurrentWidget(window.notes)
    card = window.notes.editor
    card.editor.setPlainText("Idee " * 101)
    assert not card.save(quiet=True)
    assert "100 Wörter" in card.state.text() and card.dirty
    window.notes.query.setText("anderer Filter")
    assert card in [entry for _, entry in window.notes._cards()]
    assert card.editor.toPlainText() == "Idee " * 101
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Cancel)
    assert not window.select_card(window.ids["two"])
    card.editor.setPlainText("Eine kurze Idee")
    menu = card.context_menu()
    colors = next(a.menu() for a in menu.actions() if a.text() == "Farbe")
    next(a for a in colors.actions() if a.objectName() == "note_color_pink").trigger()
    assert card.save()
    assert NoteService(window.project).notes(window.ids["one"])[0].data["note_color"] == "pink"
    menu.deleteLater()


def test_note_autosave_storage_error_keeps_draft_and_shows_reason(window, monkeypatch):
    window.tabs.setCurrentWidget(window.notes)
    card = window.notes.editor
    card.editor.setPlainText("Entwurf nicht verlieren")

    def locked(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(card.service, "write", locked)
    assert not card.save(quiet=True)
    assert card.dirty and card.current is None
    assert card.editor.toPlainText() == "Entwurf nicht verlieren"
    assert "database is locked" in card.state.text()


MARKDOWN = ("## Überschrift 🧩\n\nAbsatz mit **fett**, *kursiv*, ~~weg~~ und [Beleg][ref].\n\n"
            "| Richtung | Frames |\n| :--- | ---: |\n| SW | 16 |\n\n"
            "- [ ] Testen\n- [x] Prüfen\n  - Unterpunkt\n\n"
            "> Zitat\n\n```gdscript\nprint('SW')\n```\n\n"
            "[ref]: https://example.org/quelle \"Beleg\"\n")


def test_markdown_block_edit_preserves_other_source_tables_refs_and_same_heading_size(
        window, qt_app):
    doc = window.documents.create_document("Anleitung")
    window.tabs.setCurrentWidget(window.documents)
    editor = window.documents.editor
    editor.setPlainText(MARKDOWN)
    qt_app.processEvents()
    spans, references = markdown_spans(MARKDOWN)
    assert "".join(MARKDOWN[start:end] for start, end in spans) == MARKDOWN
    assert "https://example.org/quelle" in references
    assert len(editor.blocks) >= 6
    tables = [frame for block in editor.blocks
              for frame in block.view.document().rootFrame().childFrames()
              if isinstance(frame, QTextTable)]
    assert len(tables) == 1 and tables[0].columns() == 2 and tables[0].rows() == 2
    assert any("https://example.org/quelle" in block.view.toHtml() for block in editor.blocks)
    heading = editor.blocks[0]
    end = heading.end
    QTest.mouseClick(heading.view.viewport(), Qt.LeftButton)
    assert editor.active is heading and heading.source.isVisible()
    assert heading.source.toPlainText().startswith("## Überschrift")
    fragment = heading.view.document().begin().begin().fragment()
    assert fragment.charFormat().fontPointSize() == heading.source.font().pointSizeF() == 20
    heading.source.selectAll()
    QTest.keyClicks(heading.source, "# Geaendert")
    expected = "# Geaendert" + MARKDOWN[end:]
    assert editor.toPlainText() == expected
    # Add the separating newline explicitly: source edits do not invent Markdown characters.
    QTest.keyClick(heading.source, Qt.Key_Return)
    QTest.keyClick(heading.source, Qt.Key_Return)
    expected = "# Geaendert\n\n" + MARKDOWN[end:]
    assert window.documents.save()
    assert window.project.catalog.get(doc.id).data["body"] == expected
    root = window.project.catalog.path.parent
    window.open_project(root)
    window.open_content(doc.id)
    assert window.documents.editor.toPlainText() == expected


def test_markdown_context_templates_undo_readonly_and_resource_safety(window, monkeypatch):
    editor = window.documents.editor
    editor.setReadOnly(False)
    editor.setPlainText("Unverändert 🧩\n")
    original = editor.toPlainText()
    values = iter([(3, True), (2, True)])
    monkeypatch.setattr(QInputDialog, "getInt", lambda *a: next(values))
    menu = editor.context_menu()
    next(a for a in menu.actions() if a.objectName() == "markdown_insert_table").trigger()
    assert "Spalte 3" in editor.toPlainText() and editor.toPlainText().startswith(original)
    after = editor.toPlainText()
    editor.undo()
    assert editor.toPlainText() == original
    editor.redo()
    assert editor.toPlainText() == after
    for kind in ("code", "list", "todo", "quote", "link"):
        editor.insert_template(kind)
    assert "```text" in editor.toPlainText() and "- [ ] Aufgabe" in editor.toPlainText()
    before = editor.toPlainText()
    editor.setReadOnly(True)
    editor.insert_template("table")
    editor.undo()
    assert editor.toPlainText() == before
    for block in editor.blocks:
        assert block.view.loadResource(2, QUrl("file:///etc/passwd")).isEmpty()
        assert block.view.loadResource(2, QUrl("https://example.org/test.png")).isEmpty()
    menu.deleteLater()


def test_large_markdown_and_unknown_extensions_keep_exact_source(qt_app):
    editor = LiveMarkdownEditor()
    text = "\n\n".join(f"Absatz {i} 🧩" for i in range(250))
    text += "\n\n$$ x^2 $$\n\n[^note]: Nicht umschreiben\n"
    editor.setPlainText(text)
    assert len(editor.blocks) == 1
    editor.activate(editor.blocks[0])
    assert editor.toPlainText() == text
    editor.rebuild()
    assert editor.toPlainText() == text
    editor.deleteLater()


def test_asset_menu_reuses_live_markdown_and_stacked_postits(window, qt_app):
    assets = AssetService(window.project)
    record = assets.asset(window.ids["hero"])
    assets.configure(record.id, default_definition().to_data(), record.revision_no)
    workspace = AssetWorkspace(assets, window.ids["hero"], window)
    workspace.show()
    assert isinstance(workspace.documents.editor, LiveMarkdownEditor)
    workspace.tabs.setCurrentWidget(workspace.documentation)
    workspace.documentation.setCurrentWidget(workspace.documents)
    code = workspace.documents.findChild(QPushButton, "markdown_mode_code")
    QTest.mouseClick(code, Qt.LeftButton)
    assert workspace.documents.editor.mode == "code" and code.isChecked()
    markdown = workspace.documents.findChild(QPushButton, "markdown_mode_md")
    QTest.mouseClick(markdown, Qt.LeftButton)
    assert workspace.documents.editor.mode == "md" and markdown.isChecked()
    workspace.tabs.setCurrentWidget(workspace.documentation)
    workspace.documentation.setCurrentWidget(workspace.notes)
    note = workspace.notes.editor
    note.editor.setPlainText("Am Asset geschrieben")
    assert note.save()
    identifier = note.current.id
    assert workspace.notes.notes.flow() == QListView.TopToBottom
    assert not workspace.notes.notes.isWrapping()
    workspace.reject()
    workspace.deleteLater()
    window.refresh()
    window.open_content(identifier)
    assert window.notes.editor.editor.toPlainText() == "Am Asset geschrieben"
    assert window.notes.editor.current.owner_id == window.ids["hero"]
