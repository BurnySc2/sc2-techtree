import json
from pathlib import Path

import pytest


@pytest.fixture
def unit_data() -> dict:
    path = Path(__file__).parent.parent / "src" / "json" / "UnitData.json"
    with path.open() as f:
        return json.load(f)


class TestUnitDataKeys:
    def test_nexus_exists(self, unit_data: dict) -> None:
        assert "Nexus" in unit_data

    def test_oracle_exists(self, unit_data: dict) -> None:
        assert "Oracle" in unit_data

    def test_viper_exists(self, unit_data: dict) -> None:
        assert "Viper" in unit_data

    def test_cyclone_exists(self, unit_data: dict) -> None:
        assert "Cyclone" in unit_data

    def test_adept_exists(self, unit_data: dict) -> None:
        assert "Adept" in unit_data

    def test_swarm_host_mp_exists(self, unit_data: dict) -> None:
        assert "SwarmHostMP" in unit_data

    def test_hellion_tank_exists(self, unit_data: dict) -> None:
        assert "HellionTank" in unit_data

    def test_tempest_exists(self, unit_data: dict) -> None:
        assert "Tempest" in unit_data


class TestQueenCostResource:
    def test_queen_cost_resource_minerals(self, unit_data: dict) -> None:
        queen = unit_data["Queen"]
        assert "CostResource" in queen
        assert queen["CostResource"] == {"Minerals": 175}


class TestGhostAttributes:
    def test_ghost_attributes(self, unit_data: dict) -> None:
        ghost = unit_data["Ghost"]
        assert "Attributes" in ghost
        assert ghost["Attributes"] == ["Biological", "Light", "Psionic"]


class TestTwilightCouncilCardLayouts:
    def test_twilight_council_research_buttons(self, unit_data: dict) -> None:
        tc = unit_data["TwilightCouncil"]
        card_layouts = tc["CardLayouts"]
        layout_buttons = card_layouts["LayoutButtons"]
        buttons_by_face = {b["Face"]: b for b in layout_buttons}

        assert "ResearchCharge" in buttons_by_face
        assert buttons_by_face["ResearchCharge"]["AbilCmd"] == "TwilightCouncilResearch,Research1"

        assert "ResearchStalkerTeleport" in buttons_by_face
        assert buttons_by_face["ResearchStalkerTeleport"]["AbilCmd"] == "TwilightCouncilResearch,Research2"

        assert "ResearchAdeptShieldUpgrade" in buttons_by_face
        assert buttons_by_face["ResearchAdeptShieldUpgrade"]["AbilCmd"] == "TwilightCouncilResearch,Research3"
