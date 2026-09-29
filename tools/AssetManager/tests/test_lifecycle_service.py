"""Archive versus exact UTC trash deadlines, independent references and safe recovery."""

from datetime import datetime, timedelta, timezone

import pytest

from etherfood_studio.application.commands import Commands
from etherfood_studio.application.lifecycle_service import LifecycleService
from etherfood_studio.application.pipeline_workspace import PipelineWorkspace
from etherfood_studio.domain.models import StudioError
from test_pipeline_workspace import passthrough, project
from test_pipeline_execution import source_asset


def clocked(project):
    clock = [datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc)]
    return LifecycleService(project, now=lambda: clock[0]), clock


def test_exact_deadline_restore_cancels_and_archive_never_expires(project):
    lifecycle, clock = clocked(project)
    act = project.create_card("act", "Temporär", project.project().id)
    lifecycle.change([act.id], "trash")
    entry = lifecycle.state(act.id)
    assert datetime.fromisoformat(entry["purge_at"]) - clock[0] == timedelta(hours=720)
    clock[0] += timedelta(days=30) - timedelta(microseconds=1)
    assert lifecycle.purge() == []
    lifecycle.restore(act.id)
    clock[0] += timedelta(days=1)
    assert lifecycle.purge() == []
    assert not project.catalog.get(act.id).archived
    lifecycle.change([act.id], "archived")
    clock[0] += timedelta(days=3650)
    assert lifecycle.purge() == []
    lifecycle.restore(act.id)
    lifecycle.change([act.id], "trash")
    clock[0] += timedelta(days=30)
    assert lifecycle.purge() == [act.id]
    with pytest.raises(StudioError, match="nicht gefunden"):
        project.catalog.get(act.id)


def test_usage_archive_and_trash_never_change_shared_definition(project):
    _, definition = passthrough(project)
    workspace = PipelineWorkspace(project)
    first, second = workspace.use(definition.id), workspace.use(definition.id)
    lifecycle, clock = clocked(project)
    lifecycle.change([first.id], "archived")
    assert not project.catalog.get(second.id).archived
    assert not project.catalog.get(definition.id).archived
    lifecycle.restore(first.id)
    lifecycle.change([first.id], "trash")
    clock[0] += timedelta(days=30)
    lifecycle.purge()
    assert [r.id for r in workspace.usages()] == [second.id]
    assert len(workspace.definitions()) == len(workspace.scripts()) == 1


def test_reference_restore_drop_is_atomic_and_undoable(project, tmp_path):
    asset, _ = source_asset(project, tmp_path, "Original", "red")
    act = project.create_card("act", "Akt", project.project().id)
    other = project.create_card("act", "Anderer Akt", project.project().id)
    edge = project.relate(act.id, asset.id, "uses")
    lifecycle, _ = clocked(project)
    lifecycle.change([edge], "archived")
    assert edge not in {r["id"] for r in project.catalog.relations()}
    assert not project.catalog.get(asset.id).archived
    with pytest.raises(StudioError):
        lifecycle.restore(edge, target=asset.id)
    assert lifecycle.state(edge)["state"] == "archived"
    commands = Commands(project)
    lifecycle.command(commands, [edge], target=other.id)
    assert lifecycle.state(edge) is None
    assert next(r for r in project.catalog.relations() if r["id"] == edge)["source_id"] == other.id
    commands.undo()
    assert lifecycle.state(edge)["state"] == "archived"
    assert (
        next(r for r in project.catalog.relations(include_inactive=True) if r["id"] == edge)[
            "source_id"
        ]
        == act.id
    )


