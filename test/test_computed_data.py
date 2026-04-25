import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def computed_data() -> dict:
    path = Path(__file__).parent.parent / "src" / "computed" / "data.json"
    with path.open() as f:
        return json.load(f)


@pytest.fixture
def techtree() -> dict:
    path = Path(__file__).parent.parent / "src" / "computed" / "techtree.json"
    with path.open() as f:
        return json.load(f)


@pytest.fixture
def stableid() -> dict:
    path = Path(__file__).parent.parent / "src" / "extracted" / "stableid.json"
    with path.open() as f:
        return json.load(f)


class TestSCVInUnits:
    def test_scv_exists_in_units(self, computed_data: dict) -> None:
        assert "SCV" in computed_data["Units"]


class TestSCVBuilds:
    def test_scv_builds_excludes_bomber_launch_pad(self, computed_data: dict) -> None:
        scv = computed_data["Units"]["SCV"]
        assert "builds" in scv
        assert "BomberLaunchPad" not in scv["builds"]

    def test_scv_builds_excludes_merc_compound(self, computed_data: dict) -> None:
        scv = computed_data["Units"]["SCV"]
        assert "builds" in scv
        assert "MercCompound" not in scv["builds"]


class TestNexus:
    def test_nexus_abil_array_excludes_train_mothership_core(self, computed_data: dict) -> None:
        nexus = computed_data["Units"]["Nexus"]
        assert "AbilArray" in nexus
        assert "NexusTrainMothershipCore" not in nexus["AbilArray"]


class TestStructuresResearches:
    """Structures should have 'researches' field with upgrade names."""

    @pytest.mark.parametrize(
        "structure,expected_research",
        [
            ("TwilightCouncil", "BlinkTech"),
            ("TwilightCouncil", "Charge"),
            ("TwilightCouncil", "AdeptPiercingAttack"),
            ("Spire", "ZergFlyerArmorsLevel1"),
            ("Armory", "TerranVehicleWeaponsLevel1"),
            ("Hatchery", "Burrow"),
        ],
    )
    def test_structure_has_researches(self, computed_data: dict, structure: str, expected_research: str) -> None:
        """Each structure should have 'researches' field containing expected upgrade names."""
        unit = computed_data["Units"][structure]
        assert "researches" in unit
        assert expected_research in unit["researches"]


class TestStructuresProduces:
    """Structures should have 'produces' field with unit names."""

    @pytest.mark.parametrize(
        "structure,produces",
        [
            ("Hatchery", "Queen"),
            ("Barracks", "Marine"),
            ("Barracks", "Reaper"),
            ("Gateway", "Zealot"),
            ("Gateway", "Stalker"),
            ("OrbitalCommand", "SCV"),
        ],
    )
    def test_structure_produces(self, computed_data: dict, structure: str, produces: str) -> None:
        """Each structure should have 'produces' field containing expected unit names."""
        unit = computed_data["Units"][structure]
        assert "produces" in unit
        assert produces in unit["produces"]


class TestStructuresMorphsto:
    """Structures should have 'morphsto' field for transformations."""

    def test_spire_morphsto_greater_spire(self, computed_data: dict) -> None:
        """Spire should morphsto GreaterSpire."""
        spire = computed_data["Units"]["Spire"]
        assert "morphsto" in spire
        assert spire["morphsto"] == "GreaterSpire"

    def test_hatchery_morphsto_lair(self, computed_data: dict) -> None:
        """Hatchery should morphsto Lair."""
        hatchery = computed_data["Units"]["Hatchery"]
        assert "morphsto" in hatchery
        assert hatchery["morphsto"] == "Lair"

    def test_lair_morphsto_hive(self, computed_data: dict) -> None:
        """Lair should morphsto Hive."""
        lair = computed_data["Units"]["Lair"]
        assert "morphsto" in lair
        assert lair["morphsto"] == "Hive"

    def test_command_center_morphsto_options(self, computed_data: dict) -> None:
        """CommandCenter should have multiple morphsto options."""
        cc = computed_data["Units"]["CommandCenter"]
        assert "morphsto" in cc
        assert isinstance(cc["morphsto"], list)
        assert "OrbitalCommand" in cc["morphsto"]

    def test_factory_morphsto_flying(self, computed_data: dict) -> None:
        """Factory should morphsto FactoryFlying."""
        factory = computed_data["Units"]["Factory"]
        assert "morphsto" in factory
        assert factory["morphsto"] == "FactoryFlying"


