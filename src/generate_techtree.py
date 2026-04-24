#!/usr/bin/env python3
"""
Generate StarCraft 2 techtree.json from converted JSON data files.

Usage: uv run generate_techtree.py
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from utils import dumps_json

# === Magic Strings ===
EDITOR_CAT_STRUCTURE = "ObjectType:Structure"
EDITOR_CAT_CAMPAIGN = "ObjectFamily:Campaign"
RACE_NA = "N/A"
RACE_NOT_FOUND = "NOT_FOUND"
BUTTON_INDEX_EXECUTE = "Execute"
ABILITY_SCV_HARVEST = "SCVHarvest"
ABILITY_NEXUS_TRAIN_MOTHERSHIP_CORE = "NexusTrainMothershipCore"

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

# Ability name to exclude from morphsto handling
MORPH_BANELING_EXCLUDE = "MorphToBaneling"

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

# Research abilities shared between multiple structures
# Key: ability name, Value: set of structures that should NOT get this research
SHARED_RESEARCH_EXCLUDE = {
    "LairResearch": {"GreaterSpire"},  # GreaterSpire should NOT get LairResearch upgrades
    "HydraliskDenResearch": {"LurkerDenMP"},  # LurkerDenMP should NOT get HydraliskDenResearch upgrades
    "MercCompoundResearch": {"BarracksTechLab", "GhostAcademy"},  # These get Merc upgrades elsewhere
}

# Global research exclusions - items that appear in game data but aren't actual researches
RESEARCH_EXCLUDE = {
    "haltech",  # not a research (CyberneticsCore)
    "TerranBuildingArmor",  # not EngineeringBay research
    "ImmortalRevive",  # not RoboticsBay research
    "RoachSupply",  # not RoachWarren research
    "LocustLifetimeIncrease",  # not InfestationPit research
    "FlyingLocusts",  # not InfestationPit research
    "InfestorEnergyUpgrade",  # not InfestationPit research
    "CarrierLaunchSpeedUpgrade",  # not FleetBeacon research
    "TempestRangeUpgrade",  # not FleetBeacon research
    "SunderingImpact",  # not TwilightCouncil research
    "AmplifiedShielding",  # not TwilightCouncil research
}

# Per-structure research exclusions (structure gets research ability but shouldn't get these upgrades)
STRUCTURE_RESEARCH_EXCLUDE = {
    "BarracksTechLab": {"CombatDrugs", "ReaperSpeed"},
    "GhostAcademy": {"ReaperSpeed"},
    "FactoryTechLab": {
        "ArmorPiercingRockets",
        "CycloneAirUpgrade",
        "CycloneLockOnRangeUpgrade",
        "CycloneRapidFireLaunchers",
        "HurricaneThrusters",
        "SiegeTech",
        "SmartServos",
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
    "FusionCore": {"MedivacIncreaseSpeedBoost"},
    "HydraliskDen": {"HydraliskSpeedUpgrade", "LurkerRange", "hydraliskspeed"},
    "TwilightCouncil": {"PsionicAmplifiers"},
}

# Additional researches for structures where game data is incomplete
STRUCTURE_ADDITIONAL_RESEARCHES = {
    "FusionCore": ["LiberatorAGRangeUpgrade"],
    "HydraliskDen": ["Frenzy"],
    "InfestationPit": ["MicrobialShroud"],
    "EngineeringBay": ["HiSecAutoTracking"],
}


def load_json(filename: str) -> dict:
    """Load a JSON data file and transform to expected format."""
    path = Path(__file__).parent / "json" / filename
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    # Transform UnitData.json: extract CUnit array and index by id
    if filename == "UnitData.json" and "CUnit" in data:
        return {unit["id"]: unit for unit in data["CUnit"]}

    # Transform AbilData.json: flatten all class arrays into single dict keyed by id
    if filename == "AbilData.json":
        result = {}
        for class_name, abilities in data.items():
            if isinstance(abilities, list):
                for ability in abilities:
                    if isinstance(ability, dict) and "id" in ability:
                        result[ability["id"]] = ability
        return result

    return data


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


def _extract_units_from_info(info: Any, exclude_set: set | None = None) -> list[str]:
    """Extract unit names from InfoArray entries (handles both list and dict)."""
    targets = []
    items = info if isinstance(info, list) else [info]
    for item in items:
        if isinstance(item, dict) and "Unit" in item:
            unit = item["Unit"]
            if isinstance(unit, list):
                targets.extend(u for u in unit if u and u != "N/A")
            elif isinstance(unit, dict) and "value" in unit:
                val = unit["value"]
                if val and val != "N/A":
                    targets.append(val)
            elif unit and unit != "N/A":
                targets.append(unit)
    if exclude_set:
        targets = [t for t in targets if t not in exclude_set]
    return targets


def get_info_units(info: Any) -> list[str]:
    """Extract unit names from InfoArray entries (handles both list and dict)."""
    return _extract_units_from_info(info)


def get_info_upgrades(info: Any) -> list[str]:
    """Extract upgrade names from InfoArray entries (only if has DefaultButtonFace)."""
    upgrades = []
    if isinstance(info, list):
        for item in info:
            if isinstance(item, dict):
                btn = item.get("Button", {})
                if isinstance(btn, dict) and btn.get("DefaultButtonFace"):
                    upgrade = item.get("Upgrade")
                    if upgrade:
                        mapped = RESEARCH_NAME_MAP.get(upgrade, upgrade)
                        upgrades.append(mapped)
    elif isinstance(info, dict):
        btn = info.get("Button", {})
        if isinstance(btn, dict) and btn.get("DefaultButtonFace"):
            upgrade = info.get("Upgrade")
            if upgrade:
                mapped = RESEARCH_NAME_MAP.get(upgrade, upgrade)
                upgrades.append(mapped)
    return upgrades


def get_morph_targets(info: Any) -> list[str]:
    """Extract morph target units from InfoArray (excluding cocoons)."""
    return _extract_units_from_info(info, exclude_set=MORPH_EXCLUDE)


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
            return EDITOR_CAT_STRUCTURE in editor_categories
        return EDITOR_CAT_STRUCTURE in str(editor_categories)
    return False


def is_campaign_unit(data: dict) -> bool:
    """Check if a unit is from Campaign (should be excluded)."""
    if isinstance(data, dict):
        editor_categories = data.get("EditorCategories", "")
        if isinstance(editor_categories, list):
            return EDITOR_CAT_CAMPAIGN in editor_categories
        return EDITOR_CAT_CAMPAIGN in str(editor_categories)
    return False


def get_race(data: dict) -> str:
    """Get the race of a unit/structure."""
    if isinstance(data, dict):
        race = data.get("Race", "")
        if isinstance(race, list):
            race = race[0] if race else ""
        return RACE_MAP.get(race, race)
    return ""


def _match_ability_to_structure(
    abil_name: str,
    structure_name: str,
    ability_to_structures: dict[str, set[str]],
    check_shared_exclude: bool = False,
    require_prefix_match: bool = False,
) -> bool:
    """Check if an ability name matches a structure name (using derived mapping)."""
    # Check shared research excludes FIRST if enabled - this must be before direct mapping check
    if (
        check_shared_exclude
        and abil_name in SHARED_RESEARCH_EXCLUDE
        and structure_name in SHARED_RESEARCH_EXCLUDE[abil_name]
    ):
        return False
    # Check the derived mapping
    if abil_name in ability_to_structures:
        in_mapping = structure_name in ability_to_structures[abil_name]
        if in_mapping:
            if not require_prefix_match:
                return True
            # With require_prefix_match for train abilities:
            # Allow if this structure's name IS a prefix of ability
            if abil_name.startswith(structure_name):
                return True
            # Block only the specific bad case: Gateway-prefix ability being used
            # by a non-Gateway structure (e.g., GatewayTrain with RoboticsFacility)
            if abil_name.startswith("Gateway"):
                for other_struct in ability_to_structures[abil_name]:
                    other_is_prefix = abil_name.startswith(other_struct)
                    curr_is_prefix = abil_name.startswith(structure_name)
                    if other_struct != structure_name and other_is_prefix and not curr_is_prefix:
                        return False
            return True
    # Fallback: check if structure_name is a prefix of ability (for "XxxBuild" style)
    return bool(abil_name.startswith(structure_name))


def _build_ability_to_structures_mapping(units_data: dict) -> dict[str, set[str]]:
    """Build a mapping of which structures can use which abilities."""
    ability_to_structures = defaultdict(set)

    for unit_name, unit_data in units_data.items():
        if not isinstance(unit_data, dict):
            continue
        for abil_entry in unit_data.get("AbilArray", []):
            # Extract ability name from AbilArray entry
            if isinstance(abil_entry, dict) and "Link" in abil_entry:
                abil_name = abil_entry["Link"]
            elif isinstance(abil_entry, str):
                abil_name = abil_entry
            else:
                continue
            ability_to_structures[abil_name].add(unit_name)

    return ability_to_structures


def _is_train_ability(abil_name: str) -> bool:
    return (
        abil_name.startswith("Train") or abil_name.endswith("Train") or abil_name.startswith("NexusTrain")
    ) and abil_name not in (ABILITY_SCV_HARVEST, ABILITY_NEXUS_TRAIN_MOTHERSHIP_CORE)


def _is_build_ability(abil_name: str) -> bool:
    return abil_name.endswith("Build") or abil_name.endswith("AddOns")


def _is_research_ability(abil_name: str) -> bool:
    return abil_name.endswith("Research")


def _is_valid_produce_target(prod_data: dict) -> bool:
    """Check if a produced unit is valid (not mercenary or campaign)."""
    prod_race = prod_data.get("Race", "")
    return bool(prod_race and prod_race not in (RACE_NA, RACE_NOT_FOUND, "") and not is_campaign_unit(prod_data))


def _accumulate_morphsto(current: str | list[str] | None, new_targets: str | list[str]) -> str | list[str]:
    """Accumulate morphsto targets, handling string vs list conversion."""
    if current is None:
        return new_targets
    if isinstance(current, list):
        if isinstance(new_targets, list):
            current.extend(new_targets)
        else:
            current.append(new_targets)
        return current
    # current is a string, new_targets is string or list
    if isinstance(new_targets, list):
        return [current] + new_targets
    return [current, new_targets]


def _build_ability_indices(abils_data: dict) -> tuple[dict[str, list[tuple[str, str]]], dict[str, list[str]]]:
    """Build ability -> produces and ability -> upgrades indices."""
    ability_produces: dict[str, list[tuple[str, str]]] = defaultdict(list)
    ability_upgrades: dict[str, list[str]] = defaultdict(list)

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
                        ability_produces[abil_name].append((unit, req))
                    if _is_research_ability(abil_name):
                        upgrades = get_info_upgrades(item)
                        for upgrade in upgrades:
                            ability_upgrades[abil_name].append(upgrade)
        elif isinstance(info, dict):
            produced_units = get_info_units(info)
            req = get_requirement_from_button(info)
            for unit in produced_units:
                ability_produces[abil_name].append((unit, req))

    return ability_produces, ability_upgrades


def _build_unlocks_mapping(
    ability_produces: dict[str, list[tuple[str, str]]],
    units_data: dict,
) -> tuple[dict[str, set[str]], dict[str, list[str]]]:
    """Build unlocks and unit_requirements mappings from ability produces."""
    unlocks: dict[str, set[str]] = defaultdict(set)
    unit_requirements: dict[str, list[str]] = defaultdict(list)

    for abil_name, prod_list in ability_produces.items():
        for produced_unit, req in prod_list:
            if req:
                req_structs = parse_requirement(req)
                for req_struct in req_structs:
                    if req_struct in units_data:
                        unlocks[req_struct].add(produced_unit)
                    # Track requirements for the unit (apply fixes if needed)
                    if produced_unit in UNIT_REQUIREMENT_FIXES:
                        unit_requirements[produced_unit].extend(UNIT_REQUIREMENT_FIXES[produced_unit])
                    else:
                        unit_requirements[produced_unit].append(req_struct)

    return unlocks, unit_requirements


def generate_techtree() -> dict:
    """Generate the techtree structure from JSON data files."""
    units_data = load_json("UnitData.json")
    abils_data = load_json("AbilData.json")

    structures: dict[str, dict] = {}
    units: dict[str, dict] = {}
    abilities: dict[str, dict] = {}

    # Build ability indices
    ability_produces, ability_upgrades = _build_ability_indices(abils_data)

    # Build ability to structures mapping from unit AbilArray
    ability_to_structures = _build_ability_to_structures_mapping(units_data)

    # Build unlocks mapping
    unlocks, unit_requirements = _build_unlocks_mapping(ability_produces, units_data)

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

        for abil_entry in unit_data.get("AbilArray", []):
            # AbilArray entries are dicts with 'Link' key, e.g., {"Link": "BuildInProgress"}
            if isinstance(abil_entry, dict) and "Link" in abil_entry:
                abil_name = abil_entry["Link"]
            elif isinstance(abil_entry, str):
                abil_name = abil_entry
            else:
                continue

            if abil_name in ability_produces:
                for produced_unit, req in ability_produces[abil_name]:
                    if _is_train_ability(abil_name) and _match_ability_to_structure(
                        abil_name, unit_name, ability_to_structures, require_prefix_match=True
                    ):
                        if not is_campaign_unit(units_data.get(produced_unit, {})):
                            produces.append(produced_unit)
                    elif _is_build_ability(abil_name):
                        # For build abilities, include units not in units_data (e.g., tech labs)
                        # Also include units in units_data even if they have empty race (tech labs)
                        if produced_unit not in units_data:
                            builds.append(produced_unit)
                        else:
                            prod_data = units_data[produced_unit]
                            # Include for build abilities even if race is null/empty
                            # (tech labs have empty race but are valid build targets)
                            prod_race = prod_data.get("Race", "")
                            if prod_race and prod_race not in (RACE_NA, RACE_NOT_FOUND, "") or not prod_race:
                                builds.append(produced_unit)
                    elif (
                        _is_research_ability(abil_name)
                        and _match_ability_to_structure(
                            abil_name, unit_name, ability_to_structures, check_shared_exclude=True
                        )
                        and produced_unit not in RESEARCH_EXCLUDE
                        and produced_unit not in excludes
                    ):
                        researches.append(produced_unit)

            if abil_name in ability_upgrades and _match_ability_to_structure(
                abil_name, unit_name, ability_to_structures, check_shared_exclude=True
            ):
                for upgrade in ability_upgrades[abil_name]:
                    if upgrade not in RESEARCH_EXCLUDE and upgrade not in excludes:
                        researches.append(upgrade)

            # Handle morphsto for units with MorphTo, MorphZergling, UpgradeTo, or LiftOff abilities
            is_morph_to = (
                abil_name.startswith("MorphTo") or abil_name.startswith("MorphZergling")
            ) and abil_name != MORPH_BANELING_EXCLUDE
            is_upgrade_to = abil_name.startswith("UpgradeTo")
            is_lift_off = abil_name.endswith("LiftOff")

            if (is_morph_to or is_upgrade_to) and unit_name in units_data:
                abil = abils_data.get(abil_name)
                if isinstance(abil, dict):
                    info = abil.get("InfoArray")
                    if info:
                        targets = get_morph_targets(info)
                        if targets:
                            morphsto = _accumulate_morphsto(morphsto, targets)

            # Handle LiftOff abilities - get target from 'unit' field
            if is_lift_off:
                abil = abils_data.get(abil_name)
                if isinstance(abil, dict):
                    target = get_lift_off_target(abil)
                    if target:
                        morphsto = _accumulate_morphsto(morphsto, target)

        if produces:
            entry["produces"] = sorted(set(produces))
        if builds:
            entry["builds"] = sorted(set(builds))
        if researches:
            # Add additional researches (for structures where data is incomplete)
            all_researches = list(researches)
            for extra in additional:
                if extra not in all_researches:
                    all_researches.append(extra)
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
                            if isinstance(btn, dict) and btn.get("index") == BUTTON_INDEX_EXECUTE:
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

        # Also add research abilities (ending with "Research")
        # These don't have morphsto, but are needed for STARTING_ABILITIES in reconstruct_data
        elif _is_research_ability(abil_name):
            info = abil_data.get("InfoArray")
            upgrade_name = None
            if isinstance(info, list):
                for entry in info:
                    if isinstance(entry, dict) and "Upgrade" in entry:
                        upgrade_name = entry["Upgrade"]
                        break

            if upgrade_name:
                requires = []
                cmd_buttons = abil_data.get("CmdButtonArray", [])
                if isinstance(cmd_buttons, list):
                    for btn in cmd_buttons:
                        if isinstance(btn, dict) and btn.get("index") == BUTTON_INDEX_EXECUTE:
                            req = btn.get("Requirements", "")
                            if req:
                                requires.extend(parse_requirement(req))

                abilities[abil_name] = {
                    "upgrade": upgrade_name,
                }
                if requires:
                    abilities[abil_name]["requires"] = sorted(set(requires))

    # Gather Upgrades from all structures' researches
    upgrades = {}
    for struct_data in structures.values():
        if "researches" in struct_data:
            for upg_name in struct_data["researches"]:
                if upg_name not in upgrades:
                    upgrades[upg_name] = {}  # Empty dict - just a container for the name

    return {
        "Units": {**structures, **units},  # MERGE: combine structures + units
        "Abilities": abilities,  # RENAME: abilities → Abilities
        "Upgrades": upgrades,  # NEW: gather all unique researches
    }


def main():
    """Main entry point."""
    output_path = Path(__file__).parent / "computed" / "techtree.json"

    print("Generating techtree...")
    techtree = generate_techtree()

    output_path.write_text(dumps_json(techtree, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    print(f"Written to {output_path}")
    print(f"  Units: {len(techtree['Units'])}")
    print(f"  Abilities: {len(techtree['Abilities'])}")
    print(f"  Upgrades: {len(techtree['Upgrades'])}")


if __name__ == "__main__":
    main()
