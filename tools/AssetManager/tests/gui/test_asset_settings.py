"""Real widget saves/reopens; definition identity is not its visible name."""

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QPushButton

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.ui.asset_settings import AssetSettingsDialog


def test_save_rename_and_static_template(qt_app, tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    project = ProjectService.new(root, "Test")
    try:
        service = AssetService(project)
        identifier = project.demo()["hero"]
        dialog = AssetSettingsDialog(service, identifier)
        dialog.show()
        assert "200" in dialog.summary.text()
        QTest.mouseClick(dialog.findChild(QPushButton, "asset_save"), Qt.MouseButton.LeftButton)
        pose_id = service.definition(identifier).poses[0].id
        dialog = AssetSettingsDialog(service, identifier)
        dialog.show()
        dialog.poses.item(0, 0).setText("Gehen")
        QTest.mouseClick(dialog.findChild(QPushButton, "asset_save"), Qt.MouseButton.LeftButton)
        assert service.definition(identifier).poses[0].id == pose_id
        assert service.definition(identifier).poses[0].display_name == "Gehen"
        dialog = AssetSettingsDialog(service, identifier)
        dialog.show()
        dialog.preset.setCurrentIndex(dialog.preset.findData("texture"))
        QTest.mouseClick(dialog.findChild(QPushButton, "asset_load_preset"),
                         Qt.MouseButton.LeftButton)
        assert dialog.poses.rowCount() == 0 and dialog.frames.text() == ""
        assert "5 erwartete" in dialog.summary.text()
        QTest.mouseClick(dialog.findChild(QPushButton, "asset_save"), Qt.MouseButton.LeftButton)
        assert service.definition(identifier).workflow == "static"
    finally:
        project.catalog.close()
