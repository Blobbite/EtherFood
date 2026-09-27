"""Real Qt smoke and editing journeys; no human visual approval is implied."""

import json
from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtWidgets", reason="GUI-Abhängigkeiten fehlen")

from PySide6.QtCore import QPoint, QSettings, Qt, QTimer, QUrl
from PySide6.QtGui import QAction
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication, QDialogButtonBox, QLineEdit, QMessageBox, QPushButton,
)

from etherfood_studio.application.issue_service import IssueService
from etherfood_studio.domain.models import StudioError
from etherfood_studio.ui.documents.editor import SafePreview
from etherfood_studio.ui.main_window import MainWindow
from etherfood_studio.ui.project_dialog import ProjectDialog


@pytest.fixture
def window(tmp_path, qt_app):
    settings = QSettings(str(tmp_path / "preferences.ini"), QSettings.Format.IniFormat)
    value = MainWindow(settings)
    value.show()
    qt_app.processEvents()
    yield value
    value.documents.dirty = False
    value.close()
    qt_app.processEvents()


def create_project(window, tmp_path):
    root = tmp_path / "Demo Grün #1 100%"
    root.mkdir()
    assert window.new_project(root, "GUI-Prüfung")
    return root


def test_create_save_keyboard_and_reopen(window, tmp_path, qt_app):
    root = create_project(window, tmp_path)
    ids = window.project.demo()
    window.refresh()
    window.select_card(ids["one"])
    window.tabs.setCurrentWidget(window.documents)
    record = window.documents.create_document("Testnotiz")
    editor = window.documents.editor
    editor.setFocus()
    QTest.keyClick(editor, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    QTest.keyClicks(editor, "# GUI smoke")
    QTest.keyClick(editor, Qt.Key.Key_Return)
    QTest.keyClicks(editor, "Saved from keyboard")
    assert window.documents.dirty
    QTest.mouseClick(window.findChild(QPushButton, "save_document"), Qt.MouseButton.LeftButton)
    assert not window.documents.dirty
    assert "Saved from keyboard" in window.project.catalog.get(record.id).data["body"]
    window.open_project(root)
    window.select_card(ids["one"])
    assert "Saved from keyboard" in window.documents.editor.toPlainText()
    assert window.documents.current.id == record.id
    assert str(root) in window.settings.value("recent_projects")


def test_unsaved_cancel_discard_and_conflict(window, tmp_path, monkeypatch):
    create_project(window, tmp_path)
    ids = window.project.demo()
    window.refresh()
    window.select_card(ids["one"])
    doc = window.documents.create_document("Nicht verlieren")
    window.documents.editor.setPlainText("Ungespeichert")
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Cancel)
    window.select_card(ids["two"])
    assert window.selected_id == ids["one"]
    assert window.documents.editor.toPlainText() == "Ungespeichert"
    errors = []
    monkeypatch.setattr("etherfood_studio.ui.documents.editor.show_error",
                        lambda p, e: errors.append(e))
    window.documents.service.save(doc.id, "Parallel geändert", doc.revision_no)
    assert window.documents.save() is False
    assert errors[0].code == "conflict"
    assert window.documents.dirty
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Discard)
    window.select_card(ids["two"])
    assert window.selected_id == ids["two"]


def test_canvas_collapse_move_links_undo_and_reload(window, tmp_path, qt_app):
    root = create_project(window, tmp_path)
    ids = window.project.demo()
    window.refresh()
    original = window.project.catalog.get(ids["hero"])
    window.toggle_card(ids["act"])
    assert ids["one"] not in window.canvas.items_by_id
    window.toggle_card(ids["act"])
    assert ids["one"] in window.canvas.items_by_id
    before_edges = window.project.catalog.relations()
    window.move_card(ids["hero"], 88, 144)
    assert window.project.catalog.get(ids["hero"]) == original
    assert window.project.catalog.relations() == before_edges
    window.undo(False)
    assert window.project.catalog.layout(ids["hero"]) == {}
    window.undo(True)
    window.select_card(ids["temple"])
    window.relation_target.setCurrentIndex(window.relation_target.findData(ids["hero"]))
    QTest.mouseClick(window.findChild(QPushButton, "add_relation"), Qt.MouseButton.LeftButton)
    qt_app.processEvents()
    edge_count = len(window.project.catalog.relations())
    window.undo(False)
    assert len(window.project.catalog.relations()) == edge_count - 1
    window.undo(True)
    window.open_project(root)
    assert window.project.catalog.layout(ids["hero"])["x"] == 88
    assert len(window.project.catalog.relations()) == edge_count
    assert len(window.canvas.items_by_id) == len(window.project.cards())


