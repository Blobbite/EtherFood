"""Real Qt interactions for the dashboard review corrections."""

import pytest

QtWidgets = pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtCore import QPointF, QSettings, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QInputDialog, QMessageBox

from etherfood_studio.application.document_service import DocumentService
from etherfood_studio.application.issue_service import Finding, IssueService
from etherfood_studio.ui.main_window import MainWindow
from etherfood_studio.ui.asset_wizard import AssetWizard
from etherfood_studio.ui.tasks.editor import TaskEditor


@pytest.fixture
def window(qt_app, tmp_path):
    settings = QSettings(str(tmp_path / "preferences.ini"), QSettings.Format.IniFormat)
    result = MainWindow(settings)
    root = tmp_path / "project"
    root.mkdir()
    assert result.new_project(root, "Review")
    result.show()
    qt_app.processEvents()
    yield result
    result.documents.dirty = False
    result.notes.editor.dirty = False
    result.close()


def test_task_details_edit_conflict_cancel_and_save(window, qt_app, monkeypatch):
    service = IssueService(window.project)
    item = service.create(window.selected_id, "Issue", "Gespeicherte Beschreibung", issue=True,
                          finding=Finding(direction="SW", frame_index=0))
    window.tasks.show_record(item.id)
    window.tabs.setCurrentWidget(window.tasks)
    column = window.tasks.columns["open"]
    result = column.currentItem()
    QTest.mouseClick(column.viewport(), Qt.LeftButton,
                     pos=column.visualItemRect(result).center())
    assert "Gespeicherte Beschreibung" in window.tasks.details.toPlainText()
    assert "direction: SW" in window.tasks.details.toPlainText()
    editor = TaskEditor(service, item, window)
    editor.show()
    editor.body.setPlainText("Lokaler neuer Inhalt")
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Cancel)
    editor.reject()
    assert editor.isVisible() and editor.body.toPlainText() == "Lokaler neuer Inhalt"
    updated = service.update(item.id, item.title, "Anderer Bearbeiter", item.revision_no)
    errors = []
    monkeypatch.setattr("etherfood_studio.ui.tasks.editor.show_error",
                        lambda parent, error: errors.append(error))
    QTest.mouseClick(editor.buttons.button(QDialogButtonBox.Save), Qt.LeftButton)
    assert errors and editor.isVisible() and editor.body.toPlainText() == "Lokaler neuer Inhalt"
    assert service.catalog.get(item.id).data["body"] == "Anderer Bearbeiter"
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Discard)
    editor.reject()
    editor = TaskEditor(service, updated, window)
    editor.show()
    editor.body.setPlainText("Korrekt gespeichert")
    QTest.mouseClick(editor.buttons.button(QDialogButtonBox.Save), Qt.LeftButton)
    window.tasks.refresh()
    assert "Korrekt gespeichert" in window.tasks.details.toPlainText()
    assert window.tasks.selected_record.id == item.id


def test_search_document_open_preserves_unsaved_content(window, monkeypatch):
    service = DocumentService(window.project)
    first = window.documents.create_document("Erste Notiz")
    second = service.create(window.selected_id, "Zweites Dokument", "Zweiter Text",
                            template="Dokumentation")
    window.documents.editor.setPlainText("Ungespeichert")
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Cancel)
    window.open_document(second.id)
    assert window.documents.current.id == first.id
    assert window.documents.editor.toPlainText() == "Ungespeichert"
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Save)
    window.search.show_record(second.id)
    window.search.edit_current()
    assert service.catalog.get(first.id).data["body"] == "Ungespeichert"
    assert window.documents.current.id == second.id
    assert window.tabs.currentWidget() == window.documents


def arrange_demo(window, qt_app):
    ids = window.project.demo()
    for index, card in enumerate(window.project.cards()):
        window.project.catalog.save_layout(card.id, {
            "x": index % 3 * 310, "y": index // 3 * 170, "w": 220, "h": 100,
        })
    window.refresh()
    window.canvas.fitInView(window.canvas.sceneRect(), Qt.KeepAspectRatio)
    qt_app.processEvents()
    return ids


def drag(canvas, start, end, qt_app):
    first, last = canvas.mapFromScene(start), canvas.mapFromScene(end)
    QTest.mousePress(canvas.viewport(), Qt.LeftButton, pos=first)
    QTest.mouseMove(canvas.viewport(), (first + last) / 2, delay=10)
    QTest.mouseMove(canvas.viewport(), last, delay=10)
    QTest.mouseRelease(canvas.viewport(), Qt.LeftButton, pos=last)
    qt_app.processEvents()


