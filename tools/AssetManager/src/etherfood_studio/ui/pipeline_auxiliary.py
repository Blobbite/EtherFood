"""Project profiles, explicit assignments and asynchronous real-image pipeline runs."""

from collections import Counter
from copy import deepcopy
import json
from threading import Event

from PIL import Image
from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QProgressBar, QSpinBox,
    QSplitter, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from ..application.build_planner import BuildPlanner
from ..application.commands import Command, Commands
from ..application.pipeline_service import PipelineService
from ..application.profile_service import ProfileService
from ..application.recipe_builds import RecipeBuildService
from ..application.recipe_results import RecipeResultService
from ..domain.assets import CAPABILITIES
from ..domain.graphics import proportional_size, validate_profiles
from ..domain.models import StudioError
from ..storage.build_cache import BuildCache
from ..storage.job_store import JobStore
from ..storage.paths import safe_target
from .asset_settings import CAPTION
from .build_plan import NAMES
from .common import button, label, show_error


def choice(values, current=None):
    widget = QComboBox()
    for key, title in values:
        widget.addItem(title, key)
    widget.setCurrentIndex(max(0, widget.findData(current)))
    return widget


def readonly(text):
    item = QTableWidgetItem(str(text))
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


class ProfileSizeEdit(QLineEdit):
    """Keep full persisted precision rather than rounding settings just by opening the form."""

    def __init__(self, value):
        super().__init__(str(value))
        self.setToolTip("Ein proportionaler Wert: Faktor (z. B. 0.5) "
                        "oder maximale Kante in Pixeln.")

    def value(self):
        try:
            return float(self.text().strip().replace(",", "."))
        except ValueError as error:
            raise StudioError("validation", "Faktor/Kante benötigt eine gültige Zahl.") from error

    def setValue(self, value):
        self.setText(str(value))


