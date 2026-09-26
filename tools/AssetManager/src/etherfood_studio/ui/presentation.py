"""Shared labels and platform-native type icons; no extra image dependencies."""

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QStyle

KIND_NAMES = {"project": "Projekt", "global": "Projektweit", "act": "Akt", "chapter": "Kapitel",
              "asset": "Asset", "package": "Paket", "note": "Notiz", "document": "Dokument",
              "task": "Aufgabe", "issue": "Issue"}


def kind_icon(kind: str) -> QIcon:
    names = {"project": "SP_ComputerIcon", "global": "SP_DriveNetIcon", "act": "SP_DirIcon",
             "chapter": "SP_DirOpenIcon", "asset": "SP_FileIcon", "package": "SP_DriveHDIcon",
             "note": "SP_FileDialogDetailedView", "document": "SP_FileDialogContentsView",
             "task": "SP_DialogApplyButton", "issue": "SP_MessageBoxWarning"}
    icon = getattr(QStyle.StandardPixmap, names.get(kind, "SP_FileIcon"))
    return QApplication.style().standardIcon(icon)