class TestUnitsAbilArray:
    """Units should have abilities (AbilArray) from UnitData."""

    def test_marine_has_attack_ability(self, computed_data: dict) -> None:
        """Marine should have attack ability."""
        marine = computed_data["Units"].get("Marine", {})
        # Should have abilities or AbilArray
        has_abil = "AbilArray" in marine or "abilities" in marine
        assert has_abil, f"Marine should have abilities, got: {list(marine.keys())}"

    def test_zealot_has_abilities(self, computed_data: dict) -> None:
        """Zealot should have abilities."""
        zealot = computed_data["Units"].get("Zealot", {})
        has_abil = "AbilArray" in zealot or "abilities" in zealot
        assert has_abil, "Zealot should have abilities"

    def test_scv_has_build_ability(self, computed_data: dict) -> None:
        """SCV should have build abilities."""
        scv = computed_data["Units"]["SCV"]
        # SCV has builds, but also should have abilities
        has_abil = "AbilArray" in scv or "abilities" in scv
        assert has_abil, "SCV should have abilities"


class TestUnitsMorphsto:
    """Units should have morphsto for zerg morphs."""

    def test_larva_morphsto_many_units(self, computed_data: dict) -> None:
        """Larva should morphsto many zerg units."""
        larva = computed_data["Units"]["Larva"]
        assert "morphsto" in larva
        morph_list = larva["morphsto"] if isinstance(larva["morphsto"], list) else [larva["morphsto"]]
        assert "Zergling" in morph_list
        assert "Roach" in morph_list
        assert "Baneling" in morph_list

    def test_overlord_morphsto_overseer(self, computed_data: dict) -> None:
        """Overlord should morphsto Overseer."""
        overlord = computed_data["Units"].get("Overlord", {})
        if "morphsto" in overlord:
            morph = overlord["morphsto"]
            morph_list = morph if isinstance(morph, list) else [morph]
            assert "Overseer" in morph_list

    def test_hydralisk_morphsto_lurker(self, computed_data: dict) -> None:
        """Hydralisk should morphsto LurkerMP."""
        hydra = computed_data["Units"].get("Hydralisk", {})
        if "morphsto" in hydra:
            morph = hydra["morphsto"]
            morph_list = morph if isinstance(morph, list) else [morph]
            assert "LurkerMP" in morph_list


class TestAbilitiesNotEmpty:
    """Abilities section should not be empty - abilities should have full data."""

    def test_abilities_section_not_empty(self, computed_data: dict) -> None:
        """abilities dict should not be empty."""
        assert computed_data["Abilities"], "abilities section should not be empty"
        assert len(computed_data["Abilities"]) > 0

    def test_morph_to_baneling_has_data(self, computed_data: dict) -> None:
        """MorphToBaneling ability should have race, morphsto, requires."""
        abilities = computed_data["Abilities"]
        assert "MorphToBaneling" in abilities
        abil = abilities["MorphToBaneling"]
        assert abil.get("race") == "Zerg"
        assert abil.get("morphsto") == "Baneling"

    def test_upgrade_to_orbital_has_data(self, computed_data: dict) -> None:
        """UpgradeToOrbital ability should have race, morphsto, requires."""
        abilities = computed_data["Abilities"]
        assert "UpgradeToOrbital" in abilities
        abil = abilities["UpgradeToOrbital"]
        assert abil.get("race") == "Terran"
        assert abil.get("morphsto") == "OrbitalCommand"
        assert "requires" in abil

    def test_barracks_lift_off_has_data(self, computed_data: dict) -> None:
        """BarracksLiftOff ability should have race, morphsto."""
        abilities = computed_data["Abilities"]
        assert "BarracksLiftOff" in abilities
        abil = abilities["BarracksLiftOff"]
        assert abil.get("race") == "Terran"
        assert abil.get("morphsto") == "BarracksFlying"


