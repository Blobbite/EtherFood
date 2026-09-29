"""Backed up, journalled conversion; interrupted migration never duplicates active files."""

import json

import pytest

from etherfood_studio.application.document_service import DocumentService
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.pipeline_workspace import PipelineWorkspace
from etherfood_studio.application.tool_packages import ToolPackageService
from etherfood_studio.application.workspace_migration import WorkspaceMigration
from test_pipeline_workspace import project
from legacy_fixtures import example, source_asset


def legacy_content(project, tmp_path):
    tools = ToolPackageService(project)
    manifest, files = example()
    package = tools.register(tools.inspect_content(manifest, files))
    definition = tools.create_recipe(package["digest"], "report")
    asset, _ = source_asset(project, tmp_path)
    assignment = PipelineService(project).assign(definition.id, asset_id=asset.id)
    doc = DocumentService(project).create(definition.id, "Erhalten", "# Eigener Text\n\n001\n")
    return definition, assignment, doc


def test_empty_migration_does_not_register_examples(project):
    migration = WorkspaceMigration(project)
    result = migration.run()
    assert result["backup"] is None
    assert result["scripts"] == result["definitions"] == result["usages"] == []
    assert PipelineWorkspace(project).scripts() == []
    assert migration.run() == result


def test_existing_definition_usages_documents_and_bound_code_survive(project, tmp_path):
    old, assignment, document = legacy_content(project, tmp_path)
    migration = WorkspaceMigration(project)
    result = migration.run()
    assert result["backup"]
    backup = project.catalog.path.parent / result["backup"]
    assert (backup / "catalog.sqlite").is_file()
    assert json.loads((backup / "manifest.json").read_text())["files"]
    workspace = PipelineWorkspace(project)
    assert [r.id for r in workspace.definitions()] == [old.id]
    assert [r.id for r in workspace.usages()] == [assignment.id]
    assert workspace.usages()[0].data["targets"] == [assignment.data["asset_id"]]
    script = workspace.scripts()[0]
    assert "from helper import size" in workspace.files.text(script.id)[0]
    assert workspace.files.path(script).is_relative_to(
        project.catalog.path.parent / ".tools/scrips"
    )
    assert project.catalog.get(document.id).data["body"] == "# Eigener Text\n\n001\n"
    assert DocumentService(project).path(document.id).is_file()
    assert workspace.state(old.id)["approved_hash"] is None
    before = len(project.catalog.records(include_archived=True))
    assert migration.run() == result
    assert len(project.catalog.records(include_archived=True)) == before


def test_interruption_rolls_back_files_and_reuses_backup(project, tmp_path):
    old, assignment, document = legacy_content(project, tmp_path)
    migration = WorkspaceMigration(project)

    def interrupt(step):
        if step == "definitions":
            raise RuntimeError("synthetic interruption")

    with pytest.raises(RuntimeError, match="synthetic"):
        migration.run(checkpoint=interrupt)
    assert project.catalog.get(old.id).kind == "pipeline"
    assert PipelineWorkspace(project).scripts() == []
    assert not list((project.catalog.path.parent / ".tools/scrips").rglob("*.py"))
    result = migration.run()
    assert result["definitions"] == [old.id]
    assert len(PipelineWorkspace(project).scripts()) == 1
    assert list((project.catalog.path.parent / ".asset-studio/migrations").iterdir()) == [
        project.catalog.path.parent / result["backup"]
    ]


def test_result_transfer_retires_tables_and_preserves_unknown_files(project):
    # Isolated synthetic job, build and result evidence.
    from etherfood_studio.domain.models import new_id, utc_now
    from etherfood_studio.storage.sqlite_repository import canonical
    from etherfood_studio.storage.blob_store import file_hash

    job_id = new_id()
    root = project.catalog.path.parent
    output = root / ".asset-studio/jobs" / job_id / "output"
    output.mkdir(parents=True)
    file = output / "report.json"
    file.write_text('{"value": 42}')
    foreign = output.parent / "private.txt"
    foreign.write_text("Fremde Notiz")
    manifest = [{"path": file.name, "length": file.stat().st_size, "sha256": file_hash(file)}]
    owner = project.project().id
    with project.catalog.transaction():
        project.catalog.db.execute(
            "INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?)",
            (
                job_id,
                canonical({"inputs": [], "outputs": [file.name]}),
                "succeeded",
                "fixture",
                0,
                "",
                canonical({"files": manifest}),
                utc_now(),
            ),
        )
        build = project.catalog.create(
            "build",
            "Alter Bericht",
            owner,
            {
                "contract": "studio-build-v1",
                "job_id": job_id,
                "diagnostic": False,
                "outputs": manifest,
                "dependencies": {},
                "input_fingerprint": "legacy-fingerprint",
                "node_key": "report",
                "tools": [],
            },
        )
    migration = WorkspaceMigration(project)

    def interrupt(step):
        if step == "retired":
            raise RuntimeError("interrupted after drop")

    with pytest.raises(RuntimeError):
        migration.run(checkpoint=interrupt)
    assert file.exists()
    assert project.catalog.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1
    assert project.catalog.db.execute("SELECT COUNT(*) FROM pipeline_results").fetchone()[0] == 0
    result = migration.run()
    tables = {row[0] for row in project.catalog.db.execute("SELECT name FROM sqlite_master")}
    assert not tables & {
        "jobs",
        "job_events",
        "build_cache",
        "asset_publications",
        "workflow_publications",
    }
    evidence = project.catalog.db.execute(
        "SELECT * FROM pipeline_results WHERE id=?", (build.id,)
    ).fetchone()
    migrated = json.loads(evidence["outputs"])["report"][0]
    assert (root / migrated["path"]).read_text() == '{"value": 42}'
    assert evidence["current"] == 0
    assert not file.exists() and foreign.read_text() == "Fremde Notiz"
    assert migration.run() == result
    assert (root / result["backup"] / "catalog.sqlite").is_file()
