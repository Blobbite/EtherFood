"""Background planning and executable diagnostic cache exposed in the real Qt dialog."""

import time

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QCoreApplication, QEvent, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.ui.build_plan import BuildPlanDialog


def wait_for(predicate):
    deadline = time.monotonic() + 15
    while not predicate() and time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(0.005)  # Let the Python QThread run, not only Qt native event handlers.
    assert predicate()


def test_diagnostic_plan_execution_and_verified_reuse(qt_app, tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    project = ProjectService.new(root, "Buildplan")
    dialog = BuildPlanDialog(project, project.project().id)
    dialog.show()
    ticks = []
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start(10)
    dialog.preview()
    wait_for(lambda: dialog.worker is None)
    assert dialog.plan is not None and dialog.plan.counts["new"] == 1
    assert dialog.run_button.isEnabled()
    dialog.execute()
    assert not dialog.plan_button.isEnabled()
    wait_for(lambda: dialog.worker is None)
    assert "succeeded" in dialog.summary.text(), dialog.details.toPlainText()
    assert len(ticks) > 3
    dialog.preview()
    wait_for(lambda: dialog.worker is None)
    assert dialog.plan.counts["reused"] == 1
    assert "Wiederverwendet: 1" in dialog.summary.text()
    first = dialog.tree.topLevelItem(0)
    assert first.text(0) == "Masterprofil"
    dialog.tree.setCurrentItem(first)
    assert "Input-Fingerprint:" in dialog.details.toPlainText()
    assert "Ergebnisdigest:" in dialog.details.toPlainText()
    timer.stop()
    dialog.close()
    dialog.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qt_app.processEvents()
    project.catalog.close()
