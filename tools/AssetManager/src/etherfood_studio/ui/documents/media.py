"""Document-scoped Qt media lifecycle shared by previews, tables and dialogs."""

import hashlib
import http.client
import threading
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from urllib.parse import unquote, urlsplit

from PySide6.QtCore import (
    QByteArray, QBuffer, QEvent, QIODevice, QObject, QSize, Qt, QTimer, Signal,
)
from PySide6.QtGui import QBrush, QColor, QImage, QImageReader, QMovie, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from ...application.document_resources import FileGrant, read_image_file
from ...domain.models import StudioError
from .media_source import MediaLimits, Transfer, download, inspect_image, origin
from ..theme import color
from ..appearance import appearance

STATES = {"permission": "noch nicht freigegeben", "loading": "wird geladen",
          "ready": "angezeigt", "paused": "pausiert", "hidden": "ausgeblendet",
          "missing": "Quelle fehlt", "unsupported": "Format nicht unterstützt",
          "failed": "Laden fehlgeschlagen", "blocked": "blockiert"}


def checkerboard(image):
    if not image.hasAlphaChannel():
        return image
    result = QImage(image.size(), QImage.Format_RGB32)
    tile = QImage(24, 24, QImage.Format_RGB32)
    tile.fill(QColor(color("base")))
    pattern = QPainter(tile)
    pattern.fillRect(0, 0, 12, 12, QColor(color("border")))
    pattern.fillRect(12, 12, 12, 12, QColor(color("border")))
    pattern.end()
    painter = QPainter(result)
    painter.fillRect(result.rect(), QBrush(tile))
    painter.drawImage(0, 0, image)
    painter.end()
    return result


@dataclass
class Resource:
    source: str
    key: str
    state: str = "permission"
    reason: str = "Zugriff erlauben, um das Bild zu laden."
    image: QImage = field(default_factory=QImage)
    display: QImage = field(default_factory=QImage)
    movie: object = None
    buffer: object = None
    memory: int = 0
    frame_count: int = 1
    transfer: object = None
    pending_origin: str = ""


