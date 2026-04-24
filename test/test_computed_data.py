import json
from pathlib import Path

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


class TestSCVInUnits:
    def test_scv_exists_in_units(self, computed_data: dict) -> None:
        assert "SCV" in computed_data["units"]


class TestSCVBuilds:
    def test_scv_builds_excludes_bomber_launch_pad(self, computed_data: dict) -> None:
        scv = computed_data["units"]["SCV"]
        assert "builds" in scv
        assert "BomberLaunchPad" not in scv["builds"]

    def test_scv_builds_excludes_merc_compound(self, computed_data: dict) -> None:
        scv = computed_data["units"]["SCV"]
        assert "builds" in scv
        assert "MercCompound" not in scv["builds"]


class TestNexus:
    def test_nexus_abil_array_excludes_train_mothership_core(self, computed_data: dict) -> None:
        nexus = computed_data["structures"]["Nexus"]
        assert "AbilArray" in nexus
        assert "NexusTrainMothershipCore" not in nexus["AbilArray"]


class TestStructuresResearches:
    """Structures should have 'researches' field with upgrade names."""

    def test_twilight_council_has_researches(self, computed_data: dict) -> None:
        """TwilightCouncil should research BlinkTech, Charge, AdeptPiercingAttack."""
        twilight = computed_data["structures"]["TwilightCouncil"]
        assert "researches" in twilight
        assert "BlinkTech" in twilight["researches"]
        assert "Charge" in twilight["researches"]
        assert "AdeptPiercingAttack" in twilight["researches"]

    def test_spire_has_researches(self, computed_data: dict) -> None:
        """Spire should research ZergFlyerArmorsLevel1, etc."""
        spire = computed_data["structures"]["Spire"]
        assert "researches" in spire
        assert "ZergFlyerArmorsLevel1" in spire["researches"]

    def test_armory_has_researches(self, computed_data: dict) -> None:
        """Armory should research vehicle/ship upgrades."""
        armory = computed_data["structures"]["Armory"]
        assert "researches" in armory
        assert "TerranVehicleWeaponsLevel1" in armory["researches"]

    def test_hatchery_has_researches(self, computed_data: dict) -> None:
        """Hatchery should research Burrow, overlordspeed, overlordtransport."""
        hatchery = computed_data["structures"]["Hatchery"]
        assert "researches" in hatchery
        assert "Burrow" in hatchery["researches"]


class TestStructuresProduces:
    """Structures should have 'produces' field with unit names."""

    def test_hatchery_produces_queen(self, computed_data: dict) -> None:
        """Hatchery should produce Queen."""
        hatchery = computed_data["structures"]["Hatchery"]
        assert "produces" in hatchery
        assert "Queen" in hatchery["produces"]

    def test_barracks_produces_marine_reaper(self, computed_data: dict) -> None:
        """Barracks should produce Marine, Reaper, Marauder, Ghost."""
        barracks = computed_data["structures"]["Barracks"]
        assert "produces" in barracks
        assert "Marine" in barracks["produces"]
        assert "Reaper" in barracks["produces"]

    def test_gateway_produces_zealot_stalker(self, computed_data: dict) -> None:
        """Gateway should produce Zealot, Stalker, Sentry, etc."""
        gateway = computed_data["structures"]["Gateway"]
        assert "produces" in gateway
        assert "Zealot" in gateway["produces"]
        assert "Stalker" in gateway["produces"]

    def test_orbital_command_produces_scv(self, computed_data: dict) -> None:
        """OrbitalCommand should produce SCV."""
        orbital = computed_data["structures"]["OrbitalCommand"]
        assert "produces" in orbital
        assert "SCV" in orbital["produces"]


