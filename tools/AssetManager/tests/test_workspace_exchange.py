"""Complete current-file transport and external source reconciliation in isolated projects."""

import json
import zipfile
from PIL import Image
import pytest

from etherfood_studio.application.pipeline_workspace import PipelineWorkspace
from etherfood_studio.application.source_reconciliation import SourceReconciliation
from etherfood_studio.application.workspace_exchange import WorkspaceExchange
from etherfood_studio.application.workspace_files import WorkspaceFiles
from etherfood_studio.domain.models import StudioError
from test_pipeline_workspace import project, passthrough
from test_pipeline_execution import source_asset


def test_bundle_preserves_helpers_parameters_connections_and_not_approval(project, tmp_path):
    script, definition = passthrough(project)
    files = WorkspaceFiles(project)
    script = files.helper(script.id, "resources/example.txt", b"synthetic resource")
    workspace = PipelineWorkspace(project)
    checked = workspace.check(definition.id)
    workspace.approve(definition.id, checked["hash"])
    archive = tmp_path / "roundtrip.zip"
    service = WorkspaceExchange(project)
    service.export(definition.id, archive)
    imported = service.import_file(archive)
    assert len(imported["scripts"]) == len(imported["definitions"]) == 1
    imported_script = project.catalog.get(imported["scripts"][0])
    assert list(files.script_files(imported_script.id).values()).count(b"synthetic resource") == 1
    value, _ = files.definition(imported["definitions"][0])
    assert value["nodes"][0]["script_id"] == imported_script.id
    assert workspace.status(value["id"])[0] == "yellow"
    assert workspace.state(value["id"])["approved_hash"] is None
    assert workspace.check(value["id"])["valid"]


def test_import_does_not_execute_and_rejects_traversal_without_records(project, tmp_path):
    source = tmp_path / "bad.py"
    sentinel = tmp_path / "executed"
    source.write_text(f"from pathlib import Path\nPath({str(sentinel)!r}).touch()\n")
    exchange = WorkspaceExchange(project)
    result = exchange.import_file(source)
    assert result["scripts"] and not sentinel.exists()
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as file:
        file.writestr("../outside.py", "pass")
    before = [r.id for r in project.catalog.records()]
    with pytest.raises(StudioError):
        exchange.import_file(archive)
    assert [r.id for r in project.catalog.records()] == before


def test_external_current_source_becomes_new_revision_identical_save_is_noop(project, tmp_path):
    asset, original = source_asset(project, tmp_path, "Quelle", "red")
    service = SourceReconciliation(project)
    current, path = service.known()[0]
    original_raw = path.read_bytes()
    assert service.reconcile() == {"changed": [], "issues": []}
    Image.new("RGBA", (8, 8), "blue").save(path)
    result = service.reconcile()
    assert len(result["changed"]) == 1 and result["issues"] == []
    assert path.read_bytes() == original_raw
    assert project.catalog.get(original.id) == original
    active = project.catalog.get(asset.id).data["active_sources"]
    assert list(active.values()) == result["changed"]
    assert service.reconcile() == {"changed": [], "issues": []}
    _, new_path = service.known()[0]
    new_path.write_bytes(b"not a png")
    blocked = service.reconcile()
    assert blocked["issues"] and blocked["changed"] == []
    assert new_path.read_bytes() == b"not a png"
    assert project.catalog.get(asset.id).data["active_sources"] == active


def test_nested_legacy_bundle_imports_into_current_files_without_legacy_records(project, tmp_path):
    from etherfood_studio.application.tool_packages import ToolPackageService
    from etherfood_studio.application.tool_exchange import ToolExchange
    from legacy_fixtures import example

    packages = ToolPackageService(project)
    manifest, files = example()
    package = packages.register(packages.inspect_content(manifest, files))
    _, recipe = packages.recipe_data(package["digest"], "report")
    outer = dict(
        manifest,
        id="nested-test",
        name="Nested",
        steps=[],
        files=["README.txt"],
        flows=[dict(id="reports", name="Berichte", description="Nested", recipe=recipe)],
    )
    composed = packages.register(packages.inspect_content(outer, {"README.txt": b"Nested"}))
    target = tmp_path / "legacy.zip"
    ToolExchange(project).export_package(composed["digest"], target)
    # Export is only a fixture producer: importing never registers a second legacy library.
    before_packages = len(packages.packages())
    result = WorkspaceExchange(project).import_file(target)
    assert result["scripts"] and result["definitions"]
    assert len(packages.packages()) == before_packages
    workspace = PipelineWorkspace(project)
    for identifier in result["definitions"]:
        assert workspace.status(identifier)[0] == "yellow"
        assert workspace.state(identifier)["approved_hash"] is None
        value, _ = workspace.files.definition(identifier)
        assert all(node["script_id"] in result["scripts"] for node in value["nodes"])
    assert all(
        workspace.files.path(project.catalog.get(key)).is_file()
        for key in result["scripts"] + result["definitions"]
    )
    assert not any(
        row.kind in {"pipeline", "pipeline_assignment", "build"}
        for row in project.catalog.records()
    )
