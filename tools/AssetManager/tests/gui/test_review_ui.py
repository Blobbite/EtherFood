"""Real Qt interactions for the dashboard review corrections."""

import pytest

QtWidgets = pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtCore import QPointF, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialogButtonBox, QInputDialog, QMessageBox

from etherfood_studio.application.document_service import DocumentService
from etherfood_studio.application.issue_service import Finding, IssueService
from etherfood_studio.ui.main_window import MainWindow
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
    result.close()


def test_task_details_edit_conflict_cancel_and_save(window, qt_app, monkeypatch):
    service = IssueService(window.project)
    item = service.create(window.selected_id, "Issue", "Gespeicherte Beschreibung", issue=True,
                          finding=Finding(direction="SW", frame_index=0))
    window.tasks.show_record(item.id)
    window.tabs.setCurrentWidget(window.tasks)
    result = window.tasks.results.currentItem()
    QTest.mouseClick(window.tasks.results.viewport(), Qt.LeftButton,
                     pos=window.tasks.results.visualItemRect(result).center())
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
    assert window.tasks.results.currentItem().data(Qt.UserRole) == item.id


def test_search_document_open_preserves_unsaved_content(window, monkeypatch):
    service = DocumentService(window.project)
    first = window.documents.create_document("Erste Notiz")
    second = service.create(window.selected_id, "Zweite Notiz", "Zweiter Text")
    window.documents.editor.setPlainText("Ungespeichert")
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Cancel)
    window.open_document(second.id)
    assert window.documents.current.id == first.id
    assert window.documents.editor.toPlainText() == "Ungespeichert"
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.Save)
    window.tasks.show_record(second.id)
    window.tasks.edit_current()
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
