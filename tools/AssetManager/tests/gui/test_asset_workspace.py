"""End-to-end NPC creation, pose-local partial import and reopening the same asset."""

from time import monotonic, sleep

from PIL import Image
import pytest

pytest.importorskip("PySide6.QtWidgets", reason="Qt/GUI-Systembibliotheken fehlen")

from PySide6.QtCore import QSettings, QTimer, Qt
from PySide6.QtGui import QAction
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QPushButton

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.source_import import SourceImportService
from etherfood_studio.domain.assets import default_definition, new_pose
from etherfood_studio.ui.appearance import appearance
from etherfood_studio.ui.asset_wizard import AssetWizard
from etherfood_studio.ui.asset_workspace import AssetWorkspace
from etherfood_studio.ui.asset_settings import AssetSettingsDialog
from etherfood_studio.ui.main_window import MainWindow
from etherfood_studio.ui.inventory import InventoryDialog
from etherfood_studio.ui.source_import_dialog import SourceImportDialog


@pytest.fixture
def window(qt_app, tmp_path):
    settings = QSettings(str(tmp_path / "preferences.ini"), QSettings.Format.IniFormat)
    value = MainWindow(settings)
    root = tmp_path / "Projekt"
    root.mkdir()
    assert value.new_project(root, "NPC-Anlage")
    value.show()
    qt_app.processEvents()
    yield value
    value.documents.dirty = False
    value.close()
    qt_app.processEvents()


def wait_worker(dialog):
    deadline = monotonic() + 30
    while dialog.worker is not None and monotonic() < deadline:
        QTest.qWait(10)
        sleep(0.001)
    assert dialog.worker is None


def trigger_tree_action(window, identifier, name):
    menu = window.navigation.menu(identifier)
    action = next(action for action in menu.actions() if action.objectName() == name)
    action.trigger()
    menu.deleteLater()


def test_asset_actions_stay_out_of_project_toolbar_in_all_display_modes(window, qt_app):
    for mode in ("text", "icons", "text_icons"):
        appearance().set_preferences("light", mode, persist=False)
        qt_app.processEvents()
        names = {action.objectName() for action in window.project_toolbar.actions()}
        assert not {"new_asset", "asset_workspace"}.intersection(names)
        assert {"new_project", "open_project", "undo", "redo"}.issubset(names)
        assert not {"create_demo", "show_jobs", "image_pipeline"} & names
        assert "show_build_plan" not in names