def test_safe_preview_markdown_import_and_generated_report(window, tmp_path, monkeypatch):
    create_project(window, tmp_path)
    owner = window.project.project().id
    source = tmp_path / "README.md"
    body = ('<script>alert(1)</script>\n\n![secret](file:///etc/passwd)\n\n'
            '![x](https://invalid.test/x)')
    source.write_text(body)
    record = window.documents.import_file(source)
    assert source.read_text() == body
    assert window.project.catalog.get(record.id).data["provenance"]["original_name"] == "README.md"
    preview = window.documents.preview
    assert preview.loadResource(2, QUrl("file:///etc/passwd")).isEmpty()
    assert preview.loadResource(2, QUrl("https://invalid.test/x")).isEmpty()
    assert "<script>" not in preview.document().toHtml()
    report = window.documents.service.create(owner, "Bericht", "Technisch offen", generated=True)
    window.documents.refresh_documents(report.id)
    assert window.documents.editor.isReadOnly()
    assert not window.documents.save_button.isEnabled()
    assert window.project.catalog.get(record.id).data["body"] == body


def test_search_filters_focus_and_preserve_ids(window, tmp_path, qt_app):
    create_project(window, tmp_path)
    ids = window.project.demo()
    window.refresh()
    task = IssueService(window.project).create(ids["one"], "Suchen", "Text", issue=True)
    window.tabs.setCurrentWidget(window.search)
    QTest.keyClicks(window.search.query, "Suchen")
    qt_app.processEvents()
    assert window.search.results.count() == 1
    item = window.search.results.item(0)
    QTest.mouseClick(window.search.results.viewport(), Qt.MouseButton.LeftButton,
                     pos=window.search.results.visualItemRect(item).center())
    assert window.selected_id == ids["one"]
    window.project.rename(ids["one"], "Umbenannt",
                          window.project.catalog.get(ids["one"]).revision_no)
    window.search.refresh_scopes()
    assert window.project.catalog.get(task.id).owner_id == ids["one"]
    window.search.state.setCurrentIndex(window.search.state.findData("done"))
    assert window.search.results.count() == 0


def test_corrupt_project_missing_drive_and_broken_preview(window, tmp_path, monkeypatch):
    root = create_project(window, tmp_path)
    identifier = window.project.project().id
    config = root / "project.studio-local.json"
    data = json.loads(config.read_text())
    data["roots"]["VERSIONS_ROOT"] = str(tmp_path / "missing-usb")
    config.write_text(json.dumps(data))
    window.open_project(root)
    assert "VERSIONS_ROOT" in window.root_notice.text()
    assert window.project.project().id == identifier
    assert json.loads(config.read_text()) == data
    other = tmp_path / "bad"
    other.mkdir()
    (other / "project.studio-local.json").write_text(json.dumps({
        "schema_version": 1, "roots": {"WORKSPACE_ROOT": str(other)},
    }))
    (other / "project.studio.sqlite").write_text("broken")
    with pytest.raises(StudioError):
        window.open_project(other)
    assert window.project.project().id == identifier

    def fail(text):
        raise ValueError("broken preview")

    monkeypatch.setattr(window.documents.preview, "preview", fail)
    window.documents.create_document("Vorschaufehler")
    assert window.tree.topLevelItemCount() == 1
    assert "nicht verfügbar" in window.documents.preview.toPlainText()


