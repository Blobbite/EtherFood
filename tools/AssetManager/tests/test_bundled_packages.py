"""Shipped package discovery is declarative; imported scripts freeze shared processing too."""

import subprocess
import sys

from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.packages import ROOT
from test_project_documents import project


def test_discovery_does_not_import_processing_or_optional_ui():
    code = (
        'import sys\n'
        'from etherfood_studio.domain.pipeline_recipes import BUILTINS\n'
        'assert set(BUILTINS) == {"source", "graphics", "frames", "prepare8", '
        '"prepare16", "color", "source_color", "gif"}\n'
        'assert not any(n.endswith((".process", ".services")) and '
        'n.startswith("etherfood_studio.packages.") for n in sys.modules)\n'
        'assert "PySide6" not in sys.modules\n')
    subprocess.run([sys.executable, "-I", "-c", code], check=True, capture_output=True)


def test_runtime_algorithms_are_fingerprinted_but_optional_ui_is_not(project):
    from etherfood_studio.application.pipeline_workspace import PipelineWorkspace
    from test_pipeline_workspace import passthrough

    _, definition = passthrough(project)
    value = PipelineWorkspace(project).snapshot(definition.id)
    assert "packages/graphics/process.py" in value["runtime"]
    assert "packages/animation/process.py" in value["runtime"]
    assert not any("services.py" in name for name in value["runtime"])