def test_native_size_grip_and_live_labels(window, qt_app):
    ids = arrange_demo(window, qt_app)
    canvas = window.canvas
    item = canvas.items_by_id[ids["one"]]
    before = window.project.catalog.get(item.identifier).revision_no
    start = item.grip.scenePos() - QPointF(8, 8)
    drag(canvas, start, start + QPointF(50, 45), qt_app)
    layout = window.project.catalog.layout(ids["one"])
    assert layout["w"] > 250 and layout["h"] > 130
    assert window.project.catalog.get(ids["one"]).revision_no == before
    assert len(canvas.items_by_id[ids["one"]].ports) == 4
    for edge in canvas.edges_by_id.values():
        assert all(not edge.visible_stroke().intersects(other.caption.sceneBoundingRect())
                   for other in canvas.edges_by_id.values())
    for index, rect in enumerate(canvas.label_rects):
        assert not any(rect.intersects(other) for other in canvas.label_rects[index + 1:])
    window.undo(False)
    assert window.project.catalog.layout(ids["one"])["w"] == 220
    window.undo(True)
    assert window.project.catalog.layout(ids["one"])["w"] == layout["w"]


def test_port_drag_retarget_cancel_and_cycle(window, qt_app, monkeypatch):
    ids = arrange_demo(window, qt_app)
    canvas = window.canvas
    monkeypatch.setattr(QInputDialog, "getItem", lambda *a: ("Benötigt Voraussetzung", True))
    source = canvas.items_by_id[ids["one"]]
    target = canvas.items_by_id[ids["two"]]
    drag(canvas, source.ports["right"].scenePos(), target.scenePos() + QPointF(40, 40), qt_app)
    edge = next(row for row in window.project.catalog.relations() if row["kind"] == "depends_on")
    assert (edge["source_id"], edge["target_id"]) == (ids["one"], ids["two"])
    rendered = canvas.edges_by_id[edge["id"]]
    label_position = rendered.caption.mapToScene(rendered.caption.rect().center())
    QTest.mouseClick(canvas.viewport(), Qt.LeftButton, pos=canvas.mapFromScene(label_position))
    assert rendered.handles["target"].isVisible()
    start = rendered.handles["target"].scenePos()
    target = canvas.items_by_id[ids["hero"]]
    drag(canvas, start, target.scenePos() + QPointF(40, 40), qt_app)
    changed = next(row for row in window.project.catalog.relations() if row["id"] == edge["id"])
    assert changed["target_id"] == ids["hero"]
    window.undo(False)
    assert edge in window.project.catalog.relations()
    before = window.project.catalog.export_snapshot()
    errors = []
    monkeypatch.setattr("etherfood_studio.ui.main_window.show_error",
                        lambda parent, error: errors.append(error))
    source, target = canvas.items_by_id[ids["two"]], canvas.items_by_id[ids["one"]]
    drag(canvas, source.ports["left"].scenePos(), target.scenePos() + QPointF(40, 40), qt_app)
    assert errors and "Zyklus" in str(errors[0])
    assert window.project.catalog.export_snapshot() == before
    monkeypatch.setattr(QInputDialog, "getItem", lambda *a: ("", False))
    drag(canvas, source.ports["top"].scenePos(), target.scenePos() + QPointF(40, 40), qt_app)
    assert window.project.catalog.export_snapshot() == before


def tree_item(window, identifier):
    return next(item for item in window.tree.findItems("", Qt.MatchContains | Qt.MatchRecursive)
                if item.data(0, Qt.UserRole) == identifier)


def context_action(window, identifier, name):
    menu = window.navigation.menu(identifier)
    return next(action for action in menu.actions() if action.objectName() == name)


def choose_popup_action(name):
    def choose():
        menu = QApplication.activePopupWidget()
        if menu:
            try:
                next(action for action in menu.actions() if action.objectName() == name).trigger()
            finally:
                menu.close()
    QTimer.singleShot(0, choose)


def test_context_note_tree_navigation_rename_and_icons(window, qt_app, monkeypatch):
    ids = window.project.demo()
    window.refresh()
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Kontextnotiz", True))
    monkeypatch.setattr(QInputDialog, "getItem", lambda *a, **k: ("Freie Notiz", True))
    # Choose an action from the real popup's event loop.
    choose_popup_action("context_new_note")
    position = window.tree.visualItemRect(tree_item(window, ids["one"])).center()
    window.tree.customContextMenuRequested.emit(position)
    window.notes.editor.title.setText("Kontextnotiz")
    window.notes.editor.save()
    doc = window.notes.editor.current
    assert doc.title == "Kontextnotiz" and doc.owner_id == ids["one"]
    window.notes.editor.editor.setPlainText("Notiz mit Inhalt")
    window.notes.editor.save()
    issue = IssueService(window.project).create(ids["two"], "Baum-Issue", "Inhalt sichtbar",
                                                issue=True)
    window.refresh()
    window.tree.setCurrentItem(tree_item(window, issue.id))
    assert "Inhalt sichtbar" in window.tasks.details.toPlainText()
    assert window.selected_id == ids["two"] and window.selected_content_id == issue.id
    window.tree.setCurrentItem(tree_item(window, doc.id))
    assert window.tabs.currentWidget() == window.notes
    assert window.notes.editor.current.id == doc.id
    assert window.notes.editor.editor.toPlainText() == "Notiz mit Inhalt"
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Neuer Notizname", True))
    context_action(window, doc.id, "context_rename").trigger()
    assert "Neuer Notizname" in tree_item(window, doc.id).text(0)
    assert window.project.catalog.get(doc.id).data["body"] == "Notiz mit Inhalt"
    assert not tree_item(window, issue.id).icon(0).isNull()
    assert not tree_item(window, doc.id).icon(0).isNull()
    for index in range(1, window.tasks.kind.count()):
        assert not window.tasks.kind.itemIcon(index).isNull()
    for item in window.canvas.items_by_id.values():
        assert not item.icon.pixmap().isNull()


