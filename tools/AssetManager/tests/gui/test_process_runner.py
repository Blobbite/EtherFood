"""Actual Qt process lifecycle and responsive navigation during a long worker."""

import time

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtTest import QTest

from etherfood_studio.ui.main_window import MainWindow


def wait_for(predicate, seconds=6):
    deadline = time.monotonic() + seconds
    while not predicate() and time.monotonic() < deadline:
        QTest.qWait(10)
    assert predicate()


def test_live_qprocess_keeps_gui_responsive_and_cancels(qt_app, tmp_path):
    window = MainWindow(QSettings(str(tmp_path / "ui.ini"), QSettings.IniFormat))
    root = tmp_path / "project"
    root.mkdir()
    window.new_project(root, "Prozesse")
    ids = window.project.demo()
    window.show_jobs()
    dialog = window.job_dialog
    ticks = []
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start(10)
    request = dialog.service.prepare(ids["hero"], parameters={"mode": "child"})
    dialog.runner.start(request)
    log = dialog.service.workspace(request.job_id) / "logs/stdout.log"
    wait_for(lambda: log.exists() and b"child-ready" in log.read_bytes())
    assert window.select_card(ids["two"])
    window.tabs.setCurrentWidget(window.notes)
    # Process readiness may arrive before three timer intervals on a fast machine.
    wait_for(lambda: len(ticks) > 2)
    assert window.tabs.currentWidget() is window.notes and len(ticks) > 2
    assert not window.open_project(root)  # Never close a live worker's catalog.
    dialog.runner.cancel(request.job_id)
    wait_for(lambda: not dialog.runner.active)
    assert dialog.service.store.get(request.job_id)["status"] == "cancelled"
    QTest.qWait(1600)
    assert not (dialog.service.workspace(request.job_id) / "output/late-child.txt").exists()
    timer.stop()
    window.close()


def test_qprocess_start_error_and_verified_success(qt_app, tmp_path, monkeypatch):
    window = MainWindow(QSettings(str(tmp_path / "ui.ini"), QSettings.IniFormat))
    root = tmp_path / "project"
    root.mkdir()
    window.new_project(root, "Startfehler")
    window.show_jobs()
    service, runner = window.job_dialog.service, window.job_dialog.runner
    request = service.prepare(window.project.project().id)
    runner.start(request)
    wait_for(lambda: not runner.active)
    assert service.store.get(request.job_id)["status"] == "succeeded"
    request = service.prepare(window.project.project().id)
    monkeypatch.setattr(service, "host_argv", lambda request: ("/missing-studio-executable",))
    runner.start(request)
    wait_for(lambda: not runner.active)
    assert service.store.get(request.job_id)["status"] == "failed"
    window.close()
