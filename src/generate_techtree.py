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


def load_json(filename: str) -> dict:
    """Load a JSON data file."""
    path = Path(__file__).parent / "json" / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_requirement(req: str) -> list[str]:
    """Parse a requirement string into structure names.

    Examples:
        'HaveBarracks' -> ['Barracks']
        'HaveArmoryAndAttachedTechLab' -> ['Armory', 'AttachedTechLab']
    """
    if not req:
        return []

    parts = req.split("And")
    result = []
    for part in parts:
        if part.startswith("Have"):
            result.append(part[4:])  # Remove 'Have' prefix
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
                    if upgrade:
                        upgrades.append(upgrade)
    elif isinstance(info, dict):
        btn = info.get("Button", {})
        if isinstance(btn, dict) and btn.get("DefaultButtonFace"):
            upgrade = info.get("Upgrade")
            if upgrade:
                upgrades.append(upgrade)
    return upgrades


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


def get_lift_off_target(abil_data: dict) -> str | None:
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


def get_race(data: dict) -> str:
    """Get the race of a unit/structure."""
    if isinstance(data, dict):
        race = data.get("Race", "")
        return RACE_MAP.get(race, race)
    return ""


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
                        produces.append(produced_unit)
                    elif is_build:
                        # Exclude mercenary buildings (Race=NOT_FOUND or N/A)
                        if produced_unit in units_data:
                            unit_info = units_data[produced_unit]
                            race = unit_info.get("Race", "")
                            # Exclude if race is empty, 'N/A', or 'NOT_FOUND'
                            if race and race not in ("N/A", "NOT_FOUND", ""):
                                builds.append(produced_unit)
                        else:
                            builds.append(produced_unit)
                    elif is_research:
                        researches.append(produced_unit)

            if abil_name in ability_upgrades:
                researches.extend(ability_upgrades[abil_name])

            # Handle morphsto for units with MorphTo, UpgradeTo, or LiftOff abilities
            is_morph_to = abil_name.startswith("MorphTo") and not abil_name.startswith("MorphZergling")
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
                            else:
                                morphsto.extend(targets)

            # Handle LiftOff abilities - get target from 'unit' field
            if is_lift_off:
                abil = abils_data.get(abil_name)
                target = get_lift_off_target(abil)
                if target:
                    if morphsto is None:
                        morphsto = [target]
                    else:
                        if isinstance(morphsto, list):
                            morphsto.append(target)
                        else:
                            morphsto = [morphsto, target]

        if produces:
            entry["produces"] = sorted(set(produces))
        if builds:
            entry["builds"] = sorted(set(builds))
        if researches:
            entry["researches"] = sorted(set(researches))
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
        if is_structure(unit_data):
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
