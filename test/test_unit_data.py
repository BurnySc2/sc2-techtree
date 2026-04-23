import json
from pathlib import Path

import pytest


@pytest.fixture
def unit_data() -> dict:
    path = Path(__file__).parent.parent / "src" / "json" / "UnitData.json"
    with path.open() as f:
        raw = json.load(f)
    # Handle {"CUnit": [...]} structure by indexing on "id" field
    if isinstance(raw, dict):
        first_key = next(iter(raw.keys()))
        if isinstance(raw[first_key], list):
            return {rec["id"]: rec for rec in raw[first_key]}
    return raw


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
        # Attributes is a list of single-key dicts like [{"Biological": 1, "Psionic": 1}, {"Light": 1}]
        attrs = ghost["Attributes"]
        # Flatten to set of attribute names
        attr_names = set()
        for entry in attrs:
            if isinstance(entry, dict):
                attr_names.update(entry.keys())
        assert attr_names == {"Biological", "Light", "Psionic"}


class TestTwilightCouncilCardLayouts:
    def test_twilight_council_research_buttons(self, unit_data: dict) -> None:
        tc = unit_data["TwilightCouncil"]
        card_layouts = tc["CardLayouts"]
        assert isinstance(card_layouts, dict)
        assert "LayoutButtons" in card_layouts
        layout_buttons = card_layouts["LayoutButtons"]
        assert isinstance(layout_buttons, list)
        buttons_by_face = {b["Face"]: b for b in layout_buttons}

        assert "ResearchCharge" in buttons_by_face
        assert buttons_by_face["ResearchCharge"]["AbilCmd"] == "TwilightCouncilResearch,Research1"

        assert "ResearchStalkerTeleport" in buttons_by_face
        assert buttons_by_face["ResearchStalkerTeleport"]["AbilCmd"] == "TwilightCouncilResearch,Research2"

        assert "AdeptResearchPiercingUpgrade" in buttons_by_face
        assert buttons_by_face["AdeptResearchPiercingUpgrade"]["AbilCmd"] == "TwilightCouncilResearch,Research3"


class TestBarracksTechLabHasRequiredFaces:
    def test_barracks_tech_lab_has_required_faces(self, unit_data: dict) -> None:
        btlab = unit_data["BarracksTechLab"]
        card_layouts = btlab["CardLayouts"]
        assert isinstance(card_layouts, dict)
        assert "LayoutButtons" in card_layouts
        layout_buttons = card_layouts["LayoutButtons"]
        assert isinstance(layout_buttons, list)
        faces = {b["Face"] for b in layout_buttons}
        assert "Stimpack" in faces
        assert "ResearchShieldWall" in faces
        assert "ResearchPunisherGrenades" in faces


class TestHydraliskDenNoSpeedOrFrenzy:
    def test_hydralisk_den_no_speed_or_frenzy_face(self, unit_data: dict) -> None:
        hd = unit_data["HydraliskDen"]
        card_layouts = hd["CardLayouts"]
        assert isinstance(card_layouts, dict)
        assert "LayoutButtons" in card_layouts
        layout_buttons = card_layouts["LayoutButtons"]
        assert isinstance(layout_buttons, list)
        faces = {b["Face"] for b in layout_buttons}
        assert "hydraliskspeed" not in faces
        assert "MuscularAugments" not in faces


class TestFusionCoreNoBattlecruiserEnergyUpgrade:
    def test_fusion_core_no_battlecruiser_energy_upgrade_face(self, unit_data: dict) -> None:
        fc = unit_data["FusionCore"]
        card_layouts = fc["CardLayouts"]
        assert isinstance(card_layouts, dict)
        assert "LayoutButtons" in card_layouts
        layout_buttons = card_layouts["LayoutButtons"]
        assert isinstance(layout_buttons, list)
        faces = {b["Face"] for b in layout_buttons}
        assert "ResearchBattlecruiserEnergyUpgrade" not in faces


class TestBarracksTechLabAbilArray:
    def test_barracks_tech_lab_abil_array_has_research(self, unit_data: dict) -> None:
        btlab = unit_data["BarracksTechLab"]
        assert "AbilArray" in btlab
        abil_array = btlab["AbilArray"]
        links = [entry["Link"] for entry in abil_array]
        assert "BarracksTechLabResearch" in links
