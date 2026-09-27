"""Session-wide presentation preferences, persisted locally without editing project data."""

from PySide6.QtCore import QEvent, QObject, QSettings, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPalette
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QPushButton,
    QTabWidget,
)

from .action_icons import action_icon
from .theme import color

BUTTON_STYLES = {"text_icons": Qt.ToolButtonTextBesideIcon, "icons": Qt.ToolButtonIconOnly,
                 "text": Qt.ToolButtonTextOnly}


class Appearance(QObject):
    changed = Signal()

    def __init__(self, app: QApplication) -> None:
        super().__init__(app)
        self.app = app
        self.settings = None
        self.theme = "light"
        self.buttons = "text_icons"
        app.installEventFilter(self)

    def configure(self, settings: QSettings) -> None:
        self.settings = settings
        self.set_preferences(str(settings.value("appearance/theme", "light")),
                             str(settings.value("appearance/buttons", "text_icons")), persist=False)

    def set_preferences(self, theme: str, buttons: str, *, persist: bool = True) -> None:
        theme = theme if theme in {"light", "dark"} else "light"
        buttons = buttons if buttons in BUTTON_STYLES else "text_icons"
        if self.app.property("studio_theme") == theme and self.buttons == buttons:
            if persist:
                self.save_preferences()
            return
        self.theme, self.buttons = theme, buttons
        self.app.setProperty("studio_theme", self.theme)
        if self.app.style().objectName().lower() != "fusion":
            self.app.setStyle("Fusion")
        palette = QPalette()
        for role, name in (
            (QPalette.Window, "window"), (QPalette.WindowText, "text"),
            (QPalette.Base, "base"), (QPalette.AlternateBase, "alternate"),
            (QPalette.Text, "text"), (QPalette.Button, "button"), (QPalette.ButtonText, "text"),
            (QPalette.ToolTipBase, "base"), (QPalette.ToolTipText, "text"),
            (QPalette.Highlight, "selection"), (QPalette.HighlightedText, "selection_text"),
            (QPalette.Link, "link"), (QPalette.LinkVisited, "link"),
            (QPalette.Mid, "border"), (QPalette.Dark, "border"), (QPalette.Light, "alternate"),
            (QPalette.PlaceholderText, "muted"),
        ):
            palette.setColor(role, QColor(color(name)))
        for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
            palette.setColor(QPalette.Disabled, role, QColor(color("disabled")))
        self.app.setPalette(palette)
        # Qt style sheets retain their resolved palette across application changes.
        # Rebase them first; semantic surfaces (post-its/canvas) then apply their colors.
        for widget in self.app.allWidgets():
            if widget.styleSheet():
                widget.setPalette(palette)
                widget.setStyleSheet(widget.styleSheet())
        self.changed.emit()
        for widget in self.app.allWidgets():
            if isinstance(widget, QDialogButtonBox):
                self._style_dialog_buttons(widget)
            elif isinstance(widget, QTabWidget):
                self._style_tabs(widget)
        if persist:
            self.save_preferences()

    def save_preferences(self) -> None:
        if self.settings is not None:
            self.settings.setValue("appearance/theme", self.theme)
            self.settings.setValue("appearance/buttons", self.buttons)
            self.settings.sync()

    def _style_dialog_buttons(self, box: QDialogButtonBox) -> None:
        names = {QDialogButtonBox.Save: "save", QDialogButtonBox.Cancel: "cancel",
                 QDialogButtonBox.Close: "close", QDialogButtonBox.Ok: "check",
                 QDialogButtonBox.Apply: "apply", QDialogButtonBox.Open: "open"}
        for button in box.buttons():
            title = button.property("studio_button_title") or button.text()
            button.setProperty("studio_button_title", title)
            button.setAccessibleName(title.replace("&", ""))
            button.setToolTip(title.replace("&", ""))
            button.setText("" if self.buttons == "icons" else title)
            button.setIcon(QIcon() if self.buttons == "text" else action_icon(
                names.get(box.standardButton(button), "dialog_action")))

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Show:
            if isinstance(watched, QDialogButtonBox):
                self._style_dialog_buttons(watched)
            elif isinstance(watched, QTabWidget):
                self._style_tabs(watched)
        return super().eventFilter(watched, event)

    def _style_tabs(self, tabs: QTabWidget) -> None:
        for index in range(tabs.count()):
            page = tabs.widget(index)
            title = page.property("studio_tab_title") or tabs.tabText(index)
            page.setProperty("studio_tab_title", title)
            tabs.setTabText(index, "" if self.buttons == "icons" else title)
            tabs.setTabToolTip(index, title.replace("&&", "&"))
            name = title.casefold()
            roles = (("notiz", "new_note"), ("dokument", "new_document"),
                     ("aufgab", "new_task"), ("issue", "new_issue"), ("asset", "new_asset"),
                     ("canvas", "canvas"), ("such", "search"), ("quelle", "sources"),
                     ("revision", "undo"), ("prüf", "check"), ("pose", "asset_workspace"))
            role = next((role for keyword, role in roles if keyword in name), "tab_contents")
            tabs.setTabIcon(index, QIcon() if self.buttons == "text" else action_icon(role))


