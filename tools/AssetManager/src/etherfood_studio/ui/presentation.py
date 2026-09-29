"""Shared labels and contrast-aware type icons; no extra image dependencies."""

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from .theme import is_dark

KIND_NAMES = {
    "project": "Projekt",
    "global": "Projektweit",
    "act": "Akt",
    "chapter": "Kapitel",
    "asset": "Asset",
    "package": "Paket",
    "note": "Notiz",
    "document": "Dokument",
    "task": "Aufgabe",
    "issue": "Issue",
    "pipeline": "Pipeline",
    "pipeline_usage": "Pipelineverwendung",
    "pipeline_definition": "Pipelinedefinition",
    "script": "Python-Skript",
}
DOCUMENT_COLOR = "#eee4f8"


def kind_icon(kind: str) -> QIcon:
    if kind in {"task", "issue"}:
        return status_icon("open", issue=kind == "issue")
    if kind in {"asset", "note", "document", "task"}:
        return drawn_icon(kind)
    from .action_icons import action_icon
    return action_icon(
        {
            "project": "computer",
            "global": "globe",
            "act": "folder",
            "chapter": "folder",
            "package": "package",
            "pipeline": "pipeline",
            "pipeline_usage": "pipeline",
            "pipeline_definition": "pipeline",
        }.get(kind, "file")
    )


def record_icon(record) -> QIcon:
    """Use the same persisted status in trees, search, Canvas and task boards."""
    if record.kind in {"task", "issue"}:
        return status_icon(record.data["status"], issue=record.kind == "issue")
    from ..domain.notes import is_note
    return kind_icon("note" if is_note(record) else record.kind)


def status_icon(status: str, *, issue: bool = False) -> QIcon:
    result = QIcon()
    for size in (16, 24, 32, 48, 64):
        pixmap = QPixmap(size * (2 if issue else 1), size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.scale(size / 32, size / 32)
        if issue:
            painter.setPen(QPen(QColor("#ecc461" if is_dark() else "#8a5c06"), 5,
                                Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(16, 5, 16, 18)
            painter.drawPoint(16, 26)
            painter.translate(32, 0)
        colors = {"open": "#65778b", "in_progress": "#2878c8",
                  "blocked": "#b43a46", "done": "#21844a"}
        color = QColor(colors.get(status, colors["open"]))
        if is_dark():
            color = color.lighter(150)
        painter.setPen(QPen(color, 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        if status == "done":
            painter.setPen(QPen(color, 5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            path = QPainterPath(QPointF(5, 17))
            path.lineTo(12, 24)
            path.lineTo(27, 7)
            painter.drawPath(path)
        elif status == "blocked":
            painter.drawLine(7, 7, 25, 25)
            painter.drawLine(25, 7, 7, 25)
        elif status == "in_progress":
            painter.setBrush(color)
            painter.drawEllipse(7, 7, 18, 18)
        else:
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(6, 6, 20, 20)
        painter.end()
        result.addPixmap(pixmap)
    return result


def drawn_icon(kind: str) -> QIcon:
    """Keep semantic colors while reversing fill/ink contrast for each theme."""
    result = QIcon()
    for size in (16, 24, 32, 48, 64):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(size / 32, size / 32)
        painter.setPen(QPen(QColor("#b8e8f2" if is_dark() else "#173b4e"), 1.8))
        if kind == "asset":
            for color, points in (
                ("#80d0e5", [(4, 9), (16, 3), (28, 9), (16, 16)]),
                ("#529ebc", [(4, 9), (16, 16), (16, 29), (4, 22)]),
                ("#347594", [(16, 16), (28, 9), (28, 22), (16, 29)]),
            ):
                painter.setBrush(QColor(color) if is_dark() else QColor(color).darker(200))
                painter.drawPolygon(QPolygonF([QPointF(x, y) for x, y in points]))
        elif kind == "task":
            painter.setPen(QPen(QColor("#21844a"), 5, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            check = QPainterPath(QPointF(5, 17))
            check.lineTo(12, 24)
            check.lineTo(27, 7)
            painter.drawPath(check)
        elif kind == "document":
            painter.setPen(QPen(QColor("#4d2c64" if is_dark() else "#fff4ff"), 1.8))
            painter.setBrush(QColor("#d5b9eb" if is_dark() else "#70508e"))
            painter.drawPolygon(QPolygonF([QPointF(x, y) for x, y in (
                (6, 3), (20, 3), (27, 10), (27, 29), (6, 29),
            )]))
            painter.drawPolyline(QPolygonF([QPointF(20, 3), QPointF(20, 10), QPointF(27, 10)]))
            painter.drawLine(10, 15, 22, 15)
            painter.drawLine(10, 20, 22, 20)
            painter.drawLine(10, 25, 18, 25)
        else:
            painter.setPen(QPen(QColor("#674b0c" if is_dark() else "#fff1ad"), 1.8))
            painter.setBrush(QColor("#ffe58a" if is_dark() else "#8c6909"))
            painter.drawRoundedRect(4, 4, 24, 24, 2, 2)
            painter.drawLine(9, 12, 23, 12)
            painter.drawLine(9, 17, 20, 17)
            painter.setBrush(QColor("#fff7d5" if is_dark() else "#6a4b05"))
            painter.drawPolygon(QPolygonF([QPointF(21, 28), QPointF(28, 21), QPointF(21, 21)]))
        painter.end()
        result.addPixmap(pixmap)
    return result
