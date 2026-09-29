"""Shared semantic colors for native widgets and custom-painted Studio surfaces."""

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

LIGHT = {
    "window": "#f3f5f7", "base": "#ffffff", "alternate": "#edf1f5", "button": "#e6ecf2",
    "text": "#152a3d", "muted": "#536d80", "border": "#b7c6d4", "disabled": "#8995a2",
    "accent": "#147fb0", "selection": "#dbeafe", "selection_text": "#172c47",
    "canvas": "#f0f4f7", "global_card": "#e1eee7", "global_border": "#658076",
    "project_card": "#d7d9dc", "project_border": "#62676e",
    "warning": "#fff3cf", "warning_text": "#765329", "board": "#c5b493",
    "board_border": "#aa9878", "note_text": "#263238", "note_muted": "#52606a",
    "note_border": "#aa9868", "port": "#d6eff8", "port_border": "#187e93",
    "edge_belongs_to": "#6b849c", "edge_uses": "#187e93", "edge_depends_on": "#af5427",
    "handle": "#fff1be", "handle_border": "#9c6420", "link": "#126da5",
}
DARK = {
    "window": "#1d2632", "base": "#151d27", "alternate": "#253142", "button": "#2d3949",
    "text": "#e7edf4", "muted": "#b0bfd0", "border": "#4c6078", "disabled": "#8090a3",
    "accent": "#74bfff", "selection": "#244d75", "selection_text": "#f6faff",
    "canvas": "#111a24", "global_card": "#253e37", "global_border": "#71988a",
    "project_card": "#35383d", "project_border": "#a3a6ac",
    "warning": "#51442b", "warning_text": "#f1d393", "board": "#302b25",
    "board_border": "#665a47", "note_text": "#fff6e5", "note_muted": "#e0dacb",
    "note_border": "#998765", "port": "#244556", "port_border": "#81d5e5",
    "edge_belongs_to": "#9db5d0", "edge_uses": "#75cedf", "edge_depends_on": "#efae86",
    "handle": "#655334", "handle_border": "#f1cc7f", "link": "#8bc4ff",
}


def is_dark() -> bool:
    app = QApplication.instance()
    return bool(app and app.property("studio_theme") == "dark")


def color(name: str) -> str:
    return (DARK if is_dark() else LIGHT)[name]


def content_color(original: str) -> str:
    """Keep semantic post-it colors while reducing their brightness in dark mode."""
    return QColor(original).darker(235).name() if is_dark() else original