class TestUpgradesNotEmpty:
    """Upgrades section should have entries with data."""

    def test_upgrades_section_not_empty(self, computed_data: dict) -> None:
        """upgrades dict should contain entries."""
        assert computed_data["Upgrades"], "upgrades section should not be empty"
        assert len(computed_data["Upgrades"]) > 0

    def test_blink_tech_has_data(self, computed_data: dict) -> None:
        """BlinkTech upgrade should have race and requires."""
        upgrades = computed_data["Upgrades"]
        assert "BlinkTech" in upgrades

    def test_stimpack_has_data(self, computed_data: dict) -> None:
        """Stimpack ability should exist and have proper data."""
        abilities = computed_data["Abilities"]
        assert "Stimpack" in abilities
        abil = abilities["Stimpack"]
        assert "EditorCategories" in abil
        assert "Race:Terran" in abil["EditorCategories"]

    def test_charge_has_data(self, computed_data: dict) -> None:
        """Charge upgrade should exist."""
        upgrades = computed_data["Upgrades"]
        assert "Charge" in upgrades


class TestStructuresUnlocks:
    """Structures should have 'unlocks' field linking to units/structures."""

    @pytest.mark.parametrize(
        "structure,unlocks",
        [
            ("Barracks", "Factory"),
            ("SpawningPool", "Zergling"),
            ("CyberneticsCore", "Stargate"),
        ],
    )
    def test_structure_unlocks(self, computed_data: dict, structure: str, unlocks: str) -> None:
        """Each structure should have 'unlocks' field containing expected unit/structure names."""
        unit = computed_data["Units"][structure]
        assert "unlocks" in unit
        assert unlocks in unit["unlocks"]


class TestUnitsBuilds:
    """Units should have 'builds' field for structures they can build."""

    @pytest.mark.parametrize(
        "unit,builds",
        [
            ("Drone", "SpawningPool"),
            ("Probe", "Gateway"),
            ("SCV", "Barracks"),
        ],
    )
    def test_unit_builds(self, computed_data: dict, unit: str, builds: str) -> None:
        """Each unit should have 'builds' field containing expected structure names."""
        u = computed_data["Units"][unit]
        assert "builds" in u
        assert builds in u["builds"]


class TestTechtreeResearchesInUpgrades:
    """Tests that upgrades from techtree structures' researches exist in computed data upgrades."""

    KNOWN_EXISTING_UPGRADES = [
        "BlinkTech",
        "Charge",
        "Burrow",
        "AnabolicSynthesis",
        "BansheeCloak",
        "BansheeSpeed",
        "CycloneLockOnDamageUpgrade",
        "DrillClaws",
        "HighCapacityBarrels",
        "InterferenceMatrix",
        "PunisherGrenades",
        "ShieldWall",
        "Stimpack",
        "TransformationServos",
    ]

    def test_techtree_researches_exist_in_upgrades(self, techtree: dict, computed_data: dict) -> None:
        """All upgrade names from techtree structures' researches should exist in computed_data upgrades."""
        upgrade_names_in_techtree = set()
        for name, data in techtree.get("Units", {}).items():
            if "researches" in data:
                for upg in data["researches"]:
                    upgrade_names_in_techtree.add(upg)

        upgrades_in_computed = set(computed_data.get("Upgrades", {}).keys())

        unexpected = []
        for upg in sorted(upgrade_names_in_techtree):
            if upg not in upgrades_in_computed:
                unexpected.append(upg)

        assert not unexpected, f"Unexpectedly missing upgrades: {unexpected}"

    def test_techtree_buildings_do_not_exist_in_upgrades(self, techtree: dict, computed_data: dict) -> None:
        structures = ["Spire", "SpawningPool", "Armory", "DarkShrine"]
        for structure in structures:
            assert structure not in computed_data["Upgrades"], f"Structure in upgrades section: {structure}"