def test_original_purge_preserves_shared_blobs_and_external_files(project, tmp_path):
    one, source = source_asset(project, tmp_path, "Original1", "blue")
    two, shared = source_asset(project, tmp_path, "Original2", "blue")
    assert source.data["sha256"] == shared.data["sha256"]
    directory = project.files.path(one.id)
    foreign = directory / "fremde-datei.txt"
    foreign.write_text("Bleibt erhalten.")
    lifecycle, clock = clocked(project)
    lifecycle.change([one.id], "trash")
    clock[0] += timedelta(days=30)
    lifecycle.purge()
    assert foreign.read_text() == "Bleibt erhalten."
    from etherfood_studio.storage.blob_store import BlobStore

    assert (
        BlobStore(project.catalog, project.catalog.path.parent)
        .path_for(source.data["sha256"])
        .is_file()
    )
    assert project.catalog.get(two.id)
    assert (tmp_path / "Original1.png").is_file()


def test_selected_parent_and_child_removed_once_and_independent_archive_preserved(project):
    act = project.create_card("act", "Akt", project.project().id)
    chapter = project.create_card("chapter", "Kapitel", act.id)
    lifecycle, _ = clocked(project)
    lifecycle.change([chapter.id], "archived")
    lifecycle.change([act.id, chapter.id], "trash")
    assert len(lifecycle.entries("trash")) == 1
    lifecycle.restore(act.id)
    assert project.catalog.get(chapter.id).archived
    assert lifecycle.state(chapter.id)["state"] == "archived"
    for row in (project.project(), next(r for r in project.cards() if r.kind == "global")):
        with pytest.raises(StudioError):
            lifecycle.change([row.id], "trash")


def test_purge_asset_removes_only_its_outputs_and_frozen_run_files(project, tmp_path):
    from test_pipeline_execution import source_asset, approved
    from etherfood_studio.application.pipeline_execution import PipelineExecution
    from etherfood_studio.application.lifecycle_service import LifecycleService
    from datetime import datetime, timedelta, timezone

    a, _ = source_asset(project, tmp_path, "Löschen", "red")
    b, _ = source_asset(project, tmp_path, "Behalten", "blue")
    script, definition, usage = approved(project, "Beide", [project.project().id])
    engine = PipelineExecution(project)
    result = engine.run()
    assert result["state"] == "succeeded"
    old = [
        r["path"]
        for r in project.catalog.db.execute("SELECT * FROM pipeline_run_files")
        if r["asset_id"] == a.id
    ]
    retained = [
        r["path"]
        for r in project.catalog.db.execute("SELECT * FROM pipeline_run_files")
        if r["asset_id"] == b.id
    ]
    assert old and retained
    instant = datetime(2026, 9, 1, tzinfo=timezone.utc)
    life = LifecycleService(project, now=lambda: instant)
    life.change([a.id], "trash")
    instant += timedelta(days=30)
    life.purge()
    root = project.catalog.path.parent
    assert all(not (root / name).exists() for name in old)
    assert all((root / name).is_file() for name in retained)
    assert project.catalog.get(script.id) and project.catalog.get(definition.id)
    rows = project.catalog.db.execute("SELECT * FROM pipeline_results").fetchall()
    assert {r["asset_id"] for r in rows} == {b.id}


def test_purging_usage_removes_its_gallery_but_keeps_other_use_and_script(project, tmp_path):
    from test_pipeline_execution import approved
    from etherfood_studio.application.pipeline_execution import PipelineExecution

    asset, _ = source_asset(project, tmp_path, "Galerie", "navy")
    script, definition, usage = approved(project, "Galerie", [asset.id])
    other = PipelineWorkspace(project).use(definition.id, [asset.id])
    result = PipelineExecution(project).run()
    assert result["state"] == "succeeded"
    gallery = project.files.path(asset.id) / "Ergebnisse" / usage.id / "index.md"
    retained = project.files.path(asset.id) / "Ergebnisse" / other.id / "index.md"
    assert gallery.is_file() and retained.is_file()
    life, clock = clocked(project)
    life.change([usage.id], "trash")
    clock[0] += timedelta(days=30)
    life.purge()
    assert not gallery.exists() and retained.is_file()
    assert project.catalog.get(definition.id) and project.catalog.get(script.id)
