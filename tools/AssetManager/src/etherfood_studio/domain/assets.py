"""Versioned asset requirements; observations are neither builds nor approvals."""

from dataclasses import asdict, dataclass
from itertools import product
import math
import re
from uuid import UUID

from .models import StudioError, new_id

DIRECTIONS = ("N", "NO", "O", "SO", "S", "SW", "W", "NW")
DIRECTION_TEMPLATES = {8: DIRECTIONS, 4: ("N", "O", "S", "W"), 2: ("O", "W"), 1: ("S",)}
GRAPHICS = ("comic_high", "comic_mid", "comic_low", "pixel_high", "pixel_low")
FRAMES = (8, 10, 12, 14, 16)
CAPABILITIES = ("animated", "directional", "supports_materials", "static_image", "package_member")
TYPE_PRESETS = {
    "character": ("Figur", ("animated", "directional", "supports_materials", "package_member")),
    "effect": ("Effekt", ("animated", "package_member")),
    "texture": ("Textur", ("static_image", "package_member")),
    "prop": ("Objekt", ("static_image", "directional", "supports_materials", "package_member")),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise StudioError("validation", message)


def fields(value: dict, names: set[str]) -> None:
    require(isinstance(value, dict) and set(value) == names, "Unbekannte/fehlende Modellfelder.")


def slug(value: str) -> None:
    require(isinstance(value, str) and bool(re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", value)),
            "Exportname: Kleinbuchstaben, Ziffern, _ oder -; höchstens 64 Zeichen.")


def choices(values: list, allowed: tuple, *, empty: bool = False) -> None:
    require(isinstance(values, list) and (empty or bool(values)), "Auswahl darf nicht leer sein.")
    require(all(type(v) in {str, int} and v in allowed for v in values), "Unzulässige Auswahl.")
    require(len(set(values)) == len(values), "Doppelte Werte sind nicht erlaubt.")


@dataclass(frozen=True)
class VariantKey:
    pose_id: str | None
    direction: str | None
    graphics: str
    frames: int | None

    def to_data(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Pose:
    id: str
    display_name: str
    export_name: str
    loop: bool
    source_kind: str
    directions: tuple[str, ...] | None
    fps: float | None
    anchor: tuple[float, float]

    @classmethod
    def from_data(cls, data: dict) -> "Pose":
        fields(data, {"id", "display_name", "export_name", "loop", "source_kind",
                      "directions", "fps", "anchor"})
        try:
            require(str(UUID(data["id"])) == data["id"], "Pose-ID ist keine kanonische UUID.")
        except (ValueError, TypeError, AttributeError) as error:
            raise StudioError("validation", "Ungültige Pose-ID.") from error
        require(isinstance(data["display_name"], str) and
                0 < len(data["display_name"].strip()) <= 128, "Posenname fehlt/ist zu lang.")
        slug(data["export_name"])
        require(type(data["loop"]) is bool, "Loop muss boolesch sein.")
        require(data["source_kind"] in ("single_image", "spritesheet"), "Unbekannte Quellart.")
        directions = data["directions"]
        if directions is not None:
            choices(directions, DIRECTIONS)
        fps = data["fps"]
        if data["source_kind"] == "single_image":
            require(fps is None and not data["loop"], "Einzelbilder haben keine FPS/Schleife.")
        else:
            require(type(fps) in (int, float) and math.isfinite(fps) and 0 < fps <= 240,
                    "FPS muss zwischen 0 (exklusiv) und 240 liegen.")
        anchor = data["anchor"]
        require(isinstance(anchor, list) and len(anchor) == 2 and
                all(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1 for v in anchor),
                "Anker benötigt zwei normalisierte Werte zwischen 0 und 1.")
        return cls(**{**data, "directions": tuple(directions) if directions else None,
                      "anchor": tuple(anchor)})

    def to_data(self) -> dict:
        return {**asdict(self), "directions": list(self.directions) if self.directions else None,
                "anchor": list(self.anchor)}


@dataclass(frozen=True)
class AssetDefinition:
    type_id: str
    type_label: str
    capabilities: tuple[str, ...]
    directions: tuple[str, ...]
    graphics: tuple[str, ...]
    frames: tuple[int, ...]
    poses: tuple[Pose, ...]

    @classmethod
    def from_data(cls, data: dict) -> "AssetDefinition":
        fields(data, {"schema_version", "type", "directions", "graphics", "frames", "poses"})
        require(type(data["schema_version"]) is int and data["schema_version"] == 1,
                "Unbekannte Asset-Modellversion.")
        asset_type = data["type"]
        fields(asset_type, {"id", "label", "capabilities"})
        slug(asset_type["id"])
        require(isinstance(asset_type["label"], str) and
                0 < len(asset_type["label"].strip()) <= 128, "Asset-Typname fehlt/ist zu lang.")
        caps = asset_type["capabilities"]
        choices(caps, CAPABILITIES)
        require(("animated" in caps) != ("static_image" in caps),
                "Asset muss entweder animiert oder statisch sein.")
        choices(data["directions"], DIRECTIONS, empty="directional" not in caps)
        require(bool(data["directions"]) == ("directional" in caps),
                "Richtungen passen nicht zur Fähigkeit directional.")
        choices(data["graphics"], GRAPHICS)
        choices(data["frames"], tuple(range(1, 65)), empty="animated" not in caps)
        require(isinstance(data["poses"], list) and len(data["poses"]) <= 64,
                "Höchstens 64 Posen sind erlaubt.")
        poses = tuple(Pose.from_data(p) for p in data["poses"])
        if "animated" in caps:
            require(bool(poses), "Animierte Assets benötigen mindestens eine Pose.")
        else:
            require(not poses and not data["frames"], "Statische Assets haben keine Posen/Frames.")
        for attribute in ("id", "export_name"):
            require(len({getattr(p, attribute) for p in poses}) == len(poses),
                    "Pose-IDs und Exportnamen müssen eindeutig sein.")
        require("directional" in caps or not any(p.directions for p in poses),
                "Nicht gerichtete Assets haben keine Posenrichtungen.")
        definition = cls(asset_type["id"], asset_type["label"], tuple(caps),
                         tuple(data["directions"]), tuple(data["graphics"]),
                         tuple(data["frames"]), poses)
        require(len(definition.expected()) <= 20000, "Variantenmatrix ist zu groß (max. 20000).")
        return definition

    @property
    def workflow(self) -> str:
        return "animated" if "animated" in self.capabilities else "static"

    def to_data(self) -> dict:
        return {"schema_version": 1, "type": {"id": self.type_id, "label": self.type_label,
                "capabilities": list(self.capabilities)}, "directions": list(self.directions),
                "graphics": list(self.graphics), "frames": list(self.frames),
                "poses": [p.to_data() for p in self.poses]}

    def expected(self) -> tuple[VariantKey, ...]:
        if "static_image" in self.capabilities:
            return tuple(VariantKey(None, d, g, None)
                         for d, g in product(self.directions or (None,), self.graphics))
        return tuple(VariantKey(p.id, d, g, f) for p in self.poses
                     for d, g, f in product(p.directions or self.directions or (None,),
                                            self.graphics,
                                            (1,) if p.source_kind == "single_image"
                                            else self.frames))

    def matrix(self, observed: set[VariantKey]) -> dict[VariantKey, str]:
        expected = dict.fromkeys(self.expected(), "missing")
        for key in observed:
            expected[key] = "found" if key in expected else "not_required"
        return expected


def new_pose(name: str = "walk", *, single: bool = False) -> Pose:
    return Pose.from_data({"id": new_id(), "display_name": name, "export_name": name,
                           "loop": not single, "source_kind": "single_image" if single
                           else "spritesheet", "directions": None, "fps": None if single else 8,
                           "anchor": [0.5, 1.0]})


def default_definition(type_id: str = "character") -> AssetDefinition:
    label, caps = TYPE_PRESETS[type_id]
    return AssetDefinition.from_data({
        "schema_version": 1, "type": {"id": type_id, "label": label, "capabilities": list(caps)},
        "directions": list(DIRECTIONS) if "directional" in caps else [],
        "graphics": list(GRAPHICS), "frames": list(FRAMES) if "animated" in caps else [],
        "poses": [new_pose().to_data()] if "animated" in caps else [],
    })
