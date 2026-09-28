"""Versioned color provenance, independent from graphics/resolution profiles."""

REFERENCE_CONTRACT = "studio-reference-selection-v1"
MATERIAL_CONTRACT = "studio-material-definitions-v1"
MASK_CONTRACT = "studio-mask-revision-v1"
MASK_REVIEW_CONTRACT = "studio-mask-review-v1"
COLOR_CONTRACT = "studio-color-profile-v2"


def finding(code, message, slot, *, frame=None, bounds=None, count=None):
    return {"code": code, "message": message, "pose_id": slot.get("pose_id"),
            "direction": slot.get("direction"), "frame": frame, "bounds": bounds,
            "count": count}
