"""Reference selection and mask revision management; pixel painting belongs to T021."""

from io import BytesIO
import html
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

from ..application.mask_service import MaskService
from ..application.project_service import ProjectService
from ..application.reference_service import ReferenceService
from ..domain.materials import MASK_CONTRACT, MATERIAL_CONTRACT, REFERENCE_CONTRACT
from ..domain.models import StudioError
from ..pipelines.image_processing import legacy_modules
from .common import button, label, show_error


class ColorWorker(QThread):
    result = Signal(object)
    failed = Signal(object)

    def __init__(self, root, call, parent):
        super().__init__(parent)
        self.root, self.call = root, call

    def run(self):
        project = None
        try:
            project = ProjectService.open(self.root)
            self.result.emit(self.call(project))
        except Exception as error:
            self.failed.emit(error)
        finally:
            if project:
                project.catalog.close()


def mask_preview(project, identifier, frame):
    service = MaskService(project)
    record = project.catalog.get(identifier)
    source = service.source(record.data["source_revision"], record.owner_id, current=False)
    definitions = service.revision(record.data["material_revision"], record.owner_id,
        MATERIAL_CONTRACT)
    soft, exact = legacy_modules()[-2:]
    materials = definitions.data["definitions"]["materials"]
    result = {"status": service.status(identifier), "images": [],
              "legend": [{**row, "preview": exact.preview_color(row["id"])} for row in materials]}
    with soft.load_png(service.blob(source.data)) as image:
        boxes = list(soft.frame_boxes(image.size, source.data["grid"]))
        box = boxes[min(frame - 1, len(boxes) - 1)]
        pictures = [image.crop(box)]
        try:
            with exact.load_mask(service.blob(record.data), image, source.data["grid"],
                definitions.data["definitions"]["materials"], source.data["sha256"],
                    validate=False) as mask:
                with exact.mask_preview(mask, image, definitions.data["definitions"][
                    "materials"]) as overlay:
                    pictures.append(overlay.crop(box))
        except ValueError:
            pass  # Binding/geometry errors are reported; never stretch a wrong label mask.
        for picture in pictures:
            with picture, BytesIO() as stream:
                picture.thumbnail((800, 600), Image.Resampling.NEAREST)
                picture.save(stream, format="PNG")
                result["images"].append(stream.getvalue())
    return result


