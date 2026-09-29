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
from etherfood_studio.application.tool_environments import ToolEnvironments
from etherfood_studio.application.tool_packages import ToolPackageService
from etherfood_studio.ui.main_window import MainWindow
from etherfood_studio.ui.package_actions import invoke
from etherfood_studio.domain.models import StudioError

from legacy_fixtures import EXAMPLE, asset, import_scale
from legacy_fixtures import offline_pillow

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