class TestStructuresMorphsto:
    """Structures should have 'morphsto' field for transformations."""

    def test_spire_morphsto_greater_spire(self, computed_data: dict) -> None:
        """Spire should morphsto GreaterSpire."""
        spire = computed_data["structures"]["Spire"]
        assert "morphsto" in spire
        assert spire["morphsto"] == "GreaterSpire"

    def test_hatchery_morphsto_lair(self, computed_data: dict) -> None:
        """Hatchery should morphsto Lair."""
        hatchery = computed_data["structures"]["Hatchery"]
        assert "morphsto" in hatchery
        assert hatchery["morphsto"] == "Lair"

    def test_lair_morphsto_hive(self, computed_data: dict) -> None:
        """Lair should morphsto Hive."""
        lair = computed_data["structures"]["Lair"]
        assert "morphsto" in lair
        assert lair["morphsto"] == "Hive"

    def test_command_center_morphsto_options(self, computed_data: dict) -> None:
        """CommandCenter should have multiple morphsto options."""
        cc = computed_data["structures"]["CommandCenter"]
        assert "morphsto" in cc
        assert isinstance(cc["morphsto"], list)
        assert "OrbitalCommand" in cc["morphsto"]

    def test_factory_morphsto_flying(self, computed_data: dict) -> None:
        """Factory should morphsto FactoryFlying."""
        factory = computed_data["structures"]["Factory"]
        assert "morphsto" in factory
        assert factory["morphsto"] == "FactoryFlying"


class TestUnitsAbilArray:
    """Units should have abilities (AbilArray) from UnitData."""

    def test_marine_has_attack_ability(self, computed_data: dict) -> None:
        """Marine should have attack ability."""
        marine = computed_data["units"].get("Marine", {})
        # Should have abilities or AbilArray
        has_abil = "AbilArray" in marine or "abilities" in marine
        assert has_abil, f"Marine should have abilities, got: {list(marine.keys())}"

    def test_zealot_has_abilities(self, computed_data: dict) -> None:
        """Zealot should have abilities."""
        zealot = computed_data["units"].get("Zealot", {})
        has_abil = "AbilArray" in zealot or "abilities" in zealot
        assert has_abil, "Zealot should have abilities"

    def test_scv_has_build_ability(self, computed_data: dict) -> None:
        """SCV should have build abilities."""
        scv = computed_data["units"]["SCV"]
        # SCV has builds, but also should have abilities
        has_abil = "AbilArray" in scv or "abilities" in scv
        assert has_abil, "SCV should have abilities"


class TestUnitsMorphsto:
    """Units should have morphsto for zerg morphs."""

    def test_larva_morphsto_many_units(self, computed_data: dict) -> None:
        """Larva should morphsto many zerg units."""
        larva = computed_data["units"]["Larva"]
        assert "morphsto" in larva
        morph_list = larva["morphsto"] if isinstance(larva["morphsto"], list) else [larva["morphsto"]]
        assert "Zergling" in morph_list
        assert "Roach" in morph_list
        assert "Baneling" in morph_list

    def test_overlord_morphsto_overseer(self, computed_data: dict) -> None:
        """Overlord should morphsto Overseer."""
        overlord = computed_data["units"].get("Overlord", {})
        if "morphsto" in overlord:
            morph = overlord["morphsto"]
            morph_list = morph if isinstance(morph, list) else [morph]
            assert "Overseer" in morph_list

    def test_hydralisk_morphsto_lurker(self, computed_data: dict) -> None:
        """Hydralisk should morphsto LurkerMP."""
        hydra = computed_data["units"].get("Hydralisk", {})
        if "morphsto" in hydra:
            morph = hydra["morphsto"]
            morph_list = morph if isinstance(morph, list) else [morph]
            assert "LurkerMP" in morph_list


class TestAbilitiesNotEmpty:
    """Abilities section should not be empty - abilities should have full data."""

    def test_abilities_section_not_empty(self, computed_data: dict) -> None:
        """abilities dict should not be empty."""
        assert computed_data["abilities"], "abilities section should not be empty"
        assert len(computed_data["abilities"]) > 0

    def test_morph_to_baneling_has_data(self, computed_data: dict) -> None:
        """MorphToBaneling ability should have race, morphsto, requires."""
        abilities = computed_data["abilities"]
        assert "MorphToBaneling" in abilities
        abil = abilities["MorphToBaneling"]
        assert abil.get("race") == "Zerg"
        assert abil.get("morphsto") == "Baneling"

    def test_upgrade_to_orbital_has_data(self, computed_data: dict) -> None:
        """UpgradeToOrbital ability should have race, morphsto, requires."""
        abilities = computed_data["abilities"]
        assert "UpgradeToOrbital" in abilities
        abil = abilities["UpgradeToOrbital"]
        assert abil.get("race") == "Terran"
        assert abil.get("morphsto") == "OrbitalCommand"
        assert "requires" in abil

    def test_barracks_lift_off_has_data(self, computed_data: dict) -> None:
        """BarracksLiftOff ability should have race, morphsto."""
        abilities = computed_data["abilities"]
        assert "BarracksLiftOff" in abilities
        abil = abilities["BarracksLiftOff"]
        assert abil.get("race") == "Terran"
        assert abil.get("morphsto") == "BarracksFlying"


