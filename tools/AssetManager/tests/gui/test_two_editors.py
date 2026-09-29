"""Real Qt navigation, explicit definition editing, shared geometry and draft preservation."""

from pathlib import Path
import pytest

from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QMessageBox

from etherfood_studio.ui.main_window import MainWindow
from etherfood_studio.application.workspace_files import WorkspaceFiles
from etherfood_studio.ui.settings import SettingsDialog


@pytest.fixture
def window(qt_app, tmp_path):
    root = tmp_path / "Projekt"
    root.mkdir()
    window = MainWindow(QSettings(str(tmp_path / "ui.ini"), QSettings.IniFormat))
    window.new_project(root, "Oberflächenprüfung")
    window.processing.controller.debounce.stop()
    window.show()
    qt_app.processEvents()
    yield window
    window.processing.controller.stop()
    if window.processing.python.current:
        window.processing.python.editor.document().setModified(False)
    window.close()
    window.deleteLater()
    qt_app.processEvents()


def test_exact_navigation_no_old_panel_and_empty_workspace(window, qt_app):
    assert [window.main_navigation.item(i).text() for i in range(2)] == [
        "Projekt",
        "Skripte & Pipelines",
    ]
    assert window.main_navigation.count() == 2
    names = {
        child.objectName() for child in window.findChildren(__import__("PySide6").QtCore.QObject)
    }
    assert not names & {"card_properties", "jobs_dialog", "start_page", "processing_workspace"}
    assert not window.godot_button.isEnabled()
    assert window.godot_button.geometry().right() < window.settings_button.geometry().left()
    bounds = window.section_navigation.geometry()
    for size in ((1100, 700), (1500, 960)):
        window.resize(*size)
        qt_app.processEvents()
        for area, count in ((1, 3), (0, 5)):
            window.set_main_editor(area)
            qt_app.processEvents()
            assert window.section_navigation.count() == count
            assert window.section_navigation.x() == bounds.x()
            assert window.section_navigation.width() == bounds.width()
            assert window.workspace_stack.width() >= 300
    assert window.processing.service.scripts() == window.processing.service.definitions() == []
    settings = SettingsDialog(window)
    assert [settings.categories.item(i).text() for i in range(2)] == ["Darstellung", "Tests"]
    assert not settings.categories.item(0).icon().isNull()
    settings.deleteLater()


def test_pipeline_doubleclick_stays_project_explicit_menu_opens_definition(window, qt_app):
    definition = WorkspaceFiles(window.project).create_definition("Geteilte Pipeline")
    usage = window.processing.service.use(definition.id, [window.project.project().id])
    window.refresh()
    window.canvas.focus_card(usage.id)
    item = window.canvas.items_by_id[usage.id]
    point = window.canvas.mapFromScene(item.sceneBoundingRect().center())
    QTest.mouseDClick(window.canvas.viewport(), Qt.LeftButton, pos=point)
    qt_app.processEvents()
    assert window.main_navigation.currentRow() == 0
    menu = window.navigation.menu(usage.id)
    action = next(a for a in menu.actions() if a.text() == "Pipeline bearbeiten")
    action.trigger()
    qt_app.processEvents()
    assert window.main_navigation.currentRow() == 1
    assert window.processing.editor.current.id == definition.id
    assert menu.actions()[-2].text() == "Archivieren …"
    assert menu.actions()[-1].text() == "Entfernen …"
    menu.deleteLater()


def test_python_draft_position_and_undo_survive_main_switch(window, qt_app):
    script = WorkspaceFiles(window.project).create_script("Entwurf")
    window.processing.open_script(script.id)
    editor = window.processing.python.editor
    editor.moveCursor(QTextCursor.MoveOperation.End)
    editor.insertPlainText("\n# ungespeicherter Text")
    raw = WorkspaceFiles(window.project).read(script.id)[0]
    before = editor.toPlainText()
    position = editor.textCursor().position()
    window.set_main_editor(0)
    window.canvas.zoom(1.15)
    zoom = window.canvas.transform().m11()
    window.set_main_editor(1)
    assert window.processing.pages.currentIndex() == 1
    assert editor.toPlainText() == before
    assert editor.textCursor().position() == position
    assert WorkspaceFiles(window.project).read(script.id)[0] == raw
    window.undo(False)
    assert "ungespeicherter Text" not in editor.toPlainText()
    window.undo(True)
    assert editor.toPlainText() == before
    assert window.processing.python.save()
    window.set_main_editor(0)
    assert window.canvas.transform().m11() == zoom


def test_actual_check_approval_and_unsaved_usage_guard(window, qt_app, monkeypatch):
    from test_pipeline_workspace import passthrough
    from test_pipeline_automation import wait_until
    from PySide6.QtWidgets import QPushButton

    script, definition = passthrough(window.project)
    workspace = window.processing
    window.set_main_editor(1)
    workspace.refresh()
    workspace.overview.selectRow(0)
    QTest.mouseClick(workspace.findChild(QPushButton, "pipeline_check_selected"), Qt.LeftButton)
    wait_until(lambda: not workspace.controller.busy)
    assert workspace.service.status(definition.id)[0] == "yellow"
    assert workspace.service.state(definition.id)["approved_hash"] is None
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Cancel)
    workspace.approve_selected()
    assert workspace.service.state(definition.id)["approved_hash"] is None
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    workspace.approve_selected()
    assert workspace.service.status(definition.id)[0] == "green"
    usage = workspace.service.use(definition.id)
    window.set_main_editor(0)
    window.usage_editor.open(usage.id)
    item = window.usage_editor.targets.item(0)
    item.setCheckState(Qt.Checked)
    assert window.usage_editor.dirty
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Cancel)
    window.usage_editor.close_editor()
    assert window.usage_editor.isVisible() and window.usage_editor.dirty
    assert not window.project.catalog.get(usage.id).data["targets"]
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Discard)
    window.usage_editor.close_editor()
    assert not window.usage_editor.dirty


def test_external_python_reload_cancel_preserves_draft_and_helper_edit(window, qt_app, monkeypatch):
    files = WorkspaceFiles(window.project)
    script = files.create_script("Datei", code=b"\xef\xbb\xbf# Original\n")
    script = files.helper(script.id, "helper.py", b"value = 1\n")
    window.processing.open_script(script.id)
    python = window.processing.python
    python.editor.insertPlainText("# Entwurf\n")
    draft = python.editor.toPlainText()
    files.path(script).write_bytes(b"\xef\xbb\xbf# Extern\n")
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.Cancel)
    python.reload()
    assert python.editor.toPlainText() == draft
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.Discard)
    python.reload()
    assert python.editor.toPlainText() == "# Extern\n"
    python.editor.moveCursor(QTextCursor.End)
    python.editor.insertPlainText("# App\n")
    assert python.save()
    assert files.read(script.id)[0] == b"\xef\xbb\xbf# Extern\n# App\n"
    assert python.open_helper(script.id, "helper.py")
    python.editor.setPlainText("value = 2\n")
    python.editor.document().setModified(True)
    assert python.save()
    assert files.script_files(script.id)["helper.py"] == b"value = 2\n"
