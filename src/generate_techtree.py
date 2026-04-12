#!/usr/bin/env python3
"""
Generate StarCraft 2 techtree.json from converted JSON data files.

Usage: uv run generate_techtree.py
"""

import json
from pathlib import Path
from typing import Any

from utils import dumps_json

RACE_MAP = {
    "Terr": "Terran",
    "Zerg": "Zerg",
    "Prot": "Protoss",
}

# Mapping of units to their correct requirements when game data is inconsistent
UNIT_REQUIREMENT_FIXES = {
    "Roach": ["RoachWarren"],
}

# Units to exclude from morph targets (cocoons)
MORPH_EXCLUDE = {
    "Cocoon",
    "CocoonZergling",
    "CocoonRoach",
    "CocoonBaneling",
    "BanelingCocoon",
    "RoachCocoon",
    "ZerglingCocoon",
    "BroodLordCocoon",
}

# Research upgrades to exclude (they're not direct research abilities for this structure)
RESEARCH_EXCLUDE = {
    # TemplarArchive - HighTemplarKhaydarinAmulet is from TemplarArchivesResearch but not TemplarArchive's research
    "HighTemplarKhaydarinAmulet",
    # CyberneticsCore - haltech is not a research
    "haltech",
    # EngineeringBay - TerranBuildingArmor is not an Engineering Bay research
    "TerranBuildingArmor",
    # UltraliskCavern - UltraliskBurrowChargeUpgrade is not an Ultralisk Cavern research
    "UltraliskBurrowChargeUpgrade",
    # RoboticsBay - ImmortalRevive is not a Robotics Bay research
    "ImmortalRevive",
    # TwilightCouncil - these are not Twilight Council researches
    "SunderingImpact",
    "AmplifiedShielding",
    # Note: AdeptShieldUpgrade is mapped to AdeptPiercingAttack via RESEARCH_NAME_MAP
    # RoachWarren - RoachSupply is not a research
    "RoachSupply",
    # Lair/Hive/GreaterSpire - Burrow, overlord upgrades are from LairResearch
    "Burrow",
    "overlordspeed",
    "overlordtransport",
    # InfestationPit - extra researches from other sources
    "FlyingLocusts",
    "InfestorEnergyUpgrade",
    "LocustLifetimeIncrease",
    # FleetBeacon - extra researches from other sources
    "CarrierLaunchSpeedUpgrade",
    "TempestRangeUpgrade",
    # GhostAcademy - extra researches from MercCompoundResearch
    "EnhancedShockwaves",
    "GhostMoebiusReactor",
    "ReaperSpeed",
}

# Structure-specific research excludes (overrides general RESEARCH_EXCLUDE)
# Key: structure name, Value: set of upgrade names to exclude for that structure
STRUCTURE_RESEARCH_EXCLUDE = {
    "BarracksTechLab": {
        "CombatDrugs",
    },
    "FactoryTechLab": {
        "ArmorPiercingRockets",
        "CycloneAirUpgrade",
        "CycloneLockOnRangeUpgrade",
        "CycloneRapidFireLaunchers",
        "HurricaneThrusters",
        "SiegeTech",
        "StrikeCannons",
    },
    "StarportTechLab": {
        "DurableMaterials",
        "HunterSeeker",
        "LiberatorAGRangeUpgrade",
        "LiberatorMorph",
        "MedivacCaduceusReactor",
        "MedivacRapidDeployment",
        "MedivacIncreaseSpeedBoost",
        "RavenCorvidReactor",
        "RavenEnhancedMunitions",
        "RavenRecalibratedExplosives",
    },
    "FusionCore": {
        "MedivacIncreaseSpeedBoost",
    },
    "HydraliskDen": {
        "HydraliskSpeedUpgrade",
        "LurkerRange",
        "hydraliskspeed",
    },
}

# Additional researches to add (hard-coded for structures where data is missing)
# Key: structure name, Value: list of upgrade names to add
STRUCTURE_ADDITIONAL_RESEARCHES = {
    "FusionCore": ["LiberatorAGRangeUpgrade"],
    "HydraliskDen": ["Frenzy"],
    "InfestationPit": ["MicrobialShroud"],
}