class ReferenceMaterialsDialog(QDialog):

    def __init__(self, project, asset_id, parent=None, *, embedded=False):
        super().__init__(parent)
        self.project, self.asset_id = project, asset_id
        self.embedded = embedded
        self.refs, self.masks = ReferenceService(project), MaskService(project)
        self.worker = None
        self.changed = self.pending_close = self.loading = False
        self.references_dirty = self.materials_dirty = False
        self.success = lambda result: None
        self.preview_result = None
        self.focus_mask_id = None
        self.setObjectName("reference_materials_dialog")
        self.setWindowTitle("Referenzen / Materialien · " + self.refs.asset(asset_id).title)
        self.resize(1100, 820)
        layout = QVBoxLayout(self)
        self.pages = QTabWidget()
        layout.addWidget(self.pages)
        self.build_references()
        self.build_materials()
        self.build_masks()
        self.status = label("", "color_status")
        layout.addWidget(self.status)
        if not embedded:
            layout.addWidget(button("Schließen", "color_close", self.reject))
        self.refresh()

    def page(self, title):
        widget = QWidget()
        self.pages.addTab(widget, title)
        return QVBoxLayout(widget)

    def build_references(self):
        layout = self.page("Masterreferenzen / Farbprofile")
        layout.addWidget(label(
            "Tatsächliche Quellen auswählen. Alle Frames jeder Referenz zählen gleich; "
            "gemischte Raster sind nicht zulässig. Diese Farbprofile sind unabhängig "
            "von Grafikauflösungen."))
        self.references = QTreeWidget()
        self.references.setObjectName("color_references")
        self.references.setHeaderLabels(["Auswahl / Pose", "Richtung", "Raster / Frames",
            "Quellenrevision"])
        self.references.itemChanged.connect(lambda: self.dirty("references"))
        layout.addWidget(self.references)
        self.preview_reference = QComboBox()
        self.preview_reference.setObjectName("color_preview_reference")
        self.preview_reference.activated.connect(lambda: self.dirty("references"))
        layout.addWidget(label("Ausdrückliche gemeinsame Referenz für die Vorschau:"))
        layout.addWidget(self.preview_reference)
        self.reference_image = QLabel()
        self.reference_image.setMinimumHeight(90)
        self.preview_reference.currentIndexChanged.connect(self.show_reference)
        layout.addWidget(self.reference_image)
        self.reference_history = QComboBox()
        self.reference_history.setObjectName("color_reference_history")
        layout.addWidget(self.reference_history)
        actions = QHBoxLayout()
        actions.addWidget(button("Auswahl speichern", "color_save_references",
            self.save_references))
        actions.addWidget(button("Frühere Auswahl laden", "color_load_references",
            self.load_references))
        actions.addWidget(button("Vorlage: acht Stand-Sheets", "color_greenhero", self.greenhero))
        layout.addLayout(actions)
        self.mode = QComboBox()
        self.mode.setObjectName("color_profile_mode")
        for name, value in (("Weicher Farbabgleich", "soft"), ("Feste Palette", "fixed"), (
            "Materialfarben", "material")):
            self.mode.addItem(name, value)
        layout.addWidget(self.mode)
        layout.addWidget(button("Farbprofil aus gespeicherten Referenzen erzeugen",
            "color_generate", self.generate))
        layout.addWidget(button("Farbprofil exportieren …", "color_export_profile",
            self.export_profile))
        self.profile_info = label("", "color_profile_info")
        layout.addWidget(self.profile_info)
        layout.addWidget(
            label(
                "Farbprofile und Masken werden als ausdrücklich deklarierte "
                "Ressourcen im Pipelineeditor verwendet. Jedes Asset behält seine eigenen Profile."
            )
        )

    def build_materials(self):
        layout = self.page("Materialdefinitionen")
        layout.addWidget(label("IDs 1–255 bezeichnen Materialien, ID 0 den Hintergrund. "
            "Vorschaufarben kennzeichnen nur die IDs; Zielfarben entstehen aus "
            "gelabelten Referenzpixeln."))
        self.materials = QTableWidget(0, 3)
        self.materials.setObjectName("color_materials")
        self.materials.setHorizontalHeaderLabels(["Material-ID", "Name", "Farbstufen"])
        self.materials.itemChanged.connect(lambda: self.dirty("materials"))
        layout.addWidget(self.materials)
        actions = QHBoxLayout()
        actions.addWidget(button("Material hinzufügen", "color_add_material",
            lambda: self.add_material()))
        actions.addWidget(button("Zeile entfernen", "color_remove_material", self.remove_material))
        actions.addWidget(button("Definitionen importieren …", "color_import_definitions",
            self.import_definitions))
        actions.addWidget(button("Als neue Revision speichern", "color_save_materials",
            self.save_materials))
        layout.addLayout(actions)
        self.material_history = label("", "color_material_history")
        layout.addWidget(self.material_history)

    def build_masks(self):
        layout = self.page("Masken / Revisionen")
        self.mask_source = QComboBox()
        self.mask_source.setObjectName("color_mask_source")
        layout.addWidget(label("Konkrete Quelle für Import oder neue unbeschriftete Vorlage:"))
        layout.addWidget(self.mask_source)
        actions = QHBoxLayout()
        actions.addWidget(button("L/P-Maske importieren …", "color_import_mask", self.import_mask))
        actions.addWidget(button("Unbeschriftete Vorlage anlegen", "color_mask_template",
            self.template))
        layout.addLayout(actions)
        self.mask_history = QComboBox()
        self.mask_history.setObjectName("color_mask_history")
        self.mask_history.activated.connect(self.mask_selected)
        layout.addWidget(self.mask_history)
        actions = QHBoxLayout()
        self.frame = QSpinBox()
        self.frame.setObjectName("color_mask_frame")
        self.frame.setMinimum(1)
        actions.addWidget(label("Frame:"))
        actions.addWidget(self.frame)
        actions.addWidget(button("Prüfen / Vorschau", "color_check_mask", self.check_mask))
        actions.addWidget(button("Diese Revision verwenden", "color_activate_mask",
            self.activate_mask))
        actions.addWidget(button("Maske exportieren …", "color_export_mask", self.export_mask))
        layout.addLayout(actions)
        pictures = QHBoxLayout()
        self.source_image, self.mask_image = QLabel("Quelle"), QLabel("Material-IDs")
        for widget in (self.source_image, self.mask_image):
            widget.setMinimumSize(260, 180)
            pictures.addWidget(widget)
        layout.addLayout(pictures)
        self.mask_legend = label("", "color_mask_legend")
        self.mask_legend.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.mask_legend)
        self.findings = QPlainTextEdit()
        self.findings.setObjectName("color_mask_findings")
        self.findings.setReadOnly(True)
        layout.addWidget(self.findings)
        self.reviewed = QCheckBox(
            "Ich habe alle Frames dieser konkreten Maskenrevision visuell geprüft.")
        self.reviewed.setObjectName("color_mask_reviewed")
        layout.addWidget(self.reviewed)
        self.reviewer = QLineEdit()
        self.reviewer.setObjectName("color_mask_reviewer")
        self.reviewer.setPlaceholderText("Name / Prüfprofil")
        self.reviewer.setMaxLength(128)
        layout.addWidget(self.reviewer)
        layout.addWidget(button("Nur diese Maskenrevision bestätigen", "color_confirm_mask",
            self.confirm_mask))

    def dirty(self, kind):
        if not self.loading:
            setattr(self, kind + "_dirty", True)

    def refresh(self):
        self.loading = True
        self.record = self.refs.asset(self.asset_id)
        sources = list(self.refs.sources.active(self.asset_id).values())
        poses = {p.id: p.display_name for p in self.refs.assets.definition(self.asset_id).poses}
        self.pose_names = poses
        titles = {s.id: f"{poses.get(s.data['slot']['pose_id'], 'Einzelbild')} · "
                  f"{s.data['slot']['direction'] or 'ohne Richtung'}" for s in sources}
        selection_id = self.record.data.get("reference_selection_id")
        selection = self.project.catalog.get(selection_id).data["selection"] if selection_id else {}
        if not self.references_dirty:
            self.references.clear()
            self.preview_reference.clear()
            chosen = {r["source_revision"] for r in selection.get("references", [])}
            for source in sources:
                item = QTreeWidgetItem([poses.get(source.data["slot"]["pose_id"], "Einzelbild"),
                    source.data["slot"]["direction"] or "ohne Richtung",
                    f"{source.data['grid']} · {source.data['frames']}", source.id])
                item.setData(0, Qt.ItemDataRole.UserRole, source.id)
                item.setCheckState(0,
                    Qt.CheckState.Checked if source.id in chosen else Qt.CheckState.Unchecked)
                self.references.addTopLevelItem(item)
                self.preview_reference.addItem(titles[source.id], source.id)
            self.preview_reference.setCurrentIndex(self.preview_reference.findData(selection.get(
                "preview_reference")))
        self.reference_history.clear()
        for record in reversed(self.refs.records(self.asset_id, REFERENCE_CONTRACT)):
            self.reference_history.addItem(
                f"{record.created_at} · "
                f"{len(record.data['selection']['references'])} Referenzen", record.id)
        definition_id = self.record.data.get("material_definition_id")
        if not self.materials_dirty:
            self.materials.setRowCount(0)
            if definition_id:
                for material in self.masks.definitions(self.asset_id).data["definitions"][
                    "materials"]:
                    self.add_material(material)
        count = len(self.masks.records(self.asset_id, MATERIAL_CONTRACT))
        self.material_history.setText(
            f"{count} gespeicherte Definitionen · aktive Revision: {definition_id or 'keine'}")
        old_source = self.mask_source.currentData()
        old_mask = self.focus_mask_id or self.mask_history.currentData()
        self.focus_mask_id = None
        self.mask_source.clear()
        for source in sources:
            self.mask_source.addItem(titles[source.id], source.id)
        if old_source:
            self.mask_source.setCurrentIndex(self.mask_source.findData(old_source))
        self.mask_history.clear()
        for record in reversed(self.masks.records(self.asset_id, MASK_CONTRACT)):
            self.mask_history.addItem(
                f"{record.created_at} · {record.data['slot']['direction'] or 'Einzelbild'} · "
                f"{record.title} · {record.data['technical']}", record.id)
        if old_mask:
            self.mask_history.setCurrentIndex(self.mask_history.findData(old_mask))
        self.mask_selected()
        profiles = self.record.data.get("color_profiles", {})
        self.profile_info.setText("Gespeicherte Farbprofile: " + (", ".join(profiles) or "keine") +
            ". Aktuelle Quell-/Maskenbindung wird vor Nutzung geprüft.")
        self.loading = False
        self.show_reference()

    def show_reference(self):
        self.reference_image.clear()
        identifier = self.preview_reference.currentData()
        if identifier:
            source = self.project.catalog.get(identifier)
            pixmap = QPixmap(str(self.refs.store.path_for(source.data["sha256"])))
            self.reference_image.setPixmap(pixmap.scaled(700, 110,
                Qt.AspectRatioMode.KeepAspectRatio))

    def start(self, call, success=None):
        if self.worker:
            return
        self.success = success or (lambda result: None)
        self.preview_result = None
        self.pages.setEnabled(False)
        self.status.setText("Wird geprüft/verarbeitet …")
        self.worker = ColorWorker(self.project.catalog.path.parent, call, self)
        self.worker.result.connect(self.succeeded)
        self.worker.failed.connect(self.failed)
        self.worker.finished.connect(self.worker_finished)
        self.worker.start()

    def succeeded(self, result):
        self.success(result)
        if getattr(result, "data", {}).get("contract") == MASK_CONTRACT:
            self.focus_mask_id = result.id
        self.changed = True
        self.status.setText("Vorgang abgeschlossen. Es wurde kein Bildbuild gestartet.")

    def failed(self, error):
        self.status.setText("Vorgang fehlgeschlagen. Die Fehlermeldung enthält die Ursache.")
        show_error(self, error)

    def worker_finished(self):
        self.worker.deleteLater()
        self.worker = None
        self.pages.setEnabled(True)
        self.refresh()
        if self.preview_result is not None:
            self.render_mask(self.preview_result)
        if self.pending_close:
            self.pending_close = False
            self.reject()

    def save_references(self):
        ids = [self.references.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole)
               for i in range(self.references.topLevelItemCount())
               if self.references.topLevelItem(i).checkState(0) == Qt.CheckState.Checked]
        preview, expected = self.preview_reference.currentData(), self.record.revision_no
        self.start(lambda p: ReferenceService(p).select(self.asset_id, ids, preview, expected),
                   lambda result: setattr(self, "references_dirty", False))

    def load_references(self):
        identifier = self.reference_history.currentData()
        if not identifier:
            return
        selection = self.project.catalog.get(identifier).data["selection"]
        ids = {r["source_revision"] for r in selection["references"]}
        available = {self.references.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole)
                     for i in range(self.references.topLevelItemCount())}
        if not ids <= available:
            show_error(self, StudioError("validation",
                "Frühere Auswahl enthält inzwischen inaktive Quellen."))
            return
        for i in range(self.references.topLevelItemCount()):
            item = self.references.topLevelItem(i)
            item.setCheckState(0, Qt.CheckState.Checked if item.data(0,
                Qt.ItemDataRole.UserRole) in ids
                               else Qt.CheckState.Unchecked)
        self.preview_reference.setCurrentIndex(self.preview_reference.findData(selection[
            "preview_reference"]))
        self.references_dirty = True

    def greenhero(self):
        expected = self.record.revision_no
        self.start(lambda p: ReferenceService(p).greenhero_selection(self.asset_id, expected),
                   lambda result: setattr(self, "references_dirty", False))

    def require_saved(self):
        if self.references_dirty or self.materials_dirty:
            show_error(self, StudioError("validation",
                "Geänderte Referenzen und Materialdefinitionen zuerst speichern."))
            return False
        return True

    def generate(self):
        if self.require_saved():
            mode, expected = self.mode.currentData(), self.record.revision_no
            self.start(lambda p: ReferenceService(p).generate(self.asset_id, mode, expected))

    def export_profile(self):
        if self.require_saved():
            path, _ = QFileDialog.getSaveFileName(self, "Farbprofil exportieren", "",
                "JSON (*.json)")
            if path:
                mode = self.mode.currentData()

                def export(project):
                    service = ReferenceService(project)
                    return service.export_file(service.profile(self.asset_id, mode).data, path,
                        ".json")

                self.start(export)

    def export_mask(self):
        identifier = self.mask_history.currentData()
        if identifier:
            path, _ = QFileDialog.getSaveFileName(self, "Labelmaske exportieren", "", "PNG (*.png)")
            if path:
                self.start(lambda p: MaskService(p).export_file(
                    p.catalog.get(identifier).data, path, ".png"))

    def add_material(self, material=None):
        material = material or {"id": self.materials.rowCount() + 1, "name": "Neues Material",
            "levels": 4}
        row = self.materials.rowCount()
        self.materials.insertRow(row)
        for column, key in enumerate(("id", "name", "levels")):
            self.materials.setItem(row, column, QTableWidgetItem(str(material[key])))
        self.dirty("materials")

    def remove_material(self):
        self.materials.removeRow(self.materials.currentRow())
        self.dirty("materials")

    def import_definitions(self):
        path, _ = QFileDialog.getOpenFileName(self, "Materialdefinitionen", "", "JSON (*.json)")
        if path:
            try:
                definitions = legacy_modules()[-1].load_definitions(Path(path))
                self.materials.setRowCount(0)
                for material in definitions["materials"]:
                    self.add_material(material)
            except (OSError, ValueError) as error:
                show_error(self, error)

    def save_materials(self):
        try:
            rows = [{"id": int(self.materials.item(r, 0).text()), "name": self.materials.item(r,
                1).text(),
                     "levels": int(self.materials.item(r, 2).text())} for r in range(
                         self.materials.rowCount())]
        except (ValueError, AttributeError):
            show_error(self, StudioError("validation",
                "ID und Farbstufen benötigen ganze Zahlen; Name darf nicht fehlen."))
            return
        expected = self.record.revision_no
        self.start(lambda p: MaskService(p).save_definitions(self.asset_id, rows, expected),
                   lambda result: setattr(self, "materials_dirty", False))

    def import_mask(self):
        source = self.mask_source.currentData()
        if source and self.require_saved():
            path, _ = QFileDialog.getOpenFileName(self, "Quellgebundene L/P-Maske", "",
                "PNG (*.png)")
            if path:
                expected = self.record.revision_no
                self.start(lambda p: MaskService(p).import_mask(self.asset_id, source, Path(
                    path), expected))

    def template(self):
        source, expected = self.mask_source.currentData(), self.record.revision_no
        if source and self.require_saved():
            self.start(lambda p: MaskService(p).create_template(self.asset_id, source, expected))

    def mask_selected(self):
        self.reviewed.setChecked(False)
        identifier = self.mask_history.currentData()
        self.findings.clear()
        self.source_image.clear()
        self.mask_image.clear()
        self.mask_legend.clear()
        self.mask_info = ""
        if identifier:
            record = self.project.catalog.get(identifier)
            source = self.project.catalog.get(record.data["source_revision"])
            self.frame.setMaximum(source.data["frames"])
            self.mask_info = (
                f"Maskenrevision: {record.id}\nQuelle: {source.title} · {source.id}\n"
                f"Quellhash: {record.data['source_sha256']}\n"
                f"Raster: {record.data['grid']} · Frames: {source.data['frames']}\n"
                f"Materialdefinition: {record.data['material_revision']}\n")
            self.findings.setPlainText(self.mask_info +
                "Gespeicherter Prüfstand: " + record.data["technical"] +
                "\nFür aktuelle Quellbindung und Sichtstatus: Prüfen / Vorschau.")

    def check_mask(self):
        identifier, frame = self.mask_history.currentData(), self.frame.value()
        if identifier:
            self.start(lambda p: mask_preview(p, identifier, frame), self.present_mask)

    def present_mask(self, result):
        self.preview_result = result

    def render_mask(self, result):
        status = result["status"]
        self.findings.setPlainText(
            self.mask_info +
            f"Technisch: {status['technical']} · Sichtstatus: {status['visual']}\n" +
            "\n".join(
                f"{f['message']} · Pose {self.pose_names.get(f['pose_id'], 'Einzelbild')} · "
                f"Richtung {f['direction']} · Frame {f['frame']} · Bereich {f['bounds']}"
                for f in status["findings"]))
        self.mask_legend.setText("Vorschau-IDs (keine Zielfarben): " + " · ".join(
            f'<span style="color:#{row["preview"][0]:02x}{row["preview"][1]:02x}'
            f'{row["preview"][2]:02x}">■</span> {row["id"]}: {html.escape(row["name"])}'
            for row in result["legend"]))
        for widget, raw in zip((self.source_image, self.mask_image), result["images"]):
            pixmap = QPixmap()
            pixmap.loadFromData(raw)
            widget.setPixmap(pixmap.scaled(450, 260, Qt.AspectRatioMode.KeepAspectRatio))

    def activate_mask(self):
        identifier, expected = self.mask_history.currentData(), self.record.revision_no
        if identifier:
            self.start(lambda p: MaskService(p).activate(self.asset_id, identifier, expected))

    def confirm_mask(self):
        identifier, expected = self.mask_history.currentData(), self.record.revision_no
        if not self.reviewed.isChecked():
            show_error(self, StudioError("validation",
                "Die konkrete Maskenrevision zuerst visuell prüfen."))
            return
        if identifier:
            reviewer = self.reviewer.text()
            self.start(lambda p: MaskService(p).confirm(identifier, reviewer, expected))

    def reject(self):
        if self.worker:
            self.pending_close = True
            self.status.setText("Vorgang läuft; Fenster schließt nach seinem Abschluss.")
            return
        if self.confirm_close():
            super().reject()

    def confirm_close(self):
        if self.worker:
            return False
        if self.references_dirty or self.materials_dirty:
            answer = QMessageBox.question(self, "Ungespeicherte Auswahl/Definitionen",
                "Ungespeicherte Änderungen verwerfen?",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel)
            if answer != QMessageBox.StandardButton.Discard:
                return False
        return True

    def closeEvent(self, event):
        event.ignore()
        self.reject()
