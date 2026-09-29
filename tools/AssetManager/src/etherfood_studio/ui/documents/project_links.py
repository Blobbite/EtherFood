"""Navigate only catalog documents and verified, generated project galleries."""

from urllib.parse import unquote

from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QImageReader, QTextCursor, QTextDocument
from PySide6.QtWidgets import QDialog, QInputDialog, QMessageBox, QTextEdit, QVBoxLayout

from .preview import SafePreview
from .media import MediaControls, MediaSession
from .markdown_syntax import headings
from ..theme import color
from ...application.project_documents import read_markdown
from ...domain.models import StudioError


def image_resource(service, base, resource_type, url):
    if resource_type != QTextDocument.ImageResource:
        return None
    target = service.resolve_link(base, url.path())
    if not target or target["kind"] != "image":
        return None
    reader = QImageReader(str(target["path"]))
    size = reader.size()
    if size.width() <= 0 or size.height() <= 0 or size.width() * size.height() > 32_000_000:
        return None
    if size.width() > 512 or size.height() > 256:
        reader.setScaledSize(size.scaled(QSize(512, 256), Qt.KeepAspectRatio))
    return reader.read()


class ProjectMarkdownView(QDialog):
    def __init__(self, service, path, parent=None):
        super().__init__(parent)
        self.service, self.path = service, path
        self.resize(900, 650)
        self.view = SafePreview(self)
        self.media = MediaSession(self)
        self.view.media = self.media
        self.media.changed.connect(self.view.update_media)
        self.controls = None
        self.view.local_link = self.follow
        self.view.local_resource = lambda kind, url: image_resource(
            self.service, self.path, kind, url)
        layout = QVBoxLayout(self)
        layout.addWidget(self.view)
        self.show_path(path)
        self.finished.connect(lambda _: self.media.stop())

    def show_path(self, path, body=None):
        self.path = path
        self.body = body if body is not None else read_markdown(path)[0]
        self.media.bind(self.service, None, path)
        self.view.setExtraSelections([])
        self.setWindowTitle(path.name + " · Projektdokumentation")
        self.view.preview(self.body)
        if self.controls:
            self.layout().removeWidget(self.controls)
            self.controls.deleteLater()
        self.controls = MediaControls(self.media, self.view.media_sources, self)
        self.layout().addWidget(self.controls)

    def scroll_section(self, fragment):
        if unquote(fragment) not in {h.identifier for h in headings(self.body)}:
            QMessageBox.information(self, "Abschnitt fehlt", "Abschnitt nicht gefunden: "
                + fragment)
            return
        self.view.scrollToAnchor(unquote(fragment))
        block = self.view.document().begin()
        while block.isValid():
            iterator = block.begin()
            while not iterator.atEnd():
                if unquote(fragment) in iterator.fragment().charFormat().anchorNames():
                    selection = QTextEdit.ExtraSelection()
                    selection.cursor = QTextCursor(block)
                    selection.cursor.select(QTextCursor.BlockUnderCursor)
                    selection.format.setBackground(QColor(color("selection")))
                    self.view.setExtraSelections([selection])
                    QTimer.singleShot(1500, self, lambda: self.view.setExtraSelections([]))
                    return
                iterator += 1
            block = block.next()

    def follow(self, url):
        try:
            wiki = url.scheme() == "studio-wiki"
            if wiki:
                url = QUrl(unquote(url.toString().split(":", 1)[1]))
            if url.path():
                targets = self.service.link_candidates(None, url.toString(QUrl.FullyEncoded),
                                                       wiki=wiki, base=self.path)
                if not targets:
                    raise StudioError("missing", "Internes Markdown-Dokument fehlt.")
                if len(targets) > 1:
                    labels = [str(t["path"].relative_to(self.service.catalog.path.parent))
                        for t in targets]
                    choice, accepted = QInputDialog.getItem(self, "Dokument auswählen",
                        "Mehrere passende Dokumente:",
                                                          labels, editable=False)
                    if not accepted:
                        return
                    target = targets[labels.index(choice)]
                else:
                    target = targets[0]
                if target["kind"] == "document":
                    self.show_path(target["path"],
                        self.service.catalog.get(target["id"]).data["body"])
                elif target["kind"] == "index":
                    self.show_path(target["path"])
                else:
                    raise StudioError("missing", "Ziel ist kein Markdown-Dokument.")
            if url.fragment():
                self.scroll_section(url.fragment())
        except (StudioError, OSError, ValueError) as error:
            QMessageBox.information(self, "Dokument nicht verfügbar", str(error))