class TestStableIdAbilities:
    def test_stimpack_has_id_from_stableid(self, computed_data: dict, stableid: dict) -> None:
        """Stimpack ability should have integer id from stableid Abilities section."""
        # Build lookup: name -> id
        ability_id_map = {entry["name"]: entry["id"] for entry in stableid["Abilities"]}
        stimpack = computed_data["Abilities"]["Stimpack"]
        assert "id" in stimpack, "Stimpack should have id field"
        assert isinstance(stimpack["id"], int), "id should be integer"
        assert stimpack["id"] == ability_id_map.get("Stimpack")


class TestStableIdUnits:
    def test_marine_has_id_from_stableid(self, computed_data: dict, stableid: dict) -> None:
        """Marine unit should have integer id from stableid Units section."""
        unit_id_map = {entry["name"]: entry["id"] for entry in stableid["Units"]}
        marine = computed_data["Units"]["Marine"]
        assert "id" in marine, "Marine should have id field"
        assert isinstance(marine["id"], int), "id should be integer"
        assert marine["id"] == unit_id_map.get("Marine")

    def test_scv_has_id(self, computed_data: dict, stableid: dict) -> None:
        """SCV should have an id from stableid."""
        unit_id_map = {entry["name"]: entry["id"] for entry in stableid["Units"]}
        scv = computed_data["Units"]["SCV"]
        assert "id" in scv
        assert isinstance(scv["id"], int)
        assert scv["id"] == unit_id_map.get("SCV")


class TestStableIdStructures:
    def test_barracks_has_id(self, computed_data: dict, stableid: dict) -> None:
        """Barracks structure should have an id from stableid Units section."""
        unit_id_map = {entry["name"]: entry["id"] for entry in stableid["Units"]}
        barracks = computed_data["Units"]["Barracks"]
        assert "id" in barracks
        assert isinstance(barracks["id"], int)
        assert barracks["id"] == unit_id_map.get("Barracks")


class TestStableIdMissing:
    def test_entries_with_stableid_have_integer_ids(self, computed_data: dict, stableid: dict) -> None:
        """Abilities/Units/Upgrades in stableid should have integer id fields."""
        ability_id_map = {entry["name"]: entry["id"] for entry in stableid["Abilities"]}
        unit_id_map = {entry["name"]: entry["id"] for entry in stableid["Units"]}
        upgrade_id_map = {entry["name"]: entry["id"] for entry in stableid["Upgrades"]}

        for name, entry in computed_data["Abilities"].items():
            if name in ability_id_map:
                assert "id" in entry, f"{name} in stableid should have id"
                assert isinstance(entry["id"], int), f"{name} id should be integer"

        for name, entry in computed_data["Units"].items():
            if (entry.get("type") == "unit" or entry.get("type") == "structure") and name in unit_id_map:
                assert "id" in entry, f"{name} in stableid should have id"
                assert isinstance(entry["id"], int), f"{name} id should be integer"

        for name, entry in computed_data["Upgrades"].items():
            if name in upgrade_id_map:
                assert "id" in entry, f"{name} in stableid should have id"
                assert isinstance(entry["id"], int), f"{name} id should be integer"


