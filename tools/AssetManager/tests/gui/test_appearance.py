"""Global presentation settings preserve drafts and survive a window restart."""

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialogButtonBox

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.ui.appearance import appearance
from etherfood_studio.ui.settings import SettingsDialog
from etherfood_studio.ui.asset_workspace import AssetWorkspace
from etherfood_studio.ui.main_window import MainWindow
from etherfood_studio.ui.presentation import kind_icon
from etherfood_studio.ui.theme import color


@pytest.fixture
def window(tmp_path, qt_app):
    prefs = QSettings(str(tmp_path / "appearance.ini"), QSettings.IniFormat)
    value = MainWindow(prefs)
    root = tmp_path / "project"
    root.mkdir()
    value.new_project(root, "Darstellungsprüfung")
    value.ids = value.project.demo()
    value.refresh()
    value.show()
    qt_app.processEvents()
    yield value
    value.documents.dirty = False
    for _, card in value.notes._cards():
        card.timer.stop()
        card.dirty = False
    value.close()
    value.deleteLater()
    qt_app.processEvents()
    appearance().set_preferences("light", "text_icons", persist=False)


def test_settings_button_stays_right_and_dialog_updates_all_button_modes(window, qt_app):
    window.resize(1050, 750)
    qt_app.processEvents()
    button = window.settings_button
    assert button.isVisible()
    assert button.mapTo(window, button.rect().topRight()).x() > window.width() - 30
    seen = []

    def configure():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, SettingsDialog)
        settings = dialog
        dialog = settings.appearance
        dialog.theme.setCurrentIndex(dialog.theme.findData("dark"))
        for mode in ("icons", "text", "text_icons"):
            dialog.buttons.setCurrentIndex(dialog.buttons.findData(mode))
            assert bool(button.text()) == (mode != "icons")
            assert button.icon().isNull() == (mode == "text")
            assert button.toolTip() == "Einstellungen"
            close = settings.findChild(QDialogButtonBox).buttons()[0]
            assert bool(close.text()) == (mode != "icons")
            assert close.icon().isNull() == (mode == "text")
            assert [window.main_navigation.item(i).text() for i in range(2)] == [
                "Projekt",
                "Skripte & Pipelines",
            ]
            assert settings.categories.count() == 2
            assert all(not settings.categories.item(i).icon().isNull() for i in range(2))
        seen.append(appearance().theme)
        settings.accept()

    QTimer.singleShot(20, configure)
    QTest.mouseClick(button, Qt.LeftButton)
    assert seen == ["dark"]
    assert qt_app.palette().color(QPalette.Base).name() == color("base")
    assert window.canvas.backgroundBrush().color().name() == color("canvas")
    for column in window.tasks.columns.values():
        assert column.viewport().palette().color(QPalette.Base).name() == color("base")
    assert window.tasks.detail_title.palette().color(QPalette.WindowText).name() == color("text")


def test_theme_changes_preserve_unsaved_note_document_and_board_positions(window, qt_app):
    window.documents.create_document("Entwurf")
    window.documents.editor.setPlainText("# Noch ungespeichert\n\nText")
    note = window.notes.editor
    note.editor.setPlainText("Offene Idee")
    note.timer.stop()
    window.canvas.zoom(1.15)
    scale = window.canvas.transform().m11()
    before = window.project.catalog.export_snapshot()
    positions = {key: card.pos() for key, card in window.canvas.items_by_id.items()}
    for theme in ("dark", "light", "dark"):
        appearance().set_preferences(theme, "icons")
        qt_app.processEvents()
        assert window.documents.dirty and note.dirty
        assert note.editor.toPlainText() == "Offene Idee"
        assert window.documents.editor.toPlainText() == "# Noch ungespeichert\n\nText"
        assert window.canvas.transform().m11() == scale
        assert {key: card.pos() for key, card in window.canvas.items_by_id.items()} == positions
        assert window.project.catalog.export_snapshot() == before
        foreground = note.editor.palette().color(QPalette.Text)
        background = note.editor.palette().color(QPalette.Base)
        assert abs(foreground.lightnessF() - background.lightnessF()) > 0.4


def test_preferences_survive_new_window_and_apply_to_new_asset_dialog(window, qt_app):
    appearance().set_preferences("dark", "icons")
    window.documents.editor.set_alignment("center")
    assets = AssetService(window.project)
    asset = assets.asset(window.ids["hero"])
    assets.configure(asset.id, default_definition().to_data(), asset.revision_no)
    workspace = AssetWorkspace(assets, asset.id, window)
    workspace.show()
    assert workspace.documents.editor.alignment == "center"
    assert workspace.palette().color(QPalette.Base).name() == color("base")
    assert workspace.documents.editor.mode_buttons.buttons()[0].text() == ""
    workspace.reject()
    workspace.deleteLater()
    path = window.settings.fileName()
    restarted = MainWindow(QSettings(path, QSettings.IniFormat))
    assert appearance().theme == "dark" and appearance().buttons == "icons"
    assert restarted.documents.editor.alignment == "center"
    assert restarted.settings_button.text() == ""
    assert restarted.project_toolbar.toolButtonStyle() == Qt.ToolButtonIconOnly
    restarted.close()
    restarted.deleteLater()


def test_invalid_local_preferences_fall_back_to_readable_defaults(window):
    window.settings.setValue("appearance/theme", "invalid")
    window.settings.setValue("appearance/buttons", "invalid")
    appearance().configure(window.settings)
    assert appearance().theme == "light" and appearance().buttons == "text_icons"
    assert window.settings_button.text() == "Einstellungen"


def test_main_window_undo_from_table_never_undoes_canvas_layout(window, qt_app):
    owner = window.project.project().id
    window.commands.layout(owner, {"x": 123, "y": 45})
    before = window.project.catalog.layout(owner)
    window.documents.create_document("Tabelle")
    window.tabs.setCurrentWidget(window.documents)
    editor = window.documents.editor
    source = "| A | B |\n|---|---|\n|1|2|\n"
    editor.setPlainText(source)
    table = editor.blocks[0].table_editor.table
    table.item(1, 1).setText("3")
    window.activateWindow()
    table.setFocus()
    qt_app.processEvents()
    assert editor.hasFocus()
    window.undo(False)
    assert editor.toPlainText() == source
    assert window.project.catalog.layout(owner) == before
    assert len(window.commands.done) == 1


def test_theme_refreshes_existing_document_and_filter_icons_without_reloading_drafts(window):
    document = window.documents.create_document("Darstellung")
    window.documents.editor.setPlainText("# Ungespeicherter Entwurf")
    window.search.refresh()
    snapshot = window.project.catalog.export_snapshot()
    for theme in ("dark", "light"):
        appearance().set_preferences(theme, "icons")
        expected = kind_icon("document").pixmap(16, 16).toImage()
        assert window.documents.documents.currentData() == document.id
        assert window.documents.documents.itemIcon(0).pixmap(16, 16).toImage() == expected
        results = window.search.table
        found = next(
            results.item(index, 0)
            for index in range(results.rowCount())
            if results.item(index, 0).data(Qt.UserRole) == document.id
        )
        assert found.icon().pixmap(16, 16).toImage() == expected
        for panel in (window.tasks,):
            for index in range(panel.kind.count()):
                if kind := panel.kind.itemData(index):
                    assert panel.kind.itemIcon(index).pixmap(16, 16).toImage() \
                        == kind_icon(kind).pixmap(16, 16).toImage()
        assert window.documents.dirty
        assert window.documents.editor.toPlainText() == "# Ungespeicherter Entwurf"
        assert window.project.catalog.export_snapshot() == snapshot
