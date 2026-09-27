"""Small contrast-aware action glyphs, independent of platform icon themes."""

from math import cos, pi, sin

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

from .theme import color


def action_icon(name: str) -> QIcon:
    if name in {"new_asset", "asset_workspace", "new_note", "new_task", "new_issue",
                "new_document", "add_act", "add_chapter"}:
        from .presentation import kind_icon
        kind = {"asset_workspace": "asset", "new_document": "document"}.get(
            name, name.removeprefix("new_").removeprefix("add_"))
        return kind_icon(kind)
    if "settings" in name:
        glyph = "settings"
    elif name.startswith("document_align_"):
        glyph = name.removeprefix("document_align_")
    elif name == "markdown_mode_md":
        glyph = "preview"
    elif name == "markdown_mode_code":
        glyph = "code"
    elif any(word in name for word in ("remove", "delete", "archive")):
        glyph = "remove"
    elif any(word in name for word in ("add", "new", "create", "zoom_in")):
        glyph = "add"
    elif "zoom_out" in name:
        glyph = "minus"
    elif any(word in name for word in ("run", "jobs", "build")):
        glyph = "play"
    elif name in {"canvas", "search", "folder", "package", "computer", "globe", "file"}:
        glyph = name
    else:
        choices = (
            (("save", "apply"), "save"), (("undo", "restore"), "undo"),
            (("redo",), "redo"), (("import", "open", "inventory", "sources"), "folder"),
            (("close", "cancel"), "close"), (("edit", "rename"), "edit"),
            (("check", "test", "status"), "check"),
            (("project", "owner", "home"), "home"), (("export",), "export"),
        )
        glyph = next((icon for words, icon in choices if any(word in name for word in words)),
                     "file")
    icon = QIcon()
    for size in (16, 24, 32, 48, 64):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.scale(size / 32, size / 32)
        painter.setPen(QPen(QColor(color("text")), 2.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        if glyph == "settings":
            painter.drawEllipse(QRectF(8, 8, 16, 16))
            painter.drawEllipse(QRectF(13, 13, 6, 6))
            for index in range(8):
                angle = index * pi / 4
                painter.drawLine(QLineF(16 + 9 * cos(angle), 16 + 9 * sin(angle),
                                        16 + 13 * cos(angle), 16 + 13 * sin(angle)))
        elif glyph in {"left", "center", "right", "full"}:
            for index, y in enumerate((6, 12, 18, 24)):
                width = 22 if glyph == "full" or index % 2 == 0 else 14
                x = 5 if glyph in {"left", "full"} else 27 - width if glyph == "right" else (
                    32 - width) / 2
                painter.drawLine(QLineF(x, y, x + width, y))
        elif glyph == "preview":
            path = QPainterPath(QPointF(3, 16))
            path.cubicTo(11, 3, 21, 3, 29, 16)
            path.cubicTo(21, 29, 11, 29, 3, 16)
            painter.drawPath(path)
            painter.drawEllipse(QRectF(12, 12, 8, 8))
        elif glyph == "code":
            for x, direction in ((5, 1), (27, -1)):
                painter.drawLine(QLineF(x + direction * 7, 7, x, 16))
                painter.drawLine(QLineF(x, 16, x + direction * 7, 25))
        elif glyph == "remove":
            painter.drawLine(5, 8, 27, 8)
            painter.drawLine(12, 4, 20, 4)
            painter.drawRect(8, 8, 16, 20)
            painter.drawLine(13, 13, 13, 23)
            painter.drawLine(19, 13, 19, 23)
        elif glyph == "play":
            path = QPainterPath(QPointF(8, 5))
            path.lineTo(26, 16)
            path.lineTo(8, 27)
            path.closeSubpath()
            painter.drawPath(path)
        elif glyph == "canvas":
            painter.drawRoundedRect(QRectF(3, 4, 11, 9), 2, 2)
            painter.drawRoundedRect(QRectF(18, 19, 11, 9), 2, 2)
            painter.drawLine(9, 13, 23, 19)
        elif glyph == "search":
            painter.drawEllipse(QRectF(4, 4, 17, 17))
            painter.drawLine(20, 20, 28, 28)
        elif glyph == "save":
            painter.drawRoundedRect(QRectF(5, 4, 22, 24), 2, 2)
            painter.drawRect(10, 4, 11, 8)
            painter.drawRect(10, 19, 12, 9)
        elif glyph in {"undo", "redo", "export"}:
            if glyph == "redo":
                painter.translate(32, 0)
                painter.scale(-1, 1)
            elif glyph == "export":
                painter.translate(32, 0)
                painter.rotate(90)
            painter.drawLine(6, 16, 26, 16)
            painter.drawLine(6, 16, 14, 8)
            painter.drawLine(6, 16, 14, 24)
        elif glyph == "close":
            painter.drawLine(7, 7, 25, 25)
            painter.drawLine(25, 7, 7, 25)
        elif glyph == "check":
            painter.drawLine(5, 17, 12, 24)
            painter.drawLine(12, 24, 27, 7)
        elif glyph == "edit":
            path = QPainterPath(QPointF(6, 26))
            for x, y in ((7, 19), (22, 4), (28, 10), (13, 25), (6, 26)):
                path.lineTo(x, y)
            painter.drawPath(path)
            painter.drawLine(19, 7, 25, 13)
        elif glyph == "folder":
            path = QPainterPath(QPointF(3, 8))
            for x, y in ((12, 8), (15, 12), (29, 12), (27, 26), (3, 26), (3, 8)):
                path.lineTo(x, y)
            painter.drawPath(path)
        elif glyph == "computer":
            painter.drawRoundedRect(QRectF(3, 4, 26, 19), 2, 2)
            painter.drawLine(16, 23, 16, 28)
            painter.drawLine(9, 28, 23, 28)
        elif glyph == "globe":
            painter.drawEllipse(QRectF(4, 4, 24, 24))
            painter.drawEllipse(QRectF(10, 4, 12, 24))
            painter.drawLine(5, 16, 27, 16)
        elif glyph == "home":
            path = QPainterPath(QPointF(3, 15))
            for x, y in ((16, 4), (29, 15), (25, 15), (25, 28), (7, 28), (7, 15)):
                path.lineTo(x, y)
            painter.drawPath(path)
        elif glyph == "package":
            painter.drawRect(5, 5, 22, 23)
            painter.drawLine(5, 13, 27, 13)
            painter.drawLine(16, 5, 16, 13)
        elif glyph == "file":
            painter.drawRoundedRect(QRectF(6, 3, 20, 26), 2, 2)
            for y in (10, 16, 22):
                painter.drawLine(11, y, 21, y)
        else:
            painter.drawLine(6, 16, 26, 16)
            if glyph == "add":
                painter.drawLine(16, 6, 16, 26)
        painter.end()
        icon.addPixmap(pixmap)
    return icon
