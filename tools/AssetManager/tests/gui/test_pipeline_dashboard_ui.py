"""Pointer-driven asset connections, fixed root symbols and centralized deliveries."""

from copy import deepcopy

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QPushButton

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.ui.asset_settings import AssetDefinitionEditor
from etherfood_studio.ui.canvas.items import IconCardItem, ProjectItem, WorkflowIconItem
from etherfood_studio.ui.canvas.view import Canvas
from etherfood_studio.ui.pipeline_editor import PipelineEditor
from etherfood_studio.ui.sources import SourcesPanel
from etherfood_studio.ui.theme import color
from test_pipeline_processing import asset_source, project


def test_project_and_pipeline_keep_fixed_dimensions_in_both_themes(project, qt_app):
    pipeline = PipelineService(project).create("GIF-Vorschauen", "gif")
    project.catalog.save_layout(project.project().id, {"w": 210, "h": 100})
    project.catalog.save_layout(pipeline.id, {"w": 900, "h": 300})
    before = project.catalog.export_snapshot()
    canvas = Canvas()
    previous = qt_app.property("studio_theme")
    try:
        for theme in ("light", "dark"):
            qt_app.setProperty("studio_theme", theme)
            canvas.render(project)
            root, icon = (canvas.items_by_id[key] for key in (project.project().id, pipeline.id))
            assert isinstance(root, ProjectItem) and isinstance(icon, IconCardItem)
            root.resize(900, 300)
            icon.resize(900, 300)
            assert (root.rect().width(), root.rect().height()) == (520, 140)
            assert (icon.rect().width(), icon.rect().height()) == (144, 62)
            assert not root.grip.isVisible() and not icon.grip.isVisible()
            assert root.brush().color().name() == color("project_card")
            assert root.pen().widthF() == 3
            assert set(icon.ports) == {"top", "bottom", "left", "right"}
        assert project.catalog.export_snapshot() == before
    finally:
        qt_app.setProperty("studio_theme", previous)
        canvas.deleteLater()
        qt_app.processEvents()


def test_asset_port_connects_to_gif_and_saved_links_support_undo_reopen(
        project, tmp_path, qt_app, monkeypatch):
    asset, _ = asset_source(project, tmp_path, count=8)
    service = PipelineService(project)
    recipe = service.create("PiGIF", "gif")
    errors = []
    monkeypatch.setattr("etherfood_studio.ui.pipeline_editor.show_error",
                        lambda parent, error: errors.append(str(error)))
    dialog = PipelineEditor(project, recipe.id)
    dialog.show()
    try:
        dialog.asset_choices.setCurrentIndex(dialog.asset_choices.findData(asset.id))
        QTest.mouseClick(dialog.findChild(QPushButton, "pipeline_add_asset"), Qt.LeftButton)
        node = dialog.state["recipe"]["steps"][1]
        icon = dialog.canvas.items_by_id["asset_" + asset.id]
        assert isinstance(icon, WorkflowIconItem) and icon.icon.pixmap().width() == 48
        dialog.fit_steps()
        qt_app.processEvents()
        start = dialog.canvas.mapFromScene(icon.ports["right"].scenePos())
        target = dialog.canvas.items_by_id[node["id"]]
        end = dialog.canvas.mapFromScene(target.ports["left"].scenePos())
        QTest.mousePress(dialog.canvas.viewport(), Qt.LeftButton, pos=start)
        QTest.mouseMove(dialog.canvas.viewport(), end, 50)
        QTest.mouseRelease(dialog.canvas.viewport(), Qt.LeftButton, pos=end)
        assert not errors
        assert dialog.state["bindings"] == [asset.id]
        output = dialog.canvas.items_by_id["output_" + node["id"]]
        assert "previews/gif" in output.toolTip()
        assert dialog.save()
        assert service.resolve(asset.id, recipe.id)["recipe"].id == recipe.id
        dialog.commands.undo()
        assert not service.bound_assets(recipe.id)
        dialog.commands.redo()
        assert service.bound_assets(recipe.id) == [asset.id]
        reopened = PipelineEditor(project, recipe.id)
        try:
            assert reopened.state["bindings"] == [asset.id]
            assert "asset_" + asset.id in reopened.canvas.items_by_id
            reopened.select_step("output_" + node["id"])
            assert reopened.findChild(QPushButton, "pipeline_build")
        finally:
            reopened.deleteLater()
    finally:
        dialog.baseline = deepcopy(dialog.state)
        dialog.close()
        dialog.deleteLater()
        qt_app.processEvents()


