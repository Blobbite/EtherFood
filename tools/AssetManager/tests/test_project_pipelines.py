"""Small real PNG builds, project boundaries, timing and selective cache invalidation."""

from copy import deepcopy
import json

from PIL import Image
import pytest

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.profile_service import ProfileService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.source_import import SourceImportService, SourceSpec
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.graphics import proportional_size
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.sources import expected_sources
from etherfood_studio.storage.blob_store import file_hash


def test_proportional_rounding():
    assert proportional_size(512, 256, "factor", 0.5) == (256, 128)
    assert proportional_size(512, 256, "max_edge", 128) == (128, 64)
    assert proportional_size(40, 20, "max_edge", 128) == (40, 20)
    assert proportional_size(128, 64, "factor", 0.9) == (115, 58)
    assert proportional_size(5, 3, "factor", 0.5) == (3, 2)
    for value in (0, -1, float("nan"), float("inf")):
        with pytest.raises(StudioError):
            proportional_size(512, 256, "factor", value)
