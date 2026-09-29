"""Version project graphics in the existing catalog, independently from layouts."""

from ..domain.graphics import default_profiles, validate_profiles
from ..domain.models import StudioError


class ProfileService:
    def __init__(self, project) -> None:
        self.project = project

    def profiles(self) -> dict[str, dict]:
        return validate_profiles(self.project.project().data.get(
            "graphics_profiles", default_profiles()))

    def ensure(self) -> None:
        with self.project.catalog.transaction():
            record = self.project.project()
            if "graphics_profiles" not in record.data and not record.data.get(
                "workflow_editor_version"
            ):
                self.project.catalog.save(record, data={**record.data,
                                                         "graphics_profiles": default_profiles()})

    def save(self, profiles: list, expected_revision: int):
        values = validate_profiles(profiles)
        with self.project.catalog.transaction():
            record = self.project.project()
            self.project._check_revision(record, expected_revision)
            previous = self.profiles()
            if set(previous) - set(values):
                raise StudioError("validation", "Profilidentitäten bleiben erhalten; deaktivieren "
                                  "statt löschen. Neue Profile erhalten eigene Schlüssel.")
            data = {**record.data, "graphics_profiles": list(values.values())}
            return record if data == record.data else self.project.catalog.save(record, data=data)
