"""Qt scheduling for one bounded serial pipeline run; all execution stays in services."""

from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QObject, QThread, QTimer, Qt, Signal

from ..application.lifecycle_service import LifecycleService
from ..application.pipeline_execution import PipelineExecution
from ..application.pipeline_workspace import PipelineWorkspace
from ..domain.models import StudioError


class PipelineWorker(QThread):
    result = Signal(object)
    event = Signal(object)

    def __init__(self, call, parent=None):
        super().__init__(parent)
        self.call = call

    def run(self):
        try:
            self.result.emit({"value": self.call(self.event.emit)})
        except Exception as error:
            self.result.emit({"error": str(error)})


class PipelineController(QObject):
    requested = Signal()
    changed = Signal()
    event = Signal(object)
    checked = Signal(str, object)
    idle = Signal()

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project, self.workspace = project, PipelineWorkspace(project)
        self.engine = PipelineExecution(project)
        self.worker = None
        self.states = {}
        self.pending = False
        self.closed = False
        self.last_error = ""
        self.source_stamp = None
        self.watcher = QFileSystemWatcher(self)
        self.watcher.fileChanged.connect(self.schedule)
        self.watcher.directoryChanged.connect(self.schedule)
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.setInterval(750)
        self.debounce.timeout.connect(self.reconcile)
        self.cleanup = QTimer(self)
        self.cleanup.setInterval(60_000)
        self.cleanup.timeout.connect(self.maintenance)
        self.cleanup.start()
        self.requested.connect(self.schedule, Qt.QueuedConnection)
        self.project.pipeline_changed = self.requested.emit
        self.project.catalog.pipeline_changed = self.requested.emit
        self.watch()

    @property
    def busy(self):
        return self.worker is not None

    def watch(self):
        old = self.watcher.files() + self.watcher.directories()
        if old:
            self.watcher.removePaths(old)
        names = set()
        for record in self.workspace.scripts():
            names.add(record.data["path"])
            names.update(".tools/scrips/" + h for h in record.data.get("helpers", []))
        names.update(r.data["path"] for r in self.workspace.definitions())
        root = self.project.catalog.path.parent
        paths = {root / name for name in names}
        paths.update(path.parent for path in list(paths))
        paths.update(root / path for path in (".tools/scrips", ".tools/piplins"))
        from ..application.source_reconciliation import SourceReconciliation

        try:
            paths.update(path for _, path in SourceReconciliation(self.project).known())
        except (StudioError, OSError):
            pass  # Reconciliation reports unsafe/missing source paths in the overview.
        paths.update(path.parent for path in list(paths))
        present = [str(path) for path in paths if path.exists() and not path.is_symlink()]
        if present:
            self.watcher.addPaths(present)

    def schedule(self, *unused):
        if self.closed:
            return
        self.pending = True
        self.debounce.start()

    def _start(self, call, finish):
        if self.worker is not None:
            self.pending = True
            return False
        worker = PipelineWorker(call, self)
        self.worker = worker
        worker.event.connect(self._event)
        worker.result.connect(finish)
        worker.finished.connect(lambda: self._finished(worker))
        worker.start()
        self.changed.emit()
        return True

    def _finished(self, worker):
        self.worker = None
        worker.deleteLater()
        if not self.closed:
            self.watch()
        self.changed.emit()
        self.idle.emit()
        if self.pending and not self.closed:
            self.debounce.start()

    def _event(self, event):
        if "usage_id" in event:
            self.states[event["usage_id"]] = event
        self.event.emit(event)

    def check(self, identifier):
        def checked(result):
            self.checked.emit(identifier, result)
            self.changed.emit()

        return self._start(lambda emit: self.workspace.check(identifier), checked)

    def reconcile(self):
        if self.closed:
            return
        if self.busy:
            self.pending = True
            return
        from ..application.source_reconciliation import SourceReconciliation

        sources = SourceReconciliation(self.project)
        try:
            stamp = sources.stamp()
        except (StudioError, OSError) as error:
            self.last_error = str(error)
            self.changed.emit()
            return
        if stamp != self.source_stamp:
            self.source_stamp = stamp
            self.debounce.start()
            return
        self.pending = False

        def calculate(emit):
            self.engine.cancelled.clear()
            reconciled = sources.reconcile(cancelled=self.engine.cancelled.is_set)
            plan = self.engine.plan()
            for entry in plan["entries"].values():
                assets = {row["asset_id"] for row in entry["rows"]}
                entry["issues"].extend(
                    issue["reason"] for issue in reconciled["issues"] if issue["asset_id"] in assets
                )
            for entry in plan["entries"].values():
                if entry["issues"]:
                    emit(
                        {
                            "usage_id": entry["usage"].id,
                            "state": "blocked",
                            "reason": "\n".join(entry["issues"]),
                        }
                    )
            # Only an explicitly approved executable file set can enter automatic processing.
            runnable = any(
                entry["snapshot"]
                and not entry["issues"]
                and self.workspace.state(entry["snapshot"]["id"])["approved_hash"]
                == entry["snapshot"]["hash"]
                and not self.workspace.state(entry["snapshot"]["id"])["paused"]
                and not entry["usage"].data["paused"]
                for entry in plan["entries"].values()
            )
            return (
                self.engine.run(plan=plan, on_event=emit)
                if runnable
                else {"phases": [], "plan": plan}
            )

        def finished(result):
            self.last_error = result.get("error", "")
            if not self.last_error:
                for phase in result["value"].get("phases", []):
                    self.states[phase["usage_id"]] = phase
            self.changed.emit()

        self._start(calculate, finished)

    def cancel(self):
        self.pending = False
        self.debounce.stop()
        self.engine.cancel()

    def maintenance(self):
        if self.closed:
            return
        if LifecycleService(self.project).due():
            if self.busy:
                self.cancel()
                return
            try:
                LifecycleService(self.project).purge(
                    on_purged=lambda ids: self.event.emit({"state": "purged", "ids": ids})
                )
                self.changed.emit()
            except (StudioError, OSError) as error:
                self.last_error = str(error)
                self.changed.emit()

    def stop(self):
        self.closed = True
        self.cleanup.stop()
        self.debounce.stop()
        self.pending = False
        self.engine.cancel()
        self.project.pipeline_changed = None
        self.project.catalog.pipeline_changed = None
        return not self.busy
