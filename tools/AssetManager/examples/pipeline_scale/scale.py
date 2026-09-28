"""Importable example: actual processing and an optional, explicitly opened package UI."""

from etherfood_studio.domain.graphics import proportional_size
from etherfood_studio.pipelines.image_processing import legacy_modules, split_frames


def apply(image, metadata, parameters):
    mode = parameters["size_mode"]
    value = parameters["factor"] if mode == "factor" else parameters["max_edge"]
    size = proportional_size(*metadata["frame_size"], mode, value)
    grid, _, comic, _, _, _ = legacy_modules()
    frames = split_frames(image, metadata["grid"])
    frames = [frame.copy() if frame.size == size else comic.resize_frame(frame, size)
              for frame in frames]
    result = grid.pack_frames(frames, tuple(metadata["grid"]), optimize=False)
    return result, {"frame_size": list(size), "profile": "scaled"}


def choose_preset(parent, parameters):
    """UI imports happen only on the explicit package action, never in a build."""
    from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout

    dialog = QDialog(parent)
    dialog.setWindowTitle("Größenvorgabe · Skalierungspaket")
    layout = QVBoxLayout(dialog)
    layout.addWidget(QLabel("Gemeinsamer Faktor je Frame; anschließend im Canvas anpassbar."))
    choices = QComboBox()
    for title, factor in (("Originalgröße", 1.0), ("Halbe Größe", 0.5), ("Viertelgröße", 0.25)):
        choices.addItem(title, factor)
    choices.setCurrentIndex(max(0, choices.findData(parameters["factor"])))
    layout.addWidget(choices)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                               QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    try:
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return {**parameters, "size_mode": "factor", "factor": choices.currentData()}
        return None
    finally:
        dialog.deleteLater()
