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


class TestFactory:
    def test_factory_produces_excludes_war_hound(self, techtree_data: dict) -> None:
        factory = techtree_data["structures"]["Factory"]
        assert "produces" in factory
        assert "WarHound" not in factory["produces"]


class TestRoboticsFacility:
    def test_robotics_facility_produces(self, techtree_data: dict) -> None:
        facility = techtree_data["structures"]["RoboticsFacility"]
        assert "produces" in facility
        assert facility["produces"] == [
            "Colossus",
            "Disruptor",
            "Immortal",
            "Observer",
            "WarpPrism",
        ]


class TestTemplarArchive:
    def test_templar_archive_researches(self, techtree_data: dict) -> None:
        archive = techtree_data["structures"]["TemplarArchive"]
        assert "researches" in archive
        assert archive["researches"] == ["PsiStormTech"]


class TestTwilightCouncil:
    def test_twilight_council_researches(self, techtree_data: dict) -> None:
        council = techtree_data["structures"]["TwilightCouncil"]
        assert "researches" in council
        assert council["researches"] == [
            "AdeptPiercingAttack",
            "BlinkTech",
            "Charge",
        ]


class TestBarracksTechLab:
    def test_barracks_tech_lab_researches(self, techtree_data: dict) -> None:
        lab = techtree_data["structures"]["BarracksTechLab"]
        assert "researches" in lab
        assert lab["researches"] == [
            "PunisherGrenades",
            "ShieldWall",
            "Stimpack",
        ]


class TestUltraliskCavern:
    def test_ultralisk_cavern_researches(self, techtree_data: dict) -> None:
        cavern = techtree_data["structures"]["UltraliskCavern"]
        assert "researches" in cavern
        assert cavern["researches"] == [
            "AnabolicSynthesis",
            "ChitinousPlating",
        ]


class TestFactoryTechLab:
    def test_factory_tech_lab_researches(self, techtree_data: dict) -> None:
        lab = techtree_data["structures"]["FactoryTechLab"]
        assert "researches" in lab
        assert lab["researches"] == [
            "CycloneLockOnDamageUpgrade",
            "DrillClaws",
            "HighCapacityBarrels",
            "TransformationServos",
        ]


class TestStarportTechLab:
    def test_starport_tech_lab_researches(self, techtree_data: dict) -> None:
        lab = techtree_data["structures"]["StarportTechLab"]
        assert "researches" in lab
        assert lab["researches"] == [
            "BansheeCloak",
            "BansheeSpeed",
            "InterferenceMatrix",
        ]


class TestCyberneticsCore:
    def test_cybernetics_core_researches(self, techtree_data: dict) -> None:
        core = techtree_data["structures"]["CyberneticsCore"]
        assert "researches" in core
        assert core["researches"] == [
            "ProtossAirArmorsLevel1",
            "ProtossAirArmorsLevel2",
            "ProtossAirArmorsLevel3",
            "ProtossAirWeaponsLevel1",
            "ProtossAirWeaponsLevel2",
            "ProtossAirWeaponsLevel3",
            "WarpGateResearch",
        ]

    def test_cybernetics_core_researches_excludes_haltech(self, techtree_data: dict) -> None:
        core = techtree_data["structures"]["CyberneticsCore"]
        assert "researches" in core
        assert "haltech" not in core["researches"]


class TestEngineeringBay:
    def test_engineering_bay_researches(self, techtree_data: dict) -> None:
        bay = techtree_data["structures"]["EngineeringBay"]
        assert "researches" in bay
        assert bay["researches"] == [
            "HiSecAutoTracking",
            "NeosteelFrame",
            "TerranInfantryArmorsLevel1",
            "TerranInfantryArmorsLevel2",
            "TerranInfantryArmorsLevel3",
            "TerranInfantryWeaponsLevel1",
            "TerranInfantryWeaponsLevel2",
            "TerranInfantryWeaponsLevel3",
        ]

    def test_engineering_bay_researches_excludes_terran_building_armor(self, techtree_data: dict) -> None:
        bay = techtree_data["structures"]["EngineeringBay"]
        assert "researches" in bay
        assert "TerranBuildingArmor" not in bay["researches"]


