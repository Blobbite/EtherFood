"""Real table/header, checkbox, heading and document-width interactions."""

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLineEdit

from etherfood_studio.ui.documents.live_markdown import LiveMarkdownEditor
from etherfood_studio.ui.documents.markdown_source import MarkdownTable

SOURCE = ("# Titel\n\nUnverändert 🧩\n\n| Name | Wert |\n| :--- | ---: |\n"
          "| a \\| b | 16 |\n| **Zwei** | [Link][ref] |\n\n"
          "- [ ] Erstes To-do\n  - [x] Kind\n- normale Liste\n\n"
          "```md\n- [ ] Nicht ändern\n```\n\n[ref]: https://example.org\n")


@pytest.fixture
def editor(qt_app):
    widget = LiveMarkdownEditor()
    widget.resize(1200, 950)
    widget.setPlainText(SOURCE)
    widget.show()
    qt_app.processEvents()
    yield widget
    widget.close()
    widget.deleteLater()
    qt_app.processEvents()


def table_block(editor):
    return next(block for block in editor.blocks if block.table_editor is not None)


def test_native_cell_edit_and_structural_operations_share_source_history(editor, qt_app):
    block = table_block(editor)
    widget = block.table_editor
    table = widget.table
    original_start, original_end = block.start, block.end
    table.setCurrentCell(1, 1)
    table.editItem(table.item(1, 1))
    field = table.findChild(QLineEdit)
    assert field is not None
    field.selectAll()
    QTest.keyClicks(field, "20|30")
    QTest.keyClick(field, Qt.Key_Return)
    qt_app.processEvents()
    assert "20\\|30" in editor.toPlainText()
    assert editor.toPlainText()[:block.start] == SOURCE[:original_start]
    assert editor.toPlainText()[block.end:] == SOURCE[original_end:]
    table.horizontalHeader().moveSection(0, 1)
    table.verticalHeader().moveSection(1, 2)
    assert widget.model.rows[0] == [" Wert ", " Name "]
    assert widget.model.rows[1] == [" [Link][ref] ", " **Zwei** "]
    assert widget.model.separators == [" ---: ", " :--- "]
    QTest.mouseClick(widget.add_column, Qt.LeftButton)
    assert table.columnCount() == 3 and widget.model.rows[0][-1] == " "
    QTest.mouseClick(widget.add_row, Qt.LeftButton)
    assert table.rowCount() == 4
    header = table.horizontalHeader()
    QTest.mouseClick(header.viewport(), Qt.LeftButton,
                     pos=QPoint(header.sectionViewportPosition(1) + 30, 10))
    assert widget.removal_allowed("column")
    QTest.keyClick(table, Qt.Key_Delete)
    assert table.columnCount() == 2
    header = table.verticalHeader()
    QTest.mouseClick(header.viewport(), Qt.LeftButton,
                     pos=QPoint(5, header.sectionViewportPosition(1) + 12))
    QTest.keyClick(table, Qt.Key_Backspace)
    assert table.rowCount() == 3
    changed = editor.toPlainText()
    editor.set_mode("code")
    assert editor.code_source.toPlainText() == changed
    editor.set_mode("md")
    table = table_block(editor).table_editor.table
    QTest.keyClick(table, Qt.Key_Z, Qt.ControlModifier)
    assert table_block(editor).table_editor.table.rowCount() == 4
    editor.redo()
    assert editor.toPlainText() == changed
    while editor._undo:
        editor.undo()
    assert editor.toPlainText() == SOURCE


