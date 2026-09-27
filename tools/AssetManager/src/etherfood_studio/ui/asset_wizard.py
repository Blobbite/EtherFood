"""Metadata-only asset creation, with an explicit summary before any write."""

from PySide6.QtWidgets import (
    QComboBox, QDialog, QFormLayout, QHBoxLayout, QLineEdit, QStackedWidget,
    QVBoxLayout, QWidget,
)

from ..application.asset_service import AssetService
from ..domain.assets import TYPE_PRESETS, default_definition
from ..domain.models import StudioError
from ..domain.relations import PARENTS
from ..domain.sources import expected_sources
from .asset_settings import AssetDefinitionEditor
from ..application.profile_service import ProfileService
from .common import button, label, show_error


class AssetWizard(QDialog):
    def __init__(self, assets: AssetService, parent=None, *, owner_id=None, create=None) -> None:
        super().__init__(parent)
        self.assets = assets
        self.create_asset = create or assets.create
        self.created = None
        self.prepared = None
        self.setObjectName("asset_wizard")
        self.setWindowTitle("Neues Asset / NPC anlegen")
        self.resize(1140, 800)
        layout = QVBoxLayout(self)
        self.pages = QStackedWidget()
        page = QWidget()
        form_layout = QVBoxLayout(page)
        form = QFormLayout()
        self.name = QLineEdit()
        self.name.setObjectName("asset_wizard_name")
        self.name.setMaxLength(256)
        form.addRow("Name", self.name)
        self.owner = QComboBox()
        self.owner.setObjectName("asset_wizard_owner")
        for card in assets.project.cards():
            if card.kind in PARENTS["asset"]:
                self.owner.addItem(assets.project.breadcrumb(card.id), card.id)
        if self.owner.findData(owner_id) >= 0:
            self.owner.setCurrentIndex(self.owner.findData(owner_id))
        form.addRow("Scope / Eigentümer", self.owner)
        templates = QHBoxLayout()
        self.template = QComboBox()
        self.template.setObjectName("asset_wizard_template")
        for key, (title, _) in TYPE_PRESETS.items():
            self.template.addItem("Grundvorlage: " + title, ("type", key))
        for record in assets.project.cards():
            if record.kind == "asset" and record.data.get("asset_definition"):
                self.template.addItem("Nur Konfiguration: " + record.title, ("asset", record.id))
        templates.addWidget(self.template, 1)
        templates.addWidget(button("Konfiguration laden", "asset_wizard_load", self.load_template))
        form.addRow("Vorlage (ohne Quellen/Freigaben)", templates)
        form_layout.addLayout(form)
        self.editor = AssetDefinitionEditor(default_definition(), include_presets=False,
            profiles=ProfileService(assets.project).profiles())
        form_layout.addWidget(self.editor, 1)
        self.pages.addWidget(page)
        summary_page = QWidget()
        summary_layout = QVBoxLayout(summary_page)
        self.summary = label("", "asset_wizard_summary")
        summary_layout.addWidget(self.summary)
        summary_layout.addStretch()
        self.pages.addWidget(summary_page)
        layout.addWidget(self.pages, 1)
        actions = QHBoxLayout()
        self.back = button("Zurück", "asset_wizard_back", self.go_back)
        self.preview = button("Zusammenfassung prüfen", "asset_wizard_preview", self.review)
        self.commit = button("Asset jetzt anlegen", "asset_wizard_create", self.create)
        self.back.setEnabled(False)
        self.commit.setEnabled(False)
        for widget in (self.back, self.preview, self.commit,
                       button("Abbrechen", "asset_wizard_cancel", self.reject)):
            actions.addWidget(widget)
        layout.addLayout(actions)

    def load_template(self) -> None:
        kind, identifier = self.template.currentData()
        definition = self.assets.template(identifier) if kind == "asset" \
            else default_definition(identifier)
        self.editor.fill(definition)

    def review(self) -> None:
        try:
            definition = self.editor.value()
            name, owner = self.name.text().strip(), self.owner.currentData()
            if not name or not owner:
                raise StudioError("validation", "Name und Eigentümer auswählen.")
            self.prepared = (name, owner, definition.to_data())
            poses = ", ".join(p.display_name for p in definition.poses) or "Keine (statisch)"
            self.summary.setText(
                f"Name: {name}\nEigentümer: {self.owner.currentText()}\n"
                f"Typ: {definition.type_label}\nPosen: {poses}\n"
                f"Richtungen: {', '.join(definition.directions) or 'Keine'}\n"
                f"{len(expected_sources(definition))} benötigte Quellen\n"
                f"{len(definition.expected())} geplante Varianten\n\n"
                "Es werden nur Metadaten angelegt, keine Variantenordner oder Animationen. "
                "Vorlagen übertragen keine Quellbilder, Nachweise oder Freigaben. "
                "Quellen können danach im Asset-Menü ergänzt werden."
            )
            self.pages.setCurrentIndex(1)
            self.commit.setEnabled(True)
            self.back.setEnabled(True)
            self.preview.setEnabled(False)
        except StudioError as error:
            show_error(self, error)

    def go_back(self) -> None:
        self.prepared = None
        self.pages.setCurrentIndex(0)
        self.commit.setEnabled(False)
        self.back.setEnabled(False)
        self.preview.setEnabled(True)

    def create(self) -> None:
        if not self.prepared:
            return
        try:
            self.created = self.create_asset(*self.prepared)
            self.accept()
        except StudioError as error:
            show_error(self, error)
