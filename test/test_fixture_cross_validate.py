"""Cross-validate src/computed/data.json against the ground-truth fixture."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def computed_data() -> dict:
    path = Path(__file__).parent.parent / "src" / "computed" / "data.json"
    with path.open() as f:
        return json.load(f)


@pytest.fixture
def fixture_data() -> dict:
    path = Path(__file__).parent / "fixtures" / "liquipedia_reference.json"
    with path.open() as f:
        return json.load(f)


@pytest.fixture
def fixture_units(fixture_data: dict) -> dict:
    return {u["name"]: u for u in fixture_data["units"]}


class TestMarineMineralCost:
    def test_marine_minerals_matches_fixture(self, computed_data: dict, fixture_units: dict) -> None:
        marine_fixture = fixture_units["Marine"]
        marine_computed = computed_data["Units"]["Marine"]
        cost = marine_computed.get("CostResource", {}).get("Minerals")
        assert cost == marine_fixture["minerals"], (
            f"Marine minerals: computed={cost}, fixture={marine_fixture['minerals']}"
        )


class TestZerglingMineralCost:
    def test_zergling_minerals_matches_fixture(self, computed_data: dict, fixture_units: dict) -> None:
        zergling_fixture = fixture_units["Zergling"]
        zergling_computed = computed_data["Units"]["Zergling"]
        cost = zergling_computed.get("CostResource", {}).get("Minerals")
        assert cost == zergling_fixture["minerals"], (
            f"Zergling minerals: computed={cost}, fixture={zergling_fixture['minerals']}"
        )


class TestZealotMineralCost:
    def test_zealot_minerals_matches_fixture(self, computed_data: dict, fixture_units: dict) -> None:
        zealot_fixture = fixture_units["Zealot"]
        zealot_computed = computed_data["Units"]["Zealot"]
        cost = zealot_computed.get("CostResource", {}).get("Minerals")
        assert cost == zealot_fixture["minerals"], (
            f"Zealot minerals: computed={cost}, fixture={zealot_fixture['minerals']}"
        )


INTERNAL_AUXILIARY_UNITS = {
    "Archon",
    "MULE",
    "Changeling",
    "ChangelingMarine",
    "ChangelingMarineShield",
    "ChangelingZealot",
    "ChangelingZergling",
    "ChangelingZerglingWings",
    "Broodling",
    "CreepTumor",
    "CreepTumorBurrowed",
    "Egg",
    "Interceptor",
    "LocustMP",
    "LocustMPFlying",
    "NydusCanal",
    "NydusCanalAttacker",
    "NydusCanalCreeper",
    "OverseerSiegeMode",
    "ObserverSiegeMode",
    "PointDefenseDrone",
    "BypassArmorDrone",
    "RavenRepairDrone",
    "ReleaseInterceptorsBeacon",
    "InfestedTerransEgg",
    "InfestedTerransEggPlacement",
    "Replicant",
    "ResourceBlocker",
    "BanelingBurrowed",
    "BanelingCocoon",
    "BroodLordCocoon",
    "DroneBurrowed",
    "HydraliskBurrowed",
    "InfestorBurrowed",
    "InfestorTerranBurrowed",
    "LurkerMPBurrowed",
    "QueenBurrowed",
    "RavagerBurrowed",
    "RoachBurrowed",
    "UltraliskBurrowed",
    "ZerglingBurrowed",
    "SpineCrawlerUprooted",
    "SporeCrawlerUprooted",
    "SupplyDepotLowered",
    "SiegeTankSieged",
    "Viking",
    "VikingAssault",
    "LiberatorAG",
    "WidowMine",
    "WidowMineBurrowed",
    "TechLab",
    "Reactor",
    "BarracksReactor",
    "FactoryReactor",
    "StarportReactor",
    "PylonOvercharged",
    "AssimilatorRich",
    "ExtractorRich",
    "AutoTurret",
    "CorsairMP",
    "DefilerMP",
    "DefilerMPBurrowed",
    "DisruptorPhased",
    "MothershipCore",
    "Nuke",
    "QueenMP",
    "ScoutMP",
    "ScourgeMP",
    "ThorAALance",
    "ThorAP",
    "WarHound",
    "WarpPrismPhasing",
    "VoidMPImmortalReviveCorpse",
    "HERC",
    "HERCPlacement",
    "Elsecaro_Colonist_Hut",
    "IceProtossCrates",
    "ProtossCrates",
    "TowerMine",
}


class TestAllFixtureUnitsExistInComputed:
    def test_all_fixture_units_have_computed_entry(self, computed_data: dict, fixture_units: dict) -> None:
        missing = []
        for name in fixture_units:
            if name in INTERNAL_AUXILIARY_UNITS:
                continue
            if name not in computed_data["Units"]:
                missing.append(name)
        assert not missing, f"Fixture units missing in computed data: {missing}"


class TestRaceConsistency:
    @pytest.mark.parametrize("name", ["Marine", "Zergling", "Zealot", "SCV", "Probe", "Drone"])
    def test_unit_race_consistency(self, computed_data: dict, fixture_units: dict, name: str) -> None:
        fixture_race = fixture_units[name]["race"]
        computed_unit = computed_data["Units"][name]
        computed_race = computed_unit.get("race", "")
        assert computed_race == fixture_race, f"{name} race: computed={computed_race}, fixture={fixture_race}"


class TestMineralCostConsistency:
    @pytest.mark.parametrize(
        "name,expected_minerals",
        [
            ("Marine", 50),
            ("Zergling", 25),
            ("Zealot", 100),
            ("SCV", 50),
            ("Probe", 50),
            ("Drone", 50),
            ("Marauder", 100),
            ("Ghost", 150),
            ("Reaper", 50),
            ("Hellion", 100),
        ],
    )
    def test_mineral_cost_matches_fixture(
        self, computed_data: dict, fixture_units: dict, name: str, expected_minerals: int
    ) -> None:
        unit = computed_data["Units"].get(name)
        assert unit is not None, f"{name} not found in computed Units"
        cost = unit.get("CostResource", {}).get("Minerals")
        assert cost == expected_minerals, f"{name} minerals: computed={cost}, expected={expected_minerals}"


class TestGasCostConsistency:
    @pytest.mark.parametrize(
        "name,expected_gas",
        [
            ("Marine", 0),
            ("Zergling", 0),
            ("Zealot", 0),
            ("SCV", 0),
            ("Probe", 0),
            ("Drone", 0),
            ("Viper", 200),
            ("BroodLord", 250),
            ("Mothership", 400),
        ],
    )
    def test_gas_cost_matches_fixture(
        self, computed_data: dict, fixture_units: dict, name: str, expected_gas: int
    ) -> None:
        unit = computed_data["Units"].get(name)
        if unit is None:
            pytest.skip(f"{name} not in computed data")
        computed_gas = unit.get("CostResource", {}).get("Vespene", 0)
        assert computed_gas == expected_gas, f"{name} gas: computed={computed_gas}, expected={expected_gas}"


class TestComputedUnitsHaveRequiredFields:
    KNOWN_UNITS_WITHOUT_COST = {
        "BarracksTechLab",
        "FactoryTechLab",
        "StarportTechLab",
        "CollapsiblePurifierTowerDebris",
        "CollapsibleRockTowerDebris",
        "CollapsibleRockTowerDebrisRampLeft",
        "CollapsibleRockTowerDebrisRampLeftGreen",
        "CollapsibleRockTowerDebrisRampRight",
        "CollapsibleRockTowerDebrisRampRightGreen",
        "CollapsibleTerranTowerDebris",
        "CreepTumorQueen",
        "DebrisRampLeft",
        "DebrisRampRight",
        "Digester",
        "GhostAlternate",
        "GhostNova",
        "InfestorTerran",
        "Larva",
        "LurkerMPEgg",
        "OracleStasisTrap",
        "RavagerCocoon",
        "BomberLaunchPad",
    }

    def test_all_units_have_cost_resource(self, computed_data: dict) -> None:
        units_without_cost = []
        for name, unit in computed_data["Units"].items():
            if "CostResource" not in unit and name not in self.KNOWN_UNITS_WITHOUT_COST:
                units_without_cost.append(name)
        assert not units_without_cost, f"Units missing CostResource: {units_without_cost}"

    def test_all_units_have_race(self, computed_data: dict) -> None:
        units_without_race = []
        for name, unit in computed_data["Units"].items():
            if name in ["BomberLaunchPad", "Digester"]:
                continue
            if "race" not in unit:
                units_without_race.append(name)
        assert not units_without_race, f"Units missing Race: {units_without_race}"


class TestMorphTimes:
    def test_lurker_mp_has_morph_time(self, computed_data: dict) -> None:
        unit = computed_data["Units"].get("LurkerMP")
        assert unit is not None, "LurkerMP not in computed data"
        assert "time" in unit, "LurkerMP missing time field"
        assert unit["time"] == 33, f"LurkerMP morph time should be 33 (SectionArray.Delay), got {unit['time']}"

    def test_ravager_has_morph_time(self, computed_data: dict) -> None:
        unit = computed_data["Units"].get("Ravager")
        assert unit is not None, "Ravager not in computed data"
        assert "time" in unit, "Ravager missing time field"
        assert unit["time"] == 12, f"Ravager morph time should be 12 (SectionArray.Delay), got {unit['time']}"

    def test_brood_lord_has_morph_time(self, computed_data: dict) -> None:
        unit = computed_data["Units"].get("BroodLord")
        assert unit is not None, "BroodLord not in computed data"
        assert "time" in unit, "BroodLord missing time field"
        assert unit["time"] == 33.8332, f"BroodLord morph time should be 33.8332, got {unit['time']}"

    def test_morph_intermediates_excluded(self, computed_data: dict) -> None:
        for name in ["LurkerMPEgg", "RavagerCocoon", "BroodLordCocoon", "BanelingCocoon"]:
            unit = computed_data["Units"].get(name)
            if unit is not None:
                assert unit.get("time") is None or unit.get("time") == 0, (
                    f"{name} should not have a morph time (intermediate cocoons), got {unit.get('time')}"
                )
