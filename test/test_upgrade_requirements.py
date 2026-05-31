import json
from pathlib import Path
import pytest

# Upgrades that require no structure - just previous level
NO_EXTRA_STRUCTURE_UPGRADES = [
    ("TerranShipWeaponsLevel1", []),
    ("TerranShipWeaponsLevel2", ["TerranShipWeaponsLevel1"]),
    ("TerranShipWeaponsLevel3", ["TerranShipWeaponsLevel2"]),
    ("TerranVehicleAndShipArmorsLevel1", []),
    ("TerranVehicleAndShipArmorsLevel2", ["TerranVehicleAndShipArmorsLevel1"]),
    ("TerranVehicleAndShipArmorsLevel3", ["TerranVehicleAndShipArmorsLevel2"]),
    ("TerranVehicleWeaponsLevel1", []),
    ("TerranVehicleWeaponsLevel2", ["TerranVehicleWeaponsLevel1"]),
    ("TerranVehicleWeaponsLevel3", ["TerranVehicleWeaponsLevel2"]),
]

# Upgrades that require Armory + previous level
ARMORY_UPGRADES = [
    ("TerranInfantryArmorsLevel1", []),
    ("TerranInfantryArmorsLevel2", ["Armory", "TerranInfantryArmorsLevel1"]),
    ("TerranInfantryArmorsLevel3", ["Armory", "TerranInfantryArmorsLevel2"]),
    ("TerranInfantryWeaponsLevel1", []),
    ("TerranInfantryWeaponsLevel2", ["Armory", "TerranInfantryWeaponsLevel1"]),
    ("TerranInfantryWeaponsLevel3", ["Armory", "TerranInfantryWeaponsLevel2"]),
]

# Upgrades that require FleetBeacon + previous level
FLEETBEACON_UPGRADES = [
    ("ProtossAirArmorsLevel1", []),
    ("ProtossAirArmorsLevel2", ["FleetBeacon", "ProtossAirArmorsLevel1"]),
    ("ProtossAirArmorsLevel3", ["FleetBeacon", "ProtossAirArmorsLevel2"]),
    ("ProtossAirWeaponsLevel1", []),
    ("ProtossAirWeaponsLevel2", ["FleetBeacon", "ProtossAirWeaponsLevel1"]),
    ("ProtossAirWeaponsLevel3", ["FleetBeacon", "ProtossAirWeaponsLevel2"]),
]

# Upgrades that require TwilightCouncil + previous level
TWILIGHT_COUNCIL_UPGRADES = [
    ("ProtossGroundArmorsLevel1", []),
    ("ProtossGroundArmorsLevel2", ["TwilightCouncil", "ProtossGroundArmorsLevel1"]),
    ("ProtossGroundArmorsLevel3", ["TwilightCouncil", "ProtossGroundArmorsLevel2"]),
    ("ProtossGroundWeaponsLevel1", []),
    ("ProtossGroundWeaponsLevel2", ["TwilightCouncil", "ProtossGroundWeaponsLevel1"]),
    ("ProtossGroundWeaponsLevel3", ["TwilightCouncil", "ProtossGroundWeaponsLevel2"]),
    ("ProtossShieldsLevel1", []),
    ("ProtossShieldsLevel2", ["TwilightCouncil", "ProtossShieldsLevel1"]),
    ("ProtossShieldsLevel3", ["TwilightCouncil", "ProtossShieldsLevel2"]),
]


@pytest.fixture
def techtree_data() -> dict:
    path = Path(__file__).parent.parent / "src" / "computed" / "techtree.json"
    with path.open() as f:
        return json.load(f)


class TestNoExtraStructureRequires:
    """Tests for upgrades that only require previous level (no extra structure)."""

    @pytest.mark.parametrize("upgrade_name,expected_requires", NO_EXTRA_STRUCTURE_UPGRADES)
    def test_upgrade_requires(self, techtree_data: dict, upgrade_name: str, expected_requires: list) -> None:
        upgrades = techtree_data.get("Upgrades", {})
        upgrade = upgrades.get(upgrade_name, {})
        assert "requires" in upgrade, f"{upgrade_name} missing 'requires' field"
        assert upgrade["requires"] == expected_requires, (
            f"{upgrade_name}: expected {expected_requires}, got {upgrade['requires']}"
        )


