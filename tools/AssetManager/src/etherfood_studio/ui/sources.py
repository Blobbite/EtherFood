"""Collapsible pose deliveries, scoped replacements and retained revisions."""

from PySide6.QtCore import Signal, QSize, Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QHeaderView, QMessageBox, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from ..application.source_import import SourceImportService
from ..domain.models import StudioError
from ..domain.sources import SourceKey, validate_slot
from .common import button, label, show_error

SOURCE_STATES = {"imported": "Importiert · keine Freigabe", "missing": "Fehlt",
                 "not_required": "Nicht erforderlich", "unverified": "Ungeprüfter Verweis",
                 "unavailable": "Quellkopie fehlt/beschädigt"}
SOURCE_KINDS = {"single_image": "Einzelbild", "spritesheet": "Spritesheet"}


def revision_cells(revision) -> list[str]:
    if revision is None:
        return ["—"] * 4
    data = revision.data
    return [f"{data['grid'][0]}×{data['grid'][1]}", str(data["frames"]), revision.title,
            data["imported_at"]]


class SourcesPanel(QWidget):
    changed = Signal()
    import_requested = Signal(object)

    def __init__(self, assets, identifier: str, parent=None, *, include_import=True) -> None:
        super().__init__(parent)
        self.assets, self.identifier = assets, identifier
        self.include_import = include_import
        self.service = SourceImportService(assets)
        layout = QVBoxLayout(self)
        self.summary = label("", "source_delivery_summary")
        layout.addWidget(self.summary)
        self.matrix = QTreeWidget()
        self.matrix.setObjectName("source_delivery_matrix")
        self.matrix.setHeaderLabels([
            "Pose / Richtung / Revision", "Quellart", "Lieferstand", "Raster", "Frames",
            "Aktive Datei / Original", "Importdatum", "Aktion",
        ])
        for column, width in enumerate((180, 80, 150, 50, 55, 165, 125, 155)):
            self.matrix.setColumnWidth(column, width)
        self.matrix.header().setStretchLastSection(False)
        self.matrix.header().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.matrix.setUniformRowHeights(True)
        self.matrix.setAlternatingRowColors(True)
        layout.addWidget(self.matrix, 1)
        layout.addWidget(label("Pose aufklappen → Richtung aufklappen → ältere Revision wählen. "
                              "Raster = Spalten × Zeilen. Originale bleiben erhalten."))
        actions = QHBoxLayout()
        actions.addWidget(button("Quellen hinzufügen …", "source_add",
                                 lambda: self.request_import(None)))
        actions.addWidget(button("Posen einklappen", "source_collapse", self.matrix.collapseAll))
        layout.addLayout(actions)
        self.refresh()

    def _items(self):
        def children(parent):
            for index in range(parent.childCount()):
                item = parent.child(index)
                yield item
                yield from children(item)
        return children(self.matrix.invisibleRootItem())

    def refresh(self) -> None:
        expanded = {i.data(0, Qt.ItemDataRole.UserRole) for i in self._items() if i.isExpanded()}
        current = self.matrix.currentItem()
        selected = current.data(0, Qt.ItemDataRole.UserRole) if current else None
        definition = self.assets.definition(self.identifier)
        poses = {p.id: p.display_name for p in definition.poses}
        rows = self.service.matrix(self.identifier)
        revisions = self.service.revisions(self.identifier)
        active = {r.id for r in self.service.active(self.identifier).values()}
        required = [r for r in rows if r["required"]]
        available = sum(r["state"] == "imported" for r in required)
        self.summary.setText(f"{available}/{len(required)} benötigte Quellen importiert. "
            "Import erzeugt keine Varianten oder Freigabe. Neue Lieferungen ersetzen bewusst.")
        groups = dict.fromkeys([*(p.id for p in definition.poses),
                               *(r["key"].pose_id for r in rows),
                               *(r.data["slot"]["pose_id"] for r in revisions)])
        self.matrix.clear()
        for pose_id in groups:
            entries = [r for r in rows if r["key"].pose_id == pose_id]
            history = [r for r in revisions if r.data["slot"]["pose_id"] == pose_id]
            needed = tuple(r["key"] for r in entries if r["required"])
            count = sum(r["required"] and r["state"] == "imported" for r in entries)
            group = QTreeWidgetItem(self.matrix, [poses.get(pose_id, "Statisch / frühere Pose"),
                "Posenbündel", f"{count}/{len(needed)} geliefert", "", "",
                f"{len(history)} aufbewahrte Revisionen"])
            group.setData(0, Qt.ItemDataRole.UserRole, "pose:" + str(pose_id))
            if needed:
                self._action(group, "Pose neu liefern …", "replace_pose_" + str(pose_id),
                             lambda checked=False, keys=needed: self.request_import(keys))
            keys = dict.fromkeys([*(r["key"] for r in entries),
                                  *(SourceKey(**r.data["slot"]) for r in history)])
            entries_by_key = {r["key"]: r for r in entries}
            for key in keys:
                entry = entries_by_key.get(key)
                revision = entry["revision"] if entry else None
                state = SOURCE_STATES[entry["state"]] if entry else "Frühere Zuordnung"
                if entry and not entry["required"] and revision:
                    state = "Nicht erforderlich · " + state
                slot = QTreeWidgetItem(group, [key.direction or "Ohne Richtung",
                    SOURCE_KINDS[key.kind], state, *revision_cells(revision)])
                slot.setData(0, Qt.ItemDataRole.UserRole, "slot:" + key.token)
                try:
                    validate_slot(definition, key)
                except StudioError:
                    pass
                else:
                    self._action(slot, "Ersetzen …" if revision else "Hinzufügen …",
                        "replace_source_" + key.token,
                        lambda checked=False, value=key: self.request_import((value,)))
                for previous in reversed(history):
                    if SourceKey(**previous.data["slot"]) != key:
                        continue
                    item = QTreeWidgetItem(slot, ["Revision " + previous.id[:8],
                        SOURCE_KINDS[key.kind], "Aktiv" if previous.id in active else "Aufbewahrt",
                        *revision_cells(previous)])
                    item.setData(0, Qt.ItemDataRole.UserRole, "revision:" + previous.id)
                    item.setToolTip(0, previous.id)
                    if previous.id not in active:
                        self._action(item, "Aktivieren", "activate_" + previous.id,
                            lambda checked=False, rid=previous.id: self.activate(rid))
            self._deliveries(group, pose_id, needed, history, active)
        for item in self._items():
            key = item.data(0, Qt.ItemDataRole.UserRole)
            item.setExpanded(key in expanded)
            for column in range(1, 7):
                item.setToolTip(column, item.text(column))
            if key == selected:
                self.matrix.setCurrentItem(item)

    def _action(self, item, title, name, call) -> None:
        item.setSizeHint(0, QSize(0, 30))
        self.matrix.setItemWidget(item, 7, button(title, name, call))

    def _deliveries(self, parent, pose_id, required, history, active) -> None:
        if not history:
            return
        root = QTreeWidgetItem(parent, ["Frühere Lieferbündel", "", "Ganze Pose reaktivieren"])
        root.setData(0, Qt.ItemDataRole.UserRole, "deliveries:" + str(pose_id))
        bundles = dict.fromkeys(r.data["delivery_id"] for r in reversed(history))
        for delivery in bundles:
            sources = [r for r in history if r.data["delivery_id"] == delivery
                       and SourceKey(**r.data["slot"]) in required]
            complete = bool(required) and {SourceKey(**r.data["slot"]) for r in sources} \
                == set(required)
            is_active = complete and all(r.id in active for r in sources)
            item = QTreeWidgetItem(root, ["Lieferung " + delivery[:8], "Bündel",
                "Aktiv" if is_active else "Vollständig" if complete else "Teillieferung",
                "", "", f"{len(sources)}/{len(required)} benötigte Quellen",
                sources[0].data["imported_at"] if sources else ""])
            item.setData(0, Qt.ItemDataRole.UserRole, "delivery:" + str(pose_id) + delivery)
            if complete and not is_active:
                self._action(item, "Pose aktivieren", "activate_delivery_" + delivery,
                    lambda checked=False, pid=pose_id, did=delivery:
                    self.activate_delivery(pid, did))

    def show_pose(self, pose_id) -> None:
        for index in range(self.matrix.topLevelItemCount()):
            item = self.matrix.topLevelItem(index)
            if item.data(0, Qt.ItemDataRole.UserRole) == "pose:" + str(pose_id):
                item.setExpanded(True)
                self.matrix.setCurrentItem(item)
                self.matrix.scrollToItem(item)

    def request_import(self, keys) -> None:
        if not self.include_import:
            self.import_requested.emit(keys)
            return
        from .source_import_dialog import SourceImportDialog
        dialog = SourceImportDialog(self.assets, self.identifier, self, keys=keys)
        dialog.exec()
        if dialog.changed:
            self.refresh()
            self.changed.emit()
        dialog.deleteLater()

    def _activate(self, call) -> None:
        if QMessageBox.question(self, "Aktiven Entwurf wechseln?",
            "Ausgewählte Revision/Lieferung aktivieren? Folgeergebnisse müssen zur neuen "
            "Quellenbindung passen. Ältere Originale bleiben erhalten.") \
                != QMessageBox.StandardButton.Yes:
            return
        try:
            call(self.assets.asset(self.identifier).revision_no)
            self.refresh()
            self.changed.emit()
        except (StudioError, OSError) as error:
            show_error(self, error if isinstance(error, StudioError) else
                       StudioError("storage", "Quellkopie nicht lesbar.", str(error)))

    def activate(self, revision_id: str) -> None:
        self._activate(lambda current: self.service.activate(self.identifier, revision_id, current))

    def activate_delivery(self, pose_id, delivery_id) -> None:
        self._activate(lambda current: self.service.activate_pose_delivery(
            self.identifier, pose_id, delivery_id, current))