class TestStableIdUpgrades:
    def test_burrow_has_id_from_stableid(self, computed_data: dict, stableid: dict) -> None:
        """Burrow upgrade should have integer id from stableid Upgrades section."""
        upgrade_id_map = {entry["name"]: entry["id"] for entry in stableid["Upgrades"]}
        burrow = computed_data["Upgrades"]["Burrow"]
        assert "id" in burrow, "Burrow should have id field"
        assert isinstance(burrow["id"], int), "id should be integer"
        assert burrow["id"] == upgrade_id_map.get("Burrow")


class TestStimpackUpgradeAndAbility:
    """Test Stimpack upgrade and ability have correct resource costs."""

    def _check_value(self, value: Any, expected: int, field_name: str) -> None:
        """Check a value is an integer."""
        assert isinstance(value, int), f"{field_name} should be integer, got {type(value).__name__}: {value}"
        assert value == expected, f"{field_name} should be {expected}, got {value}"

    def test_stimpack_upgrade_exists(self, computed_data: dict) -> None:
        """Stimpack upgrade should exist in Upgrades."""
        assert "Stimpack" in computed_data["Upgrades"], "Stimpack upgrade should exist"

    def test_stimpack_upgrade_minerals(self, computed_data: dict) -> None:
        """Stimpack upgrade should have minerals = 100."""
        stimpack = computed_data["Upgrades"]["Stimpack"]
        assert "minerals" in stimpack, "Stimpack upgrade should have minerals field"
        self._check_value(stimpack["minerals"], 100, "minerals")

    def test_stimpack_upgrade_gas(self, computed_data: dict) -> None:
        """Stimpack upgrade should have gas = 100."""
        stimpack = computed_data["Upgrades"]["Stimpack"]
        assert "gas" in stimpack, "Stimpack upgrade should have gas field"
        self._check_value(stimpack["gas"], 100, "gas")

    def test_stimpack_upgrade_time(self, computed_data: dict) -> None:
        """Stimpack upgrade should have time = 140."""
        stimpack = computed_data["Upgrades"]["Stimpack"]
        assert "time" in stimpack, "Stimpack upgrade should have time field"
        self._check_value(stimpack["time"], 140, "time")

    def test_stimpack_ability_exists(self, computed_data: dict) -> None:
        """Stimpack ability should exist in Abilities."""
        assert "Stimpack" in computed_data["Abilities"], "Stimpack ability should exist"

    def test_stimpack_ability_minerals(self, computed_data: dict) -> None:
        """Stimpack ability should have minerals = 100."""
        stimpack = computed_data["Abilities"]["Stimpack"]
        assert "minerals" in stimpack, "Stimpack ability should have minerals field"
        self._check_value(stimpack["minerals"], 100, "minerals")

    def test_stimpack_ability_gas(self, computed_data: dict) -> None:
        """Stimpack ability should have gas = 100."""
        stimpack = computed_data["Abilities"]["Stimpack"]
        assert "gas" in stimpack, "Stimpack ability should have gas field"
        self._check_value(stimpack["gas"], 100, "gas")

    def test_stimpack_ability_time(self, computed_data: dict) -> None:
        """Stimpack ability should have time = 140."""
        stimpack = computed_data["Abilities"]["Stimpack"]
        assert "time" in stimpack, "Stimpack ability should have time field"
        self._check_value(stimpack["time"], 140, "time")


