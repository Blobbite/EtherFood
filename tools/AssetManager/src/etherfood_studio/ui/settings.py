"""Two real settings categories; synthetic data is always an explicit action."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .action_icons import action_icon
from .appearance import AppearanceDialog
from .common import button, label


class SettingsDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.setObjectName("studio_settings")
        self.setWindowTitle("Einstellungen")
        self.resize(660, 370)
        outer = QVBoxLayout(self)
        body = QHBoxLayout()
        self.categories = QListWidget()
        self.categories.setObjectName("settings_categories")
        self.categories.setMaximumWidth(180)
        for title, icon in (("Darstellung", "appearance"), ("Tests", "check")):
            self.categories.addItem(QListWidgetItem(action_icon(icon), title))
        self.pages = QStackedWidget()
        self.appearance = AppearanceDialog(self)
        self.appearance.setWindowFlags(Qt.Widget)
        for box in self.appearance.findChildren(QDialogButtonBox):
            self.appearance.layout().removeWidget(box)
            box.deleteLater()
        self.pages.addWidget(self.appearance)
        tests = QWidget()
        layout = QVBoxLayout(tests)
        layout.addWidget(
            label(
                "Synthetische Testinhalte für den tatsächlichen Projektablauf. "
                "Neue Pipelines benötigen anschließend Prüfung und ausdrückliche Freigabe."
            )
        )
        demo = button("Demo anlegen", "create_demo", window.demo_dialog)
        demo.setEnabled(window.project is not None)
        layout.addWidget(demo)
        layout.addStretch()
        self.pages.addWidget(tests)
        body.addWidget(self.categories)
        body.addWidget(self.pages, 1)
        outer.addLayout(body)
        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.rejected.connect(self.accept)
        outer.addWidget(close)
        self.categories.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.categories.setCurrentRow(0)
