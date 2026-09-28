"""Navigate only catalog documents and verified, generated project galleries."""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImageReader, QTextDocument
from PySide6.QtWidgets import QDialog, QVBoxLayout

from .preview import SafePreview


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
        self.view.local_link = self.follow
        self.view.local_resource = lambda kind, url: image_resource(
            self.service, self.path, kind, url)
        layout = QVBoxLayout(self)
        layout.addWidget(self.view)
        self.show_path(path)

    def show_path(self, path, body=None):
        self.path = path
        self.setWindowTitle(path.name + " · Projektdokumentation")
        self.view.preview(body if body is not None else path.read_text(encoding="utf-8"))

    def follow(self, url):
        target = self.service.resolve_link(self.path, url.path())
        if target and target["kind"] == "document":
            self.show_path(target["path"], self.service.catalog.get(target["id"]).data["body"])
        elif target and target["kind"] == "index":
            self.show_path(target["path"])