# Requirement name fixes (maps incorrect names to correct ones)
REQUIREMENT_NAME_FIXES = {
    "RoboticsFa": "RoboticsFacility",
}
# Map research upgrade names to canonical names
RESEARCH_NAME_MAP = {
    "AdeptShieldUpgrade": "AdeptPiercingAttack",
    "LurkerRangeMP": "LurkerRange",
    "BattlecruiserBehemothReactor": "BattlecruiserEnableSpecializations",
}

# Additional structures that should be included (tech labs)
TECH_LABS = {
    "BarracksTechLab",
    "FactoryTechLab",
    "StarportTechLab",
}

# Ability to structure mapping for shared abilities
# Key: ability name, Value: structure prefix it belongs to
ABILITY_STRUCTURE_MAP = {
    # Train abilities
    "GatewayTrain": "Gateway",
    "WarpGateTrain": "WarpGate",
    "BarracksTrain": "Barracks",
    "FactoryTrain": "Factory",
    "StarportTrain": "Starport",
    "SpireTrain": "Spire",
    "CommandCenterTrain": ["CommandCenter", "OrbitalCommand", "PlanetaryFortress"],
    # Research abilities where structure name doesn't match ability prefix
    "SpireResearch": "GreaterSpire",  # GreaterSpire gets SpireResearch
    "LurkerDenResearch": "LurkerDenMP",  # LurkerDenMP gets LurkerDenResearch
}

# Research abilities shared between multiple structures
# Key: ability name, Value: set of structures that should NOT get this research
SHARED_RESEARCH_EXCLUDE = {
    "LairResearch": {"GreaterSpire"},  # GreaterSpire should NOT get LairResearch upgrades
    "HydraliskDenResearch": {"LurkerDenMP"},  # LurkerDenMP should NOT get HydraliskDenResearch upgrades
    "MercCompoundResearch": {"BarracksTechLab", "GhostAcademy"},  # These get Merc upgrades elsewhere
}


def load_json(filename: str) -> dict:
    """Load a JSON data file."""
    path = Path(__file__).parent / "json" / filename
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def parse_requirement(req: str) -> list[str]:
    """Parse a requirement string into structure names.

    Examples:
        'HaveBarracks' -> ['Barracks']
        'HaveArmoryAndAttachedTechLab' -> ['Armory', 'AttachedTechLab']
        'HaveRoboticsBay' -> ['RoboticsBay']
    """
    if not req:
        return []

    parts = req.split("And")
    result = []
    for part in parts:
        if part.startswith("Have"):
            name = part[4:]  # Remove 'Have' prefix
            # Apply requirement name fixes
            name = REQUIREMENT_NAME_FIXES.get(name, name)
            result.append(name)
        elif part.startswith("Learn"):
            # Skip LearnX requirements - these are prerequisite unlocks
            pass
        else:
            result.append(part)
    return result


def get_info_units(info: Any) -> list[str]:
    """Extract unit names from InfoArray entries (handles both list and dict)."""
    units = []
    if isinstance(info, list):
        for item in info:
            if isinstance(item, dict) and "Unit" in item:
                unit = item["Unit"]
                if isinstance(unit, list):
                    units.extend(u for u in unit if u and u != "N/A")
                elif unit and unit != "N/A":
                    units.append(unit)
    elif isinstance(info, dict) and "Unit" in info:
        unit = info["Unit"]
        if isinstance(unit, list):
            units.extend(u for u in unit if u and u != "N/A")
        elif unit and unit != "N/A":
            units.append(unit)
    return units


def get_info_upgrades(info: Any) -> list[str]:
    """Extract upgrade names from InfoArray entries (only if has DefaultButtonFace)."""
    upgrades = []
    if isinstance(info, list):
        for item in info:
            if isinstance(item, dict):
                btn = item.get("Button", {})
                if isinstance(btn, dict) and btn.get("DefaultButtonFace"):
                    upgrade = item.get("Upgrade")
                    if upgrade and upgrade not in RESEARCH_EXCLUDE:
                        mapped = RESEARCH_NAME_MAP.get(upgrade, upgrade)
                        upgrades.append(mapped)
    elif isinstance(info, dict):
        btn = info.get("Button", {})
        if isinstance(btn, dict) and btn.get("DefaultButtonFace"):
            upgrade = info.get("Upgrade")
            if upgrade and upgrade not in RESEARCH_EXCLUDE:
                mapped = RESEARCH_NAME_MAP.get(upgrade, upgrade)
                upgrades.append(mapped)
    return upgrades