def appearance() -> Appearance:
    app = QApplication.instance()
    if not hasattr(app, "_studio_appearance"):
        app._studio_appearance = Appearance(app)
    return app._studio_appearance


class ActionButton(QPushButton):
    def __init__(self, text: str, name: str, parent=None) -> None:
        super().__init__(text, parent)
        self._title = text
        self.setObjectName(name)
        self.setAccessibleName(text)
        self.setToolTip(text)
        self.setIconSize(QSize(18, 18))
        appearance().changed.connect(self.refresh_appearance)
        self.refresh_appearance()

    def setText(self, text: str) -> None:
        self._title = text
        self.setAccessibleName(text)
        self.setToolTip(text)
        self.refresh_appearance()

    def refresh_appearance(self) -> None:
        mode = appearance().buttons
        super().setText("" if mode == "icons" else self._title)
        self.setIcon(QIcon() if mode == "text" or (self._title == "+" and mode != "icons")
                     else action_icon(self.objectName()))


class AppearanceDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("appearance_settings")
        self.setWindowTitle("Einstellungen · Darstellung")
        self.setMinimumWidth(390)
        layout = QFormLayout(self)
        self.theme = QComboBox()
        self.theme.setObjectName("appearance_theme")
        self.theme.addItem("Hell · Tag", "light")
        self.theme.addItem("Dunkel · Nacht", "dark")
        self.buttons = QComboBox()
        self.buttons.setObjectName("appearance_buttons")
        for text, value in (("Text + Icons", "text_icons"), ("Nur Icons", "icons"),
                             ("Nur Text", "text")):
            self.buttons.addItem(text, value)
        manager = appearance()
        self.theme.setCurrentIndex(self.theme.findData(manager.theme))
        self.buttons.setCurrentIndex(self.buttons.findData(manager.buttons))
        layout.addRow("Farbschema", self.theme)
        layout.addRow("Aktionsschaltflächen", self.buttons)
        self.notice = QLabel("Änderungen gelten sofort und bleiben nach Neustart erhalten.\n"
                            "Nur Icons: Beschriftungen bleiben als Tooltip verfügbar.\n"
                            "Projektinhalte und ungespeicherte Texte bleiben unverändert.")
        self.notice.setWordWrap(True)
        layout.addRow(self.notice)
        self.theme.currentIndexChanged.connect(self.apply)
        self.buttons.currentIndexChanged.connect(self.apply)
        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.rejected.connect(self.accept)
        layout.addRow(close)

    def apply(self) -> None:
        manager = appearance()
        manager.set_preferences(self.theme.currentData(), self.buttons.currentData())
        if manager.settings is not None and manager.settings.status() != QSettings.NoError:
            self.notice.setText("Lokale Einstellungen konnten nicht gespeichert werden. "
                                "Die Auswahl gilt vorerst nur in dieser Sitzung.")
