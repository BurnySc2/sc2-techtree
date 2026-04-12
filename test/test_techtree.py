import json
from pathlib import Path

import pytest


@pytest.fixture
def techtree_data() -> dict:
    path = Path(__file__).parent.parent / "src" / "json" / "techtree.json"
    with path.open() as f:
        return json.load(f)


class TestBarracks:
    def test_barracks_exists(self, techtree_data: dict) -> None:
        assert "Barracks" in techtree_data["structures"]

    def test_barracks_produces(self, techtree_data: dict) -> None:
        barracks = techtree_data["structures"]["Barracks"]
        assert "produces" in barracks
        assert barracks["produces"] == ["Ghost", "Marauder", "Marine", "Reaper"]

    def test_barracks_unlocks(self, techtree_data: dict) -> None:
        barracks = techtree_data["structures"]["Barracks"]
        assert "unlocks" in barracks
        assert barracks["unlocks"] == ["Bunker", "Factory", "GhostAcademy"]


class TestSupplyDepot:
    def test_supply_depot_unlocks(self, techtree_data: dict) -> None:
        supply_depot = techtree_data["structures"]["SupplyDepot"]
        assert "unlocks" in supply_depot
        assert supply_depot["unlocks"] == ["Barracks"]


class TestThor:
    def test_thor_requires(self, techtree_data: dict) -> None:
        thor = techtree_data["units"]["Thor"]
        assert "requires" in thor
        assert thor["requires"] == ["Armory", "AttachedTechLab"]


class TestZerglingMorphsto:
    def test_zergling_morphsto_baneling(self, techtree_data: dict) -> None:
        zergling = techtree_data["units"]["Zergling"]
        assert "morphsto" in zergling
        assert zergling["morphsto"] == "Baneling"


class TestCorruptor:
    def test_corruptor_morphsto_broodlord(self, techtree_data: dict) -> None:
        corruptor = techtree_data["units"]["Corruptor"]
        assert "morphsto" in corruptor
        assert corruptor["morphsto"] == "BroodLord"


class TestMorphToBroodLord:
    def test_morph_to_broodlord_morphsto(self, techtree_data: dict) -> None:
        morph = techtree_data["abilities"]["MorphToBroodLord"]
        assert morph["morphsto"] == "BroodLord"


class TestRoach:
    def test_roach_requires(self, techtree_data: dict) -> None:
        roach = techtree_data["units"]["Roach"]
        assert "requires" in roach
        assert roach["requires"] == ["RoachWarren"]


class TestSCV:
    def test_scv_builds(self, techtree_data: dict) -> None:
        scv = techtree_data["units"]["SCV"]
        assert "builds" in scv
        assert set(scv["builds"]) >= {
            "Armory",
            "Barracks",
            "Bunker",
            "CommandCenter",
            "EngineeringBay",
            "Factory",
            "FusionCore",
            "GhostAcademy",
            "MissileTurret",
            "Refinery",
            "SensorTower",
            "Starport",
            "SupplyDepot",
        }


class TestSpire:
    def test_spire_morphsto(self, techtree_data: dict) -> None:
        spire = techtree_data["structures"]["Spire"]
        assert "morphsto" in spire
        assert spire["morphsto"] == "GreaterSpire"

    def test_spire_unlocks(self, techtree_data: dict) -> None:
        spire = techtree_data["structures"]["Spire"]
        assert "unlocks" in spire
        assert spire["unlocks"] == ["Corruptor", "Mutalisk"]


class TestMorphToBaneling:
    def test_morph_to_baneling_exists(self, techtree_data: dict) -> None:
        assert "MorphToBaneling" in techtree_data["abilities"]

    def test_morph_to_baneling_fields(self, techtree_data: dict) -> None:
        morph = techtree_data["abilities"]["MorphToBaneling"]
        assert morph["morphsto"] == "Baneling"
        assert morph["race"] == "Zerg"
        assert morph["requires"] == ["BanelingNest"]


class TestLarva:
    def test_larva_morphsto(self, techtree_data: dict) -> None:
        larva = techtree_data["units"]["Larva"]
        assert "morphsto" in larva
        assert set(larva["morphsto"]) >= {
            "Corruptor",
            "Drone",
            "Hydralisk",
            "Infestor",
            "Mutalisk",
            "Overlord",
            "Roach",
            "SwarmHostMP",
            "Ultralisk",
            "Viper",
        }


class TestCommandCenter:
    def test_command_center_morphsto_orbital_command(self, techtree_data: dict) -> None:
        cc = techtree_data["structures"]["CommandCenter"]
        assert "morphsto" in cc
        assert cc["morphsto"] == ["CommandCenterFlying", "OrbitalCommand", "PlanetaryFortress"]

    def test_command_center_produces(self, techtree_data: dict) -> None:
        cc = techtree_data["structures"]["CommandCenter"]
        assert "produces" in cc
        assert cc["produces"] == ["SCV"]


class TestArmory:
    def test_armory_researches(self, techtree_data: dict) -> None:
        armory = techtree_data["structures"]["Armory"]
        assert "researches" in armory
        assert armory["researches"] == [
            "TerranShipWeaponsLevel1",
            "TerranShipWeaponsLevel2",
            "TerranShipWeaponsLevel3",
            "TerranVehicleAndShipArmorsLevel1",
            "TerranVehicleAndShipArmorsLevel2",
            "TerranVehicleAndShipArmorsLevel3",
            "TerranVehicleWeaponsLevel1",
            "TerranVehicleWeaponsLevel2",
            "TerranVehicleWeaponsLevel3",
        ]

    def test_armory_unlocks(self, techtree_data: dict) -> None:
        armory = techtree_data["structures"]["Armory"]
        assert "unlocks" in armory
        assert armory["unlocks"] == ["HellionTank", "Thor"]


class TestOrbitalCommand:
    def test_orbital_command_produces_scv(self, techtree_data: dict) -> None:
        orbital = techtree_data["structures"]["OrbitalCommand"]
        assert "produces" in orbital
        assert orbital["produces"] == ["SCV"]

    def test_orbital_command_morphsto_flying(self, techtree_data: dict) -> None:
        orbital = techtree_data["structures"]["OrbitalCommand"]
        assert "morphsto" in orbital
        assert orbital["morphsto"] == "OrbitalCommandFlying"


class TestUpgradeToOrbital:
    def test_upgrade_to_orbital_morphsto(self, techtree_data: dict) -> None:
        upgrade = techtree_data["abilities"]["UpgradeToOrbital"]
        assert upgrade["morphsto"] == "OrbitalCommand"

    def test_upgrade_to_orbital_requires(self, techtree_data: dict) -> None:
        upgrade = techtree_data["abilities"]["UpgradeToOrbital"]
        assert "requires" in upgrade
        assert upgrade["requires"] == ["Barracks"]


class TestUpgradeToGreaterSpire:
    def test_upgrade_to_greater_spire(self, techtree_data: dict) -> None:
        upgrade = techtree_data["abilities"]["UpgradeToGreaterSpire"]
        assert upgrade["morphsto"] == "GreaterSpire"
        assert upgrade["race"] == "Zerg"
        assert upgrade["requires"] == ["Hive"]
