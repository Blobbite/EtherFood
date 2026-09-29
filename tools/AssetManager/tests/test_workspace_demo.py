"""Explicit demo exercises the real native execution contract, including animated GIFs."""

from PIL import Image
from etherfood_studio.application.pipeline_execution import PipelineExecution
from etherfood_studio.application.pipeline_workspace import PipelineWorkspace
from etherfood_studio.application.workspace_demo import WorkspaceDemo
from test_pipeline_workspace import project


def test_demo_is_explicit_idempotent_yellow_and_two_asset_gif_chain(project):
    workspace = PipelineWorkspace(project)
    assert workspace.definitions() == workspace.scripts() == []
    first = WorkspaceDemo(project).create()
    again = WorkspaceDemo(project).create()
    assert again == first | {"existing": True}
    assert len(workspace.scripts()) == len(workspace.definitions()) == 2
    engine = PipelineExecution(project)
    plan = engine.plan()
    rows = plan["entries"][first["usages"][0]]["rows"]
    assert len([r for r in rows if r["state"] == "matching"]) == 2
    assert len([r for r in rows if r["state"] == "nonmatching"]) == 1
    for definition in first["pipelines"]:
        assert workspace.status(definition)[0] == "yellow"
        check = workspace.check(definition)
        assert check["valid"], check
        assert workspace.status(definition)[0] == "yellow"
        workspace.approve(definition, check["hash"])
    result = engine.run()
    assert result["state"] == "succeeded", result
    assert result["executed"] == 4
    gif_rows = result["phases"][1]["rows"]
    assert len(gif_rows) == 2
    for row in gif_rows:
        path = project.catalog.path.parent / row["outputs"]["animation"][0]["path"]
        with Image.open(path) as image:
            assert image.format == "GIF" and image.n_frames > 1
            image.seek(0)
            first_frame = image.convert("RGB").tobytes()
            image.seek(1)
            assert image.convert("RGB").tobytes() != first_frame
    assert engine.run()["executed"] == 0