class TestFleetBeacon:
    def test_fleet_beacon_researches(self, techtree_data: dict) -> None:
        beacon = techtree_data["structures"]["FleetBeacon"]
        assert "researches" in beacon
        assert beacon["researches"] == [
            "PhoenixRangeUpgrade",
            "TempestGroundAttackUpgrade",
            "VoidRaySpeedUpgrade",
        ]


class TestFusionCore:
    def test_fusion_core_researches(self, techtree_data: dict) -> None:
        core = techtree_data["structures"]["FusionCore"]
        assert "researches" in core
        assert core["researches"] == [
            "BattlecruiserEnableSpecializations",
            "LiberatorAGRangeUpgrade",
            "MedivacCaduceusReactor",
        ]


class TestGhostAcademy:
    def test_ghost_academy_researches(self, techtree_data: dict) -> None:
        academy = techtree_data["structures"]["GhostAcademy"]
        assert "researches" in academy
        assert academy["researches"] == ["PersonalCloaking"]


class TestGreaterSpire:
    def test_greater_spire_researches(self, techtree_data: dict) -> None:
        spire = techtree_data["structures"]["GreaterSpire"]
        assert "researches" in spire
        assert spire["researches"] == [
            "ZergFlyerArmorsLevel1",
            "ZergFlyerArmorsLevel2",
            "ZergFlyerArmorsLevel3",
            "ZergFlyerWeaponsLevel1",
            "ZergFlyerWeaponsLevel2",
            "ZergFlyerWeaponsLevel3",
        ]


class TestHydraliskDen:
    def test_hydralisk_den_researches(self, techtree_data: dict) -> None:
        den = techtree_data["structures"]["HydraliskDen"]
        assert "researches" in den
        assert den["researches"] == [
            "EvolveGroovedSpines",
            "EvolveMuscularAugments",
            "Frenzy",
        ]


class TestInfestationPit:
    def test_infestation_pit_researches(self, techtree_data: dict) -> None:
        pit = techtree_data["structures"]["InfestationPit"]
        assert "researches" in pit
        assert pit["researches"] == [
            "MicrobialShroud",
            "NeuralParasite",
        ]


class TestLurkerDenMP:
    def test_lurker_den_mp_researches(self, techtree_data: dict) -> None:
        den = techtree_data["structures"]["LurkerDenMP"]
        assert "researches" in den
        assert den["researches"] == [
            "DiggingClaws",
            "LurkerRange",
        ]


class TestRoachWarren:
    def test_roach_warren_researches(self, techtree_data: dict) -> None:
        warren = techtree_data["structures"]["RoachWarren"]
        assert "researches" in warren
        assert warren["researches"] == [
            "GlialReconstitution",
            "TunnelingClaws",
        ]


class TestRoboticsBay:
    def test_robotics_bay_requires(self, techtree_data: dict) -> None:
        bay = techtree_data["structures"]["RoboticsBay"]
        assert "requires" in bay
        assert bay["requires"] == ["RoboticsFacility"]

    def test_robotics_bay_researches(self, techtree_data: dict) -> None:
        bay = techtree_data["structures"]["RoboticsBay"]
        assert "researches" in bay
        assert bay["researches"] == [
            "ExtendedThermalLance",
            "GraviticDrive",
            "ObserverGraviticBooster",
        ]


class TestUpgradeToGreaterSpire:
    def test_upgrade_to_greater_spire(self, techtree_data: dict) -> None:
        upgrade = techtree_data["abilities"]["UpgradeToGreaterSpire"]
        assert upgrade["morphsto"] == "GreaterSpire"
        assert upgrade["race"] == "Zerg"
        assert upgrade["requires"] == ["Hive"]


class TestNexus:
    def test_nexus_produces(self, techtree_data: dict) -> None:
        nexus = techtree_data["structures"]["Nexus"]
        assert "produces" in nexus
        assert nexus["produces"] == ["Mothership", "Probe"]


class TestPlanetaryFortress:
    def test_planetary_fortress_produces(self, techtree_data: dict) -> None:
        pf = techtree_data["structures"]["PlanetaryFortress"]
        assert "produces" in pf
        assert pf["produces"] == ["SCV"]
