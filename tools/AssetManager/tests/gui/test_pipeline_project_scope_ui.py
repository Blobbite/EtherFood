"""Project actions reference existing definitions; creation stays in the tool editor."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QFileDialog, QPushButton

from etherfood_studio.application.workspace_files import WorkspaceFiles
from test_two_editors import window


@pytest.mark.parametrize("scope", ["project", "global", "act", "chapter", "asset"])
def test_context_use_keeps_definition_shared_and_uses_clicked_scope(window, qt_app, scope):
    project = window.project
    root = project.project()
    global_scope = next(r for r in project.cards() if r.kind == "global")
    act = project.create_card("act", "Akt", root.id)
    chapter = project.create_card("chapter", "Kapitel", act.id)
    asset = project.create_card("asset", "Asset", global_scope.id)
    selected = dict(project=root, global_=global_scope, act=act, chapter=chapter, asset=asset)
    target = global_scope if scope == "global" else selected[scope]
    definition = WorkspaceFiles(project).create_definition("Vorhanden")
    window.refresh()
    window.select_card(global_scope.id)
    menu = window.navigation.menu(target.id)
    names = {a.objectName() for a in menu.actions()}
    assert not names & {"context_pipeline_new", "context_workflow_open", "context_pipeline_import"}
    next(a for a in menu.actions() if a.objectName() == "context_pipeline_use").trigger()
    menu.deleteLater()
    assert window.main_navigation.currentRow() == 0
    QTest.mouseClick(
        window.usage_editor.findChild(QPushButton, "create_pipeline_usage"), Qt.LeftButton
    )
    service = window.processing.service
    (usage,) = service.usages()
    assert usage.data["definition_id"] == definition.id
    assert usage.data["targets"] == [target.id]
    assert len(service.definitions()) == 1 and service.scripts() == []
    window.undo(False)
    assert project.catalog.get(usage.id).archived
    assert not project.catalog.get(definition.id).archived
    window.undo(True)
    assert service.usages()[0].id == usage.id


def test_new_pipeline_button_needs_no_asset_and_import_is_explicit(window, qt_app, monkeypatch):
    window.set_main_editor(1)
    workspace = window.processing
    workspace.name.setText("Ohne Asset")
    QTest.mouseClick(workspace.findChild(QPushButton, "pipeline_create"), Qt.LeftButton)
    (definition,) = workspace.service.definitions()
    assert workspace.editor.current.id == definition.id
    assert not any(r.kind == "asset" for r in window.project.cards())
    assert workspace.editor.save()
    paths = []
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a: (paths.append(a) or ("", "")))
    workspace.import_files()
    assert paths and "*.py" in paths[0][-1]
    assert len(workspace.service.definitions()) == 1
    assert workspace.service.scripts() == []