def get_morph_targets(info: Any) -> list[str]:
    """Extract morph target units from InfoArray (excluding cocoons)."""
    targets = []
    if isinstance(info, list):
        for item in info:
            if isinstance(item, dict) and "Unit" in item:
                unit = item["Unit"]
                if isinstance(unit, list):
                    targets.extend(u for u in unit if u and u not in MORPH_EXCLUDE)
                elif unit and unit not in MORPH_EXCLUDE:
                    targets.append(unit)
    elif isinstance(info, dict) and "Unit" in info:
        unit = info["Unit"]
        if isinstance(unit, list):
            targets.extend(u for u in unit if u and u not in MORPH_EXCLUDE)
        elif unit and unit not in MORPH_EXCLUDE:
            targets.append(unit)
    return targets


def get_lift_off_target(abil_data: Any) -> str | None:
    """Extract the unit a LiftOff ability transforms into from the 'unit' field."""
    if isinstance(abil_data, dict):
        return abil_data.get("unit")
    return None


def get_requirement_from_button(item: dict) -> str:
    """Extract requirement from a button entry in InfoArray."""
    btn = item.get("Button", {})
    if isinstance(btn, dict):
        return btn.get("Requirements", "")
    return ""


def is_structure(data: dict) -> bool:
    """Check if a unit is a structure."""
    if isinstance(data, dict):
        editor_categories = data.get("EditorCategories", "")
        if isinstance(editor_categories, list):
            return "ObjectType:Structure" in editor_categories
        return "ObjectType:Structure" in str(editor_categories)
    return False


def is_campaign_unit(data: dict) -> bool:
    """Check if a unit is from Campaign (should be excluded)."""
    if isinstance(data, dict):
        editor_categories = data.get("EditorCategories", "")
        if isinstance(editor_categories, list):
            return "ObjectFamily:Campaign" in editor_categories
        return "ObjectFamily:Campaign" in str(editor_categories)
    return False


def get_race(data: dict) -> str:
    """Get the race of a unit/structure."""
    if isinstance(data, dict):
        race = data.get("Race", "")
        return RACE_MAP.get(race, race)
    return ""


def ability_matches_structure(abil_name: str, structure_name: str) -> bool:
    """Check if an ability name matches a structure name (handles shared abilities)."""
    # Direct match (ability name starts with structure name)
    if abil_name.startswith(structure_name):
        return True
    # Check shared ability mapping
    expected = ABILITY_STRUCTURE_MAP.get(abil_name)
    if expected:
        if isinstance(expected, list):
            return structure_name in expected
        return structure_name.startswith(expected)
    return False


def research_matches_structure(abil_name: str, structure_name: str) -> bool:
    """Check if a research ability matches a structure."""
    # Direct match (ability name starts with structure name)
    if abil_name.startswith(structure_name):
        return True
    # Check shared ability mapping
    expected_prefix = ABILITY_STRUCTURE_MAP.get(abil_name)
    if expected_prefix:
        if isinstance(expected_prefix, list):
            return structure_name in expected_prefix
        return structure_name.startswith(expected_prefix)
    # Check if this is a shared research that should be excluded for this structure
    if abil_name in SHARED_RESEARCH_EXCLUDE:
        excluded_structures = SHARED_RESEARCH_EXCLUDE[abil_name]
        if structure_name in excluded_structures:
            return False
    return False


