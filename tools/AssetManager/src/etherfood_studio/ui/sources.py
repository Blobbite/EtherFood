"""Delivery matrix and explicit selection of retained source revisions."""

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QMessageBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ..application.source_import import SourceImportService
from ..domain.models import StudioError
from .common import button, label, show_error

SOURCE_STATES = {"imported": "Importiert · keine Freigabe", "missing": "Fehlt",
                 "not_required": "Nicht erforderlich", "unverified": "Ungeprüfter Verweis",
                 "unavailable": "Quellkopie fehlt/beschädigt"}
SOURCE_KINDS = {"single_image": "Einzelbild", "spritesheet": "Spritesheet"}


class SourcesPanel(QWidget):
    changed = Signal()

    def __init__(self, assets, identifier: str, parent=None, *, include_import=True) -> None:
        super().__init__(parent)
        self.assets, self.identifier = assets, identifier
        self.service = SourceImportService(assets)
        layout = QVBoxLayout(self)
        self.summary = label("", "source_delivery_summary")
        layout.addWidget(self.summary)
        self.matrix = QTableWidget(0, 6)
        self.matrix.setObjectName("source_delivery_matrix")
        self.matrix.setHorizontalHeaderLabels([
            "Pose", "Richtung", "Quellart", "Erwartet", "Lieferstand", "Aktive Datei",
        ])
        self.matrix.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.matrix, 1)
        layout.addWidget(label("Aufbewahrte Revisionen – ältere Originale bleiben erhalten:"))
        self.revisions = QComboBox()
        self.revisions.setObjectName("source_revisions")
        layout.addWidget(self.revisions)
        actions = QHBoxLayout()
        if include_import:
            actions.addWidget(button("Quellen hinzufügen …", "source_add", self.import_sources))
        self.activate_button = button("Ausgewählte Revision aktivieren", "source_activate",
                                       self.activate)
        actions.addWidget(self.activate_button)
        layout.addLayout(actions)
        self.refresh()

    def refresh(self) -> None:
        definition = self.assets.definition(self.identifier)
        poses = {p.id: p.display_name for p in definition.poses}
        rows = self.service.matrix(self.identifier)
        required = [r for r in rows if r["required"]]
        available = sum(r["state"] == "imported" for r in required)
        self.summary.setText(f"{available}/{len(required)} benötigte Quellen importiert. "
            "Originalanimation bleibt extern; Import erzeugt keine Varianten und keine Freigabe.")
        self.matrix.setRowCount(len(rows))
        for row, value in enumerate(rows):
            key, revision = value["key"], value["revision"]
            texts = [poses.get(key.pose_id, "Statisch / frühere Pose"), key.direction or "—",
                     SOURCE_KINDS[key.kind], "Ja" if value["required"] else "Nein",
                     SOURCE_STATES[value["state"]], revision.title if revision else "—"]
            for column, text in enumerate(texts):
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                item.setToolTip(text if not revision else text + "\nRevision: " + revision.id)
                self.matrix.setItem(row, column, item)
        self.matrix.resizeColumnsToContents()
        self.revisions.clear()
        active = {r.id for r in self.service.active(self.identifier).values()}
        for revision in reversed(self.service.revisions(self.identifier)):
            data, slot = revision.data, revision.data["slot"]
            self.revisions.addItem(
                f"{'● aktiv' if revision.id in active else '○'} · {data['imported_at']} · "
                f"{poses.get(slot['pose_id'], 'Statisch / frühere Pose')} "
                f"{slot['direction'] or '—'} "
                f"· {SOURCE_KINDS[slot['kind']]} · {data['frames']} Frames · {revision.title}",
                revision.id,
            )
        self.activate_button.setEnabled(self.revisions.count() > 0)

    def import_sources(self, pose_id: str | None = None) -> None:
        from .source_import_dialog import SourceImportDialog
        dialog = SourceImportDialog(self.assets, self.identifier, self, pose_id=pose_id)
        dialog.exec()
        if dialog.changed:
            self.refresh()
            self.changed.emit()
        dialog.deleteLater()

    def activate(self) -> None:
        revision_id = self.revisions.currentData()
        if not revision_id:
            return
        if QMessageBox.question(self, "Aktiven Entwurf wechseln?",
            "Diese Revision für ihre Pose/Richtung aktivieren? Folgeergebnisse müssen zur "
            "neuen Quellenbindung passen. Ältere Revisionen bleiben erhalten.") \
                != QMessageBox.StandardButton.Yes:
            return
        try:
            self.service.activate(self.identifier, revision_id,
                                   self.assets.asset(self.identifier).revision_no)
            self.refresh()
            self.changed.emit()
        except (StudioError, OSError) as error:
            show_error(self, error if isinstance(error, StudioError) else
                       StudioError("storage", "Quellkopie nicht lesbar.", str(error)))
