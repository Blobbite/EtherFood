"""Explicit recipe-copy previews and hash-confirmed local Python registration."""

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QSplitter,
    QTabWidget, QVBoxLayout,
)

from ..application.pipeline_exchange import PipelineExchange, read_json
from ..application.plugin_service import PluginService, read_manifest
from ..domain.models import Record, StudioError
from ..storage.sqlite_repository import canonical
from .common import button, label, show_error

TRUST_WARNING = (
    "Nur ausdrücklich vertrauenswürdigen, selbst geprüften Python-Code freigeben. "
    "Der Worker ist KEINE Sicherheits-Sandbox: Code läuft mit Ihren Benutzerrechten "
    "und kann Dateien lesen, verändern oder löschen. Schutz gegen versehentliche "
    "Netzwerk-/Prozesszugriffe ersetzt keine Isolation gegen bösartigen Code. "
    "Es werden keine Pakete automatisch installiert. Die Freigabe gilt nur für "
    "die angezeigte registrierte Codekopie mit diesem SHA-256. Ein geändertes "
    "Manifest oder neu registrierter Code verlangt eine erneute Freigabe. "
    "Registrierung und Freigabe starten keinen Build."
    " Optionale Paketoberflächen laufen erst beim ausdrücklichen Öffnen im GUI-Prozess "
    "mit denselben Benutzerrechten; auch dort besteht keine Sicherheits-Sandbox."
)


def _text(text, name):
    widget = QPlainTextEdit()
    widget.setObjectName(name)
    widget.setReadOnly(True)
    widget.setPlainText(text)
    return widget


class PipelineImportDialog(QDialog):
    def __init__(self, project, plan, parent=None):
        super().__init__(parent)
        self.setObjectName("pipeline_import_preview")
        self.setWindowTitle("Pipeline importieren · Vorschau")
        self.resize(820, 650)
        self.exchange, self.plan, self.record = PipelineExchange(project), plan, None
        data = read_json(plan.document)
        layout = QVBoxLayout(self)
        layout.addWidget(label(
            "Eigenständige Kopie im geöffneten Projekt. Kein automatischer Build, "
            "keine Asset-Zuweisungen, keine Codefreigaben und keine Live-Verknüpfung."
        ))
        form = QFormLayout()
        self.title = QLineEdit(data["name"])
        self.title.setObjectName("pipeline_import_name")
        self.title.setMaxLength(256)
        form.addRow("Name der neuen Pipeline", self.title)
        layout.addLayout(form)
        tabs = QTabWidget()
        recipe = data["recipe"]
        summary = ["Name: " + data["name"], "Kategorie: " + recipe["category"],
                   "Aktiviert: " + ("ja" if recipe["enabled"] else "nein"), "", "Schritte:"]
        summary += [f"• {n['operation']} · {'aktiv' if n['enabled'] else 'deaktiviert'}"
                    for n in recipe["steps"]]
        summary += ["", "Projektprofile:"]
        summary += [f"• {p['name']} ({p['key']}) · {p['mode']}={p['value']} · " +
                    ("aktiv" if p["enabled"] else "deaktiviert") for p in data["profiles"]]
        tabs.addTab(_text("\n".join(summary), "pipeline_import_summary"), "Überblick")
        tabs.addTab(_text(json.dumps(recipe, ensure_ascii=False, indent=2),
                          "pipeline_import_parameters"), "Schritte / Parameter")
        resources = [f"• {v['name']} · {v['length']} Bytes · SHA-256 {v['sha256']}"
                     for v in recipe["resources"].values()]
        notices = resources or ["Keine deklarativen Ressourcen."]
        notices += ["", "Prüfung / Konflikte / Code:", *(plan.warnings or ("Keine Konflikte.",))]
        notices += ["", "Fehlende Ressourcen oder Werkzeuge bleiben ein blockierter Entwurf.",
                    "Python-Dateien werden ausschließlich getrennt registriert und freigegeben."]
        tabs.addTab(_text("\n".join(notices), "pipeline_import_warnings"), "Ressourcen / Prüfung")
        layout.addWidget(tabs, 1)
        self.error = label("", "pipeline_import_error")
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Als Kopie importieren")
        buttons.accepted.connect(self.import_copy)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def import_copy(self):
        try:
            self.record = self.exchange.accept(self.plan, self.title.text())
        except (StudioError, OSError, ValueError) as exc:
            self.error.setText(str(exc))
            return
        self.accept()


