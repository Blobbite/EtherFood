"""Current files, stable usages and approvals on isolated temporary projects."""

from copy import deepcopy

import pytest

from etherfood_studio.application.pipeline_workspace import PipelineWorkspace
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.workspace_files import WorkspaceFiles
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.pipeline_contract import INPUT, empty_definition


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "Projekt"
    root.mkdir()
    service = ProjectService.new(root, "Synthetische Pipelineprüfung")
    WorkspaceFiles(service).initialize()
    yield service
    service.catalog.close()


def passthrough(project, title="Kopie"):
    files = WorkspaceFiles(project)
    script = files.create_script(
        title,
        code=(
            "def run(context, inputs, parameters):\n"
            "    source = inputs['input']\n"
            "    result = context.artifact('copy.bin', source.type, source.metadata)\n"
            "    result.path.write_bytes(source.path.read_bytes())\n"
            "    return {'output': result}\n"
        ),
    )
    value = empty_definition("pending")
    value["inputs"] = {"input": {"type": "file"}}
    value["nodes"] = [{"id": "copy", "script_id": script.id, "parameters": {}}]
    value["connections"] = [{"from": INPUT, "out": "input", "to": "copy", "in": "input"}]
    value["folders"] = [
        {"id": "output", "node": "copy", "port": "output", "directory": "Kopien", "scope": "asset"}
    ]
    return script, files.create_definition(title, definition=value)


def test_new_workspace_remains_empty_after_open_and_refresh(project):
    service = PipelineWorkspace(project)
    assert service.scripts() == service.definitions() == service.usages() == []
    assert list((project.catalog.path.parent / ".tools/scrips").iterdir()) == []
    owner = next(row for row in project.cards() if row.kind == "global")
    project.create_card("asset", "Erstes Asset", owner.id)
    assert service.scripts() == service.definitions() == []
    reopened = ProjectService.open(project.catalog.path.parent)
    try:
        other = PipelineWorkspace(reopened)
        assert other.scripts() == other.definitions() == []
    finally:
        reopened.catalog.close()


def test_definition_without_assets_check_approve_and_external_change(project):
    script, definition = passthrough(project)
    service = PipelineWorkspace(project)
    assert service.status(definition.id)[0] == "yellow"
    checked = service.check(definition.id)
    assert checked["valid"], checked
    assert service.status(definition.id)[0] == "yellow"
    service.approve(definition.id, checked["hash"])
    assert service.status(definition.id)[0] == "green"
    file = service.files.path(script)
    file.write_text(file.read_text() + "\n# externe Änderung\n")
    assert service.status(definition.id)[0] == "yellow"
    with pytest.raises(StudioError, match="zuerst"):
        service.approve(definition.id, checked["hash"])
    missing = file.with_suffix(".away")
    file.rename(missing)
    assert service.status(definition.id)[0] == "red"
    assert not file.exists()  # No database-code fallback or recreation.


def test_save_invalid_python_preserves_draft_and_conflict(project):
    files = WorkspaceFiles(project)
    script = files.create_script("Entwurf")
    old, digest = files.text(script.id)
    changed, new_digest = files.save(script.id, "def broken(:\n", digest, script.revision_no)
    assert files.text(script.id) == ("def broken(:\n", new_digest)
    assert PipelineWorkspace(project).script_snapshot(script.id)["issues"]
    files.path(script).write_text("# extern\n")
    with pytest.raises(StudioError, match="extern geändert"):
        files.save(script.id, old, new_digest, changed.revision_no)
    assert files.path(script).read_text() == "# extern\n"


def test_current_writes_rollback_with_sql(project):
    files = WorkspaceFiles(project)
    before = set(project.catalog.path.parent.rglob("*.py"))
    with pytest.raises(RuntimeError):
        with project.catalog.transaction():
            files.create_script("Nicht übernehmen")
            raise RuntimeError("synthetic transaction failure")
    assert files.records("script") == []
    assert set(project.catalog.path.parent.rglob("*.py")) == before


def test_usage_identity_removal_and_explicit_graph(project):
    _, definition = passthrough(project)
    service = PipelineWorkspace(project)
    a = service.use(definition.id, [project.project().id])
    b = service.use(definition.id)
    b = service.update_usage(
        b.id,
        connections=[{"usage": a.id, "out": "output", "in": "input"}],
        expected_revision=b.revision_no,
    )
    assert service.usage_order() == [a.id, b.id]
    with pytest.raises(StudioError, match="Kreis"):
        service.update_usage(
            a.id,
            targets=[],
            connections=[{"usage": b.id, "out": "output", "in": "input"}],
            expected_revision=a.revision_no,
        )
    with pytest.raises(StudioError, match="gemischt"):
        service.update_usage(b.id, targets=[project.project().id], expected_revision=b.revision_no)
    project.archive(a.id, True, project.catalog.get(a.id).revision_no)
    assert len(service.definitions()) == len(service.scripts()) == 1
    with pytest.raises(StudioError, match="Vorgängerverwendung"):
        service.usage_order()


def test_layout_title_not_executable_and_move_keeps_ids(project):
    script, definition = passthrough(project)
    service = PipelineWorkspace(project)
    before = service.snapshot(definition.id)["hash"]
    project.catalog.save_layout(definition.id, {"x": 20, "y": 30})
    project.rename(definition.id, "Neuer Titel", definition.revision_no)
    assert service.snapshot(definition.id)["hash"] == before
    old_path = script.data["path"].removeprefix(".tools/scrips/")
    service.files.move(old_path, "Eigene/umbenannt.py")
    assert service.files.path(project.catalog.get(script.id)).is_file()
    value, _ = service.files.definition(definition.id)
    assert value["nodes"][0]["script_id"] == script.id


def test_local_import_move_refuses_broken_helpers(project):
    files = WorkspaceFiles(project)
    script = files.create_script(
        "Mit Hilfsdatei",
        path="Gruppe/main.py",
        code=(
            "from .helper import value\n" "def run(context, inputs, parameters):\n    return {}\n"
        ),
    )
    files.helper(script.id, "Gruppe/helper.py", b"value = 1\n")
    owner = project.project().id
    project.catalog.save_layout(owner, {"script_tree_order": {"folder:Gruppe": 3}})
    with pytest.raises(StudioError, match="Imports beschädigen"):
        files.move("Gruppe/main.py", "Andere/main.py")
    assert files.path(script).is_file()
    files.move("Gruppe", "Andere")
    assert files.path(project.catalog.get(script.id)).is_file()
    assert project.catalog.layout(owner)["script_tree_order"] == {"folder:Andere": 3}
    reopened = ProjectService.open(project.catalog.path.parent)
    try:
        assert reopened.catalog.layout(owner)["script_tree_order"] == {"folder:Andere": 3}
    finally:
        reopened.catalog.close()


def test_folder_traversal_and_image_sheet_conversion_are_rejected(project):
    script, definition = passthrough(project)
    service = PipelineWorkspace(project)
    data, digest = service.files.definition(definition.id)
    data["folders"][0]["directory"] = "../source"
    from etherfood_studio.domain.pipeline_contract import validate_definition

    with pytest.raises(StudioError):
        validate_definition(data, service.descriptions())
    data["folders"][0]["directory"] = "Kopien"
    data["inputs"]["input"]["type"] = "image"
    descriptions = deepcopy(service.descriptions())
    descriptions[script.id]["inputs"]["input"]["type"] = "spritesheet"
    with pytest.raises(StudioError, match="Anschlusstypen"):
        validate_definition(data, descriptions)
