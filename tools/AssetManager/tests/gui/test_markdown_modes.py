"""Rendered/source mode switches preserve drafts, history and revision protection."""

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox, QPushButton

from etherfood_studio.application.document_service import DocumentService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.ui.documents.editor import DocumentEditor


@pytest.fixture
def documents(tmp_path, qt_app):
    project = ProjectService.new(tmp_path, "Ansichtswechsel")
    panel = DocumentEditor()
    panel.bind(DocumentService(project))
    panel.show_card(project.project().id)
    panel.create_document("Anleitung")
    panel.resize(850, 650)
    panel.show()
    qt_app.processEvents()
    yield panel
    panel.dirty = False
    panel.close()
    panel.deleteLater()
    qt_app.processEvents()
    project.catalog.close()


def switch(panel, mode, qt_app):
    button = panel.findChild(QPushButton, "markdown_mode_" + mode)
    QTest.mouseClick(button, Qt.LeftButton)
    qt_app.processEvents()
    assert button.isChecked()
    assert panel.editor.mode == mode


@pytest.mark.parametrize("source", [
    "# Titel 🧩\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n```python\nprint('x')\n```\n",
    "# Unverändert\r\n\r\n[Link][ref]\r\n\r\n[ref]: https://example.org\r\n",
    "",
])
def test_switches_preserve_exact_saved_source_without_new_revisions(documents, qt_app, source):
    documents.editor.setPlainText(source)
    assert documents.save()
    before = documents.service.catalog.export_snapshot()
    signals = []
    documents.editor.textChanged.connect(lambda: signals.append(True))
    for _ in range(3):
        switch(documents, "code", qt_app)
        assert documents.editor.code_source.isVisible()
        documents.documents.setFocus()
        qt_app.processEvents()
        assert documents.editor.mode == "code"  # Focus loss must not switch back to MD.
        switch(documents, "md", qt_app)
        assert documents.editor.scroll.isVisible()
        assert documents.editor.active is None
    assert documents.editor.toPlainText() == source
    assert not signals and not documents.dirty
    assert documents.service.catalog.export_snapshot() == before


def test_inline_and_code_drafts_share_history_save_and_reopen(documents, qt_app):
    editor = documents.editor
    original = "# Titel\n\nAlter Text\n"
    editor.setPlainText(original)
    documents.save()
    editor.activate(editor.blocks[0])
    editor.active.source.setPlainText("## Neuer Titel\n\n")
    inline = editor.toPlainText()
    switch(documents, "code", qt_app)
    assert documents.dirty and editor.code_source.toPlainText() == inline
    editor.code_source.appendPlainText("- Neue Idee 🧩")
    changed = editor.toPlainText()
    switch(documents, "md", qt_app)
    assert "Neue Idee" in "".join(block.view.toPlainText() for block in editor.blocks)
    editor.undo()
    assert editor.toPlainText() == inline
    switch(documents, "code", qt_app)
    QTest.keyClick(editor.code_source, Qt.Key_Z, Qt.ControlModifier)
    assert editor.toPlainText() == original
    QTest.keyClick(editor.code_source, Qt.Key_Z, Qt.ControlModifier | Qt.ShiftModifier)
    editor.redo()
    assert editor.toPlainText() == changed and documents.dirty
    assert documents.save()
    assert editor.mode == "code" and not documents.dirty
    identifier = documents.current.id
    reopened = ProjectService.open(documents.service.catalog.path.parent)
    try:
        assert reopened.catalog.get(identifier).data["body"] == changed
    finally:
        reopened.catalog.close()
    second = documents.service.create(documents.owner_id, "Zweite", "Andere Quelle",
                                      template="Dokumentation")
    documents.open_document(second.id)
    assert editor.mode == "code" and editor.code_source.toPlainText() == "Andere Quelle"


def test_context_source_mode_templates_and_generated_readonly(documents, qt_app):
    editor = documents.editor
    menu = editor.context_menu()
    next(a for a in menu.actions() if a.objectName() == "markdown_full_source").trigger()
    qt_app.processEvents()
    assert editor.mode == "code"
    assert documents.findChild(QPushButton, "markdown_mode_code").isChecked()
    editor.insert_template("table")
    assert "| Spalte 1" in editor.code_source.toPlainText()
    assert editor.mode == "code"
    menu.deleteLater()
    documents.save()
    report = documents.service.create(documents.owner_id, "Bericht", "# Bericht", generated=True)
    documents.open_document(report.id)
    assert editor.isReadOnly() and editor.code_source.isReadOnly()
    before = documents.service.catalog.export_snapshot()
    QTest.keyClicks(editor.code_source, "Nicht schreiben")
    editor.insert_template("code")
    editor.undo()
    switch(documents, "md", qt_app)
    switch(documents, "code", qt_app)
    assert editor.toPlainText() == "# Bericht" and not documents.dirty
    assert documents.service.catalog.export_snapshot() == before


def test_code_draft_cancel_and_revision_conflict_survive_mode_switch(
        documents, qt_app, monkeypatch):
    switch(documents, "code", qt_app)
    documents.editor.code_source.setPlainText("Mein Entwurf")
    other = documents.service.create(documents.owner_id, "Andere", template="Dokumentation")
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Cancel)
    assert not documents.open_document(other.id)
    current = documents.current
    documents.service.save(current.id, "Parallel gespeichert", current.revision_no)
    errors = []
    monkeypatch.setattr("etherfood_studio.ui.documents.editor.show_error",
                        lambda parent, error: errors.append(error.code))
    switch(documents, "md", qt_app)
    assert not documents.save() and errors == ["conflict"]
    switch(documents, "code", qt_app)
    assert documents.dirty and documents.editor.code_source.toPlainText() == "Mein Entwurf"