def import_pipeline(project, parent=None) -> Record | None:
    path, _ = QFileDialog.getOpenFileName(parent, "Pipeline importieren", "",
        "Pipeline (*.json *.zip *.canvas);;JSON-Rezept (*.json);;Paket (*.zip);;Legacy (*.canvas)")
    if not path:
        return None
    try:
        candidate = Path(path)
        if candidate.suffix.lower() == ".json" and candidate.stat().st_size <= 65536:
            data = read_json(candidate.read_bytes())
            if isinstance(data, dict) and data.get("contract") == "studio-python-step-v2":
                dialog = PluginPackageImportDialog(project, candidate, parent)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    return dialog.record
                return None
        plan = PipelineExchange(project).preview(Path(path))
        dialog = PipelineImportDialog(project, plan, parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.record
    except (StudioError, OSError, ValueError) as exc:
        show_error(parent, exc)
    return None


class PluginPackageImportDialog(QDialog):
    def __init__(self, project, path, parent=None):
        super().__init__(parent)
        self.service, self.path, self.record = PluginService(project), path, None
        self.package = self.service.package(path)
        self.setObjectName("pipeline_package_import")
        self.setWindowTitle("Python-Pipeline-Paket importieren")
        self.resize(780, 620)
        layout = QVBoxLayout(self)
        manifest = self.package["manifest"]
        layout.addWidget(label("Projektlokale Kopie von Rezept, Manifest und Python-Code. "
            "Der Code bleibt bis zur gesonderten Freigabe blockiert. Kein automatischer Build."))
        self.title = QLineEdit(manifest["name"])
        self.title.setObjectName("pipeline_package_name")
        self.title.setMaxLength(256)
        layout.addWidget(self.title)
        layout.addWidget(_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                               "pipeline_package_manifest"), 1)
        layout.addWidget(label("Code: " + manifest["source"] + "\nSHA-256: " +
                               self.package["code_hash"]))
        self.error = label("", "pipeline_package_error")
        if manifest["id"] in self.service.manifests():
            self.error.setText("Paket-ID existiert bereits; Aktualisierung im Erweiterungsdialog.")
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Als Pipeline importieren")
        buttons.accepted.connect(self.import_copy)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def import_copy(self):
        try:
            self.record = self.service.import_package(self.path, self.package["manifest"],
                self.package["code_hash"], self.title.text())
        except (StudioError, OSError, ValueError) as error:
            self.error.setText(str(error))
            return
        self.accept()


def export_pipeline(project, recipe_id, parent=None):
    path, selected = QFileDialog.getSaveFileName(parent, "Pipeline exportieren", "",
        "Rezept mit deklarativen Ressourcen (*.zip);;Nur JSON-Rezept (*.json)")
    if not path:
        return
    destination = Path(path)
    package = destination.suffix.lower() == ".zip" or (
        not destination.suffix and "*.zip" in selected)
    if not destination.suffix:
        destination = destination.with_suffix(".zip" if package else ".json")
    try:
        PipelineExchange(project).export(recipe_id, destination, package=package)
        QMessageBox.information(parent, "Pipeline exportiert", "Rezept exportiert. " + (
            "Deklarative Ressourcen sind enthalten; Python-Code und lokale Freigaben nicht."
            if package else "JSON enthält nur Ressourcenverweise. Ohne vorhandene Ressourcen "
            "bleibt die importierte Kopie blockiert. "
            "Für vollständige Ressourcen das ZIP-Paket wählen."
        ))
    except (StudioError, OSError, ValueError) as exc:
        show_error(parent, exc)


class PluginApprovalDialog(QDialog):
    def __init__(self, service, identifier, parent=None):
        super().__init__(parent)
        self.service, self.identifier = service, identifier
        self.details = service.details(identifier)
        self.setObjectName("pipeline_plugin_approval")
        self.setWindowTitle("Python-Codeversion ausdrücklich freigeben")
        self.resize(820, 700)
        layout = QVBoxLayout(self)
        layout.addWidget(label(TRUST_WARNING, "pipeline_plugin_warning"))
        manifest = self.details["manifest"]
        layout.addWidget(label(
            f"{manifest['name']} · Version {manifest['version']} · {identifier}"))
        digest = label("SHA-256: " + self.details["code_hash"], "pipeline_plugin_hash")
        digest.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(digest)
        source = service.store.path_for(self.details["code_hash"])
        service._verify_code(self.details)
        layout.addWidget(_text(source.read_text(encoding="utf-8", errors="replace"),
                               "pipeline_plugin_source"), 1)
        self.consent = QCheckBox(
            "Ich habe den Quelltext geprüft und vertraue genau dieser Version.")
        self.consent.setObjectName("pipeline_plugin_consent")
        layout.addWidget(self.consent)
        self.confirmation = QLineEdit()
        self.confirmation.setObjectName("pipeline_plugin_hash_confirmation")
        self.confirmation.setPlaceholderText("Vollständigen SHA-256 zur Bestätigung eingeben")
        self.confirmation.setMaxLength(64)
        layout.addWidget(self.confirmation)
        self.error = label("", "pipeline_plugin_approval_error")
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        self.approve_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.approve_button.setText("Diese Codeversion freigeben")
        self.approve_button.setEnabled(False)
        buttons.accepted.connect(self.approve)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.consent.toggled.connect(self.refresh)
        self.confirmation.textChanged.connect(self.refresh)

    def refresh(self):
        self.approve_button.setEnabled(self.consent.isChecked() and
                                       self.confirmation.text() == self.details["code_hash"])

    def approve(self):
        if not self.consent.isChecked() or self.confirmation.text() != self.details["code_hash"]:
            return
        try:
            latest = self.service.details(self.identifier)
            if canonical(latest["manifest"]) != canonical(self.details["manifest"]):
                raise StudioError("conflict", "Manifest wurde geändert; Dialog erneut öffnen.")
            self.service.approve(self.identifier, self.details["code_hash"])
        except (StudioError, OSError, ValueError) as exc:
            self.error.setText(str(exc))
            return
        self.accept()


