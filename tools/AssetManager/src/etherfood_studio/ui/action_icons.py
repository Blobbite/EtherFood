"""Small code-native action glyphs and Qt fallbacks, with no image dependencies."""

from math import cos, pi, sin

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QStyle

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
    elif name in {"canvas", "search"}:
        glyph = name
    else:
        choices = (
            (("save", "apply"), QStyle.SP_DialogSaveButton),
            (("undo", "restore"), QStyle.SP_ArrowBack),
            (("redo",), QStyle.SP_ArrowForward),
            (("import", "open", "inventory", "sources"), QStyle.SP_DialogOpenButton),
            (("close", "cancel"), QStyle.SP_DialogCloseButton),
            (("edit", "rename"), QStyle.SP_FileDialogDetailedView),
            (("run", "jobs", "build"), QStyle.SP_MediaPlay),
            (("check", "test", "status"), QStyle.SP_DialogApplyButton),
            (("project", "owner", "home"), QStyle.SP_DirHomeIcon),
            (("export",), QStyle.SP_ArrowUp),
        )
        standard = next((icon for words, icon in choices if any(word in name for word in words)),
                        QStyle.SP_FileDialogContentsView)
        return QApplication.style().standardIcon(standard)
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
        else:
            painter.drawLine(6, 16, 26, 16)
            if glyph == "add":
                painter.drawLine(16, 6, 16, 26)
        painter.end()
        icon.addPixmap(pixmap)
    return icon
