"""Optional profile editor supplied by the graphics package."""


def profiles(context, parameters, parent):
    from ...ui.pipeline_auxiliary import ProfileDialog

    dialog = ProfileDialog(context["project"], parent)
    dialog.exec()
    dialog.deleteLater()
    return parameters