def generate_techtree() -> dict:
    """Generate the techtree structure from JSON data files."""
    units_data = load_json("UnitData.json")
    abils_data = load_json("AbilData.json")

    structures: dict[str, dict] = {}
    units: dict[str, dict] = {}
    abilities: dict[str, dict] = {}

    # Build index of which ability produces which units and what requirements they have
    ability_produces: dict[str, list[tuple[str, str]]] = {}
    ability_upgrades: dict[str, list[str]] = {}

    for abil_name, abil_data in abils_data.items():
        if not isinstance(abil_data, dict):
            continue
        info = abil_data.get("InfoArray")
        if not info:
            continue

        if isinstance(info, list):
            for item in info:
                if isinstance(item, dict):
                    produced_units = get_info_units(item)
                    req = get_requirement_from_button(item)
                    for unit in produced_units:
                        ability_produces.setdefault(abil_name, []).append((unit, req))
                    if abil_name.endswith("Research"):
                        upgrades = get_info_upgrades(item)
                        for upgrade in upgrades:
                            ability_upgrades.setdefault(abil_name, []).append(upgrade)
        elif isinstance(info, dict):
            produced_units = get_info_units(info)
            req = get_requirement_from_button(info)
            for unit in produced_units:
                ability_produces.setdefault(abil_name, []).append((unit, req))

    # Build unlocks mapping: structure -> list of structures/units it unlocks
    unlocks: dict[str, set[str]] = {}
    unit_requirements: dict[str, list[str]] = {}

    for abil_name, prod_list in ability_produces.items():
        for produced_unit, req in prod_list:
            if req:
                req_structs = parse_requirement(req)
                for req_struct in req_structs:
                    if req_struct in units_data:
                        unlocks.setdefault(req_struct, set()).add(produced_unit)
                    # Track requirements for the unit (apply fixes if needed)
                    if produced_unit in UNIT_REQUIREMENT_FIXES:
                        unit_requirements.setdefault(produced_unit, []).extend(UNIT_REQUIREMENT_FIXES[produced_unit])
                    else:
                        unit_requirements.setdefault(produced_unit, []).append(req_struct)

    # Collect produces, builds, researches, morphsto for each structure/unit
    for unit_name, unit_data in units_data.items():
        if not isinstance(unit_data, dict):
            continue

        race = get_race(unit_data)
        entry: dict[str, Any] = {"race": race}

        produces: list[str] = []
        builds: list[str] = []
        researches: list[str] = []
        morphsto: str | list[str] | None = None

        # Get structure-specific excludes and additional researches
        excludes = STRUCTURE_RESEARCH_EXCLUDE.get(unit_name, set())
        additional = STRUCTURE_ADDITIONAL_RESEARCHES.get(unit_name, [])

        for abil_name in unit_data.get("AbilArray", []):
            if not isinstance(abil_name, str):
                continue

            if abil_name in ability_produces:
                for produced_unit, req in ability_produces[abil_name]:
                    is_train = (
                        abil_name.endswith("Train") or abil_name.startswith("NexusTrain")
                    ) and abil_name not in ["SCVHarvest", "NexusTrainMothershipCore"]
                    is_build = abil_name.endswith("Build")
                    is_research = abil_name.endswith("Research")

                    if is_train:
                        # Check if this unit's ability matches the structure name
                        if ability_matches_structure(abil_name, unit_name):
                            # Exclude campaign units like WarHound
                            if not is_campaign_unit(units_data.get(produced_unit, {})):
                                produces.append(produced_unit)
                    elif is_build:
                        # Exclude mercenary buildings (Race=NOT_FOUND or N/A) and campaign units
                        if produced_unit in units_data:
                            prod_data = units_data[produced_unit]
                            prod_race = prod_data.get("Race", "")
                            if (
                                prod_race
                                and prod_race not in ("N/A", "NOT_FOUND", "")
                                and not is_campaign_unit(prod_data)
                            ):
                                builds.append(produced_unit)
                        else:
                            builds.append(produced_unit)
                    elif is_research:
                        # Only add research if it matches the structure
                        if research_matches_structure(abil_name, unit_name):
                            if produced_unit not in excludes:
                                researches.append(produced_unit)

            if abil_name in ability_upgrades:
                # Only add upgrades if the ability matches the structure
                if research_matches_structure(abil_name, unit_name):
                    for upgrade in ability_upgrades[abil_name]:
                        if upgrade not in excludes:
                            researches.append(upgrade)

            # Handle morphsto for units with MorphTo, MorphZergling, UpgradeTo, or LiftOff abilities
            is_morph_to = (
                abil_name.startswith("MorphTo") or abil_name.startswith("MorphZergling")
            ) and abil_name != "MorphToBaneling"
            is_upgrade_to = abil_name.startswith("UpgradeTo")
            is_lift_off = abil_name.endswith("LiftOff")

            if (is_morph_to or is_upgrade_to) and unit_name in units_data:
                abil = abils_data.get(abil_name)
                if isinstance(abil, dict):
                    info = abil.get("InfoArray")
                    if info:
                        targets = get_morph_targets(info)
                        if targets:
                            if morphsto is None:
                                morphsto = targets
                            elif isinstance(morphsto, list):
                                morphsto.extend(targets)

            # Handle LiftOff abilities - get target from 'unit' field
            if is_lift_off:
                abil = abils_data.get(abil_name)
                if isinstance(abil, dict):
                    target = get_lift_off_target(abil)
                    if target:
                        if morphsto is None:
                            morphsto = [target]
                        elif isinstance(morphsto, list):
                            morphsto.append(target)
                        else:
                            morphsto = [morphsto, target]

        if produces:
            entry["produces"] = sorted(set(produces))
        if builds:
            entry["builds"] = sorted(set(builds))
        if researches or additional:
            # Add additional researches (for structures where data is incomplete)
            all_researches = list(researches) + [r for r in additional if r not in researches]
            entry["researches"] = sorted(set(all_researches))
        if unlocks.get(unit_name):
            entry["unlocks"] = sorted(unlocks[unit_name])
        if morphsto:
            if isinstance(morphsto, list):
                unique_targets = sorted(set(morphsto))
                entry["morphsto"] = unique_targets[0] if len(unique_targets) == 1 else unique_targets
            else:
                entry["morphsto"] = morphsto
        if unit_name in unit_requirements:
            entry["requires"] = sorted(set(unit_requirements[unit_name]))

        # For Larva, morphsto should equal its produces
        if unit_name == "Larva" and "produces" in entry:
            entry["morphsto"] = entry["produces"]

        # Separate structures and units
        # Tech labs are structures even without ObjectType:Structure
        if is_structure(unit_data) or unit_name in TECH_LABS:
            structures[unit_name] = entry
        else:
            units[unit_name] = entry

    # Process abilities for MorphTo, UpgradeTo, and LiftOff abilities
    for abil_name, abil_data in abils_data.items():
        if not isinstance(abil_data, dict):
            continue

        is_morph_to = abil_name.startswith("MorphTo") and not abil_name.startswith("MorphZergling")
        is_upgrade_to = abil_name.startswith("UpgradeTo")
        is_lift_off = abil_name.endswith("LiftOff")

        if is_morph_to or is_upgrade_to:
            info = abil_data.get("InfoArray")
            if info:
                targets = get_morph_targets(info)
                if targets:
                    morph_target = targets[0] if len(targets) == 1 else targets

                    race = ""
                    if isinstance(morph_target, str) and morph_target in units_data:
                        race = get_race(units_data[morph_target])

                    requires = []
                    cmd_buttons = abil_data.get("CmdButtonArray", [])
                    if isinstance(cmd_buttons, list):
                        for btn in cmd_buttons:
                            if isinstance(btn, dict) and btn.get("index") == "Execute":
                                req = btn.get("Requirements", "")
                                if req:
                                    requires.extend(parse_requirement(req))

                    abilities[abil_name] = {
                        "morphsto": morph_target,
                        "race": race,
                    }
                    if requires:
                        abilities[abil_name]["requires"] = sorted(set(requires))

        elif is_lift_off:
            target = get_lift_off_target(abil_data)
            if target:
                race = ""
                if target in units_data:
                    race = get_race(units_data[target])
                abilities[abil_name] = {
                    "morphsto": target,
                    "race": race,
                }

    return {
        "structures": structures,
        "units": units,
        "abilities": abilities,
    }


def main():
    """Main entry point."""
    output_path = Path(__file__).parent / "json" / "techtree.json"

    print("Generating techtree...")
    techtree = generate_techtree()

    output_path.write_text(dumps_json(techtree, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    print(f"Written to {output_path}")
    print(f"  Structures: {len(techtree['structures'])}")
    print(f"  Units: {len(techtree['units'])}")
    print(f"  Abilities: {len(techtree['abilities'])}")


if __name__ == "__main__":
    main()