class TestArmoryRequires:
    """Tests for upgrades that require Armory + previous level."""

    @pytest.mark.parametrize("upgrade_name,expected_requires", ARMORY_UPGRADES)
    def test_upgrade_requires(self, techtree_data: dict, upgrade_name: str, expected_requires: list) -> None:
        upgrades = techtree_data.get("Upgrades", {})
        upgrade = upgrades.get(upgrade_name, {})
        assert "requires" in upgrade, f"{upgrade_name} missing 'requires' field"
        assert upgrade["requires"] == expected_requires, (
            f"{upgrade_name}: expected {expected_requires}, got {upgrade['requires']}"
        )


class TestFleetBeaconRequires:
    """Tests for upgrades that require FleetBeacon + previous level."""

    @pytest.mark.parametrize("upgrade_name,expected_requires", FLEETBEACON_UPGRADES)
    def test_upgrade_requires(self, techtree_data: dict, upgrade_name: str, expected_requires: list) -> None:
        upgrades = techtree_data.get("Upgrades", {})
        upgrade = upgrades.get(upgrade_name, {})
        assert "requires" in upgrade, f"{upgrade_name} missing 'requires' field"
        assert upgrade["requires"] == expected_requires, (
            f"{upgrade_name}: expected {expected_requires}, got {upgrade['requires']}"
        )


class TestTwilightCouncilRequires:
    """Tests for upgrades that require TwilightCouncil + previous level."""

    @pytest.mark.parametrize("upgrade_name,expected_requires", TWILIGHT_COUNCIL_UPGRADES)
    def test_upgrade_requires(self, techtree_data: dict, upgrade_name: str, expected_requires: list) -> None:
        upgrades = techtree_data.get("Upgrades", {})
        upgrade = upgrades.get(upgrade_name, {})
        assert "requires" in upgrade, f"{upgrade_name} missing 'requires' field"
        assert upgrade["requires"] == expected_requires, (
            f"{upgrade_name}: expected {expected_requires}, got {upgrade['requires']}"
        )


class TestLairHiveRequires:
    """Tests for Zerg upgrades that require Lair/Hive + previous level."""

    @pytest.mark.parametrize(
        "upgrade_name,expected_requires",
        [
            # ZergFlyerArmors
            ("ZergFlyerArmorsLevel1", []),
            ("ZergFlyerArmorsLevel2", ["Lair", "ZergFlyerArmorsLevel1"]),
            ("ZergFlyerArmorsLevel3", ["Hive", "ZergFlyerArmorsLevel2"]),
            # ZergFlyerWeapons (same pattern)
            ("ZergFlyerWeaponsLevel1", []),
            ("ZergFlyerWeaponsLevel2", ["Lair", "ZergFlyerWeaponsLevel1"]),
            ("ZergFlyerWeaponsLevel3", ["Hive", "ZergFlyerWeaponsLevel2"]),
        ],
    )
    def test_upgrade_requires(self, techtree_data: dict, upgrade_name: str, expected_requires: list) -> None:
        upgrades = techtree_data.get("Upgrades", {})
        upgrade = upgrades.get(upgrade_name, {})
        assert "requires" in upgrade, f"{upgrade_name} missing 'requires' field"
        assert upgrade["requires"] == expected_requires, (
            f"{upgrade_name}: expected {expected_requires}, got {upgrade['requires']}"
        )


class TestFactoryUpgradesRequires:
    """Tests for Factory upgrades - some require Armory, some have no requirements."""

    @pytest.mark.parametrize(
        "upgrade_name,expected_requires",
        [
            ("CycloneLockOnDamageUpgrade", []),
            ("DrillClaws", ["Armory"]),
            ("HighCapacityBarrels", []),
            ("TransformationServos", ["Armory"]),
        ],
    )
    def test_upgrade_requires(self, techtree_data: dict, upgrade_name: str, expected_requires: list) -> None:
        upgrades = techtree_data.get("Upgrades", {})
        upgrade = upgrades.get(upgrade_name, {})
        assert "requires" in upgrade, f"{upgrade_name} missing 'requires' field"
        assert upgrade["requires"] == expected_requires, (
            f"{upgrade_name}: expected {expected_requires}, got {upgrade['requires']}"
        )


