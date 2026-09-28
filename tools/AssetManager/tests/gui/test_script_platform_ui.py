"""Canvas package import and manifest-driven controls use the same real worker as services."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication, QComboBox, QFileDialog, QDoubleSpinBox, QPushButton

from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.plugin_service import PluginService
from etherfood_studio.ui.main_window import MainWindow
from etherfood_studio.ui.package_actions import invoke
from etherfood_studio.ui.pipeline_editor import PipelineEditor
from etherfood_studio.ui.pipeline_exchange_dialogs import PluginPackageImportDialog
from etherfood_studio.ui.pipeline_auxiliary import PipelineRunWorker
from etherfood_studio.domain.models import StudioError

from test_script_platform import EXAMPLE, asset, import_scale


def test_canvas_package_import_fields_action_undo_worker_and_folder(tmp_path, qt_app, monkeypatch):
    window = MainWindow(QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat))
    root = tmp_path / "project"
    root.mkdir()
    window.new_project(root, "Skript-Canvas")
    project = window.project
    opened = []
    monkeypatch.setattr(window, "open_pipeline", opened.append)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(EXAMPLE), "JSON"))
    def accept_import(dialog):
        dialog.import_copy()
        return dialog.result()
    monkeypatch.setattr(PluginPackageImportDialog, "exec", accept_import)
    menu = window.navigation.menu(project.project().id)
    next(a for a in menu.actions() if a.objectName() == "context_pipeline_import").trigger()
    menu.deleteLater()
    assert len(opened) == 1
    recipe = project.catalog.get(opened[0])
    assert recipe.id in window.canvas.items_by_id
    plugins = PluginService(project)
    identifier = "python:proportional-scale"
    assert plugins.details(identifier)["approved_hash"] is None
    editor = PipelineEditor(project, recipe.id)
    try:
        editor.show()
        qt_app.processEvents()
        assert editor.operations.currentData() == identifier
        for item in editor.canvas.items_by_id.values():
            visible = editor.canvas.mapToScene(editor.canvas.viewport().rect()).boundingRect()
            assert visible.contains(item.sceneBoundingRect())
        node = editor.state["recipe"]["steps"][1]
        editor.select_step(node["id"])
        assert editor.findChild(QDoubleSpinBox, "pipeline_parameter_factor").value() == 0.5
        assert editor.findChild(QPushButton, "pipeline_action_presets") is None
        assert editor.findChild(QPushButton, "pipeline_profiles") is None
        plugins.approve(identifier, plugins.details(identifier)["code_hash"])
        editor.render()
        assert editor.findChild(QPushButton, "pipeline_action_presets") is not None
        monkeypatch.setattr("etherfood_studio.ui.package_actions.invoke",
            lambda service, key, action, parameters, parent, **kwargs:
                {**parameters, "factor": 0.25})
        editor.package_action(node, "presets")
        assert editor.state["recipe"]["steps"][1]["parameters"]["factor"] == 0.25
        editor.undo()
        assert editor.state["recipe"]["steps"][1]["parameters"]["factor"] == 0.5
        editor.move_nodes({node["id"]: {"x": 456, "y": 123}})
        assert editor.save()
        parent = next(r for r in project.cards() if r.kind == "global")
        record, _ = asset(project, tmp_path, parent.id)
        PipelineService(project).assign(recipe.id, asset_id=record.id)
        planned, finished = [], []
        worker = PipelineRunWorker(project, recipe.id, record.id)
        worker.result.connect(planned.append)
        worker.run()
        plan = planned[0]["rows"][0]["plan"]
        worker = PipelineRunWorker(project, recipe.id, record.id, plans=[plan])
        worker.result.connect(finished.append)
        worker.run()
        assert finished[0]["reports"][0]["report"]["published"]
        assert list((project.files.path(record.id) / "Ergebnisse/scaled").glob("*.png"))
        paths = []
        monkeypatch.setattr("etherfood_studio.ui.navigation.QDesktopServices.openUrl",
                            lambda url: paths.append(url.toLocalFile()) or True)
        menu = window.navigation.menu(record.id)
        next(a for a in menu.actions() if a.objectName() == "context_folder").trigger()
        assert paths == [str(project.files.path(record.id))]
        menu.deleteLater()
        plugins.revoke(identifier)
        editor.render()
        assert editor.findChild(QPushButton, "pipeline_action_presets") is None
    finally:
        editor.baseline = deepcopy(editor.state)
        editor.reject()
        editor.deleteLater()
        qt_app.processEvents()
        window.close()


def test_explicit_package_ui_code_loads_only_after_trust_and_click(tmp_path, qt_app):
    from etherfood_studio.application.project_service import ProjectService

    root = tmp_path / "project"
    root.mkdir()
    project = ProjectService.new(root, "Optionale Dienste")
    service = PluginService(project)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(EXAMPLE.read_text())
    marker = tmp_path / "executed"
    code = tmp_path / "scale.py"
    code.write_text(f"from pathlib import Path\nPath({str(marker)!r}).touch()\n"
                    'def choose_preset(parent, parameters):\n'
                    '    return {**parameters, "factor": 0.25}\n')
    try:
        registered = service.register(manifest, code)
        parameters = {k: s["default"] for k, s in registered["manifest"]["parameters"].items()}
        with pytest.raises(StudioError, match="freigegeben"):
            invoke(service, registered["identifier"], "presets", parameters, None)
        assert not marker.exists()
        service.approve(registered["identifier"], registered["code_hash"])
        assert service.actions(registered["identifier"]) and not marker.exists()
        result = invoke(service, registered["identifier"], "presets", parameters, None)
        assert result["factor"] == 0.25
        assert marker.exists() and parameters["factor"] == 0.5
        service.remove(registered["identifier"])
        assert not service.actions(registered["identifier"])
    finally:
        project.catalog.close()


def test_shipped_optional_dialog_returns_parameters_through_generic_action(tmp_path, qt_app):
    from etherfood_studio.application.project_service import ProjectService

    root = tmp_path / "project"
    root.mkdir()
    project = ProjectService.new(root, "Paketoberfläche")
    try:
        recipe = import_scale(project)
        parameters = recipe.data["recipe"]["steps"][1]["parameters"]
        def choose_quarter():
            dialog = QApplication.activeModalWidget()
            dialog.findChild(QComboBox).setCurrentIndex(2)
            dialog.accept()
        QTimer.singleShot(0, choose_quarter)
        result = invoke(PluginService(project), "python:proportional-scale", "presets",
                        parameters, None)
        assert result["factor"] == 0.25 and parameters["factor"] == 0.5
    finally:
        project.catalog.close()
