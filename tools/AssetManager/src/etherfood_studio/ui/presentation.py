"""Shared labels and platform-native type icons; no extra image dependencies."""

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QApplication, QStyle

KIND_NAMES = {"project": "Projekt", "global": "Projektweit", "act": "Akt", "chapter": "Kapitel",
              "asset": "Asset", "package": "Paket", "note": "Notiz", "document": "Dokument",
              "task": "Aufgabe", "issue": "Issue"}
DOCUMENT_COLOR = "#eee4f8"


def kind_icon(kind: str) -> QIcon:
    if kind in {"asset", "note", "document", "task"}:
        return drawn_icon(kind)
    names = {"project": "SP_ComputerIcon", "global": "SP_DriveNetIcon", "act": "SP_DirIcon",
             "chapter": "SP_DirOpenIcon", "package": "SP_DriveHDIcon",
             "issue": "SP_MessageBoxWarning"}
    icon = getattr(QStyle.StandardPixmap, names.get(kind, "SP_FileIcon"))
    return QApplication.style().standardIcon(icon)


def drawn_icon(kind: str) -> QIcon:
    """Code-native type symbols, crisp and theme-independent at common display scales."""
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
        elif kind == "task":
            painter.setPen(QPen(QColor("#21844a"), 5, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            check = QPainterPath(QPointF(5, 17))
            check.lineTo(12, 24)
            check.lineTo(27, 7)
            painter.drawPath(check)
        elif kind == "document":
            painter.setPen(QPen(QColor("#745398"), 1.8))
            painter.setBrush(QColor(DOCUMENT_COLOR))
            painter.drawPolygon(QPolygonF([QPointF(x, y) for x, y in (
                (6, 3), (20, 3), (27, 10), (27, 29), (6, 29),
            )]))
            painter.drawPolyline(QPolygonF([QPointF(20, 3), QPointF(20, 10), QPointF(27, 10)]))
            painter.drawLine(10, 15, 22, 15)
            painter.drawLine(10, 20, 22, 20)
            painter.drawLine(10, 25, 18, 25)
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
