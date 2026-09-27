"""Shared accessible widgets and safe error presentation."""

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMessageBox, QPushButton, QWidget

from .appearance import ActionButton


def button(text: str, name: str, callback: Callable, parent: QWidget | None = None) -> QPushButton:
    widget = ActionButton(text, name, parent)
    widget.clicked.connect(callback)
    return widget


def label(text: str, name: str = "") -> QLabel:
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(True)
    widget.setObjectName(name)
    return widget


def show_error(parent: QWidget, error: Exception) -> None:
    dialog = QMessageBox(parent)
    dialog.setObjectName("studio_error")
    dialog.setIcon(QMessageBox.Icon.Warning)
    dialog.setWindowTitle("Aktion nicht möglich")
    dialog.setTextFormat(Qt.TextFormat.PlainText)
    dialog.setText(str(error))
    dialog.setDetailedText(getattr(error, "detail", "") or type(error).__name__)
    dialog.exec()