class TestStarportTechLabRequires:
    """Tests for StarportTechLab upgrades - no extra requirements."""

    @pytest.mark.parametrize(
        "upgrade_name,expected_requires",
        [
            ("BansheeCloak", []),
            ("BansheeSpeed", []),
            ("InterferenceMatrix", []),
        ],
    )
    def test_upgrade_requires(self, techtree_data: dict, upgrade_name: str, expected_requires: list) -> None:
        upgrades = techtree_data.get("Upgrades", {})
        upgrade = upgrades.get(upgrade_name, {})
        assert "requires" in upgrade, f"{upgrade_name} missing 'requires' field"
        assert upgrade["requires"] == expected_requires, (
            f"{upgrade_name}: expected {expected_requires}, got {upgrade['requires']}"
        )


class TestBarracksTechLabRequires:
    """Tests for BarracksTechLab upgrades - no extra requirements."""

    @pytest.mark.parametrize(
        "upgrade_name,expected_requires",
        [
            ("PunisherGrenades", []),
            ("ShieldWall", []),
            ("Stimpack", []),
        ],
    )
    def test_upgrade_requires(self, techtree_data: dict, upgrade_name: str, expected_requires: list) -> None:
        upgrades = techtree_data.get("Upgrades", {})
        upgrade = upgrades.get(upgrade_name, {})
        assert "requires" in upgrade, f"{upgrade_name} missing 'requires' field"
        assert upgrade["requires"] == expected_requires, (
            f"{upgrade_name}: expected {expected_requires}, got {upgrade['requires']}"
        )


class TestFusionCoreRequires:
    """Tests for FusionCore upgrades - no extra requirements."""

    @pytest.mark.parametrize(
        "upgrade_name,expected_requires",
        [
            ("BattlecruiserEnableSpecializations", []),
            ("LiberatorAGRangeUpgrade", []),
            ("MedivacCaduceusReactor", []),
        ],
    )
    def test_upgrade_requires(self, techtree_data: dict, upgrade_name: str, expected_requires: list) -> None:
        upgrades = techtree_data.get("Upgrades", {})
        upgrade = upgrades.get(upgrade_name, {})
        assert "requires" in upgrade, f"{upgrade_name} missing 'requires' field"
        assert upgrade["requires"] == expected_requires, (
            f"{upgrade_name}: expected {expected_requires}, got {upgrade['requires']}"
        )


class TestCyberneticsCoreRequires:
    """Tests for CyberneticsCore upgrades - no extra requirements."""

    @pytest.mark.parametrize(
        "upgrade_name,expected_requires",
        [
            ("WarpGateResearch", []),
        ],
    )
    def test_upgrade_requires(self, techtree_data: dict, upgrade_name: str, expected_requires: list) -> None:
        upgrades = techtree_data.get("Upgrades", {})
        upgrade = upgrades.get(upgrade_name, {})
        assert "requires" in upgrade, f"{upgrade_name} missing 'requires' field"
        assert upgrade["requires"] == expected_requires, (
            f"{upgrade_name}: expected {expected_requires}, got {upgrade['requires']}"
        )


class TestTwilightCouncilNoRequires:
    """Tests for TwilightCouncil upgrades with no requirements."""

    @pytest.mark.parametrize(
        "upgrade_name,expected_requires",
        [
            ("AdeptPiercingAttack", []),
            ("BlinkTech", []),
            ("Charge", []),
        ],
    )
    def test_upgrade_requires(self, techtree_data: dict, upgrade_name: str, expected_requires: list) -> None:
        upgrades = techtree_data.get("Upgrades", {})
        upgrade = upgrades.get(upgrade_name, {})
        assert "requires" in upgrade, f"{upgrade_name} missing 'requires' field"
        assert upgrade["requires"] == expected_requires, (
            f"{upgrade_name}: expected {expected_requires}, got {upgrade['requires']}"
        )