def test_sources_and_sheets_have_separate_actions_outside_pose_configuration(
        project, tmp_path, qt_app):
    asset, _ = asset_source(project, tmp_path, count=8)
    assets = AssetService(project)
    editor = AssetDefinitionEditor(assets.definition(asset.id))
    panel = SourcesPanel(assets, asset.id, include_import=False)
    selected = []
    panel.import_requested.connect(selected.append)
    try:
        assert all("Lieferung" not in editor.poses.horizontalHeaderItem(i).text()
                   for i in range(editor.poses.columnCount()))
        pose = assets.definition(asset.id).poses[0].id
        single = panel.findChild(QPushButton, "delivery_single_image_" + pose)
        sheet = panel.findChild(QPushButton, "delivery_spritesheet_" + pose)
        assert single.text().startswith("0/1") and sheet.text().startswith("1/1")
        single.click()
        sheet.click()
        assert [values[0].kind for values in selected] == ["single_image", "spritesheet"]
        assert panel.overview.item(0, 5).text() == "0/1 aktuell"
    finally:
        editor.deleteLater()
        panel.deleteLater()
        qt_app.processEvents()


def test_moving_asset_endpoint_replaces_binding_and_undo_restores_it(
        project, tmp_path, qt_app, monkeypatch):
    first, _ = asset_source(project, tmp_path, count=8)
    second, _ = asset_source(project, tmp_path, count=8)
    first, second = sorted((first, second), key=lambda asset: asset.id, reverse=True)
    service = PipelineService(project)
    recipe = service.create("PiGIF", "gif")
    service.assign(recipe.id, asset_id=first.id)
    errors = []
    monkeypatch.setattr("etherfood_studio.ui.pipeline_editor.show_error",
                        lambda parent, error: errors.append(str(error)))
    dialog = PipelineEditor(project, recipe.id)
    dialog.show()
    try:
        dialog.asset_choices.setCurrentIndex(dialog.asset_choices.findData(second.id))
        dialog.add_asset()
        dialog.fit_steps()
        qt_app.processEvents()
        first_icon = dialog.canvas.items_by_id["asset_" + first.id]
        second_icon = dialog.canvas.items_by_id["asset_" + second.id]
        assert not first_icon.sceneBoundingRect().intersects(second_icon.sceneBoundingRect())
        key = next(key for key, value in dialog.canvas.asset_edges.items() if value == first.id)
        edge = dialog.canvas.edges_by_id[key]
        edge.setSelected(True)
        dialog.canvas.update_edges()
        qt_app.processEvents()
        start = dialog.canvas.mapFromScene(edge.handles["source"].scenePos())
        end = dialog.canvas.mapFromScene(
            dialog.canvas.items_by_id["asset_" + second.id].ports["right"].scenePos())
        QTest.mousePress(dialog.canvas.viewport(), Qt.LeftButton, pos=start)
        QTest.mouseMove(dialog.canvas.viewport(), end, 50)
        QTest.mouseRelease(dialog.canvas.viewport(), Qt.LeftButton, pos=end)
        assert not errors and dialog.state["bindings"] == [second.id]
        assert dialog.save() and service.bound_assets(recipe.id) == [second.id]
        dialog.commands.undo()
        assert service.bound_assets(recipe.id) == [first.id]
        dialog.commands.redo()
        assert service.bound_assets(recipe.id) == [second.id]
    finally:
        dialog.baseline = deepcopy(dialog.state)
        dialog.close()
        dialog.deleteLater()
        qt_app.processEvents()
