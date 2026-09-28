"""Configuration templates do not clone another asset's identity or evidence."""

import pytest

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.domain.assets import default_definition, new_pose
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.sources import expected_sources


def test_template_only_configuration_fresh_ids_and_atomic_creation(tmp_path):
    project = ProjectService.new(tmp_path, "Vorlagen")
    try:
        assets = AssetService(project)
        owner = next(c.id for c in project.cards() if c.kind == "global")
        data = default_definition().to_data()
        data["directions"] = ["N", "O", "S", "W"]
        data["poses"].append(new_pose("stand").to_data())
        original = assets.create("Vorlage", owner, data)
        project.catalog.create("source_revision", "Fremde Quelle", original.id)
        project.catalog.create("approval", "Synthetischer Nachweis", original.id)
        project.catalog.save(original, data={**original.data, "approval": "Nicht übertragen"})
        template = assets.template(original.id)
        new = assets.create("Neuer NPC", owner, template.to_data())
        assert new.id != original.id
        assert set(new.data) == {"order", "workflow", "asset_definition"}
        assert {p.id for p in template.poses}.isdisjoint(p["id"] for p in data["poses"])
        assert len(expected_sources(template)) == 8
        assert len(template.expected()) == 200
        children = [r for r in project.catalog.records() if r.owner_id == new.id]
        assert len(children) == 1 and children[0].data.get("automation") == "section"
        assert not (tmp_path / ".asset-studio/jobs").exists()
        assert not (tmp_path / ".asset-studio/objects").exists()
        assert not list((project.files.path(new.id) / "Quellen").iterdir())
        before = project.catalog.export_snapshot()
        with pytest.raises(StudioError):
            assets.create("Ungültiger Besitzer", new.id, template.to_data())
        assert project.catalog.export_snapshot() == before
        renamed = project.rename(new.id, "Neuer Name", new.revision_no)
        assert renamed.id == new.id and assets.definition(new.id) == template
    finally:
        project.catalog.close()