class PluginManagerDialog(QDialog):
    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.service = PluginService(project)
        self.setObjectName("pipeline_plugin_manager")
        self.setWindowTitle("Python-Erweiterungen · nur dieses Projekt")
        self.resize(900, 620)
        layout = QVBoxLayout(self)
        layout.addWidget(label(TRUST_WARNING))
        splitter = QSplitter()
        self.items = QListWidget()
        self.items.setObjectName("pipeline_plugins")
        self.details = _text("Erweiterung auswählen.", "pipeline_plugin_details")
        splitter.addWidget(self.items)
        splitter.addWidget(self.details)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)
        actions = QHBoxLayout()
        actions.addWidget(button("Python-Schritt hinzufügen / aktualisieren …",
                                 "pipeline_plugin_register", self.register))
        self.approval = button("Codeversion freigeben …", "pipeline_plugin_approve", self.approve)
        self.revocation = button("Freigabe widerrufen", "pipeline_plugin_revoke", self.revoke)
        actions.addWidget(self.approval)
        actions.addWidget(self.revocation)
        actions.addWidget(button("Registrierung entfernen", "pipeline_plugin_remove", self.remove))
        layout.addLayout(actions)
        layout.addWidget(button("Schließen", "pipeline_plugin_close", self.accept))
        self.items.currentItemChanged.connect(self.selected)
        self.reload()

    def reload(self):
        self.items.clear()
        for identifier, manifest in self.service.manifests().items():
            item = QListWidgetItem(manifest["name"] + " · " + manifest["version"])
            item.setData(Qt.ItemDataRole.UserRole, identifier)
            self.items.addItem(item)
        if self.items.count():
            self.items.setCurrentRow(0)
        else:
            self.selected()

    def identifier(self):
        item = self.items.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def selected(self, *_):
        identifier = self.identifier()
        self.approval.setEnabled(bool(identifier))
        self.revocation.setEnabled(bool(identifier))
        if not identifier:
            self.details.setPlainText("Keine Python-Erweiterungen registriert.")
            return
        try:
            row = self.service.details(identifier)
            try:
                self.service.trusted(identifier)
                status = "Freigegeben; Ausführung nur nach ausdrücklichem Build-Auftrag."
            except StudioError as exc:
                status = str(exc)
            self.details.setPlainText(status + "\n\nSHA-256: " + row["code_hash"] + "\n\n" +
                                      json.dumps(row["manifest"], ensure_ascii=False, indent=2))
        except (StudioError, OSError, ValueError) as exc:
            self.details.setPlainText(str(exc))

    def register(self):
        manifest, _ = QFileDialog.getOpenFileName(self, "Erweiterungsmanifest auswählen", "",
                                                 "Python-Schritt-Manifest (*.json)")
        if not manifest:
            return
        code, _ = QFileDialog.getOpenFileName(self, "Python-Code ausdrücklich auswählen", "",
                                             "Python-Quelldatei (*.py)")
        if not code:
            return
        try:
            # Registration copies data only. Read at most the manifest limit before this preview.
            with Path(manifest).open("rb") as stream:
                declaration = read_manifest(stream.read(65537))
            if declaration["id"] in self.service.manifests():
                answer = QMessageBox.question(self, "Registrierung ersetzen?",
                    "Diese ID ist bereits registriert. Ersetzen widerruft die bisherige Freigabe. "
                    "Rezeptschritte mit dieser ID verwenden erst nach erneuter Freigabe "
                    "den neuen Code.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No)
                if answer != QMessageBox.StandardButton.Yes:
                    return
            self.service.register(Path(manifest), Path(code))
            self.reload()
        except (StudioError, OSError, ValueError) as exc:
            show_error(self, exc)

    def approve(self):
        if self.identifier():
            try:
                PluginApprovalDialog(self.service, self.identifier(), self).exec()
                self.selected()
            except (StudioError, OSError, ValueError) as exc:
                show_error(self, exc)

    def revoke(self):
        if self.identifier():
            try:
                self.service.revoke(self.identifier())
                self.selected()
            except (StudioError, OSError, ValueError) as exc:
                show_error(self, exc)

    def remove(self):
        if self.identifier():
            try:
                self.service.remove(self.identifier())
                self.reload()
            except (StudioError, OSError, ValueError) as exc:
                show_error(self, exc)


def manage_plugins(project, parent=None):
    try:
        PluginManagerDialog(project, parent).exec()
    except (StudioError, OSError, ValueError) as exc:
        show_error(parent, exc)