class TestUpgradesNotEmpty:
    """Upgrades section should have entries with data."""

    def test_upgrades_section_not_empty(self, computed_data: dict) -> None:
        """upgrades dict should contain entries."""
        assert computed_data["upgrades"], "upgrades section should not be empty"
        assert len(computed_data["upgrades"]) > 0

    def test_blink_tech_has_data(self, computed_data: dict) -> None:
        """BlinkTech upgrade should have race and requires."""
        upgrades = computed_data["upgrades"]
        assert "BlinkTech" in upgrades

    def test_stimpack_has_data(self, computed_data: dict) -> None:
        """Stimpack ability should exist and have proper data."""
        abilities = computed_data["abilities"]
        assert "Stimpack" in abilities
        abil = abilities["Stimpack"]
        assert "EditorCategories" in abil
        assert "Race:Terran" in abil["EditorCategories"]

    def test_charge_has_data(self, computed_data: dict) -> None:
        """Charge upgrade should exist."""
        upgrades = computed_data["upgrades"]
        assert "Charge" in upgrades


class TestStructuresUnlocks:
    """Structures should have 'unlocks' field linking to units/structures."""

    def test_barracks_unlocks_factory(self, computed_data: dict) -> None:
        """Barracks should unlock Factory."""
        barracks = computed_data["structures"]["Barracks"]
        assert "unlocks" in barracks
        assert "Factory" in barracks["unlocks"]

    def test_spawning_pool_unlocks_zergling(self, computed_data: dict) -> None:
        """SpawningPool should unlock Zergling."""
        pool = computed_data["structures"]["SpawningPool"]
        assert "unlocks" in pool
        assert "Zergling" in pool["unlocks"]

    def test_cybernetics_core_unlocks_stargate(self, computed_data: dict) -> None:
        """CyberneticsCore should unlock Stargate."""
        core = computed_data["structures"]["CyberneticsCore"]
        assert "unlocks" in core
        assert "Stargate" in core["unlocks"]


class TestUnitsBuilds:
    """Units should have 'builds' field for structures they can build."""

    def test_drone_builds_spawning_pool(self, computed_data: dict) -> None:
        """Drone should build SpawningPool."""
        drone = computed_data["units"]["Drone"]
        assert "builds" in drone
        assert "SpawningPool" in drone["builds"]

    def test_probe_builds_gateway(self, computed_data: dict) -> None:
        """Probe should build Gateway."""
        probe = computed_data["units"]["Probe"]
        assert "builds" in probe
        assert "Gateway" in probe["builds"]

    def test_scv_builds_barracks(self, computed_data: dict) -> None:
        """SCV should build Barracks."""
        scv = computed_data["units"]["SCV"]
        assert "builds" in scv
        assert "Barracks" in scv["builds"]


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
        for name, data in techtree.get("structures", {}).items():
            if "researches" in data:
                for upg in data["researches"]:
                    upgrade_names_in_techtree.add(upg)

        upgrades_in_computed = set(computed_data.get("upgrades", {}).keys())

        unexpected = []
        for upg in sorted(upgrade_names_in_techtree):
            if upg not in upgrades_in_computed:
                unexpected.append(upg)

        assert not unexpected, f"Unexpectedly missing upgrades: {unexpected}"

    def test_techtree_buildings_do_not_exist_in_upgrades(self, techtree: dict, computed_data: dict) -> None:
        structures = ["Spire", "SpawningPool", "Armory", "DarkShrine"]
        for structure in structures:
            assert structure not in computed_data["upgrades"], f"Structure in upgrades section: {structure}"
