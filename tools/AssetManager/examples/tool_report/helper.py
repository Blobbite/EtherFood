"""A separate, portable helper module included in the tool package."""

import hashlib


def describe(path):
    content = path.read_bytes()
    return {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
