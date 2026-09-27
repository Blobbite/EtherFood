"""Quiet table chrome, responsive text and full-width content alignment."""

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractButton

from etherfood_studio.ui.appearance import appearance
from etherfood_studio.ui.documents.live_markdown import LiveMarkdownEditor

SOURCE = ("# Titel\n\nText unverändert.\n\n| Name | Beschreibung |\n|:---|---:|\n"
          "| **SW** | Lange Beschreibung mit genug Worten für einen Umbruch bei schmalem "
          "Fenster und viel Platz bei einem großen Fenster. |\n|SO|Kurz|\n\n"
          "- [ ] Prüfung\n\n```py\nprint('unverändert')\n```\n")


@pytest.fixture
def editor(qt_app, tmp_path):
    manager = appearance()
    previous = manager.settings
    manager.configure(QSettings(str(tmp_path / "preferences.ini"), QSettings.IniFormat))
    widget = LiveMarkdownEditor()
    widget.resize(1200, 950)
    widget.setPlainText(SOURCE)
    widget.show()
    QTest.qWait(20)
    yield widget
    widget.close()
    widget.deleteLater()
    qt_app.processEvents()
    manager.settings = previous


def table_widget(editor):
    return next(block.table_editor for block in editor.blocks if block.table_editor)


def test_table_handles_appear_on_hover_or_focus_without_changing_layout_or_source(editor, qt_app):
    widget = table_widget(editor)
    table = widget.table
    outside = editor.mode_buttons.buttons()[0]
    outside.setFocus()
    QTest.mouseMove(outside)
    qt_app.processEvents()
    bounds = table.geometry()
    assert not widget.add_row.isVisible() and not widget.add_column.isVisible()
    assert not table.horizontalHeader().controls_visible
    assert {button.text() for button in widget.findChildren(QAbstractButton)
            if button.objectName().startswith("markdown_")} == {"+"}
    for orientation, count in ((Qt.Horizontal, table.columnCount()),
                               (Qt.Vertical, table.rowCount())):
        assert all(table.model().headerData(i, orientation) == "" for i in range(count))
        assert all(table.model().headerData(i, orientation, Qt.AccessibleTextRole)
                   for i in range(count))
    QTest.mouseMove(table.viewport(), QPoint(40, 30))
    qt_app.processEvents()
    assert widget.add_row.isVisible() and widget.add_column.isVisible()
    assert table.horizontalHeader().controls_visible
    assert table.geometry() == bounds
    QTest.mouseMove(outside)
    qt_app.processEvents()
    assert not widget.add_row.isVisible()
    table.setFocus()
    qt_app.processEvents()
    assert widget.add_row.isVisible()
    assert table.geometry() == bounds
    assert editor.toPlainText() == SOURCE and not editor._undo


def test_columns_fill_available_width_and_long_cells_wrap_without_clipping(editor):
    table = table_widget(editor).table
    wide_height = table.rowHeight(1)
    assert sum(table.columnWidth(i) for i in range(table.columnCount())) >= table.viewport().width()
    editor.resize(580, 950)
    QTest.qWait(30)
    assert table.rowHeight(1) > wide_height
    assert table.rowHeight(1) >= table.sizeHintForRow(1)
    assert table.horizontalScrollBar().maximum() == 0
    editor.resize(1200, 950)
    QTest.qWait(30)
    assert table.rowHeight(1) == wide_height
    assert editor.toPlainText() == SOURCE and not editor._undo


def test_many_columns_scroll_without_squeezing_cells(editor):
    editor.setPlainText("|" + " A |" * 12 + "\n|" + "---|" * 12 + "\n|" + " x |" * 12)
    QTest.qWait(30)
    table = table_widget(editor).table
    assert min(table.columnWidth(i) for i in range(12)) >= 120
    assert table.horizontalScrollBar().maximum() > 0


def test_delete_requires_header_selection_and_context_actions_guard_structure(editor):
    widget = table_widget(editor)
    table = widget.table
    table.setCurrentCell(1, 1)
    QTest.keyClick(table, Qt.Key_Delete)
    assert editor.toPlainText() == SOURCE
    table.selectRow(0)
    widget.select_axis("row")
    QTest.keyClick(table, Qt.Key_Delete)
    assert editor.toPlainText() == SOURCE
    table.selectAll()
    assert not widget.removal_allowed("column")
    table.selectColumn(1)
    menu = widget.context_menu()
    action = next(action for action in menu.actions()
                  if action.objectName() == "markdown_delete_column")
    assert action.isEnabled()
    action.trigger()
    assert table.columnCount() == 1
    menu.deleteLater()
    table.selectColumn(0)
    assert not widget.removal_allowed("column")
    editor.undo()
    assert editor.toPlainText() == SOURCE


@pytest.mark.parametrize("alignment", ["left", "center", "right"])
def test_alignment_keeps_full_width_at_different_sizes_and_checkbox_hit_targets(editor, alignment):
    editor.set_alignment(alignment)
    for width in (580, 1200):
        editor.resize(width, 950)
        QTest.qWait(20)
        assert editor.surface_widget.width() >= width - 40
        assert editor.surface_widget.x() <= 4
    block = next(block for block in editor.blocks if block.view.checkboxes)
    checkbox = block.view.checkboxes[0][0]
    assert checkbox.isVisible() and block.view.viewport().rect().contains(checkbox.geometry())
    QTest.mouseClick(checkbox, Qt.LeftButton)
    assert editor.toPlainText() == SOURCE.replace("- [ ]", "- [x]")
    editor.undo()
    assert editor.toPlainText() == SOURCE
    code = editor.blocks[-1].view.document().begin()
    assert code.blockFormat().alignment() == Qt.AlignLeft
    editor.set_mode("code")
    assert editor.code_source.toPlainText() == SOURCE
    assert not editor._undo


def test_obsolete_full_width_preference_maps_to_left_without_source_changes(editor):
    settings = appearance().settings
    settings.setValue("appearance/document_alignment", "full")
    legacy = LiveMarkdownEditor()
    assert legacy.alignment == "left"
    assert len(legacy.alignment_buttons.buttons()) == 3
    legacy.set_alignment("right")
    restored = LiveMarkdownEditor()
    assert restored.alignment == "right"
    legacy.deleteLater()
    restored.deleteLater()