class ProfileDialog(QDialog):
    """Edit stable project keys and proportional per-frame dimensions."""

    changed = Signal()

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project, self.service = project, ProfileService(project)
        self.revision = project.project().revision_no
        self.original = list(self.service.profiles().values())
        self.commands = Commands(project)
        self.draft, self.track_changes = deepcopy(self.original), False
        self.loading_rows = True
        self.filling = False
        self.setWindowTitle("Projektweite Grafikprofile")
        self.resize(1160, 620)
        layout = QVBoxLayout(self)
        layout.addWidget(label(
            "Größen gelten pro Frame, nicht für das gesamte Spritesheet. Bestehende Schlüssel "
            "bleiben unverändert. Deaktivierte Profile sind nicht angefordert; Pixel High kann "
            "für Pixel Low trotzdem intern nötig sein. Beispielquelle: 512 × 256 Pixel."
        ))
        self.table = QTableWidget(0, 9)
        self.table.setObjectName("pipeline_profiles")
        self.table.setHorizontalHeaderLabels([
            "Schlüssel", "Anzeigename", "Aktiv", "Verfahren", "Größenmodus",
            "Wert", "Farben", "Pixel-High-Bezug", "Beispiel pro Frame",
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemChanged.connect(self.update_samples)
        layout.addWidget(self.table)
        self.notice = label("", "pipeline_profile_notice")
        layout.addWidget(self.notice)
        actions = QHBoxLayout()
        actions.addWidget(button("+ Profil", "pipeline_profile_add", self.add_profile))
        self.undo_button = button("Entwurf rückgängig", "pipeline_profile_undo",
                                  lambda: self.history(False))
        self.redo_button = button("Entwurf wiederholen", "pipeline_profile_redo",
                                  lambda: self.history(True))
        actions.addWidget(self.undo_button)
        actions.addWidget(self.redo_button)
        actions.addStretch()
        actions.addWidget(button("Profile speichern", "pipeline_profile_save", self.save))
        actions.addWidget(button("Schließen", "pipeline_profile_close", self.reject))
        layout.addLayout(actions)
        for profile in self.original:
            self.add_row(profile, existing=True)
        self.loading_rows = False
        self.track_changes = True
        self.table.resizeColumnsToContents()
        self.update_samples()

    def add_row(self, profile, *, existing=False):
        self.filling = True
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, readonly(profile["key"]) if existing else
                           QTableWidgetItem(profile["key"]))
        self.table.setItem(row, 1, QTableWidgetItem(profile["name"]))
        enabled = QCheckBox()
        enabled.setChecked(profile["enabled"])
        method = choice((("comic", "Comic · glatt"), ("pixel", "Pixel High · Palette"),
                         ("pixel_low", "Pixel Low · gleiche Palette")), profile["method"])
        mode = choice((("factor", "Faktor"), ("max_edge", "Maximale Kante")), profile["mode"])
        size = ProfileSizeEdit(profile["value"])
        colors = QSpinBox()
        colors.setRange(2, 256)
        colors.setValue(profile["colors"])
        colors.setKeyboardTracking(False)
        parent = choice(((None, "HD-Quelle"), (profile["parent"], profile["parent"] or "")),
                        profile["parent"])
        for column, widget in enumerate((enabled, method, mode, size, colors, parent), 2):
            self.table.setCellWidget(row, column, widget)
        self.table.setItem(row, 8, readonly(""))
        self.filling = False
        enabled.toggled.connect(self.update_samples)
        method.currentIndexChanged.connect(self.update_samples)
        mode.currentIndexChanged.connect(lambda: self.update_mode(row))
        size.textChanged.connect(self.update_samples)
        colors.valueChanged.connect(self.update_samples)
        parent.currentIndexChanged.connect(self.update_samples)
        self.update_mode(row)

    def update_mode(self, row):
        size, mode = self.table.cellWidget(row, 5), self.table.cellWidget(row, 4).currentData()
        size.setPlaceholderText("Faktor > 0 bis 1" if mode == "factor" else "Ganze Pixelzahl")
        self.update_samples()

    def add_profile(self):
        keys = {self.table.item(row, 0).text() for row in range(self.table.rowCount())}
        index = 1
        while f"custom_{index}" in keys:
            index += 1
        self.add_row({"key": f"custom_{index}", "name": "Eigenes Profil", "enabled": True,
                      "method": "comic", "mode": "factor", "value": 0.5,
                      "colors": 64, "parent": None})
        self.table.setCurrentCell(self.table.rowCount() - 1, 1)

    def values(self):
        result = []
        for row in range(self.table.rowCount()):
            mode = self.table.cellWidget(row, 4).currentData()
            value = self.table.cellWidget(row, 5).value()
            result.append({
                "key": self.table.item(row, 0).text().strip(),
                "name": self.table.item(row, 1).text().strip(),
                "enabled": self.table.cellWidget(row, 2).isChecked(),
                "method": self.table.cellWidget(row, 3).currentData(),
                "mode": mode,
                "value": int(value) if mode == "max_edge" and value.is_integer() else value,
                "colors": self.table.cellWidget(row, 6).value(),
                "parent": self.table.cellWidget(row, 7).currentData(),
            })
        return result

    def update_samples(self, *_args):
        if self.filling or self.loading_rows:
            return
        self.filling = True
        try:
            values = self.values()
            parents = [(p["key"], p["name"]) for p in values if p["method"] == "pixel"]
            for row, profile in enumerate(values):
                low = profile["method"] == "pixel_low"
                parent = self.table.cellWidget(row, 7)
                selected = parent.currentData()
                parent.blockSignals(True)
                parent.clear()
                for key, title in (parents if low else [(None, "HD-Quelle")]):
                    parent.addItem(f"{title} · {key}" if key else title, key)
                parent.setCurrentIndex(max(0, parent.findData(selected)))
                parent.setEnabled(low)
                parent.blockSignals(False)
                self.table.cellWidget(row, 6).setEnabled(profile["method"] == "pixel")
            profiles = validate_profiles(self.values())
            for row, profile in enumerate(profiles.values()):
                size = (512, 256)
                if profile["parent"]:
                    parent = profiles[profile["parent"]]
                    size = proportional_size(*size, parent["mode"], parent["value"])
                width, height = proportional_size(*size, profile["mode"], profile["value"])
                self.table.item(row, 8).setText(f"{width} × {height} px")
            self.notice.setText(
                "Proportional, ohne Vergrößerung; Pixelmaße werden halb aufgerundet. "
                "Pixel Low übernimmt die Palette seines Pixel-High-Profils.")
        except (StudioError, ValueError) as error:
            self.notice.setText(str(error))
            for row in range(self.table.rowCount()):
                self.table.item(row, 8).setText("–")
        finally:
            self.filling = False
        if self.track_changes:
            self.record_change()

    def record_change(self):
        try:
            before, after = deepcopy(self.draft), self.values()
            validate_profiles(after)
        except (StudioError, ValueError):
            return
        if before != after:
            initial = [True]

            def forward():
                if initial[0]:
                    initial[0] = False
                else:
                    self.restore_draft(after)

            self.commands.execute(Command("Profilentwurf ändern", forward,
                                           lambda: self.restore_draft(before)))
            self.draft = deepcopy(after)
        self.undo_button.setEnabled(bool(self.commands.done))
        self.redo_button.setEnabled(bool(self.commands.undone))

    def restore_draft(self, values):
        self.track_changes = False
        self.loading_rows = True
        self.filling = True
        self.table.setRowCount(0)
        keys = {profile["key"] for profile in self.original}
        for profile in values:
            self.add_row(profile, existing=profile["key"] in keys)
        self.draft = deepcopy(values)
        self.track_changes = True
        self.loading_rows = False
        self.update_samples()

    def history(self, redo):
        self.commands.redo() if redo else self.commands.undo()
        self.undo_button.setEnabled(bool(self.commands.done))
        self.redo_button.setEnabled(bool(self.commands.undone))

    def save(self):
        try:
            self.service.save(self.values(), self.revision)
            self.original = deepcopy(self.values())
            self.revision = self.project.project().revision_no
            self.changed.emit()
            self.accept()
        except (StudioError, OSError, ValueError) as error:
            show_error(self, error)

    def may_close(self):
        try:
            unchanged = self.values() == self.original
        except (StudioError, ValueError):
            unchanged = False
        return unchanged or QMessageBox.question(
            self, "Ungespeicherte Profile", "Änderungen an Projektprofilen verwerfen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def reject(self):
        if self.may_close():
            super().reject()

    def closeEvent(self, event):
        event.accept() if self.may_close() else event.ignore()


class AssignmentDialog(QDialog):
    """Assignments are catalog records, never executable Canvas relationships."""

    changed = Signal()

    def __init__(self, project, recipe_id, parent=None):
        super().__init__(parent)
        self.project, self.recipe_id = project, recipe_id
        self.service, self.commands = PipelineService(project), Commands(project)
        self.recipe = self.service.recipe(recipe_id)
        self.setWindowTitle("Pipeline-Zuweisungen · " + self.recipe.title)
        self.resize(960, 660)
        layout = QVBoxLayout(self)
        layout.addWidget(label(
            "Priorität: einzelnes Asset vor Typ-/Fähigkeitsregel vor Projektstandard. "
            "Gleichrangige Treffer sind Konflikte, keine Verkettung. Neue passende Assets "
            "erben Regeln, werden aber nicht automatisch gebaut."
        ))
        self.table = QTableWidget(0, 5)
        self.table.setObjectName("pipeline_assignments")
        self.table.setHorizontalHeaderLabels([
            "Zuweisung", "Ziel", "Fähigkeiten", "Lokale Abweichungen", "Zustand",
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        form = QFormLayout()
        self.mode = choice((("asset", "Einzelnes Asset"), ("type", "Asset-Typ / Fähigkeiten"),
                            ("default", "Projektstandard")), "asset")
        self.assets = choice(((r.id, r.title) for r in project.catalog.records()
                             if r.kind == "asset" and "asset_definition" in r.data))
        self.types = choice([(None, "Alle passenden Typen"), *self.service.asset_types().items()])
        self.capabilities = {}
        caps = QHBoxLayout()
        for name in CAPABILITIES:
            check = QCheckBox(CAPTION[name])
            self.capabilities[name] = check
            caps.addWidget(check)
        form.addRow("Zuweisungsart", self.mode)
        form.addRow("Asset", self.assets)
        form.addRow("Asset-Typ", self.types)
        form.addRow("Benötigte Fähigkeiten", caps)
        self.overrides = QPlainTextEdit("{}")
        self.overrides.setObjectName("pipeline_assignment_overrides")
        self.overrides.setMaximumHeight(75)
        allowed = self.recipe.data["recipe"]["overridable"]
        self.overrides.setToolTip("Nur freigegebene Parameter: " + (", ".join(allowed) or "keine"))
        self.overrides.setEnabled(bool(allowed))
        form.addRow("Lokale Parameter (JSON)", self.overrides)
        layout.addLayout(form)
        self.notice = label("", "pipeline_assignment_status")
        layout.addWidget(self.notice)
        actions = QHBoxLayout()
        self.add_button = button("Zuweisung hinzufügen", "pipeline_assignment_add", self.add)
        actions.addWidget(self.add_button)
        actions.addWidget(button("Zuweisung entfernen", "pipeline_assignment_remove", self.remove))
        self.undo_button = button("Rückgängig", "pipeline_assignment_undo",
                                  lambda: self.history(False))
        self.redo_button = button("Wiederholen", "pipeline_assignment_redo",
                                  lambda: self.history(True))
        actions.addWidget(self.undo_button)
        actions.addWidget(self.redo_button)
        actions.addStretch()
        actions.addWidget(button("Schließen", "pipeline_assignment_close", self.accept))
        layout.addLayout(actions)
        self.mode.currentIndexChanged.connect(self.update_mode)
        self.update_mode()
        self.refresh()

    def update_mode(self):
        mode = self.mode.currentData()
        self.assets.setEnabled(mode == "asset")
        self.types.setEnabled(mode == "type")
        for check in self.capabilities.values():
            check.setEnabled(mode == "type")
        self.add_button.setEnabled(mode != "asset" or self.assets.count() > 0)

    def refresh(self):
        conflicts, effective = [], []
        for asset in self.project.catalog.records():
            if asset.kind != "asset" or "asset_definition" not in asset.data:
                continue
            try:
                binding = self.service.resolve(asset.id)
                if binding and binding["recipe"].id == self.recipe_id:
                    effective.append(asset.title)
            except StudioError as error:
                conflicts.append(f"{asset.title}: {error}")
        rows = [r for r in self.service.assignments() if r.data["recipe_id"] == self.recipe_id]
        self.table.setRowCount(0)
        for record in rows:
            data = record.data
            target = "Gesamtes Projekt"
            origin = "Projektstandard"
            if data["asset_id"]:
                target = self.project.catalog.get(data["asset_id"]).title
                origin = "Asset"
            elif data["type_id"] or data["capabilities"]:
                target = self.service.asset_types().get(data["type_id"], "Passende Fähigkeiten")
                origin = "Typ-/Fähigkeitsregel"
            duplicates = [r for r in self.service.assignments() if
                          all(r.data[key] == data[key] for key in
                              ("asset_id", "type_id", "capabilities"))]
            state = "Konflikt: gleichrangige Regel" if len(duplicates) > 1 else "Gespeichert"
            columns = (origin, target, ", ".join(CAPTION[c] for c in data["capabilities"]),
                       json.dumps(data["overrides"], ensure_ascii=False), state)
            row = self.table.rowCount()
            self.table.insertRow(row)
            for column, text in enumerate(columns):
                item = readonly(text)
                item.setData(Qt.ItemDataRole.UserRole, record.id)
                self.table.setItem(row, column, item)
        self.table.resizeColumnsToContents()
        self.notice.setText(
            f"Wirksam für {len(effective)} Assets. " +
            ("\n".join(conflicts) if conflicts else "Keine Asset-Konflikte erkannt."))
        self.undo_button.setEnabled(bool(self.commands.done))
        self.redo_button.setEnabled(bool(self.commands.undone))

    def _archive(self, identifier, state):
        record = self.project.catalog.get(identifier)
        self.project.catalog.save(record, archived=state)

    def add(self):
        try:
            mode = self.mode.currentData()
            capabilities = tuple(k for k, w in self.capabilities.items() if w.isChecked()) \
                if mode == "type" else ()
            if mode == "type" and not self.types.currentData() and not capabilities:
                raise StudioError("validation", "Typ oder mindestens eine Fähigkeit auswählen.")
            overrides = json.loads(self.overrides.toPlainText())
            if not isinstance(overrides, dict):
                raise StudioError("validation", "Lokale Parameter benötigen ein JSON-Objekt.")
            kwargs = {"asset_id": self.assets.currentData() if mode == "asset" else None,
                      "type_id": self.types.currentData() if mode == "type" else None,
                      "capabilities": capabilities, "overrides": overrides}
            identifiers = []

            def forward():
                if identifiers:
                    self._archive(identifiers[0], False)
                else:
                    identifiers.append(self.service.assign(self.recipe_id, **kwargs).id)

            self.commands.execute(Command("Pipeline zuweisen", forward,
                                           lambda: self._archive(identifiers[0], True)))
            self.refresh()
            self.changed.emit()
        except (StudioError, OSError, ValueError) as error:
            show_error(self, error)

    def remove(self):
        row = self.table.currentRow()
        if row < 0:
            return
        identifier = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        try:
            self.commands.execute(Command("Pipeline-Zuweisung entfernen",
                lambda: self._archive(identifier, True), lambda: self._archive(identifier, False)))
            self.refresh()
            self.changed.emit()
        except (StudioError, OSError, ValueError) as error:
            show_error(self, error)

    def history(self, redo):
        try:
            self.commands.redo() if redo else self.commands.undo()
            self.refresh()
            self.changed.emit()
        except (StudioError, OSError, ValueError) as error:
            show_error(self, error)


class PipelineRunWorker(QThread):
    """Qt scheduling only; admission, snapshots and execution stay in BuildPlanner."""

    result = Signal(object)
    failed = Signal(str)
    event_received = Signal(object)

    def __init__(self, project, recipe_id, asset_id, plans=None, parent=None):
        super().__init__(parent)
        self.project, self.recipe_id, self.asset_id = project, recipe_id, asset_id
        self.plans, self.cancelled = plans, Event()

    def run(self):
        try:
            if self.plans is None:
                service = RecipeBuildService(self.project)
                if self.asset_id:
                    asset = self.project.catalog.get(self.asset_id)
                    row = {"asset_id": asset.id, "title": asset.title}
                    try:
                        binding = PipelineService(self.project).resolve(asset.id)
                        if self.recipe_id and (not binding or
                                               binding["recipe"].id != self.recipe_id):
                            row.update(state="excluded", reason="Andere/keine wirksame Pipeline")
                        else:
                            plan = service.plan(asset.id)
                            requested = any(v.required for v in plan.variants)
                            row.update(state="affected" if requested else "excluded",
                                       reason="Geprüfter Ausführungsplan" if requested else
                                       "Alle Zielprofile sind deaktiviert", plan=plan)
                    except (StudioError, OSError, ValueError) as error:
                        row.update(state="blocked", reason=str(error))
                    rows = [row]
                else:
                    rows = service.dry_run(self.recipe_id)
                self.result.emit({"mode": "plan", "rows": rows,
                                  "cancelled": self.cancelled.is_set()})
            else:
                reports, errors = [], []
                for plan in self.plans:
                    if self.cancelled.is_set():
                        break
                    self.event_received.emit({"kind": "asset_started", "asset_id": plan.owner_id})
                    try:
                        report = BuildPlanner(self.project).execute(
                            plan, cancelled=self.cancelled.is_set,
                            on_event=lambda event, owner=plan.owner_id: self.event_received.emit(
                                {**event, "asset_id": owner}))
                        reports.append({"asset_id": plan.owner_id, "report": report})
                    except Exception as error:
                        failure = {"asset_id": plan.owner_id, "reason": str(error)}
                        errors.append(failure)
                        self.event_received.emit({"kind": "asset_failed", **failure})
                self.result.emit({"mode": "run", "reports": reports,
                                  "errors": errors, "planned_assets": len(self.plans),
                                  "cancelled": self.cancelled.is_set()})
        except Exception as error:
            self.failed.emit(str(error))


class ResultPreviewWorker(QThread):
    """Verify outputs again and decode bounded previews away from the GUI thread."""

    result = Signal(object)
    failed = Signal(str)

    def __init__(self, project, build_id, parent=None):
        super().__init__(parent)
        self.project, self.build_id, self.cancelled = project, build_id, Event()

    def resampling(self, record):
        """Use the frozen build procedure, not a profile name or its edited current value."""
        visited = set()
        jobs = JobStore(self.project.catalog)
        while record.id not in visited and len(visited) <= 128:
            visited.add(record.id)
            request = jobs.get(record.data["job_id"])["request"]
            profile = json.loads(request["parameters"]).get("profile")
            if profile:
                return Image.Resampling.NEAREST if profile["method"] in {"pixel", "pixel_low"} \
                    else Image.Resampling.LANCZOS
            upstream = next((v for v in request["inputs"] if v["name"] == "upstream.png"), None)
            if upstream is None:
                break
            record = self.project.catalog.get(upstream["revision_id"])
        return Image.Resampling.LANCZOS

    def run(self):
        try:
            record = self.project.catalog.get(self.build_id)
            data = record.data
            cache = BuildCache(self.project.catalog)
            cache.verify(record, tuple(o["path"] for o in data["outputs"]), data["dependencies"])
            artifact = RecipeResultService(self.project).metadata(record)
            image_path = safe_target(cache.root, artifact["image_path"])
            metadata = artifact["metadata"]
            frames = []
            with Image.open(image_path) as sheet:
                cols, rows = metadata["grid"]
                count = metadata["frames"]
                if (sheet.width * sheet.height > 64 * 1024 * 1024 or
                        not 1 <= count <= 256 or cols * rows < count):
                    raise StudioError("unavailable",
                                      "Ergebnis geprüft, aber zu groß für die Vorschau.")
                width, height = sheet.width // cols, sheet.height // rows
                method = self.resampling(record)
                for index in range(count):
                    if self.cancelled.is_set():
                        return
                    x, y = index % cols * width, index // cols * height
                    frame = sheet.crop((x, y, x + width, y + height)).convert("RGBA")
                    frame.thumbnail((384, 384), method)
                    raw = frame.tobytes()
                    frames.append(QImage(raw, frame.width, frame.height, frame.width * 4,
                                         QImage.Format.Format_RGBA8888).copy())
            self.result.emit({"build_id": record.id, "metadata": metadata, "frames": frames,
                              "path": str(image_path)})
        except Exception as error:
            self.failed.emit(str(error))


class PipelineRunDialog(QDialog):
    """Preview an immutable plan, confirm explicitly, then run it without blocking Qt."""

    changed = Signal()

    def __init__(self, project, recipe_id=None, parent=None, asset_id=None):
        super().__init__(parent)
        self.project, self.recipe_id, self.asset_id = project, recipe_id, asset_id
        self.worker = self.preview_worker = None
        self.plans, self.rows, self.reports = (), [], []
        self.preview_frames, self.frame_index, self.preview_metadata = [], 0, {}
        self.selected_build, self.completed_nodes = None, 0
        self.selected_job = None
        self.setWindowTitle("Pipeline ausführen · Dry-run und geprüfte Bilder")
        self.resize(1100, 800)
        layout = QVBoxLayout(self)
        self.notice = label(
            "Zuerst Dry-run: betroffene, ausgeschlossene und blockierte Assets prüfen. "
            "Erst die bestätigte Ausführung schreibt Ableitungen; Originale bleiben erhalten.",
            "pipeline_run_notice")
        layout.addWidget(self.notice)
        actions = QHBoxLayout()
        self.plan_button = button("Dry-run erstellen", "pipeline_run_plan", self.preview)
        self.run_button = button("Geprüften Plan ausführen …", "pipeline_run_execute", self.execute)
        self.run_button.setEnabled(False)
        self.cancel_button = button("Abbrechen", "pipeline_run_cancel", self.cancel)
        self.cancel_button.setEnabled(False)
        actions.addWidget(self.plan_button)
        actions.addWidget(self.run_button)
        actions.addWidget(self.cancel_button)
        self.log_button = button("Auftragsprotokolle …", "pipeline_raw_logs", self.show_logs)
        self.log_button.setEnabled(False)
        actions.addWidget(self.log_button)
        actions.addStretch()
        actions.addWidget(button("Schließen", "pipeline_run_close", self.reject))
        layout.addLayout(actions)
        self.summary = label("Noch kein Dry-run erstellt.", "pipeline_run_summary")
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        layout.addWidget(self.summary)
        layout.addWidget(self.progress)
        self.tree = QTreeWidget()
        self.tree.setObjectName("pipeline_run_results")
        self.tree.setHeaderLabels(["Asset / Schritt", "Zustand", "Geplante Ausgaben / Ergebnis"])
        self.tree.currentItemChanged.connect(self.show_details)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setObjectName("pipeline_result_metadata")
        self.image = QLabel("Noch kein geprüftes Bild ausgewählt.")
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setMinimumSize(180, 150)
        self.image.setObjectName("pipeline_image_preview")
        self.preview_fps = QDoubleSpinBox()
        self.preview_fps.setObjectName("pipeline_preview_fps")
        self.preview_fps.setRange(0.01, 240)
        self.preview_fps.setDecimals(2)
        self.preview_fps.setValue(8)
        self.preview_fps.setSuffix(" Vorschau-FPS")
        self.preview_fps.setEnabled(False)
        self.preview_fps.valueChanged.connect(self.update_preview_rate)
        self.play_button = button("Vorschau abspielen", "pipeline_preview_play", self.toggle_play)
        self.play_button.setEnabled(False)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame)
        preview = QWidget()
        preview_layout = QVBoxLayout(preview)
        preview_layout.addWidget(self.image, 1)
        playback = QHBoxLayout()
        playback.addWidget(self.preview_fps)
        playback.addWidget(self.play_button)
        preview_layout.addLayout(playback)
        preview_layout.addWidget(label("Vorschau-FPS sind flüchtig: keine Änderung an PNG, "
                                        "Rezept oder gespeichertem Wiedergabe-Timing."))
        horizontal = QSplitter(Qt.Orientation.Horizontal)
        horizontal.addWidget(self.details)
        horizontal.addWidget(preview)
        vertical = QSplitter(Qt.Orientation.Vertical)
        vertical.addWidget(self.tree)
        vertical.addWidget(horizontal)
        layout.addWidget(vertical, 1)
        self.logs = QPlainTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setMaximumBlockCount(2000)
        self.logs.setMaximumHeight(135)
        self.logs.setObjectName("pipeline_run_logs")
        layout.addWidget(self.logs)

    def preview(self):
        if self.worker:
            return
        self.plans, self.rows = (), []
        self.run_button.setEnabled(False)
        self.tree.clear()
        self.start_worker(None)

    def execute(self):
        if self.worker or not self.plans:
            return
        count = len(self.plans)
        response = QMessageBox.question(
            self, "Bildverarbeitung starten", f"{count} Asset(s) mit genau dem geprüften "
            "Rezept-/Profil-Snapshot verarbeiten? Ausgeschlossene und blockierte Assets "
            "werden nicht ausgeführt. Änderungen nach diesem Dry-run werden nicht übernommen.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if response == QMessageBox.StandardButton.Yes:
            self.start_worker(tuple(self.plans))

    def start_worker(self, plans):
        self.completed_nodes = 0
        self.progress.setRange(0, sum(len(p.nodes) for p in plans) if plans is not None else 0)
        self.progress.setValue(0)
        self.worker = PipelineRunWorker(self.project, self.recipe_id, self.asset_id, plans, self)
        self.worker.result.connect(self.present)
        self.worker.failed.connect(self.failed)
        self.worker.event_received.connect(self.on_event)
        self.worker.finished.connect(self.finished_worker)
        self.plan_button.setEnabled(False)
        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.summary.setText("Dry-run läuft …" if plans is None else "Bildverarbeitung läuft …")
        self.logs.clear()
        self.worker.start()

    def on_event(self, event):
        self.logs.appendPlainText(json.dumps(event, ensure_ascii=False))
        if event.get("kind") == "node_finished":
            self.completed_nodes += 1
            self.progress.setValue(self.completed_nodes)

    def failed(self, message):
        self.summary.setText("Fehlgeschlagen: " + message)
        self.logs.appendPlainText(message)
        self.plans = ()

    def finished_worker(self):
        self.worker.deleteLater()
        self.worker = None
        self.plan_button.setEnabled(True)
        self.run_button.setEnabled(bool(self.plans))
        self.cancel_button.setEnabled(False)
        if self.progress.maximum() == 0:
            self.progress.setRange(0, 1)
            self.progress.setValue(1)

    def present(self, value):
        self.tree.clear()
        if value["mode"] == "plan":
            self.present_plan(value)
        else:
            self.present_run(value)
        self.tree.resizeColumnToContents(0)
        self.tree.resizeColumnToContents(1)
        self.tree.setColumnWidth(0, min(400, self.tree.columnWidth(0)))

    def present_plan(self, value):
        self.rows = value["rows"]
        counts, plans = Counter(), []
        for row in self.rows:
            plan = row.get("plan")
            if plan and any(n.state == "blocked" and n.node.required for n in plan.nodes):
                row.update(state="blocked", reason="Technische Schritte blockiert")
            counts[row["state"]] += 1
            if row["state"] == "affected":
                plans.append(plan)
            state = {"affected": "Betroffen", "blocked": "Blockiert", "excluded": "Ausgeschlossen"}
            detail = row["reason"]
            if plan:
                targets = sum(v.required for v in plan.variants)
                outputs = sum(len(n.node.outputs) for n in plan.nodes if n.node.required)
                detail += f" · {targets} Zielvarianten / {outputs} Dateien (inkl. Zwischenschritte)"
            item = QTreeWidgetItem([row["title"], state[row["state"]], detail])
            item.setData(0, Qt.ItemDataRole.UserRole, {"text": detail})
            self.tree.addTopLevelItem(item)
            if plan:
                for planned in plan.nodes:
                    child = QTreeWidgetItem([
                        planned.node.key, NAMES[planned.state], planned.reason])
                    payload = {"text": json.dumps({
                        "snapshot": json.loads(plan.snapshot), "parameter":
                        json.loads(planned.node.parameters), "outputs":
                        [o.path for o in planned.node.outputs], "fingerprint": planned.fingerprint,
                    }, ensure_ascii=False, indent=2)}
                    if planned.state == "reused":
                        payload["build_id"] = planned.build_id
                    child.setData(0, Qt.ItemDataRole.UserRole, payload)
                    item.addChild(child)
        self.plans = () if value["cancelled"] else tuple(plans)
        self.summary.setText(
            f"Betroffen: {counts['affected']} · Ausgeschlossen: {counts['excluded']} · "
            f"Blockiert: {counts['blocked']}" +
            (" · Dry-run abgebrochen" if value["cancelled"] else ""))
        self.notice.setText("Der Plan ist eingefroren. Vor Ausführung Zielvarianten und Blocker "
                            "prüfen; bei geänderten Einstellungen einen neuen Dry-run erstellen.")

    def present_run(self, value):
        self.plans, self.reports = (), value["reports"]
        succeeded = 0
        for entry in self.reports:
            report = entry["report"]
            success = report["status"] == "succeeded"
            succeeded += success
            asset = self.project.catalog.get(entry["asset_id"])
            detail = report.get("publication_error", "Snapshot: " + report["run_id"])
            item = QTreeWidgetItem([asset.title, "Erfolgreich" if success else "Unvollständig",
                                   detail])
            item.setData(0, Qt.ItemDataRole.UserRole, {"text": json.dumps(
                json.loads(report["plan"].get("snapshot", "{}")),
                ensure_ascii=False, indent=2)})
            self.tree.addTopLevelItem(item)
            for row in report["actual"]:
                child = QTreeWidgetItem([row["node"], NAMES.get(row["actual"], row["actual"]),
                                        row.get("reason", "")])
                payload = {"text": json.dumps(row, ensure_ascii=False, indent=2)}
                if row.get("job_id"):
                    payload["job_id"] = row["job_id"]
                if row["actual"] in {"built", "reused"}:
                    payload["build_id"] = row["build_id"]
                child.setData(0, Qt.ItemDataRole.UserRole, payload)
                item.addChild(child)
            item.setExpanded(True)
        for error in value.get("errors", []):
            asset = self.project.catalog.get(error["asset_id"])
            item = QTreeWidgetItem([asset.title, "Fehlgeschlagen", error["reason"]])
            item.setData(0, Qt.ItemDataRole.UserRole, {"text": error["reason"]})
            self.tree.addTopLevelItem(item)
        total = value.get("planned_assets", len(self.reports))
        self.summary.setText(f"Erfolgreich geprüft: {succeeded}/{total} Assets" +
                            (" · Abbruch angefordert" if value["cancelled"] else ""))
        self.notice.setText(
            "Nur vollständige Asset-Läufe gelten als veröffentlicht. Geprüfte Zwischenschritte "
            "unvollständiger Läufe sind nur Diagnoseansichten. Bildschritt für Vorschau auswählen.")
        self.changed.emit()

    def show_details(self, current, _previous=None):
        self.timer.stop()
        self.play_button.setText("Vorschau abspielen")
        self.play_button.setEnabled(False)
        self.preview_fps.setEnabled(False)
        self.preview_frames = []
        self.selected_build = None
        self.selected_job = None
        self.log_button.setEnabled(False)
        self.image.clear()
        if not current:
            return
        data = current.data(0, Qt.ItemDataRole.UserRole) or {}
        self.details.setPlainText(data.get("text", ""))
        self.selected_build = data.get("build_id")
        self.selected_job = data.get("job_id")
        if self.selected_build and not self.selected_job:
            self.selected_job = self.project.catalog.get(self.selected_build).data["job_id"]
        self.log_button.setEnabled(bool(self.selected_job))
        if self.preview_worker:
            self.preview_worker.cancelled.set()
        elif self.selected_build:
            self.start_preview()

    def start_preview(self):
        self.image.setText("Prüfe Bild-Ergebnis …")
        self.preview_worker = ResultPreviewWorker(self.project, self.selected_build, self)
        self.preview_worker.result.connect(self.present_preview)
        self.preview_worker.failed.connect(self.preview_failed)
        self.preview_worker.finished.connect(self.finished_preview)
        self.preview_worker.start()

    def show_logs(self):
        if not self.selected_job:
            return
        try:
            root = self.project.catalog.path.parent
            chunks = []
            for name in ("stdout.log", "stderr.log", "host-stderr.log"):
                path = safe_target(root, f".asset-studio/jobs/{self.selected_job}/logs/{name}")
                if path.is_file():
                    with path.open("rb") as stream:
                        raw = stream.read(65537)
                    content = raw[:65536].decode("utf-8", errors="replace")
                    chunks.append(name + "\n" + content +
                                  ("\n[auf 64 KiB gekürzt]" if len(raw) > 65536 else ""))
            dialog = QDialog(self)
            dialog.setWindowTitle("Auftragsprotokolle · " + self.selected_job)
            dialog.resize(920, 620)
            layout = QVBoxLayout(dialog)
            text = QPlainTextEdit()
            text.setReadOnly(True)
            text.setPlainText("\n\n".join(chunks) or "Noch keine Prozessprotokolle vorhanden.")
            layout.addWidget(text)
            layout.addWidget(button("Schließen", "pipeline_logs_close", dialog.accept))
            dialog.exec()
            dialog.deleteLater()
        except (StudioError, OSError) as error:
            show_error(self, error)

    def preview_failed(self, message):
        if self.preview_worker and self.preview_worker.build_id == self.selected_build:
            self.image.setText(message)

    def finished_preview(self):
        previous = self.preview_worker.build_id
        self.preview_worker.deleteLater()
        self.preview_worker = None
        if self.selected_build and self.selected_build != previous:
            self.start_preview()

    def present_preview(self, value):
        if value["build_id"] != self.selected_build:
            return
        self.preview_frames, self.preview_metadata = value["frames"], value["metadata"]
        self.frame_index = 0
        metadata = value["metadata"]
        self.details.setPlainText("Geprüftes Bild: " + value["path"] + "\n" +
                                  json.dumps(metadata, ensure_ascii=False, indent=2))
        self.image.setPixmap(QPixmap.fromImage(self.preview_frames[0]))
        animated = metadata["kind"] == "spritesheet"
        self.preview_fps.setVisible(animated)
        self.play_button.setVisible(animated)
        self.preview_fps.setEnabled(animated)
        self.play_button.setEnabled(animated and len(self.preview_frames) > 1)
        if animated:
            self.preview_fps.setValue(metadata["fps"])

    def update_preview_rate(self):
        self.timer.setInterval(max(1, round(1000 / self.preview_fps.value())))

    def toggle_play(self):
        if self.timer.isActive():
            self.timer.stop()
            self.play_button.setText("Vorschau abspielen")
        elif len(self.preview_frames) > 1:
            self.frame_index = 0
            self.update_preview_rate()
            self.timer.start()
            self.play_button.setText("Vorschau pausieren")

    def next_frame(self):
        if not self.preview_frames:
            self.timer.stop()
            return
        if (self.frame_index + 1 == len(self.preview_frames) and
                not self.preview_metadata.get("loop")):
            self.timer.stop()
            self.play_button.setText("Vorschau abspielen")
            return
        self.frame_index = (self.frame_index + 1) % len(self.preview_frames)
        self.image.setPixmap(QPixmap.fromImage(self.preview_frames[self.frame_index]))

    def cancel(self):
        if self.worker:
            self.worker.cancelled.set()
            self.logs.appendPlainText("Abbruch angefordert; laufenden Worker geordnet beenden.")

    def may_close(self):
        self.timer.stop()
        if self.worker or self.preview_worker:
            self.cancel()
            if self.preview_worker:
                self.selected_build = None
                self.preview_worker.cancelled.set()
            self.notice.setText("Bitte das Ende der laufenden Prüfung/Verarbeitung abwarten.")
            return False
        return True

    def reject(self):
        if self.may_close():
            super().reject()

    def closeEvent(self, event):
        event.accept() if self.may_close() else event.ignore()