class MediaSession(QObject):
    changed = Signal(str)
    finished = Signal(int, str, object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.limits = MediaLimits()
        self.identifier = None
        self.base = None
        self.generation = 0
        self.service = None
        self.resources = {}
        self.permissions = {}
        self.policy = "ask"
        self.autoplay = True
        self.reduced_motion = False
        self.pending = []
        self.running = set()
        self.memory_lock = threading.Lock()
        self.memory_used = 0
        self.finished.connect(self.accept_result)
        self.destroyed.connect(lambda: self.stop())
        self.window = None
        self.close_timer = QTimer(self)
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.window_closed)
        appearance().changed.connect(self.refresh_appearance)

    def refresh_appearance(self):
        for item in self.resources.values():
            item.display = QImage()
            self.changed.emit(item.key)

    def window_closed(self):
        if self.window and not self.window.isVisible():
            self.stop()

    def watch_window(self):
        parent = self.parent()
        window = parent.window() if isinstance(parent, QWidget) else None
        if window and window is not self.window:
            if self.window:
                self.window.removeEventFilter(self)
            self.window = window
            window.installEventFilter(self)

    def eventFilter(self, watched, event):
        if watched is self.window and event.type() == QEvent.Close:
            self.close_timer.start(0)
        return super().eventFilter(watched, event)

    def bind(self, service, identifier, base=None):
        if service is self.service and identifier == self.identifier and base == self.base:
            return
        self.stop()
        self.service, self.identifier, self.base = service, identifier, base

    def grants(self):
        return self.permissions.setdefault((id(self.service), self.identifier, self.base),
                                           {"urls": set(), "origins": set(), "private": set(),
                                               "files": {}})

    def stop(self):
        self.generation += 1
        self.pending.clear()
        for item in self.resources.values():
            self.dispose(item)
            item.state = "hidden"
            self.changed.emit(item.key)
        self.resources.clear()

    def retain(self, sources):
        for key, item in list(self.resources.items()):
            if item.source not in sources:
                self.dispose(item)
                item.state = "hidden"
                self.changed.emit(item.key)
                del self.resources[key]

    def dispose(self, item):
        if item.transfer:
            item.transfer.cancel()
            if not any(ticket[2] == id(item.transfer) for ticket in self.running):
                self.release(item.transfer)
        if item.movie:
            item.movie.stop()
            item.movie.deleteLater()
            item.movie = None
        if item.buffer:
            item.buffer.close()
            item.buffer.deleteLater()
            item.buffer = None
        item.image = QImage()
        item.display = QImage()
        item.memory = 0

    def reserve(self, transfer, amount):
        with self.memory_lock:
            if self.memory_used + amount > self.limits.memory:
                raise StudioError("blocked", "Bildspeicher belegt. Andere Bilder ausblenden.")
            self.memory_used += amount
            transfer.memory = amount

    def release(self, transfer):
        with self.memory_lock:
            self.memory_used -= getattr(transfer, "memory", 0)
            transfer.memory = 0

    def ensure(self, source):
        self.watch_window()
        key = hashlib.sha256(source.encode()).hexdigest()
        if key not in self.resources:
            item = Resource(source, key)
            self.resources[key] = item
            self.request(item)
        return self.resources[key]

    def permitted(self, source):
        scheme = urlsplit(source).scheme.lower()
        if scheme not in {"http", "https"}:
            return True
        if self.policy == "block":
            return False
        return source in self.grants()["urls"] or (scheme == "https" and self.policy == "https")

    def request(self, item):
        if item.state == "loading" or not self.permitted(item.source):
            if self.policy == "block":
                item.state = "blocked"
                item.reason = "Externe Bilder sind blockiert. Medienrichtlinie ändern."
            return
        try:
            parts = urlsplit(item.source)
            if parts.scheme in {"http", "https"}:
                current = origin(item.source)
                allowed = {current} | self.grants()["origins"]
                private = set(self.grants()["private"])
                loader = lambda transfer: download(item.source, limits=self.limits,
                    transfer=transfer,
                                                    permitted_origins=allowed,
                                                        private_origins=private)
            elif parts.scheme == "studio-svg":
                data = unquote(item.source.split(":", 1)[1]).encode("utf-8")
                loader = lambda transfer: data
            elif self.service and (self.identifier or self.base):
                path, digest = self.service.image_file(self.identifier, item.source,
                    self.grants()["files"],
                                                       base=self.base)
                loader = lambda transfer: read_image_file(path, self.limits.transferred, digest)
            elif parts.scheme == "file":
                path = Path(unquote(parts.path)).absolute()
                grant = self.grants()["files"].get(str(path))
                if not grant:
                    raise StudioError("permission",
                        "Datei gezielt über Zugriff erlauben auswählen.")
                loader = lambda transfer: read_image_file(path, self.limits.transferred,
                    grant.digest)
            else:
                raise StudioError("permission", "Ohne Projekt die konkrete Bilddatei auswählen.")
            item.state, item.reason = "loading", "Bild wird geladen; Ausblenden bricht ab."
            item.transfer = Transfer()
            self.pending.append((self.generation, item, loader))
            self.pump()
        except (StudioError, OSError, ValueError) as error:
            self.failure(item, error)

    def pump(self):
        while self.pending and len(self.running) < self.limits.concurrent:
            generation, item, loader = self.pending.pop(0)
            if generation != self.generation or item.transfer.cancelled.is_set():
                continue
            ticket = (generation, item.key, id(item.transfer))
            self.running.add(ticket)
            transfer = item.transfer

            def work(gen=generation, resource=item, load=loader, token=transfer, task=ticket):
                result, error = None, None
                try:
                    raw = load(token)
                    if token.cancelled.is_set():
                        return
                    result = inspect_image(raw, self.limits)
                    if result["format"] == "SVG":
                        renderer = QSvgRenderer(QByteArray(result["data"]))
                        renderer.setAnimationEnabled(False)
                        size = renderer.defaultSize()
                        if not renderer.isValid() or size.width() <= 0 or size.height() <= 0:
                            raise StudioError("unsupported",
                                "SVG konnte nicht vollständig dargestellt werden.")
                        if size.width() * size.height() > self.limits.pixels:
                            raise StudioError("blocked", "SVG überschreitet die Pixelgrenze.")
                        size = size.scaled(QSize(2048, 2048), Qt.KeepAspectRatio)
                        result["memory"] = size.width() * size.height() * 8 + len(raw)
                        self.reserve(token, result["memory"])
                        frame = QImage(size, QImage.Format_ARGB32_Premultiplied)
                        frame.fill(Qt.transparent)
                        painter = QPainter(frame)
                        renderer.render(painter)
                        painter.end()
                        result["image"] = frame
                    elif not result.get("animated"):
                        self.reserve(token, result["memory"])
                        result["image"] = QImage.fromData(result["data"])
                        if result["image"].isNull():
                            raise StudioError("unsupported",
                                "Bilddecoder unterstützt diese Datei nicht.")
                    else:
                        self.reserve(token, result["memory"])
                except (StudioError, OSError, ValueError, RuntimeError,
                    http.client.HTTPException) as exc:
                    error = exc
                finally:
                    if error or token.cancelled.is_set():
                        self.release(token)
                        result = None
                    try:
                        self.finished.emit(gen, resource.key, (task, result, token), error)
                    except RuntimeError:
                        self.release(token)

            threading.Thread(target=work, daemon=True, name="markdown-media").start()

    def failure(self, item, error):
        if item.movie:
            self.dispose(item)
        code = getattr(error, "code", "failed")
        item.state = code if code in STATES else "failed"
        item.reason = str(error)
        if code == "permission" and ": http" in str(error):
            item.pending_origin = str(error).split(": ", 1)[1]
        self.changed.emit(item.key)

    def accept_result(self, generation, key, payload, error):
        ticket, result, token = payload
        self.running.discard(ticket)
        item = self.resources.get(key)
        if (generation == self.generation and item and item.transfer is token
                and not token.cancelled.is_set()):
            if error:
                self.failure(item, error)
            elif result:
                memory = result.get("memory", 0)
                if memory > self.limits.memory:
                    self.failure(item, StudioError("blocked",
                        "Bildspeicher belegt. Andere Bilder ausblenden."))
                else:
                    item.memory, item.state, item.reason = memory, "ready", ""
                    item.frame_count = result.get("frames", 1)
                    if result.get("animated"):
                        item.buffer = QBuffer(self)
                        item.buffer.setData(QByteArray(result["data"]))
                        item.buffer.open(QIODevice.ReadOnly)
                        item.movie = QMovie(item.buffer, QByteArray(b"gif"), self)
                        item.movie.setCacheMode(QMovie.CacheNone)
                        item.movie.frameChanged.connect(lambda _, r=item: self.frame(r))
                        item.movie.error.connect(lambda code, r=item: self.movie_failed(r, code))
                        item.movie.finished.connect(lambda r=item: self.finished_movie(r))
                        if self.autoplay and not self.reduced_motion:
                            item.movie.start()
                        else:
                            item.movie.jumpToFrame(0)
                            item.state = "paused"
                    else:
                        item.image = result["image"]
                    self.changed.emit(key)
        else:
            self.release(token)
        self.pump()

    def frame(self, item):
        if item.key in self.resources and item.movie:
            item.image = item.movie.currentImage()
            item.display = QImage()
            self.changed.emit(item.key)

    def finished_movie(self, item):
        item.state = "paused"
        self.changed.emit(item.key)

    def movie_failed(self, item, code):
        # Qt 6.10 reports UnknownError on a normal GIF loop boundary, then restarts.
        # Ignore only EOF after every structurally verified frame was actually displayed.
        if (code == QImageReader.UnknownError and item.movie and item.buffer
                and item.buffer.atEnd() and not item.image.isNull()
                and item.movie.currentFrameNumber() == item.frame_count - 1):
            return
        reason = item.movie.lastErrorString() if item.movie else "Unbekannter Decoderfehler"
        # Do not close a QIODevice while the decoder is still inside its read callback.
        def report():
            if self.resources.get(item.key) is item and item.movie:
                self.failure(item, StudioError("failed", "GIF-Frame nicht lesbar: " + reason))
        QTimer.singleShot(0, self, report)

    def action(self, item, action, parent):
        if action == "allow":
            parts = urlsplit(item.source)
            if parts.scheme in {"http", "https"}:
                target = item.pending_origin or item.source
                local = "Lokaler Medienserver" in item.reason
                title = "Lokalen Medienserver freigeben?" if local else "Bildzugriff erlauben?"
                hint = target + ("\nFreigabe nur für diese Herkunft in diesem Dokument."
                    if local else
                                 "\nFreigabe nur für diese Bildadresse "
                                 "bzw. dieses Weiterleitungsziel.")
                if QMessageBox.question(parent, title, hint, QMessageBox.Yes | QMessageBox.No,
                                        QMessageBox.No) != QMessageBox.Yes:
                    return
                self.grants()["urls"].add(item.source)
                self.grants()["origins"].add(origin(target))
                if local:
                    self.grants()["private"].add(origin(target))
                item.pending_origin = ""
            else:
                path, _ = QFileDialog.getOpenFileName(parent, "Genau diese Bildquelle freigeben")
                if not path:
                    return
                expected = Path(unquote(parts.path)).absolute() if parts.scheme == "file" else None
                if expected and Path(path).absolute() != expected:
                    QMessageBox.information(parent, "Andere Quelle",
                        "Zum Ersetzen Quelle ändern verwenden.")
                    return
                grant = FileGrant.select(Path(path), self.limits.transferred)
                self.grants()["files"][str(grant.path)] = grant
            item.state = "permission"
            self.request(item)
        elif action == "hide":
            self.dispose(item)
            item.state, item.reason = "hidden", "Erneut versuchen zeigt die Quelle wieder an."
        elif action == "pause" and item.movie:
            paused = item.state != "paused"
            if paused:
                item.movie.setPaused(True)
            elif item.movie.state() == QMovie.NotRunning:
                item.movie.start()
            else:
                item.movie.setPaused(False)
            item.state = "paused" if paused else "ready"
        elif action == "retry":
            self.dispose(item)
            item.state = "permission"
            self.request(item)
        self.changed.emit(item.key)

    def set_policy(self, policy):
        self.policy = policy
        for item in self.resources.values():
            if urlsplit(item.source).scheme in {"https", "http"}:
                if policy == "block":
                    self.dispose(item)
                    item.state = "blocked"
                    item.reason = "Externe Bilder blockiert. Medienrichtlinie ändern."
                elif item.state in {"blocked", "permission"}:
                    self.request(item)
                self.changed.emit(item.key)

    def resource_image(self, key):
        item = self.resources.get(key)
        if item and not item.image.isNull():
            if item.display.isNull():
                item.display = checkerboard(item.image)
            return item.display
        placeholder = QImage(260, 36, QImage.Format_ARGB32)
        placeholder.fill(QColor("#737d87"))
        painter = QPainter(placeholder)
        painter.setPen(QColor("white"))
        painter.drawText(placeholder.rect().adjusted(5, 0, -5, 0), Qt.AlignVCenter,
                         STATES.get(item.state, "Bild") if item else "Bild")
        painter.end()
        return placeholder

    def image(self, key, width):
        image = self.resource_image(key)
        return image.scaledToWidth(min(image.width(), max(1, int(width))), Qt.SmoothTransformation)

    def display_size(self, key, width):
        item = self.resources.get(key)
        size = item.image.size() if item and not item.image.isNull() else QSize(260, 36)
        factor = min(1, max(1, int(width)) / size.width())
        return QSize(max(1, int(size.width() * factor)), max(1, int(size.height() * factor)))

    def markup(self, source, alt, title, width):
        item = self.ensure(source)
        size = self.display_size(item.key, width)
        return (f'<img src="studio-media:{item.key}" width="{size.width()}" '
                f'height="{size.height()}" alt="{escape(alt, quote=True)}" '
                f'title="{escape(title or alt, quote=True)}" />')


