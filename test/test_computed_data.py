import json
from pathlib import Path

import pytest


@pytest.fixture
def computed_data() -> dict:
    path = Path(__file__).parent.parent / "src" / "computed" / "data.json"
    with path.open() as f:
        return json.load(f)


@pytest.mark.skip()
class TestSCVInUnits:
    def test_scv_exists_in_units(self, computed_data: dict) -> None:
        assert "SCV" in computed_data["units"]


@pytest.mark.skip()
class TestSCVBuilds:
    def test_scv_builds_excludes_bomber_launch_pad(self, computed_data: dict) -> None:
        scv = computed_data["units"]["SCV"]
        assert "builds" in scv
        assert "BomberLaunchPad" not in scv["builds"]

    def test_scv_builds_excludes_merc_compound(self, computed_data: dict) -> None:
        scv = computed_data["units"]["SCV"]
        assert "builds" in scv
        assert "MercCompound" not in scv["builds"]


@pytest.mark.skip()
class TestNexus:
    def test_nexus_abil_array_excludes_train_mothership_core(self, computed_data: dict) -> None:
        nexus = computed_data["structures"]["Nexus"]
        assert "AbilArray" in nexus
        assert "NexusTrainMothershipCore" not in nexus["AbilArray"]
