"""Shared labels and platform-native type icons; no extra image dependencies."""

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QApplication, QStyle

KIND_NAMES = {"project": "Projekt", "global": "Projektweit", "act": "Akt", "chapter": "Kapitel",
              "asset": "Asset", "package": "Paket", "note": "Notiz", "document": "Dokument",
              "task": "Aufgabe", "issue": "Issue"}


def kind_icon(kind: str) -> QIcon:
    if kind in {"asset", "note"}:
        return drawn_icon(kind)
    names = {"project": "SP_ComputerIcon", "global": "SP_DriveNetIcon", "act": "SP_DirIcon",
             "chapter": "SP_DirOpenIcon", "asset": "SP_FileIcon", "package": "SP_DriveHDIcon",
             "note": "SP_FileDialogDetailedView", "document": "SP_FileDialogContentsView",
             "task": "SP_DialogApplyButton", "issue": "SP_MessageBoxWarning"}
    icon = getattr(QStyle.StandardPixmap, names.get(kind, "SP_FileIcon"))
    return QApplication.style().standardIcon(icon)


def drawn_icon(kind: str) -> QIcon:
    """Code-native cube and sticky-note symbols, crisp at common display scales."""
    result = QIcon()
    for size in (16, 24, 32, 48, 64):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(size / 32, size / 32)
        painter.setPen(QPen(QColor("#294b65"), 1.5))
        if kind == "asset":
            for color, points in (
                ("#80d0e5", [(4, 9), (16, 3), (28, 9), (16, 16)]),
                ("#529ebc", [(4, 9), (16, 16), (16, 29), (4, 22)]),
                ("#347594", [(16, 16), (28, 9), (28, 22), (16, 29)]),
            ):
                painter.setBrush(QColor(color))
                painter.drawPolygon(QPolygonF([QPointF(x, y) for x, y in points]))
        else:
            painter.setPen(QPen(QColor("#a4852a"), 1.5))
            painter.setBrush(QColor("#ffe58a"))
            painter.drawRoundedRect(4, 4, 24, 24, 2, 2)
            painter.drawLine(9, 12, 23, 12)
            painter.drawLine(9, 17, 20, 17)
            painter.setBrush(QColor("#fff7d5"))
            painter.drawPolygon(QPolygonF([QPointF(21, 28), QPointF(28, 21), QPointF(21, 21)]))
        painter.end()
        result.addPixmap(pixmap)
    return result