class TestRoboticsBayNoRequires:
    """Tests for RoboticsBay upgrades with no requirements."""

    @pytest.mark.parametrize(
        "upgrade_name,expected_requires",
        [
            ("ExtendedThermalLance", []),
            ("GraviticDrive", []),
            ("ObserverGraviticBooster", []),
        ],
    )
    def test_upgrade_requires(self, techtree_data: dict, upgrade_name: str, expected_requires: list) -> None:
        upgrades = techtree_data.get("Upgrades", {})
        upgrade = upgrades.get(upgrade_name, {})
        assert "requires" in upgrade, f"{upgrade_name} missing 'requires' field"
        assert upgrade["requires"] == expected_requires, (
            f"{upgrade_name}: expected {expected_requires}, got {upgrade['requires']}"
        )


class TestFleetBeaconNoRequires:
    """Tests for FleetBeacon upgrades with no requirements."""

    @pytest.mark.parametrize(
        "upgrade_name,expected_requires",
        [
            ("PhoenixRangeUpgrade", []),
            ("TempestGroundAttackUpgrade", []),
            ("VoidRaySpeedUpgrade", []),
        ],
    )
    def test_upgrade_requires(self, techtree_data: dict, upgrade_name: str, expected_requires: list) -> None:
        upgrades = techtree_data.get("Upgrades", {})
        upgrade = upgrades.get(upgrade_name, {})
        assert "requires" in upgrade, f"{upgrade_name} missing 'requires' field"
        assert upgrade["requires"] == expected_requires, (
            f"{upgrade_name}: expected {expected_requires}, got {upgrade['requires']}"
        )


class TestDarkShrineRequires:
    """Tests for DarkShrine upgrades with no requirements."""

    @pytest.mark.parametrize(
        "upgrade_name,expected_requires",
        [
            ("DarkTemplarBlinkUpgrade", []),
        ],
    )
    def test_upgrade_requires(self, techtree_data: dict, upgrade_name: str, expected_requires: list) -> None:
        upgrades = techtree_data.get("Upgrades", {})
        upgrade = upgrades.get(upgrade_name, {})
        assert "requires" in upgrade, f"{upgrade_name} missing 'requires' field"
        assert upgrade["requires"] == expected_requires, (
            f"{upgrade_name}: expected {expected_requires}, got {upgrade['requires']}"
        )


class TestBanelingNestRequires:
    """Tests for BanelingNest upgrades."""

    @pytest.mark.parametrize(
        "upgrade_name,expected_requires",
        [
            # CentrificalHooks requires Lair (or Hive)
            ("CentrificalHooks", ["Lair"]),
        ],
    )
    def test_upgrade_requires(self, techtree_data: dict, upgrade_name: str, expected_requires: list) -> None:
        upgrades = techtree_data.get("Upgrades", {})
        upgrade = upgrades.get(upgrade_name, {})
        assert "requires" in upgrade, f"{upgrade_name} missing 'requires' field"
        assert upgrade["requires"] == expected_requires, (
            f"{upgrade_name}: expected {expected_requires}, got {upgrade['requires']}"
        )


class TestSpawningPoolRequires:
    """Tests for SpawningPool upgrades."""

    @pytest.mark.parametrize(
        "upgrade_name,expected_requires",
        [
            # zerglingmovementspeed (Metabolic Boost) - no requirements
            ("zerglingmovementspeed", []),
            # zerglingattackspeed (Adrenal Glands) - requires Hive
            ("zerglingattackspeed", ["Hive"]),
        ],
    )
    def test_upgrade_requires(self, techtree_data: dict, upgrade_name: str, expected_requires: list) -> None:
        upgrades = techtree_data.get("Upgrades", {})
        upgrade = upgrades.get(upgrade_name, {})
        assert "requires" in upgrade, f"{upgrade_name} missing 'requires' field"
        assert upgrade["requires"] == expected_requires, (
            f"{upgrade_name}: expected {expected_requires}, got {upgrade['requires']}"
        )


