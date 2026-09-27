"""Real processes, failure evidence, original protection and persistent admission."""

from dataclasses import FrozenInstanceError
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from etherfood_studio.application.job_service import JobService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.domain.models import StudioError
from etherfood_studio.pipelines.base import BuildRequest
from etherfood_studio.pipelines.processes import identity
from etherfood_studio.storage.blob_store import BlobStore, file_hash


@pytest.fixture
def jobs(tmp_path):
    root = tmp_path / "Projekt mit Leerzeichen ; $(nichts)"
    root.mkdir()
    project = ProjectService.new(root, "Diagnose")
    service = JobService(project)
    yield service
    project.catalog.close()


@pytest.mark.parametrize("mode,status,code", [
    ("success", "succeeded", 0), ("exit7", "failed", 7), ("missing", "failed", 0),
])
def test_real_worker_exit_verify_and_raw_logs(jobs, mode, status, code):
    value = '$(touch nope); "Ausgabe" & !'
    request = jobs.prepare(jobs.project.project().id, parameters={"mode": mode, "value": value})
    assert BuildRequest.from_data(request.to_data()) == request
    with pytest.raises(FrozenInstanceError):
        request.timeout = 1
    result = jobs.run(request)
    directory = jobs.workspace(request.job_id)
    assert result["status"] == status, (result, (directory / "logs/host-stderr.log").read_text())
    assert result["exit_code"] == code
    events = jobs.store.events(request.job_id)
    assert [v["seq"] for v in events] == list(range(1, len(events) + 1))
    assert events[0]["kind"] == "started" and events[-1]["kind"] == "finished"
    assert (directory / "logs/stderr.log").read_bytes() == b"Diagnose stderr\n"
    assert not (directory / "output/nope").exists()
    if status == "succeeded":
        assert {r["path"] for r in result["files"]} == {"result.json", "report.json"}
        assert json.loads((directory / "output/result.json").read_text())["value"] == value
    else:
        assert any(v["kind"] == "error" for v in events)


def test_timeout_and_child_cancellation_prevent_late_writes(jobs):
    owner = jobs.project.project().id
    request = jobs.prepare(owner, parameters={"mode": "slow"}, timeout=0.15)
    assert "Zeitlimit" in jobs.run(request)["reason"]
    request = jobs.prepare(owner, parameters={"mode": "child"})
    log = jobs.workspace(request.job_id) / "logs/stdout.log"
    result = jobs.run(request, cancelled=lambda: log.exists()
                      and b"child-ready" in log.read_bytes())
    assert result["status"] == "cancelled"
    time.sleep(1.6)
    assert not (jobs.workspace(request.job_id) / "output/late-child.txt").exists()


def test_registered_help_adapter_and_unknown_commands(jobs):
    with pytest.raises(StudioError, match="registriert"):
        jobs.prepare(jobs.project.project().id, "evil.py")
    with pytest.raises(StudioError, match="Argumente"):
        jobs.prepare(jobs.project.project().id, "framreduce-help", {"argv": ["rm"]})
    request = jobs.prepare(jobs.project.project().id, "framreduce-help")
    result = jobs.run(request)
    assert result["status"] == "succeeded", result
    assert b"--dry-run" in (jobs.workspace(request.job_id) / "output/help.txt").read_bytes()


def test_original_copied_never_renamed_or_linked(jobs, tiny_sheet):
    owner = jobs.project.demo()["hero"]
    blob = BlobStore(jobs.project.catalog, jobs.root).import_file(tiny_sheet)
    revision = jobs.project.catalog.create("source_revision", "Quelle", owner, blob)
    before = file_hash(tiny_sheet)
    request = jobs.prepare(owner, source_ids=(revision.id,))
    assert jobs.run(request)["status"] == "succeeded"
    copied = jobs.workspace(request.job_id) / "input" / (revision.id + ".png")
    assert file_hash(copied) == before == file_hash(tiny_sheet)
    assert copied.stat().st_ino != tiny_sheet.stat().st_ino
    copied.write_bytes(b"Only the disposable copy changes")
    assert file_hash(tiny_sheet) == before
    assert file_hash(BlobStore(jobs.project.catalog, jobs.root).path_for(before)) == before


def test_parallel_limit_writer_lock_and_recovery(jobs):
    owner = jobs.project.project().id
    one = jobs.prepare(owner)
    with pytest.raises(StudioError, match="Ergebnisbereich"):
        jobs.prepare(owner)
    two = jobs.prepare(owner, resource_key="second-target")
    with pytest.raises(StudioError, match="Parallelitätsgrenze"):
        jobs.prepare(owner, resource_key="third-target")
    assert jobs.run(one)["status"] == "succeeded"
    jobs.store.finish(two.job_id, {"status": "interrupted", "reason": "simulated crash"})
    jobs.store.finish(two.job_id, {"status": "succeeded"})
    assert jobs.store.get(two.job_id)["status"] == "interrupted"
    orphan = jobs.prepare(owner)
    jobs.project.catalog.db.execute("UPDATE jobs SET owner_stamp='dead-instance' WHERE id=?",
                                    (orphan.job_id,))
    JobService(jobs.project)
    assert jobs.store.get(orphan.job_id)["status"] == "interrupted"


def test_start_failure_is_terminal(jobs, monkeypatch):
    request = jobs.prepare(jobs.project.project().id)
    monkeypatch.setattr(jobs, "host_argv", lambda request: ("/missing-studio-executable",))
    assert jobs.run(request)["status"] == "failed"
    assert "Prozessstart" in jobs.store.get(request.job_id)["result"]["reason"]


def test_core_import_has_no_qt_dependency():
    source = Path(__file__).resolve().parents[1] / "src"
    code = (f"import sys; sys.path.insert(0, {str(source)!r}); "
            "from etherfood_studio.application.job_service import JobService; "
            "assert not any(k.startswith('PySide') for k in sys.modules)")
    subprocess.run([sys.executable, "-I", "-c", code], check=True)


def test_parent_crash_stops_child_and_recovery_never_claims_success(jobs):
    source = Path(__file__).resolve().parents[1] / "src"
    code = (f"import sys; sys.path.insert(0, {str(source)!r}); from pathlib import Path; "
            "from etherfood_studio.application.project_service import ProjectService; "
            "from etherfood_studio.application.job_service import JobService; "
            f"p=ProjectService.open(Path({str(jobs.root)!r})); j=JobService(p); "
            "r=j.prepare(p.project().id,parameters={'mode':'child'}); j.run(r)")
    parent = subprocess.Popen([sys.executable, "-I", "-c", code])
    try:
        deadline = time.monotonic() + 5
        directory = None
        while time.monotonic() < deadline:
            rows = jobs.store.rows()
            if rows:
                directory = jobs.workspace(rows[0]["id"])
                log = directory / "logs/stdout.log"
                if log.exists() and b"child-ready" in log.read_bytes():
                    break
            time.sleep(0.02)
        else:
            pytest.fail("Child did not start")
        parent.kill()
        parent.wait()
        time.sleep(1.7)
        assert not (directory / "output/late-child.txt").exists()
        jobs.store.recover()
        assert jobs.store.rows()[0]["status"] == "interrupted"
        process = json.loads((directory / "process.json").read_text())
        assert identity(process["pid"]) != process["stamp"]
    finally:
        if parent.poll() is None:
            parent.terminate()
            parent.wait()
