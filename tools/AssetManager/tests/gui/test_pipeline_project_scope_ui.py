"""Qt entry points create project-owned pipelines independently of asset selection."""

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QPoint, QSettings, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QInputDialog, QMenu

from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.ui.main_window import MainWindow


@pytest.fixture
def window(tmp_path, qt_app):
    value = MainWindow(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat))
    assert not value.pipeline_action.isEnabled()
    root = tmp_path / "project"
    root.mkdir()
    value.new_project(root, "Projekt-Pipelines")
    value.show()
    qt_app.processEvents()
    yield value
    value.close()
    qt_app.processEvents()


def choose_menu(action_name, seen):
    def choose():
        menu = QApplication.activePopupWidget()
        if not isinstance(menu, QMenu):
            return
        actions = {action.objectName() or action.text(): action for action in menu.actions()}
        seen.update({name: action.text() for name, action in actions.items()})
        if action_name not in actions:
            menu.close()
            return
        menu.setActiveAction(actions[action_name])
        QTest.keyClick(menu, Qt.Key_Return)
    return choose


@pytest.mark.parametrize("entry", ["tree", "canvas_card", "toolbar"])
def test_visible_project_entries_create_pipeline_sibling_of_global(window, qt_app, monkeypatch,
                                                                  entry):
    opened, seen = [], {}
    monkeypatch.setattr(window, "open_pipeline", opened.append)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Projekt-Rezept", True))
    monkeypatch.setattr(QInputDialog, "getItem", lambda *a, **k: ("Grafik-Assets", True))
    project = window.project
    root = project.project().id
    scope = next(r.id for r in project.cards() if r.kind == "global")
    # A folded global scope cannot conceal project-owned pipeline cards.
    window.commands.layout(scope, {"collapsed": True})
    window.refresh()
    window.select_card(scope)
    qt_app.processEvents()
    if entry != "toolbar":
        QTimer.singleShot(0, choose_menu("context_pipeline_new", seen))
    if entry == "toolbar":
        assert window.pipeline_action.isEnabled()
        QTest.mouseClick(window.project_toolbar.widgetForAction(window.pipeline_action),
                         Qt.LeftButton)
        assert window.tabs.currentWidget() is window.processing
        menu = window.navigation.menu(root)
        seen.update({a.objectName(): a.text() for a in menu.actions()})
        menu.deleteLater()
        window.create_pipeline()
    elif entry == "tree":
        item = window.tree.topLevelItem(0)
        point = window.tree.visualItemRect(item).center()
        window.tree.customContextMenuRequested.emit(point)
    else:
        card = window.canvas.items_by_id[root]
        window.canvas.centerOn(card)
        point = window.canvas.mapFromScene(card.sceneBoundingRect().center())
        window.canvas.customContextMenuRequested.emit(point)
    qt_app.processEvents()
    assert {
        "context_pipeline_new",
        "context_workflow_open",
        "context_pipeline_import",
    } <= seen.keys()
    assert len(opened) == 1
    recipe = PipelineService(project).recipe(opened[0])
    assert recipe.owner_id == root
    assert recipe.data["recipe"]["contract"] == "studio-pipeline-v2"
    assert recipe.id in window.canvas.items_by_id
    positions = window.canvas.default_positions(project)
    assert positions[recipe.id]["x"] == positions[scope]["x"]
    assert positions[recipe.id]["y"] < positions[scope]["y"]
    item = window.tree.currentItem()
    assert item.data(0, Qt.UserRole) == recipe.id
    assert item.parent().data(0, Qt.UserRole) == root
    assert item.parent().child(0) == item
    window.undo(False)
    assert project.catalog.get(recipe.id).archived
    window.undo(True)
    assert PipelineService(project).recipe(recipe.id).owner_id == root


@pytest.mark.parametrize("selection", ["none", "project", "global", "act", "multiple"])
def test_blank_canvas_pipeline_creation_uses_project_regardless_of_selection(
        window, qt_app, monkeypatch, selection):
    project = window.project
    root = project.project().id
    scope = next(r.id for r in project.cards() if r.kind == "global")
    act = project.create_card("act", "Akt", root)
    window.refresh()
    if selection == "none":
        window.canvas.select_many(set())
        window.selected_id = None
    elif selection == "multiple":
        window.canvas.select_many({scope, act.id})
    else:
        window.select_card({"project": root, "global": scope, "act": act.id}[selection])
    opened, seen = [], {}
    monkeypatch.setattr(window, "open_pipeline", opened.append)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Leere Pipeline", True))
    qt_app.processEvents()
    viewport = window.canvas.viewport()
    point = next(QPoint(x, y) for x in range(10, viewport.width(), 30)
                 for y in range(10, viewport.height(), 30)
                 if window.canvas.card_at(window.canvas.mapToScene(QPoint(x, y))) is None)
    QTimer.singleShot(0, choose_menu("context_pipeline_new", seen))
    window.canvas.customContextMenuRequested.emit(point)
    qt_app.processEvents()
    assert {
        "context_pipeline_new",
        "context_workflow_open",
        "context_pipeline_import",
    } <= seen.keys()
    assert len(opened) == 1
    assert project.catalog.get(opened[0]).owner_id == root
    if selection == "multiple":
        assert "Auswahl anordnen" in seen.values()


def test_toolbar_opens_unified_import_workspace(window, monkeypatch):
    from PySide6.QtWidgets import QFileDialog, QPushButton

    calls = []
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", lambda *args: (calls.append(args) or ("", ""))
    )
    window.pipeline_action.trigger()
    assert window.tabs.currentWidget() is window.processing
    window.processing.findChild(QPushButton, "workflow_import").click()
    assert calls and "*.py" in calls[0][-1]
