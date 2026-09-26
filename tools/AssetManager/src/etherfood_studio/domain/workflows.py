"""Versioned, pure workflow rules; no jobs or approvals are executed here."""

from dataclasses import dataclass
import hashlib
import json

from .models import StudioError

WORKFLOW_VERSION = 1
STATES = frozenset({
    "not_started", "waiting_external", "ready", "running", "blocked", "failed",
    "cancelled", "passed", "stale", "not_required",
})


@dataclass(frozen=True)
class Step:
    id: str
    requires: tuple[str, ...] = ()
    required: bool = True
    reason: str = ""


@dataclass(frozen=True)
class Evidence:
    state: str
    fingerprint: str
    build_id: str | None = None
    detail: str = ""


@dataclass(frozen=True)
class StepStatus:
    id: str
    state: str
    reason: str
    predecessors: tuple[str, ...] = ()


def template(kind: str, *, supports_materials: bool = True) -> tuple[Step, ...]:
    if kind not in {"animated", "effect", "static", "document"}:
        raise StudioError("validation", "Workflow-Vorlage nicht vorhanden.")
    if kind == "document":
        return (Step("document"), Step("review", ("document",)))
    animated = kind in {"animated", "effect"}
    return (
        Step("source"),
        Step("mask", ("source",), supports_materials, "Asset benötigt keine Materialmaske."),
        Step("color", ("mask",), supports_materials, "Asset benötigt keine Materialfarben."),
        Step("frames", ("color" if supports_materials else "source",), animated,
             "Statischer Inhalt hat keine Frame-Ableitung."),
        Step("scale", ("frames" if animated else "color" if supports_materials else "source",)),
        Step("checks", ("scale",)), Step("review", ("checks",)),
        Step("godot", ("review",)), Step("runtime", ("godot",)),
    )


def input_fingerprint(step: str, inputs: dict[str, str]) -> str:
    keys = {
        "source": ("source",), "mask": ("source", "mask", "mask_source"),
        "document": ("document",),
    }.get(step, ("source", "mask", "mask_source", "profile", "timing", "recipe", "document"))
    payload = {key: inputs.get(key) for key in keys}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def resolve(kind: str, inputs: dict[str, str], evidence: dict[str, Evidence] | None = None,
            *, current_build_id: str | None = None,
            supports_materials: bool = True) -> dict[str, StepStatus]:
    statuses = {}
    evidence = evidence or {}
    for step in template(kind, supports_materials=supports_materials):
        if not step.required:
            statuses[step.id] = StepStatus(step.id, "not_required", step.reason)
            continue
        proof = evidence.get(step.id)
        if proof and proof.state not in {"running", "passed", "failed", "cancelled", "skipped"}:
            raise StudioError("validation", "Unzulässiger Nachweisstatus.")
        missing = tuple(name for name in step.requires if statuses[name].state != "passed")
        if proof and proof.fingerprint != input_fingerprint(step.id, inputs):
            state, reason = "stale", "Nachweis gehört zu älteren Eingaben; erneut prüfen."
        elif proof and proof.state == "skipped":
            state, reason = "blocked", "Prüfung wurde nicht ausgeführt (skipped)."
        elif proof and proof.state in {"failed", "cancelled"}:
            state, reason = proof.state, proof.detail or "Kein erfolgreicher Nachweis."
        elif missing:
            state, reason = "blocked", "Voraussetzungen fehlen: " + ", ".join(missing)
        elif step.id in {"source", "mask", "document"}:
            if step.id == "mask" and inputs.get("mask") \
                    and inputs.get("mask_source") != inputs.get("source"):
                state, reason = "stale", "Maskenbindung an die aktuelle Quelle fehlt."
            elif inputs.get(step.id):
                state, reason = "passed", "Eingabe vorhanden; keine automatische Sichtfreigabe."
            else:
                external = step.id in {"source", "mask"}
                state = "waiting_external" if external else "not_started"
                reason = "Externe Eingabe fehlt." if external else "Dokument ist noch leer."
        elif proof and proof.state == "running":
            state, reason = "running", "Auftrag läuft; Ergebnis steht aus."
        elif proof and proof.state == "passed":
            exact = bool(proof.build_id and proof.build_id == current_build_id)
            if kind == "document" and step.id == "review":
                exact = proof.build_id == inputs.get("document")
            state = "passed" if exact else "blocked"
            reason = "Exakter Nachweis vorhanden." if exact else "Build-/Revisionsbindung fehlt."
        else:
            state, reason = "ready", "Voraussetzungen vorhanden; noch kein erfolgreicher Nachweis."
        statuses[step.id] = StepStatus(step.id, state, reason, missing)
    return statuses


def progress(statuses: dict[str, StepStatus], required: tuple[str, ...]) -> tuple[int, int]:
    completed = sum(name in statuses and statuses[name].state == "passed" for name in required)
    return completed, len(required)


def invalidated_steps(changed_fields: set[str]) -> frozenset[str]:
    if changed_fields & {"source", "mask", "profile", "timing", "recipe"}:
        steps = {"color", "frames", "scale", "checks", "review", "godot", "runtime"}
        if "source" in changed_fields:
            steps |= {"source", "mask"}
        elif "mask" in changed_fields:
            steps.add("mask")
        return frozenset(steps)
    if "document" in changed_fields:
        return frozenset({"document", "review"})
    return frozenset()
