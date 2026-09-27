"""Source slots distinguish design originals from delivered animations."""

from dataclasses import asdict, dataclass

from .assets import AssetDefinition, DIRECTIONS, require


@dataclass(frozen=True)
class SourceKey:
    pose_id: str | None
    direction: str | None
    kind: str

    @property
    def token(self) -> str:
        return f"{self.pose_id or '-'}|{self.direction or '-'}|{self.kind}"

    def to_data(self) -> dict:
        return asdict(self)


def expected_sources(definition: AssetDefinition) -> tuple[SourceKey, ...]:
    if definition.workflow == "static":
        return tuple(SourceKey(None, direction, "single_image")
                     for direction in definition.directions or (None,))
    return tuple(SourceKey(pose.id, direction, pose.source_kind) for pose in definition.poses
                 for direction in pose.directions or definition.directions or (None,))


def validate_slot(definition: AssetDefinition, key: SourceKey) -> None:
    allowed = set(expected_sources(definition))
    # Design originals are independent optional inputs for externally animated poses.
    allowed.update(SourceKey(k.pose_id, k.direction, "single_image") for k in tuple(allowed))
    require(key in allowed, "Pose, Richtung oder Quellart passt nicht zu den Anforderungen.")


def matrix_slots(definition: AssetDefinition) -> tuple[SourceKey, ...]:
    expected = expected_sources(definition)
    slots = dict.fromkeys(expected)
    for key in expected:
        for direction in DIRECTIONS if key.direction is not None else (None,):
            slots[SourceKey(key.pose_id, direction, key.kind)] = None
    return tuple(slots)