def test_header_plus_controls_and_readonly_table(editor, qt_app):
    widget = table_block(editor).table_editor
    table = widget.table
    header = table.horizontalHeader()
    table.setFocus()
    qt_app.processEvents()
    point = QPoint(header.sectionViewportPosition(0) + header.sectionSize(0) - 11,
                   header.height() // 2)
    QTest.mouseClick(header.viewport(), Qt.LeftButton, pos=point)
    assert table.columnCount() == 3 and widget.model.rows[0][1] == " "
    vertical = table.verticalHeader()
    point = QPoint(vertical.width() - 11, vertical.sectionViewportPosition(1)
                   + vertical.sectionSize(1) // 2)
    QTest.mouseClick(vertical.viewport(), Qt.LeftButton, pos=point)
    assert table.rowCount() == 4
    editor.setReadOnly(True)
    before = editor.toPlainText()
    QTest.mouseClick(header.viewport(), Qt.LeftButton, pos=QPoint(30, 10))
    widget.insert_column()
    widget.insert_row()
    widget.remove_rows()
    assert not widget.add_row.isEnabled() and not widget.add_column.isEnabled()
    assert editor.toPlainText() == before


def test_checkboxes_toggle_exact_marker_excluding_fences_and_readonly(editor, qt_app):
    block = next(block for block in editor.blocks if block.view.checkboxes)
    assert len(block.view.checkboxes) == 2
    checkbox = block.view.checkboxes[0][0]
    QTest.mouseClick(checkbox, Qt.LeftButton)
    assert editor.toPlainText() == SOURCE.replace("- [ ] Erstes", "- [x] Erstes")
    assert editor.active is None and checkbox.isChecked()
    QTest.mouseClick(block.view.checkboxes[1][0], Qt.LeftButton)
    changed = editor.toPlainText()
    assert "  - [ ] Kind" in changed
    assert "```md\n- [ ] Nicht ändern\n```" in changed
    editor.setReadOnly(True)
    assert not checkbox.isEnabled()
    QTest.mouseClick(checkbox, Qt.LeftButton)
    assert editor.toPlainText() == changed
    editor.setReadOnly(False)
    editor.undo()
    assert "  - [x] Kind" in editor.toPlainText()
    editor.undo()
    assert editor.toPlainText() == SOURCE
    editor.set_mode("code")
    editor.redo()
    assert "- [x] Erstes" in editor.code_source.toPlainText()


def test_heading_activation_does_not_expand_blank_separator_lines(editor, qt_app):
    block = editor.blocks[0]
    height = block.height()
    editor.activate(block)
    qt_app.processEvents()
    assert block.height() <= height + 20
    assert block.source.toPlainText() == "# Titel\n\n"
    assert editor.toPlainText() == SOURCE


def test_alignment_keeps_full_surface_and_only_moves_rendered_content(editor, qt_app):
    assert len(editor.alignment_buttons.buttons()) == 3
    for alignment in ("left", "center", "right"):
        button = next(button for button in editor.alignment_buttons.buttons()
                      if button.objectName() == "document_align_" + alignment)
        QTest.mouseClick(button, Qt.LeftButton)
        qt_app.processEvents()
        assert button.isChecked()
        rect = editor.surface_widget.geometry()
        assert rect.left() < 5 and rect.width() > 1100
        expected = {"left": Qt.AlignLeft, "center": Qt.AlignHCenter,
                    "right": Qt.AlignRight}[alignment]
        assert editor.blocks[0].view.document().begin().blockFormat().alignment() == expected
        assert table_block(editor).table_editor.model.separators == [" :--- ", " ---: "]
        assert editor.toPlainText() == SOURCE and not editor._undo


def test_table_source_roundtrip_handles_no_body_rows(editor):
    editor.setPlainText("| A | B |\n|---|---|")
    widget = table_block(editor).table_editor
    assert widget.table.rowCount() == 1
    widget.insert_row()
    assert MarkdownTable.parse(editor.toPlainText()).rows == [[" A ", " B "], [" ", " "]]


def test_checkbox_after_crlf_and_emoji_preserves_exact_bytes(editor):
    source = "- [ ] 🧩 Eins\r\n  - [X] Zwei\r\n\r\nUnberührt\r\n"
    editor.setPlainText(source)
    checkbox = editor.blocks[0].view.checkboxes[1][0]
    QTest.mouseClick(checkbox, Qt.LeftButton)
    assert editor.toPlainText() == source.replace("[X]", "[ ]")


def test_heading_to_table_focus_does_not_destroy_new_cell_editor(editor, qt_app):
    heading = editor.blocks[0]
    editor.activate(heading)
    heading.source.setPlainText("# Neuer Titel\n\n")
    block = table_block(editor)
    table = block.table_editor.table
    table.setFocus()
    table.setCurrentCell(1, 1)
    table.editItem(table.item(1, 1))
    qt_app.processEvents()
    assert table_block(editor) is block
    field = table.findChild(QLineEdit)
    assert field is not None and field.isVisible()
    field.selectAll()
    QTest.keyClicks(field, "24")
    QTest.keyClick(field, Qt.Key_Return)
    table.setFocus()
    QTest.keyPress(table, Qt.Key_Control)
    assert table.hasFocus()
    QTest.keyRelease(table, Qt.Key_Control)
    assert editor.toPlainText().startswith("# Neuer Titel\n\n")
    assert "| a \\| b | 24 |" in editor.toPlainText()
