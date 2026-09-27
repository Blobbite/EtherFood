"""Compact controls and readable glyphs without OS icon-theme dependencies."""

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDialogButtonBox, QHBoxLayout, QWidget

from etherfood_studio.ui.action_icons import action_icon
from etherfood_studio.ui.appearance import ActionButton, appearance
from etherfood_studio.ui.presentation import kind_icon, status_icon
from etherfood_studio.ui.theme import color


@pytest.fixture(autouse=True)
def restore_appearance(qt_app):
    yield
    appearance().set_preferences("light", "text_icons", persist=False)


def test_icon_only_buttons_are_narrower_and_restore_native_text_sizes(qt_app):
    host = QWidget()
    row = QHBoxLayout(host)
    button = ActionButton("Einstellungen", "settings")
    issue = ActionButton("Neues Issue", "new_issue")
    dialog = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
    for widget in (button, issue, dialog):
        row.addWidget(widget)
    row.addStretch(1)
    host.resize(1000, 80)
    host.show()
    widths = {}
    for mode in ("text", "icons", "text_icons", "text"):
        appearance().set_preferences("light", mode, persist=False)
        qt_app.processEvents()
        widths[mode] = button.width()
        assert button.iconSize() == QSize(16, 16)
        assert issue.iconSize() == QSize(32, 16)
        if mode == "icons":
            assert button.width() == 28 and issue.width() == 44
            assert all(value.width() == 28 for value in dialog.buttons())
        else:
            assert all(value.width() > 28 for value in dialog.buttons())
        assert button.toolTip() == "Einstellungen"
    assert widths["icons"] < widths["text"] < widths["text_icons"]
    host.close()
    host.deleteLater()


def luminance(value):
    channels = [value.redF(), value.greenF(), value.blueF()]
    linear = [part / 12.92 if part <= 0.04045 else ((part + 0.055) / 1.055) ** 2.4
              for part in channels]
    return sum(part * weight for part, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast(first, second):
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_action_and_semantic_icons_contrast_with_button_and_content_backgrounds(qt_app, theme):
    appearance().set_preferences(theme, "icons", persist=False)
    actions = [action_icon(name) for name in (
        "settings", "open", "save", "undo", "redo", "export", "cancel", "edit", "check",
        "canvas", "search", "unmapped_action", "markdown_mode_md", "document_align_center")]
    semantic = [kind_icon(kind) for kind in (
        "project", "global", "chapter", "package", "asset", "document", "note", "issue")]
    semantic.extend(status_icon(status) for status in ("open", "in_progress", "blocked", "done"))
    for icon in actions + semantic:
        picture = icon.pixmap(32, 32).toImage()
        pixels = [picture.pixelColor(x, y) for x in range(picture.width())
                  for y in range(picture.height()) if picture.pixelColor(x, y).alpha() > 240]
        assert len(pixels) > 20
        for background in ("base", "button"):
            ratios = [contrast(pixel, QColor(color(background))) for pixel in pixels]
            assert sum(ratio >= 3 for ratio in ratios) > len(ratios) * 0.6
        if icon in actions:
            expected = QColor(color("text")).getRgb()[:3]
            assert all(max(abs(a - b) for a, b in zip(pixel.getRgb()[:3], expected)) <= 2
                       for pixel in pixels)