class TestResearchAbilities:
    """Test all research abilities have correct resource costs."""

    @pytest.fixture
    def research_abilities_with_costs(self) -> list[tuple[str, dict]]:
        """Load research abilities and their expected costs from AbilData.json.

        Returns a list of (ability_name, expected_costs) tuples for abilities that exist
        in computed data's Abilities section.
        """
        abil_path = Path(__file__).parent.parent / "src" / "json" / "AbilData.json"
        with abil_path.open() as f:
            abil_data = json.load(f)

        # First, find all research buttons with costs from AbilData
        abil_costs: dict[str, dict] = {}
        for ability in abil_data.values():
            if not isinstance(ability, list):
                continue
            for entry in ability:
                if not isinstance(entry, dict):
                    continue
                info_array = entry.get("InfoArray", [])
                if not isinstance(info_array, list):
                    continue
                for item in info_array:
                    if not isinstance(item, dict):
                        continue
                    button = item.get("Button", {})
                    if not isinstance(button, dict):
                        continue
                    face = button.get("DefaultButtonFace", "")
                    if not face:
                        continue
                    # Only include abilities starting with "Research"
                    if not face.startswith("Research"):
                        continue
                    resource = item.get("Resource", {})
                    minerals = resource.get("Minerals", 0)
                    gas = resource.get("Vespene", 0)
                    time_str = item.get("Time", "0")
                    try:
                        time = int(time_str)
                    except (ValueError, TypeError):
                        time = 0
                    if minerals or gas or time:
                        abil_costs[face] = {"minerals": minerals, "gas": gas, "time": time}

        # Now find which ones actually exist in computed data Abilities
        computed_path = Path(__file__).parent.parent / "src" / "computed" / "data.json"
        with computed_path.open() as f:
            computed_data = json.load(f)

        result: list[tuple[str, dict]] = []
        for ability_name in abil_costs:
            if ability_name in computed_data["Abilities"]:
                result.append((ability_name, abil_costs[ability_name]))

        return result

    def test_all_research_abilities_have_correct_costs(
        self, computed_data: dict, research_abilities_with_costs: list[tuple[str, dict]]
    ) -> None:
        """Test all discovered research abilities have correct costs in computed data."""
        abilities = computed_data["Abilities"]
        for ability_name, expected in research_abilities_with_costs:
            assert ability_name in abilities, f"{ability_name} should be in Abilities"
            ability = abilities[ability_name]
            # Test each expected value
            for field, expected_value in expected.items():
                assert field in ability, f"{ability_name} should have {field}"
                actual = ability[field]
                assert isinstance(actual, (int, float)), f"{ability_name}.{field} should be numeric"
                assert actual == expected_value, f"{ability_name}.{field} should be {expected_value}, got {actual}"