def test_actual_four_direction_npc_partial_import_reopen_and_same_id(
        window, qt_app, tmp_path, monkeypatch):
    owner = next(card.id for card in window.project.cards() if card.kind == "global")

    def create_npc():
        wizard = QApplication.activeModalWidget()
        assert isinstance(wizard, AssetWizard)
        wizard.name.setText("NPC Vier")
        wizard.editor.directions.setText("N,O,S,W")
        wizard.editor.add_pose(new_pose("stand"))
        QTest.mouseClick(wizard.preview, Qt.MouseButton.LeftButton)
        assert "8 benötigte Quellen" in wizard.summary.text()
        assert "Ausgabevarianten werden im Ablaufeditor" in wizard.summary.text()
        QTest.mouseClick(wizard.commit, Qt.MouseButton.LeftButton)

    QTimer.singleShot(0, create_npc)
    trigger_tree_action(window, owner, "context_card_asset")
    identifier = window.selected_id
    assert window.project.catalog.get(identifier).owner_id == owner
    assets = AssetService(window.project)
    definition = assets.definition(identifier)
    assert definition.directions == ("N", "O", "S", "W")
    assert len(definition.poses) == 2
    root = window.project.catalog.path.parent
    assert not (root / ".asset-studio/jobs").exists()
    assert not [row for row in window.project.catalog.records() if row.kind == "source_revision"]
    assert not list((window.project.files.path(identifier) / "source").rglob("*.png"))
    source = tmp_path / "npc_walk_N_4x4.png"
    Image.new("RGBA", (16, 16), (50, 170, 70, 255)).save(source)
    monkeypatch.setattr(QFileDialog, "getOpenFileNames", lambda *args: ([str(source)], ""))
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)

    def import_one():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, SourceImportDialog)
        assert dialog.pose_id is None
        QTest.mouseClick(dialog.choose, Qt.MouseButton.LeftButton)
        dialog.table.cellWidget(0, 4).setCurrentText("4x4")
        QTest.mouseClick(dialog.check_button, Qt.MouseButton.LeftButton)
        wait_worker(dialog)
        assert dialog.plan is not None
        QTest.mouseClick(dialog.import_button, Qt.MouseButton.LeftButton)
        wait_worker(dialog)
        assert dialog.changed
        dialog.reject()

    def use_workspace():
        workspace = QApplication.activeModalWidget()
        assert isinstance(workspace, AssetWorkspace)
        assert workspace.identifier == identifier
        assert workspace.tabs.count() == 7
        assert all(workspace.tabs.isTabEnabled(i) for i in (3, 4))
        assert not workspace.tabs.isTabEnabled(5)  # No automatic Godot/sight approval.
        assert "0/8" in workspace.workflow.toPlainText()
        workspace.tabs.setCurrentIndex(2)
        assert workspace.editor.poses.horizontalHeaderItem(7).text() == "Anker Y"
        assert workspace.editor.poses.columnCount() == 8
        workspace.tabs.setCurrentIndex(1)
        action = workspace.sources.findChild(QPushButton, "source_add")
        QTimer.singleShot(0, import_one)
        QTest.mouseClick(action, Qt.MouseButton.LeftButton)
        assert "1/8" in workspace.workflow.toPlainText()
        assert "1/8" in workspace.sources.summary.text()
        delivered = workspace.sources.findChild(QPushButton,
            "delivery_spritesheet_" + definition.poses[0].id)
        assert delivered.text().startswith("1/4")
        workspace.documents.create_document("NPC-Notiz")
        workspace.documents.editor.setPlainText("Gehört zu derselben Karte")
        workspace.documents.save()
        assert workspace.documents.owner_id == identifier
        workspace.reject()

    QTimer.singleShot(0, use_workspace)
    trigger_tree_action(window, identifier, "context_asset_workspace")
    revision, = SourceImportService(assets).revisions(identifier)
    assert revision.owner_id == identifier
    window.open_project(root)
    window.select_card(identifier)
    assets = AssetService(window.project)
    workspace = AssetWorkspace(assets, identifier)
    assert "1/8" in workspace.workflow.toPlainText()
    assert "stand" in workspace.workflow.toPlainText()
    saved_doc = next(d for d in workspace.documents.service.documents(identifier)
                     if d.title == "NPC-Notiz")
    workspace.documents.open_document(saved_doc.id)
    assert workspace.documents.editor.toPlainText() == "Gehört zu derselben Karte"
    assert SourceImportService(assets).revisions(identifier)[0].id == revision.id
    assert len([c for c in window.project.cards() if c.kind == "asset"]) == 1
    workspace.close()
    workspace.deleteLater()
    asset = assets.asset(identifier)
    window.project.archive(identifier, True, asset.revision_no)
    window.open_project(root)
    window.select_card(identifier)
    assert window.project.catalog.get(identifier).archived
    assert any(
        item.data(0, Qt.UserRole) == identifier
        for item in window.tree.findItems("", Qt.MatchContains | Qt.MatchRecursive)
    )