def test_controls_and_manual_layout_are_real(window, tmp_path):
    create_project(window, tmp_path)
    ids = window.project.demo()
    window.refresh()
    window.move_card(ids["hero"], 72, 94)
    window.auto_layout()
    window.restore_layout()
    assert window.project.catalog.layout(ids["hero"])["x"] == 72
    assert window.findChild(QAction, "undo").isEnabled()
    disabled = [a for a in window.findChildren(QAction) if "später" in a.text()]
    assert len(disabled) == 2 and all(not a.isEnabled() for a in disabled)
    assert window.findChild(QPushButton, "add_act") is not None


def test_project_dialog_actual_buttons(window, tmp_path, qt_app):
    root = tmp_path / "dialog-project"
    root.mkdir()
    captured = []

    def fill_dialog():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, ProjectDialog)
        captured.append(dialog.objectName())
        name = dialog.findChild(QLineEdit, "new_project_name")
        QTest.keyClicks(name, "Dialog smoke")
        dialog.findChild(QLineEdit, "root_workspace_root").setText(str(root))
        buttons = dialog.findChild(QDialogButtonBox)
        QTest.mouseClick(buttons.button(QDialogButtonBox.StandardButton.Ok),
                         Qt.MouseButton.LeftButton)

    QTimer.singleShot(0, fill_dialog)
    window.findChild(QAction, "new_project").trigger()
    assert captured == ["new_project_dialog"]
    assert window.project.project().title == "Dialog smoke"
    assert (root / "project.studio.sqlite").is_file()


def test_two_tree_references_open_same_asset(window, tmp_path, qt_app):
    create_project(window, tmp_path)
    ids = window.project.demo()
    window.refresh()
    refs = [item for item in window.tree.findItems(
        "↪", Qt.MatchFlag.MatchStartsWith | Qt.MatchFlag.MatchRecursive,
    ) if item.data(0, Qt.ItemDataRole.UserRole) == ids["hero"]]
    assert len(refs) == 2
    for item in refs:
        window.tree.scrollToItem(item)
        qt_app.processEvents()
        QTest.mouseClick(window.tree.viewport(), Qt.MouseButton.LeftButton,
                         pos=window.tree.visualItemRect(item).center())
        assert window.selected_id == ids["hero"]
        assert window.documents.owner_id == ids["hero"]
        assert ids["hero"] in window.details.toPlainText()


def test_actual_drag_and_view_size_do_not_change_asset(window, tmp_path, qt_app):
    create_project(window, tmp_path)
    ids = window.project.demo()
    window.refresh()
    window.select_card(ids["hero"])
    qt_app.processEvents()
    before = window.project.catalog.get(ids["hero"])
    item = window.canvas.items_by_id[ids["hero"]]
    original = item.pos()
    start = window.canvas.mapFromScene(item.sceneBoundingRect().center())
    QTest.mousePress(window.canvas.viewport(), Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(window.canvas.viewport(), start + QPoint(45, 30), 20)
    QTest.mouseRelease(window.canvas.viewport(), Qt.MouseButton.LeftButton,
                       pos=start + QPoint(45, 30))
    qt_app.processEvents()
    layout = window.project.catalog.layout(ids["hero"])
    assert (layout["x"], layout["y"]) != (original.x(), original.y())
    window.card_width.setValue(420)
    window.card_height.setValue(130)
    QTest.mouseClick(window.findChild(QPushButton, "resize_card"), Qt.MouseButton.LeftButton)
    assert window.project.catalog.layout(ids["hero"])["w"] == 420
    assert window.project.catalog.get(ids["hero"]) == before


def test_save_choice_before_switch_and_safe_attachment(window, tmp_path, monkeypatch):
    create_project(window, tmp_path)
    ids = window.project.demo()
    window.refresh()
    window.select_card(ids["one"])
    doc = window.documents.create_document("Speichern vor Wechsel")
    window.documents.editor.setPlainText("Behalten")
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Save)
    window.select_card(ids["two"])
    assert window.project.catalog.get(doc.id).data["body"] == "Behalten"
    window.select_card(ids["one"])
    source = tmp_path / "script.sh"
    source.write_text("exit 123\n")
    current = window.documents.current
    window.documents.service.attach(current.id, source, current.revision_no)
    assert "deaktiviert" in window.documents.service.attachment_text(current.id, 0)
    assert source.read_text() == "exit 123\n"
