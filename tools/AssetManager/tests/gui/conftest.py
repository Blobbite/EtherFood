"""Optional real Qt events in an isolated display/configuration environment."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qt_app():
    widgets = pytest.importorskip("PySide6.QtWidgets", reason="Qt/GUI-Systembibliotheken fehlen")
    app = widgets.QApplication.instance() or widgets.QApplication([])
    yield app
    # Release native widgets before QApplication and Python finalize in arbitrary order.
    from PySide6.QtCore import QCoreApplication, QEvent
    for widget in app.topLevelWidgets():
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