class MediaControls(QWidget):
    source_change = Signal(str)

    def __init__(self, session, sources, parent=None):
        super().__init__(parent)
        self.session = session
        self.rows = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        for source, alt in dict(sources).items():
            item = session.ensure(source)
            row, text = QHBoxLayout(), QLabel()
            text.setTextFormat(Qt.PlainText)
            text.setWordWrap(True)
            row.addWidget(text, 1)
            buttons = {}
            for action, title in (("allow", "Zugriff erlauben"), ("retry", "Erneut versuchen"),
                                  ("pause", "Pause / Fortsetzen"), ("hide", "Ausblenden"),
                                  ("zoom", "Bildansicht"), ("source", "Quelle ändern")):
                button = QPushButton(title)
                button.setAccessibleName(title + ": " + (alt or source))
                button.clicked.connect(lambda checked=False, value=action, r=item:
                                       self.zoom(r) if value == "zoom" else
                                       self.source_change.emit(r.source) if value == "source"
                                           else self.perform(r, value))
                row.addWidget(button)
                buttons[action] = button
            self.rows[item.key] = text, buttons, alt or Path(urlsplit(source).path).name or "Bild"
            layout.addLayout(row)
        session.changed.connect(self.refresh)
        self.refresh()

    def perform(self, item, action):
        try:
            self.session.action(item, action, self)
        except (StudioError, OSError, ValueError) as error:
            self.session.failure(item, error)

    def refresh(self, key=""):
        for identifier, (text, buttons, alt) in self.rows.items():
            if key and key != identifier:
                continue
            item = self.session.resources.get(identifier)
            if not item:
                continue
            label = alt + " · " + STATES[item.state] + (" · " + item.reason if item.reason else "")
            if text.text() != label:
                text.setText(label)
            buttons["allow"].setVisible(item.state == "permission")
            buttons["retry"].setVisible(item.state not in {"loading", "ready", "paused",
                "permission"})
            buttons["pause"].setVisible(item.movie is not None)
            buttons["hide"].setVisible(item.state in {"loading", "ready", "paused"})
            buttons["zoom"].setVisible(not item.image.isNull())

    def zoom(self, item):
        dialog = QDialog(self)
        dialog.setWindowTitle("Bildansicht · Originalgröße und Zoom")
        layout = QVBoxLayout(dialog)
        scroll, label = QScrollArea(), QLabel()
        scroll.setWidget(label)
        layout.addWidget(scroll)
        zoom = [1.0]

        def show(factor):
            from PySide6.QtGui import QPixmap
            zoom[0] = factor
            pixels = item.image.width() * item.image.height() * factor * factor
            if pixels * 4 > self.session.limits.memory // 4:
                QMessageBox.information(dialog, "Zoom begrenzt",
                    "Diese Zoomstufe überschreitet das Ansichtsbudget.")
                return
            frame = item.image.scaled(item.image.size() * factor, Qt.KeepAspectRatio,
                                       Qt.SmoothTransformation)
            label.setPixmap(QPixmap.fromImage(checkerboard(frame)))
            label.resize(frame.size())
        buttons = QHBoxLayout()
        for title, factor in (("−", 0.8), ("Originalgröße", 0), ("+", 1.25)):
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, f=factor:
                                   show(max(0.1, min(4, zoom[0] * f))) if f else show(1))
            buttons.addWidget(button)
        layout.addLayout(buttons)
        show(1)
        dialog.resize(800, 600)
        dialog.exec()
        dialog.deleteLater()
