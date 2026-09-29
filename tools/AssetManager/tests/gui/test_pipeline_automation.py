"""Actual Qt events plus isolated processes: automatic start, debounce, pause and cancellation."""

from time import monotonic, sleep
from pathlib import Path
import json

from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
import pytest
from PIL import Image

from etherfood_studio.application.pipeline_workspace import PipelineWorkspace
from etherfood_studio.application.source_reconciliation import SourceReconciliation
from etherfood_studio.application.workspace_files import WorkspaceFiles
from etherfood_studio.ui.main_window import MainWindow
from test_pipeline_execution import source_asset, approved


def wait_until(condition, seconds=15):
    end = monotonic() + seconds
    while not condition() and monotonic() < end:
        QTest.qWait(10)
        sleep(0.001)
    assert condition()


@pytest.fixture
def window(qt_app, tmp_path):
    root = tmp_path / "Projekt"
    root.mkdir()
    value = MainWindow(QSettings(str(tmp_path / "ui.ini"), QSettings.IniFormat))
    value.new_project(root, "Automatikprüfung")
    value.show()
    yield value
    value.processing.controller.stop()
    wait_until(lambda: not value.processing.busy)
    value.close()
    value.deleteLater()
    qt_app.processEvents()


def count_results(window):
    return window.project.catalog.db.execute("SELECT COUNT(*) FROM pipeline_results").fetchone()[0]


def test_first_approval_incremental_identical_content_no_feedback_and_pause(window, tmp_path):
    asset, source = source_asset(window.project, tmp_path, "Quelle", "red")
    script, definition, usage = approved(window.project, "Automatik", [asset.id])
    controller = window.processing.controller
    controller.schedule()
    wait_until(lambda: count_results(window) == 1 and not controller.busy)
    end = count_results(window)
    # Repeated notifications, a file saved with identical bytes and a Canvas move.
    path = WorkspaceFiles(window.project).path(script)
    path.write_bytes(path.read_bytes())
    for _ in range(5):
        controller.schedule()
    window.project.catalog.save_layout(usage.id, {"x": 420, "y": 900})
    wait_until(
        lambda: not controller.busy
        and not controller.pending
        and not controller.debounce.isActive()
    )
    assert count_results(window) == end
    service = PipelineWorkspace(window.project)
    service.pause(definition.id, True)
    _, visible = SourceReconciliation(window.project).known()[0]
    Image.new("RGBA", (8, 8), "blue").save(visible)
    controller.schedule()
    wait_until(
        lambda: not controller.busy
        and not controller.pending
        and not controller.debounce.isActive()
    )
    assert count_results(window) == end
    assert source.id not in window.project.catalog.get(asset.id).data["active_sources"].values()
    service.pause(definition.id, False)
    controller.schedule()
    wait_until(lambda: count_results(window) == end + 1 and not controller.busy)
    assert service.state(definition.id)["approved_hash"] == service.snapshot(definition.id)["hash"]
    assert not (window.project.catalog.path.parent / ".asset-studio/jobs").exists()


def test_running_worker_keeps_ui_responsive_cancel_never_publishes(window, tmp_path):
    asset, source = source_asset(window.project, tmp_path, "Langsam", "orange")
    script, definition, usage = approved(window.project, "Abbruch", [asset.id])
    files = WorkspaceFiles(window.project)
    code, digest = files.text(script.id)
    record, _ = files.save(
        script.id,
        code.replace("    source =", "    import time\n    time.sleep(30)\n    source ="),
        digest,
        script.revision_no,
    )
    service = PipelineWorkspace(window.project)
    check = service.check(definition.id)
    service.approve(definition.id, check["hash"])
    controller = window.processing.controller
    controller.schedule()
    wait_until(lambda: controller.states.get(usage.id, {}).get("state") == "running")
    window.set_main_editor(1)
    window.set_section(1)
    assert window.main_navigation.currentRow() == 1
    controller.cancel()
    wait_until(lambda: not controller.busy, 10)
    assert count_results(window) == 0
    assert controller.states[usage.id]["state"] == "cancelled"
    # There is no delayed completion that can turn the cancelled phase green/current.
    QTest.qWait(150)
    assert count_results(window) == 0