def test_wizard_cancel_and_configuration_template_do_not_import_sources(window, qt_app):
    assets = AssetService(window.project)
    owner = next(c.id for c in window.project.cards() if c.kind == "global")
    original = assets.create("Held-Vorlage", owner, default_definition().to_data())
    window.project.catalog.create("approval", "Testfixture, keine echte Freigabe", original.id)
    before = window.project.catalog.export_snapshot()
    wizard = AssetWizard(assets)
    wizard.show()
    wizard.name.setText("Nicht angelegt")
    wizard.review()
    wizard.reject()
    assert window.project.catalog.export_snapshot() == before
    wizard = AssetWizard(assets)
    wizard.show()
    index = next(i for i in range(wizard.template.count())
                 if wizard.template.itemData(i)[1] == original.id)
    wizard.template.setCurrentIndex(index)
    wizard.load_template()
    wizard.name.setText("Neuer NPC")
    wizard.editor.directions.setText("O,W")
    wizard.review()
    wizard.create()
    record = wizard.created
    assert record.id != original.id
    assert assets.definition(record.id).poses[0].id != assets.definition(original.id).poses[0].id
    children = [r for r in window.project.catalog.records() if r.owner_id == record.id]
    assert len(children) == 1 and children[0].data.get("automation") == "section"
    assert not record.data.get("active_sources") and not record.data.get("approval")
    wizard.deleteLater()


def test_workspace_unsaved_requirements_and_note_guards(window, qt_app, monkeypatch):
    assets = AssetService(window.project)
    owner = next(c.id for c in window.project.cards() if c.kind == "global")
    record = assets.create("Offene Eingaben", owner, default_definition().to_data())
    workspace = AssetWorkspace(assets, record.id)
    workspace.show()
    workspace.editor.directions.setText("O,W")
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Cancel)
    workspace.close()
    assert workspace.isVisible()
    assert len(assets.definition(record.id).directions) == 8
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Save)
    workspace.close()
    assert not workspace.isVisible()
    assert assets.definition(record.id).directions == ("O", "W")
    workspace = AssetWorkspace(assets, record.id)
    workspace.show()
    note = workspace.documents.create_document("Nicht verlieren")
    workspace.documents.editor.setPlainText("Ungespeicherter Inhalt")
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Cancel)
    workspace.close()
    assert workspace.isVisible() and workspace.documents.dirty
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Save)
    workspace.close()
    assert assets.project.catalog.get(note.id).data["body"] == "Ungespeicherter Inhalt"
    workspace.deleteLater()


def test_pose_configuration_only_saves_requirements_without_import(window, qt_app):
    assets = AssetService(window.project)
    owner = next(c.id for c in window.project.cards() if c.kind == "global")
    record = window.project.create_card("asset", "Noch ohne Anforderungen", owner)
    dialog = AssetSettingsDialog(assets, record.id)
    dialog.show()
    dialog.directions.setText("N,O,S,W")
    assert dialog.poses.columnCount() == 8
    before = window.project.catalog.export_snapshot()
    assert window.project.catalog.export_snapshot() == before and not dialog.changed
    dialog.save()
    assert dialog.changed
    assert assets.definition(record.id).directions == ("N", "O", "S", "W")
    assert SourceImportService(assets).revisions(record.id) == []
    dialog.close()
    dialog.deleteLater()


def test_only_asset_menu_exposes_data_actions_and_inventory(window, qt_app):
    assets = AssetService(window.project)
    owner = next(c.id for c in window.project.cards() if c.kind == "global")
    record = assets.create("Zentral", owner, default_definition().to_data())
    window.refresh()
    window.select_card(record.id)
    for name in ("new_asset", "asset_workspace", "asset_settings", "asset_sources",
                 "asset_inventory"):
        assert window.findChild(QAction, name) is None
    menu = window.navigation.menu(record.id)
    names = [action.objectName() for action in menu.actions()]
    assert "context_asset_workspace" in names
    assert not {"context_asset_settings", "context_asset_sources", "context_asset_inventory"} \
        .intersection(names)
    menu.deleteLater()
    workspace = AssetWorkspace(assets, record.id)
    workspace.show()
    workspace.tabs.setCurrentWidget(workspace.sources_page)

    def close_inventory():
        inventory = QApplication.activeModalWidget()
        assert isinstance(inventory, InventoryDialog)
        assert inventory.identifier == record.id
        inventory.reject()

    QTimer.singleShot(0, close_inventory)
    QTest.mouseClick(workspace.inventory_button, Qt.MouseButton.LeftButton)
    workspace.close()
    workspace.deleteLater()
