"""Signal-driven QProcess controller; no waitForFinished in the GUI thread."""

from PySide6.QtCore import QObject, QProcess, Signal


class ProcessRunner(QObject):
    event_received = Signal(str, object)
    finished = Signal(str, object)

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.active = {}
        self.buffers = {}
        self.logs = {}

    def start(self, request):
        identifier = request.job_id
        process = QProcess(self)
        self.active[identifier] = process
        self.buffers[identifier] = b""
        self.logs[identifier] = (self.service.workspace(identifier) /
                                 "logs/host-stderr.log").open("xb")
        process.readyReadStandardOutput.connect(lambda: self._stdout(identifier))
        process.readyReadStandardError.connect(lambda: self._stderr(identifier))
        process.errorOccurred.connect(lambda error: self._error(identifier, error))
        process.finished.connect(lambda code, status: self._done(identifier, code))
        argv = self.service.host_argv(request)
        process.setWorkingDirectory(str(self.service.workspace(identifier)))
        process.start(argv[0], list(argv[1:]))
        return identifier

    def cancel(self, identifier):
        process = self.active.get(identifier)
        if process is not None:
            self.service.store.cancelling(identifier)
            process.write(b"cancel\n")

    def _stdout(self, identifier):
        process = self.active[identifier]
        self.buffers[identifier] += bytes(process.readAllStandardOutput())
        while b"\n" in self.buffers[identifier]:
            line, self.buffers[identifier] = self.buffers[identifier].split(b"\n", 1)
            try:
                event = self.service.consume(identifier, line)
                self.event_received.emit(identifier, event)
            except Exception as error:
                self.logs[identifier].write((str(error) + "\n").encode())
                self.cancel(identifier)

    def _stderr(self, identifier):
        self.logs[identifier].write(bytes(self.active[identifier].readAllStandardError()))
        self.logs[identifier].flush()

    def _error(self, identifier, error):
        if error == QProcess.ProcessError.FailedToStart:
            result = self.service.start_failed(identifier, self.active[identifier].errorString())
            self._release(identifier, result)

    def _done(self, identifier, code):
        if identifier not in self.active:
            return
        self._stdout(identifier)
        self._stderr(identifier)
        result = self.service.complete(identifier, code)
        self._release(identifier, result)

    def _release(self, identifier, result):
        self.active.pop(identifier).deleteLater()
        self.logs.pop(identifier).close()
        self.buffers.pop(identifier)
        self.finished.emit(identifier, result)