def test_context_actions_and_tree_cancel_preserve_unsaved_document(window, monkeypatch):
    ids = window.project.demo()
    window.refresh()
    window.select_card(ids["one"])
    doc = window.documents.create_document("Behalten")
    task = IssueService(window.project).create(ids["two"], "Andere Aufgabe", "Details")
    window.refresh()
    window.documents.editor.setPlainText("Lokaler Entwurf")
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Cancel)
    window.tree.setCurrentItem(tree_item(window, task.id))
    assert window.selected_id == ids["one"]
    assert window.tree.currentItem().data(0, Qt.UserRole) == doc.id
    called = []
    monkeypatch.setattr(window.tasks, "new_item", lambda issue: called.append(issue))
    context_action(window, ids["two"], "context_new_task").trigger()
    assert not called
    assert window.documents.editor.toPlainText() == "Lokaler Entwurf"


def test_canvas_context_menu_and_direct_card_creation(window, qt_app, monkeypatch):
    ids = arrange_demo(window, qt_app)
    choose_popup_action("context_card_asset")

    def fill_wizard():
        wizard = QApplication.activeModalWidget()
        assert isinstance(wizard, AssetWizard)
        wizard.name.setText("Canvas-Asset")
        wizard.review()
        wizard.create()

    QTimer.singleShot(0, fill_wizard)
    card = window.canvas.items_by_id[ids["one"]]
    point = window.canvas.mapFromScene(card.scenePos() + QPointF(30, 40))
    window.canvas.customContextMenuRequested.emit(point)
    record = window.project.catalog.get(window.selected_id)
    assert record.title == "Canvas-Asset" and record.owner_id == ids["one"]
    assert record.kind == "asset"


def test_visible_status_and_using_same_asset_from_two_chapters(window, monkeypatch):
    ids = window.project.demo()
    global_id = window.project.catalog.get(ids["hero"]).owner_id
    shared = window.project.create_card("asset", "Gemeinsam", global_id, {"workflow": "static"})
    count = len(window.project.cards())
    monkeypatch.setattr(QInputDialog, "getItem", lambda *a: (
        next(choice for choice in a[3] if f"[{shared.id[:8]}]" in choice), True,
    ))
    for owner in (ids["one"], ids["two"]):
        context_action(window, owner, "context_use_existing").trigger()
    assert len(window.project.cards()) == count
    references = [item for item in window.tree.findItems("", Qt.MatchContains | Qt.MatchRecursive)
                  if item.data(0, Qt.UserRole) == shared.id and item.text(0).startswith("↪")]
    assert len(references) == 2
    for reference in references:
        window.tree.setCurrentItem(reference)
        assert window.selected_id == shared.id
        assert "Externe Eingabe fehlt" in window.workflow_status.text()
        assert "waiting_external" not in window.details.toPlainText()
        assert "2 Ort(en)" in window.usage.text() and "Projektweite Inhalte" in window.usage.text()
        assert shared.id in window.details.toPlainText()
    window.commands.link(shared.id, ids["two"], "depends_on")
    window.refresh()
    assert "Blockiert" in window.workflow_status.text()
    assert "Kapitel 2" in window.workflow_status.text()
    window.undo(False)
    assert "Externe Eingabe fehlt" in window.workflow_status.text()


def test_canvas_selection_can_save_dirty_note_without_deleting_active_mouse_item(
        window, qt_app, monkeypatch):
    ids = arrange_demo(window, qt_app)
    window.select_card(ids["one"])
    document = window.documents.create_document("Canvas-Wechsel")
    window.documents.editor.setPlainText("Entwurf vor Kartenwechsel")
    window.tabs.setCurrentIndex(0)
    window.canvas.fitInView(window.canvas.sceneRect(), Qt.KeepAspectRatio)
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Save)
    target = window.canvas.items_by_id[ids["two"]]
    position = window.canvas.mapFromScene(target.scenePos() + QPointF(45, 40))
    QTest.mouseClick(window.canvas.viewport(), Qt.LeftButton, pos=position)
    qt_app.processEvents()
    assert window.selected_id == ids["two"]
    assert window.project.catalog.get(document.id).data["body"] == "Entwurf vor Kartenwechsel"
