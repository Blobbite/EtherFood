"""Actual Qt drops, lifecycle undo, both searches and Canvas/text deletion separation."""

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from etherfood_studio.application.lifecycle_service import LifecycleService
from etherfood_studio.application.tree_service import TreeService
from etherfood_studio.application.workspace_files import WorkspaceFiles
from etherfood_studio.ui.project_tree import ID_ROLE, EDGE_ROLE
from test_two_editors import window


def send_drop(tree, item, mime, qt_app):
    tree.scrollToItem(item)
    qt_app.processEvents()
    point = tree.visualItemRect(item).center()
    for event in (
        QDragEnterEvent(point, Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier),
        QDragMoveEvent(point, Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier),
    ):
        QApplication.sendEvent(tree.viewport(), event)
    event = QDropEvent(QPointF(point), Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)
    QApplication.sendEvent(tree.viewport(), event)
    qt_app.processEvents()
    return event.isAccepted()


def items(tree):
    return tree.findItems("", Qt.MatchContains | Qt.MatchRecursive)


def test_reference_archive_drop_restore_and_single_undo(window, qt_app):
    project = window.project
    owner = next(r for r in project.cards() if r.kind == "global")
    asset = project.create_card("asset", "Original", owner.id)
    a = project.create_card("act", "Erster Akt", project.project().id)
    b = project.create_card("act", "Zweiter Akt", project.project().id)
    edge = project.relate(a.id, asset.id, "uses")
    life = LifecycleService(project)
    life.change([edge], "archived")
    window.refresh()
    tree = window.tree
    tree.dragged = TreeService(window.commands).capture(asset.id, edge)
    target = next(
        i for i in items(tree) if i.data(0, ID_ROLE) == asset.id and not i.data(0, EDGE_ROLE)
    )
    assert not send_drop(tree, target, tree.drag_mime(), qt_app)
    assert life.state(edge)["state"] == "archived"
    target = next(i for i in items(tree) if i.data(0, ID_ROLE) == b.id)
    assert send_drop(tree, target, tree.drag_mime(), qt_app)
    tree.dragged = None
    assert life.state(edge) is None
    assert next(e for e in project.catalog.relations() if e["id"] == edge)["source_id"] == b.id
    assert project.catalog.get(asset.id).owner_id == owner.id
    window.undo(False)
    assert life.state(edge)["state"] == "archived"
    assert life._edge(edge)["source_id"] == a.id


def test_tools_restore_drop_to_actual_folder_and_pipeline_group(window, qt_app):
    files = WorkspaceFiles(window.project)
    script = files.create_script("Archiviertes Skript")
    definition = files.create_definition("Archivierte Pipeline")
    files.create_folder("Ziel")
    life = LifecycleService(window.project)
    life.change([script.id, definition.id], "archived")
    window.set_main_editor(1)
    window.processing.refresh()
    tree = window.processing.tree
    tree.setFocus()
    target = next(i for i in items(tree) if i.data(0, Qt.UserRole) == ("folder", "Ziel"))
    assert send_drop(tree, target, tree.drag_mime(("script", script.id)), qt_app)
    assert life.state(script.id) is None
    assert window.project.catalog.get(script.id).data["path"].startswith(".tools/scrips/Ziel/")
    tree.setFocus()
    window.undo(False)
    assert life.state(script.id)["state"] == "archived"
    assert window.project.catalog.get(script.id).data["path"] == script.data["path"]
    target = next(i for i in items(tree) if i.data(0, Qt.UserRole) == ("group", "pipelines"))
    assert send_drop(tree, target, tree.drag_mime(("pipeline_definition", definition.id)), qt_app)
    assert life.state(definition.id) is None
    tree.setFocus()
    window.undo(False)
    assert life.state(definition.id)["state"] == "archived"


def test_both_searches_open_identity_and_delete_is_scoped(window, qt_app, monkeypatch):
    files = WorkspaceFiles(window.project)
    script = files.create_script("Suchskript")
    definition = files.create_definition("Suchpipeline")
    usage = window.processing.service.use(definition.id)
    window.refresh()
    project_search = window.search
    project_search.query.setText("Suchpipeline")
    hit = next(i for i, h in enumerate(project_search.hits) if h.id == usage.id)
    project_search.activate(hit)
    assert window.main_navigation.currentRow() == 0 and window.selected_id == usage.id
    tool_search = window.processing.search
    tool_search.query.setText("Suchskript")
    tool_search.activate(0)
    editor = window.processing.python.editor
    assert window.processing.python.current.id == script.id
    editor.setFocus()
    editor.moveCursor(QTextCursor.Start)
    before = editor.toPlainText()
    QTest.keyClick(editor, Qt.Key_Delete)
    assert len(editor.toPlainText()) == len(before) - 1
    assert LifecycleService(window.project).state(script.id) is None
    editor.undo()
    window.set_main_editor(0)
    window.canvas.focus_card(usage.id)
    window.canvas.items_by_id[usage.id].setSelected(True)
    window.canvas.setFocus()
    questions = []

    def confirm(*args):
        questions.append(args)
        return QMessageBox.Yes

    monkeypatch.setattr(QMessageBox, "question", confirm)
    QTest.keyClick(window.canvas, Qt.Key_Delete)
    qt_app.processEvents()
    assert questions and "30 Tage" in questions[0][2] and questions[0][-1] == QMessageBox.Cancel
    assert LifecycleService(window.project).state(usage.id)["state"] == "trash"
    assert not window.project.catalog.get(definition.id).archived
    assert not window.project.catalog.get(script.id).archived


def test_script_tree_context_order_and_view_specific_structure(window, qt_app):
    files = WorkspaceFiles(window.project)
    files.create_folder("A")
    files.create_folder("B")
    script = files.create_script("Skript", path="B/main.py")
    workspace = window.processing
    window.set_main_editor(1)
    workspace.refresh()
    tree = workspace.tree

    def folder(name):
        return next(i for i in items(tree) if i.data(0, Qt.UserRole) == ("folder", name))

    def order():
        root = folder("")
        return [root.child(i).text(0) for i in range(root.childCount())]

    assert order() == ["A", "B"]
    target = folder("B")
    tree.scrollToItem(target)
    qt_app.processEvents()

    def choose():
        menu = QApplication.activePopupWidget()
        next(a for a in menu.actions() if a.text() == "In Struktur nach oben").trigger()
        menu.close()

    QTimer.singleShot(0, choose)
    tree.customContextMenuRequested.emit(tree.visualItemRect(target).center())
    assert order() == ["B", "A"]
    workspace.open_script(script.id)
    top = [tree.topLevelItem(i).text(0) for i in range(tree.topLevelItemCount())]
    assert top == ["Eigene Skripte", "Archiv"]
    assert order() == ["B", "A"]
    tree.setFocus()
    window.undo(False)
    assert order() == ["A", "B"]
    window.undo(True)
    assert order() == ["B", "A"]
    workspace.move_file("B", "Umbenannt")
    assert order() == ["Umbenannt", "A"]
    assert window.project.catalog.get(script.id).data["path"] == ".tools/scrips/Umbenannt/main.py"
    window.section_navigation.setCurrentRow(0)
    assert any(
        tree.topLevelItem(i).text(0) == "Programmbausteine" for i in range(tree.topLevelItemCount())
    )
