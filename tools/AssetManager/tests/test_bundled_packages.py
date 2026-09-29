"""Shipped package discovery is declarative; imported scripts freeze shared processing too."""

import subprocess
import sys

from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.recipe_builds import RecipeBuildService
from etherfood_studio.packages import ROOT
from test_project_documents import project
from test_script_platform import EXAMPLE, asset, import_scale


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


def test_python_wrapper_fingerprints_shipped_algorithms(project, tmp_path, monkeypatch):
    from etherfood_studio.pipelines import image_adapter

    owner = next(r for r in project.cards() if r.kind == "global")
    record, _ = asset(project, tmp_path, owner.id, animated=True)
    recipe = import_scale(project, EXAMPLE.parent.parent / "pipeline_frames/manifest.json")
    PipelineService(project).assign(recipe.id, asset_id=record.id)
    before = RecipeBuildService(project).plan(record.id)
    script = ROOT / "animation/process.py"
    assert str(script) in dict(before.nodes[0].node.tools)
    original = image_adapter.file_hash
    monkeypatch.setattr(image_adapter, "file_hash",
                        lambda path: "f" * 64 if path == script else original(path))
    after = RecipeBuildService(project).plan(record.id)
    assert before.nodes[0].fingerprint != after.nodes[0].fingerprint


def test_builtin_scale_does_not_depend_on_unrelated_color_ui(project, tmp_path):
    owner = next(r for r in project.cards() if r.kind == "global")
    record, _ = asset(project, tmp_path, owner.id)
    pipelines = PipelineService(project)
    recipe = pipelines.create("Grafik", "graphics")
    pipelines.assign(recipe.id, asset_id=record.id)
    plan = RecipeBuildService(project).plan(record.id)
    for row in plan.nodes:
        paths = dict(row.node.tools)
        assert str(ROOT / "graphics/process.py") in paths
        assert str(ROOT / "colors/services.py") not in paths
