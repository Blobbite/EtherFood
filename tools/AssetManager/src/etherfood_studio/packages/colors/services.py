"""Explicit asset-context resource tools; the core UI does not depend on this dialog."""


def references(context, parameters, parent):
    from ...ui.reference_materials import ReferenceMaterialsDialog

    dialog = ReferenceMaterialsDialog(context["project"], context["asset_id"], parent)
    dialog.exec()
    dialog.deleteLater()
    return parameters