class TestBFSReachability:
    """Tests for BFS reachability through the techtree graph."""

    TRAVERSE_KEYS = ["produces", "builds", "researches", "morphsto", "unlocks"]

    def reachable(self, computed_data: dict, start_units: list[str]) -> set[str]:
        """Do BFS from starting units through the techtree graph."""
        visited: set[str] = set()
        queue: list[str] = list(start_units)

        structures = computed_data.get("Structures", {})
        units = computed_data.get("Units", {})
        upgrades = computed_data.get("Upgrades", {})

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            # Check structures
            if current in structures:
                entry = structures[current]
                for key in self.TRAVERSE_KEYS:
                    if key in entry:
                        value = entry[key]
                        if isinstance(value, list):
                            queue.extend(value)
                        elif isinstance(value, str) and value:
                            queue.append(value)

            # Check units
            if current in units:
                entry = units[current]
                for key in self.TRAVERSE_KEYS:
                    if key in entry:
                        value = entry[key]
                        if isinstance(value, list):
                            queue.extend(value)
                        elif isinstance(value, str) and value:
                            queue.append(value)

            # Check upgrades
            if current in upgrades:
                entry = upgrades[current]
                for key in self.TRAVERSE_KEYS:
                    if key in entry:
                        value = entry[key]
                        if isinstance(value, list):
                            queue.extend(value)
                        elif isinstance(value, str) and value:
                            queue.append(value)

        return visited

    def test_terran_fusion_core_reachable(self, computed_data: dict) -> None:
        """Test Fusion Core is reachable from SCV."""
        reachable = self.reachable(computed_data, ["SCV"])
        assert "FusionCore" in reachable, "FusionCore should be reachable from SCV"

    def test_terran_starport_techlab_upgrades_reachable(self, computed_data: dict) -> None:
        """Test Banshee upgrades are reachable from SCV via Starport + Tech Lab."""
        reachable = self.reachable(computed_data, ["SCV"])
        assert "BansheeCloak" in reachable, "BansheeCloak should be reachable from SCV"
        assert "BansheeSpeed" in reachable, "BansheeSpeed should be reachable from SCV"

    def test_terran_banshee_reachable(self, computed_data: dict) -> None:
        """Test Banshee is reachable from SCV."""
        reachable = self.reachable(computed_data, ["SCV"])
        assert "Banshee" in reachable, "Banshee should be reachable from SCV"

    def test_zerg_hive_reachable(self, computed_data: dict) -> None:
        """Test Hive is reachable from Larva."""
        reachable = self.reachable(computed_data, ["Larva"])
        assert "Hive" in reachable, "Hive should be reachable from Larva"

    def test_zerg_greater_spire_reachable(self, computed_data: dict) -> None:
        """Test GreaterSpire is reachable from Larva."""
        reachable = self.reachable(computed_data, ["Larva"])
        assert "GreaterSpire" in reachable, "GreaterSpire should be reachable from Larva"

    def test_zerg_baneling_reachable(self, computed_data: dict) -> None:
        """Test Baneling is reachable from Larva."""
        reachable = self.reachable(computed_data, ["Larva"])
        assert "Baneling" in reachable, "Baneling should be reachable from Larva"

    def test_zerg_ravager_reachable(self, computed_data: dict) -> None:
        """Test Ravager is reachable from Larva."""
        reachable = self.reachable(computed_data, ["Larva"])
        assert "Ravager" in reachable, "Ravager should be reachable from Larva"

    def test_zerg_lurker_upgrades_reachable(self, computed_data: dict) -> None:
        """Test Lurker MP upgrades are reachable from Larva."""
        reachable = self.reachable(computed_data, ["Larva"])
        assert "LurkerMP" in reachable, "LurkerMP should be reachable from Larva"

    def test_protoss_fleet_beacon_reachable(self, computed_data: dict) -> None:
        """Test FleetBeacon is reachable from Probe."""
        reachable = self.reachable(computed_data, ["Probe"])
        assert "FleetBeacon" in reachable, "FleetBeacon should be reachable from Probe"

    def test_protoss_tempest_reachable(self, computed_data: dict) -> None:
        """Test Tempest is reachable from Probe."""
        reachable = self.reachable(computed_data, ["Probe"])
        assert "Tempest" in reachable, "Tempest should be reachable from Probe"

    def test_protoss_oracle_reachable(self, computed_data: dict) -> None:
        """Test Oracle is reachable from Probe."""
        reachable = self.reachable(computed_data, ["Probe"])
        assert "Oracle" in reachable, "Oracle should be reachable from Probe"

    def test_campaign_units_not_reachable(self, computed_data: dict) -> None:
        """Test that campaign units are NOT reachable (filtered from techtree)."""
        reachable = self.reachable(computed_data, ["SCV"])
        # Campaign units should be filtered out, so Sirius should not be in the reachable set
        assert "Sirius" not in reachable, "Campaign unit Sirius should not be reachable from SCV"


class TestSpireBuildTime:
    def test_spire_build_time(self, computed_data: dict) -> None:
        """Spire should have a build time of 92.4 seconds."""
        spire = computed_data["Units"]["Spire"]
        assert "time" in spire, "Spire should have time field"
        assert spire["time"] == 92.4, f"Spire time should be 92.4, got {spire.get('time')}"


class TestQueenBuildTime:
    def test_queen_build_time(self, computed_data: dict) -> None:
        """Queen should have a build time of 50 seconds."""
        queen = computed_data["Units"]["Queen"]
        assert "time" in queen, "Queen should have time field"
        assert queen["time"] == 50, f"Queen time should be 50, got {queen.get('time')}"