class TestHatcheryRequires:
    """Tests for Hatchery/Lair/Hive upgrades with no requirements."""

    @pytest.mark.parametrize(
        "upgrade_name,expected_requires",
        [
            ("Burrow", []),
            ("overlordspeed", []),
        ],
    )
    def test_upgrade_requires(self, techtree_data: dict, upgrade_name: str, expected_requires: list) -> None:
        upgrades = techtree_data.get("Upgrades", {})
        upgrade = upgrades.get(upgrade_name, {})
        assert "requires" in upgrade, f"{upgrade_name} missing 'requires' field"
        assert upgrade["requires"] == expected_requires, (
            f"{upgrade_name}: expected {expected_requires}, got {upgrade['requires']}"
        )


class TestRoachWarrenRequires:
    """Tests for RoachWarren upgrades requiring Lair."""

    @pytest.mark.parametrize(
        "upgrade_name,expected_requires",
        [
            ("GlialReconstitution", ["Lair"]),
            ("TunnelingClaws", ["Lair"]),
        ],
    )
    def test_upgrade_requires(self, techtree_data: dict, upgrade_name: str, expected_requires: list) -> None:
        upgrades = techtree_data.get("Upgrades", {})
        upgrade = upgrades.get(upgrade_name, {})
        assert "requires" in upgrade, f"{upgrade_name} missing 'requires' field"
        assert upgrade["requires"] == expected_requires, (
            f"{upgrade_name}: expected {expected_requires}, got {upgrade['requires']}"
        )


class TestHydraliskDenRequires:
    """Tests for HydraliskDen upgrades."""

    @pytest.mark.parametrize(
        "upgrade_name,expected_requires",
        [
            # EvolveGroovedSpines, EvolveMuscularAugments - no requirements
            ("EvolveGroovedSpines", []),
            ("EvolveMuscularAugments", []),
            # Frenzy - requires Hive
            ("Frenzy", ["Hive"]),
        ],
    )
    def test_upgrade_requires(self, techtree_data: dict, upgrade_name: str, expected_requires: list) -> None:
        upgrades = techtree_data.get("Upgrades", {})
        upgrade = upgrades.get(upgrade_name, {})
        assert "requires" in upgrade, f"{upgrade_name} missing 'requires' field"
        assert upgrade["requires"] == expected_requires, (
            f"{upgrade_name}: expected {expected_requires}, got {upgrade['requires']}"
        )


class TestLurkerDenMPRequires:
    """Tests for LurkerDenMP upgrades requiring Hive."""

    @pytest.mark.parametrize(
        "upgrade_name,expected_requires",
        [
            ("DiggingClaws", ["Hive"]),
            ("LurkerRange", ["Hive"]),
        ],
    )
    def test_upgrade_requires(self, techtree_data: dict, upgrade_name: str, expected_requires: list) -> None:
        upgrades = techtree_data.get("Upgrades", {})
        upgrade = upgrades.get(upgrade_name, {})
        assert "requires" in upgrade, f"{upgrade_name} missing 'requires' field"
        assert upgrade["requires"] == expected_requires, (
            f"{upgrade_name}: expected {expected_requires}, got {upgrade['requires']}"
        )


class TestUltraliskCavernRequires:
    """Tests for UltraliskCavern upgrades with no requirements."""

    @pytest.mark.parametrize(
        "upgrade_name,expected_requires",
        [
            ("AnabolicSynthesis", []),
            ("ChitinousPlating", []),
        ],
    )
    def test_upgrade_requires(self, techtree_data: dict, upgrade_name: str, expected_requires: list) -> None:
        upgrades = techtree_data.get("Upgrades", {})
        upgrade = upgrades.get(upgrade_name, {})
        assert "requires" in upgrade, f"{upgrade_name} missing 'requires' field"
        assert upgrade["requires"] == expected_requires, (
            f"{upgrade_name}: expected {expected_requires}, got {upgrade['requires']}"
        )
