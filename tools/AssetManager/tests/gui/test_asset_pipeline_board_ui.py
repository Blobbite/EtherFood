"""The asset tools board shows one asset; project dashboards retain all assigned assets."""

from copy import deepcopy

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QPushButton

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.ui.appearance import appearance
from etherfood_studio.ui.asset_workspace import AssetWorkspace
from etherfood_studio.ui.pipeline_editor import PipelineEditor
from test_asset_pipeline_board import profiles_enabled
from test_pipeline_processing import asset_source, project


def test_asset_board_isolated_to_one_asset_while_project_dashboard_shows_inherited_assets(
        project, tmp_path, qt_app):
    first, _ = asset_source(project, tmp_path, count=8)
    second, _ = asset_source(project, tmp_path, count=8)
    service = PipelineService(project)
    recipe = service.create("Spreadsheet-Animation", "gif")
    service.assign(recipe.id, type_id="effect")
    workspace = AssetWorkspace(AssetService(project), first.id)
    before = project.catalog.export_snapshot()
    dashboard = PipelineEditor(project, recipe.id)
    previous = appearance().theme
    try:
        workspace.show()
        qt_app.processEvents()
        workspace.tabs.setCurrentWidget(workspace.pipeline_page)
        qt_app.processEvents()
        assert not workspace.workflow.isVisible()
        assert workspace.pipeline_board.canvas.transform().m11() > 0.1
        for theme in ("light", "dark"):
            appearance().set_preferences(theme, "text_icons", persist=False)
            qt_app.processEvents()
            board = workspace.pipeline_board
            assets = [card for card in board.canvas.items_by_id.values() if card.kind == "asset"]
            assert len(assets) == 1 and assets[0].identifier == "asset_" + first.id
            assert {"asset_" + first.id, "asset_" + second.id} <= set(dashboard.canvas.items_by_id)
            board.select("recipe_" + recipe.id)
            assert "Asset-Typ-/Fähigkeitsregel" in board.details.toPlainText()
            assert "effect" in board.details.toPlainText()
        assert service.bound_assets(recipe.id) == []
        assert project.catalog.export_snapshot() == before
    finally:
        appearance().set_preferences(previous, "text_icons", persist=False)
        workspace.close()
        dashboard.baseline = deepcopy(dashboard.state)
        dashboard.close()
        workspace.deleteLater()
        dashboard.deleteLater()
        qt_app.processEvents()


def test_graphics_settings_are_steps_and_absent_from_asset_menu(project, tmp_path, qt_app):
    profiles_enabled(project, {"comic_high", "pixel_low"})
    asset, _ = asset_source(project, tmp_path, count=8)
    service = PipelineService(project)
    recipe = service.create("Grafikvarianten", "graphics")
    service.assign(recipe.id, asset_id=asset.id)
    workspace = AssetWorkspace(AssetService(project), asset.id)
    try:
        assert workspace.findChild(QPushButton, "asset_pipeline_profiles") is None
        assert workspace.findChild(QPushButton, "workspace_build") is None
        assert not hasattr(workspace.editor, "graphics")
        data = service.resolve(asset.id)["data"]
        targets = {node["parameters"].get("profile") for node in data["steps"]}
        assert {"comic_high", "pixel_high", "pixel_low"} <= targets
        paths = {path for value in workspace.pipeline_board.entries.values() for path in value.get("paths", [])}
        assert "Ergebnisse/walk/comic_high" in paths
        assert "Ergebnisse/walk/pixel_low" in paths
        assert "Ergebnisse/walk/pixel_high" not in paths
    finally:
        workspace.close()
        workspace.deleteLater()
        qt_app.processEvents()


def test_asset_board_keeps_multiple_pipelines_and_opens_the_shared_recipe(project, tmp_path, qt_app,
                                                                       monkeypatch):
    asset, _ = asset_source(project, tmp_path, count=8)
    service = PipelineService(project)
    recipes = [service.create("Test", "gif"), service.create("Grafikvarianten", "graphics")]
    for recipe in recipes:
        service.assign(recipe.id, asset_id=asset.id)
    workspace = AssetWorkspace(AssetService(project), asset.id)
    opened, directories = [], []
    def edit(container):
        dialog = container.findChild(PipelineEditor)
        opened.append((dialog.project, dialog.identifier))
        dialog.name.setText("Test · gemeinsam geändert")
        dialog.header_changed()
        assert dialog.save()
        return 1
    monkeypatch.setattr("etherfood_studio.ui.asset_workspace.QDialog.exec", edit)
    monkeypatch.setattr("etherfood_studio.ui.asset_workspace.QDesktopServices.openUrl",
                        lambda url: directories.append(url.toLocalFile()) or True)
    try:
        board = workspace.pipeline_board
        assert set(board.flow_ids) == {recipe.id for recipe in recipes}
        key = "recipe_" + recipes[0].id
        board.select(key)
        assert workspace.pipeline_choice.currentData() == recipes[0].id
        board.open(key)
        assert opened == [(project, recipes[0].id)]
        assert service.recipe(recipes[0].id).title == "Test · gemeinsam geändert"
        key = next(key for key, value in board.entries.items()
                   if value.get("recipe_id") == recipes[0].id and value.get("paths"))
        board.open(key)
        assert directories == [str(project.files.path(asset.id) / "previews/gif")]
    finally:
        workspace.close()
        workspace.deleteLater()
        qt_app.processEvents()
