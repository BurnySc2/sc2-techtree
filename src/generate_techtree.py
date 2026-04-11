#!/usr/bin/env python3
import json
import re
from pathlib import Path

from utils import dump_json

DATA_DIR = Path(__file__).parent / "json"
OUTPUT_FILE = Path(__file__).parent / "json/techtree.json"

RACE_MAP = {
    "Terr": "Terran",
    "Zerg": "Zerg",
    "Prot": "Protoss",
}


def load_json(filename: str) -> dict:
    with (DATA_DIR / filename).open() as f:
        return json.load(f)


def parse_race(categories: str, race_field: str | None = None) -> str | None:
    if race_field and race_field in RACE_MAP:
        return RACE_MAP[race_field]
    if race_field and race_field in RACE_MAP.values():
        return race_field
    if not categories:
        return None
    for part in categories.split(","):
        if part.startswith("Race:"):
            return RACE_MAP.get(part.split(":")[1], part.split(":")[1])
    return None


def extract_unit_build_ability(abil_array: list) -> str | None:
    """Extract build ability name from unit's AbilArray."""
    if not abil_array:
        return None
    for abil in abil_array:
        if not abil:
            continue
        name = abil if isinstance(abil, str) else abil.get("Link")
        if not name:
            continue
        if name.endswith("Build") or name.endswith("AddOns"):
            return name
    return None


def extract_train_building(abil_array: list) -> str | None:
    if not abil_array:
        return None
    for abil in abil_array:
        if not abil:
            continue
        name = abil if isinstance(abil, str) else abil.get("Link")
        if not name:
            continue
        if name.endswith("Train"):
            return name.replace("Train", "")
        if name.endswith("TrainLarge"):
            return name.replace("TrainLarge", "")
        if name.endswith("TrainMorph"):
            return name.replace("TrainMorph", "")
    return None


def is_techlab_unit(unit_data: dict) -> bool:
    tech_alias = unit_data.get("TechAliasArray")
    if isinstance(tech_alias, list):
        return any("TechLab" in alias for alias in tech_alias)
    return isinstance(tech_alias, str) and "TechLab" in tech_alias


def extract_build_requirements(abil_data: dict) -> dict[str, list[str]]:
    """Extract unit -> requirement mappings from AbilData.InfoArray."""
    result = {}
    info_array = abil_data.get("InfoArray", [])
    if not isinstance(info_array, list):
        return result
    for item in info_array:
        if not isinstance(item, dict):
            continue
        button = item.get("Button", {})
        if not isinstance(button, dict):
            continue
        unit = item.get("Unit")
        if not unit or not isinstance(unit, str):
            continue
        requirements = button.get("Requirements", "")
        if requirements and isinstance(requirements, str):
            match = re.match(r"Have(\w+)", requirements)
            if match:
                reqs = []
                for part in match.group(1).split("And"):
                    if part.startswith("Attached") and part.endswith("TechLab"):
                        part = "AttachedTechLab"
                    reqs.append(part)
                result[unit] = reqs
    return result


def extract_morph_info(abil_data: dict, ability_name: str) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Extract morph ability -> primary target unit and requirements from CmdButtonArray.
    Returns (morphsto_map, requires_map) for MorphTo* abilities."""
    morphsto_map: dict[str, str] = {}
    requires_map: dict[str, list[str]] = {}

    cmd_button_array = abil_data.get("CmdButtonArray", [])
    if isinstance(cmd_button_array, dict):
        cmd_button_array = [cmd_button_array]

    # Get requirement from Execute button
    ability_requires: list[str] = []
    for button in cmd_button_array:
        if not isinstance(button, dict):
            continue
        index = button.get("index", "")
        if index != "Execute":
            continue
        requirements = button.get("Requirements", "")
        if requirements and isinstance(requirements, str):
            match = re.match(r"Have(\w+)", requirements)
            if match:
                for part in match.group(1).split("And"):
                    if part.startswith("Attached") and part.endswith("TechLab"):
                        part = "AttachedTechLab"
                    ability_requires.append(part)

    # Find primary morph target (unit with Score=1, skip intermediate cocoons/eggs)
    info_array = abil_data.get("InfoArray", [])
    # Handle InfoArray being either a dict or list
    if isinstance(info_array, dict):
        info_array = [info_array] if info_array else []
    primary_unit = None
    if isinstance(info_array, list):
        # First pass: find unit with Score=1 (the actual morph result)
        for item in info_array:
            if isinstance(item, dict):
                unit = item.get("Unit", "")
                score = item.get("Score")
                if unit and isinstance(unit, str) and score == 1:
                    primary_unit = unit
                    break
        # Second pass: if no Score=1, take first non-egg, non-cocoon unit
        if not primary_unit:
            for item in info_array:
                if isinstance(item, dict):
                    unit = item.get("Unit", "")
                    if unit and isinstance(unit, str) and not unit.endswith("Cocoon") and not unit.endswith("Egg"):
                        primary_unit = unit
                        break
    if primary_unit:
        morphsto_map[ability_name] = primary_unit
        requires_map[ability_name] = ability_requires
    return morphsto_map, requires_map


def extract_all_morph_info(abil_data: dict) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Extract all MorphTo* abilities' morph target and requirements."""
    morphsto_map: dict[str, str] = {}
    morph_requires: dict[str, list[str]] = {}
    for name, data in abil_data.items():
        if not isinstance(data, dict):
            continue
        if not (name.startswith("MorphTo") or name.startswith("UpgradeTo") or name.endswith("LiftOff")):
            continue
        ms, mr = extract_morph_info(data, name)
        morphsto_map.update(ms)
        morph_requires.update(mr)
    return morphsto_map, morph_requires


def extract_buildable_units(abil_data: dict, valid_units: set[str]) -> dict[str, list[str]]:
    """Extract build ability -> list of buildable units from *Build and *AddOns abilities in AbilData.
    Only includes units that exist in valid_units (i.e., have a UnitData.json entry)."""
    result = {}
    for name, data in abil_data.items():
        if not isinstance(data, dict):
            continue
        if not (name.endswith("Build") or name.endswith("AddOns")):
            continue
        info_array = data.get("InfoArray", [])
        if isinstance(info_array, dict):
            info_array = [info_array] if info_array else []
        buildables = []
        for item in info_array:
            if isinstance(item, dict) and "Unit" in item:
                unit = item.get("Unit")
                if unit and isinstance(unit, str) and unit in valid_units:
                    buildables.append(unit)
        if buildables:
            result[name] = sorted(set(buildables))
    return result


def extract_trainable_units(abil_data: dict) -> dict[str, list[str]]:
    """Extract building -> trainable unit mappings from *Train abilities in AbilData."""
    result = {}
    for name, data in abil_data.items():
        if not isinstance(data, dict):
            continue
        if not name.endswith("Train"):
            continue
        building = name.replace("Train", "").replace("TrainLarge", "").replace("TrainMorph", "")
        info_array = data.get("InfoArray", [])
        if not isinstance(info_array, list):
            info_array = [info_array] if info_array else []
        for item in info_array:
            if isinstance(item, dict) and "Unit" in item:
                unit = item.get("Unit")
                if unit and isinstance(unit, str):
                    if building not in result:
                        result[building] = []
                    result[building].append(unit)
    return result


def extract_trainable_units_by_ability(abil_data: dict) -> dict[str, list[str]]:
    """Extract ability name -> trainable unit mappings from *Train abilities in AbilData."""
    result = {}
    for name, data in abil_data.items():
        if not isinstance(data, dict):
            continue
        if not name.endswith("Train"):
            continue
        info_array = data.get("InfoArray", [])
        if not isinstance(info_array, list):
            info_array = [info_array] if info_array else []
        units = []
        for item in info_array:
            if isinstance(item, dict) and "Unit" in item:
                unit = item.get("Unit")
                if unit and isinstance(unit, str):
                    units.append(unit)
        if units:
            result[name] = sorted(set(units))
    return result


def extract_researchable_upgrades(abil_data: dict) -> dict[str, list[str]]:
    """Extract research ability -> list of upgrade names from *Research abilities in AbilData."""
    result = {}
    for name, data in abil_data.items():
        if not isinstance(data, dict):
            continue
        if not name.endswith("Research"):
            continue
        info_array = data.get("InfoArray", [])
        if not isinstance(info_array, list):
            info_array = [info_array] if info_array else []
        upgrades = []
        for item in info_array:
            if isinstance(item, dict) and "Upgrade" in item:
                upgrade = item.get("Upgrade")
                if upgrade and isinstance(upgrade, str):
                    upgrades.append(upgrade)
        if upgrades:
            result[name] = upgrades
    return result


def extract_morphable_units(abil_data: dict) -> dict[str, list[str]]:
    """Extract morph ability -> list of morphable units from MorphTo* abilities in AbilData."""
    result = {}
    for name, data in abil_data.items():
        if not isinstance(data, dict):
            continue
        if not name.startswith("MorphTo"):
            continue
        info_array = data.get("InfoArray", [])
        if isinstance(info_array, dict):
            info_array = [info_array] if info_array else []
        morphables = []
        for item in info_array:
            if isinstance(item, dict) and "Unit" in item:
                unit = item.get("Unit")
                if unit and isinstance(unit, str):
                    morphables.append(unit)
        if morphables:
            result[name] = sorted(set(morphables))
    return result


def main():
    unit_data = load_json("UnitData.json")
    abil_data = load_json("AbilData.json")
    upgrade_data = load_json("UpgradeData.json")

    structures: dict[str, dict] = {}
    units: dict[str, dict] = {}
    upgrades: dict[str, dict] = {}
    abilities: dict[str, dict] = {}

    building_unlocks: dict[str, list[str]] = {}
    building_produces: dict[str, list[str]] = {}
    build_requirements: dict[str, list[str]] = {}

    for name, data in abil_data.items():
        if not isinstance(data, dict):
            continue
        build_requirements.update(extract_build_requirements(data))

    requirement_unlocks: dict[str, list[str]] = {}
    for unit, reqs in build_requirements.items():
        for req in reqs:
            if req not in requirement_unlocks:
                requirement_unlocks[req] = []
            requirement_unlocks[req].append(unit)

    for name, data in unit_data.items():
        if not isinstance(data, dict):
            continue

        categories = data.get("EditorCategories", "")
        is_structure = "ObjectType:Structure" in categories

        if is_structure:
            produced = data.get("TechTreeProducedUnitArray")
            if produced:
                if isinstance(produced, str):
                    produced = [produced]
                building_produces[name] = produced

            unlocked = data.get("TechTreeUnlockedUnitArray")
            if unlocked:
                if isinstance(unlocked, str):
                    unlocked = [unlocked]
                building_unlocks[name] = unlocked

    trainable_units_by_ability = extract_trainable_units_by_ability(abil_data)
    researchable_upgrades = extract_researchable_upgrades(abil_data)
    valid_units = set(unit_data.keys())
    buildable_units = extract_buildable_units(abil_data, valid_units)
    morphsto_map, morph_requires = extract_all_morph_info(abil_data)

    for name, data in unit_data.items():
        if not isinstance(data, dict):
            continue

        categories = data.get("EditorCategories", "")
        race = parse_race(categories, data.get("Race"))
        is_structure = "ObjectType:Structure" in categories
        is_unit = "ObjectType:Unit" in categories

        if is_structure:
            produced = building_produces.get(name, [])
            abil_array = data.get("AbilArray", [])
            trainable = []
            if isinstance(abil_array, list):
                for abil in abil_array:
                    abil_name = abil if isinstance(abil, str) else abil.get("Link")
                    if abil_name and abil_name.endswith("Train") and abil_name in trainable_units_by_ability:
                        trainable.extend(trainable_units_by_ability[abil_name])
            combined = list({*produced, *trainable})
            valid_produces = sorted({u for u in combined if isinstance(u, str) and u in valid_units})
            unlocked = building_unlocks.get(name, [])
            req_unlocked = requirement_unlocks.get(name, [])
            filtered_unlocked = [u for u in unlocked if isinstance(u, str)]
            combined_unlocks = list({*filtered_unlocked, *req_unlocked})
            unlocks = sorted({u for u in combined_unlocks if isinstance(u, str) and u in valid_units})

            researches = []
            structure_abilities = []
            valid_upgrades = set(upgrade_data.keys())
            if isinstance(abil_array, list):
                for abil in abil_array:
                    if isinstance(abil, dict) and abil.get("Link"):
                        research_name = abil.get("Link")
                    elif isinstance(abil, str):
                        research_name = abil
                    else:
                        continue
                    if research_name in researchable_upgrades:
                        for upgrade in researchable_upgrades[research_name]:
                            if upgrade in valid_upgrades:
                                researches.append(upgrade)
                    structure_abilities.append(research_name)
            elif isinstance(abil_array, dict) and abil_array.get("Link"):
                research_name = abil_array.get("Link")
                if research_name in researchable_upgrades:
                    for upgrade in researchable_upgrades[research_name]:
                        if upgrade in valid_upgrades:
                            researches.append(upgrade)
                structure_abilities.append(research_name)

            structures[name] = {
                "produces": valid_produces,
                "unlocks": unlocks,
                "race": race,
            }
            if researches:
                structures[name]["researches"] = sorted(set(researches))
            if structure_abilities:
                structures[name]["abilities"] = sorted(set(structure_abilities))

        elif is_unit:
            abil_array = data.get("AbilArray", [])
            train_building = extract_train_building(abil_array)
            build_ability = extract_unit_build_ability(abil_array)
            requires = set()

            if train_building:
                requires.add(train_building)
                if is_techlab_unit(data):
                    requires.add(f"{train_building}TechLab")

            for building, unlocked_units in building_unlocks.items():
                if name in unlocked_units:
                    requires.add(building)

            if name in build_requirements:
                requires.update(build_requirements[name])

            units[name] = {
                "requires": sorted(requires),
                "race": race,
            }

            if build_ability and build_ability in buildable_units:
                units[name]["builds"] = buildable_units[build_ability]

    for name, data in upgrade_data.items():
        if not isinstance(data, dict):
            continue

        categories = data.get("EditorCategories", "")
        race = parse_race(categories, data.get("Race"))

        affected = data.get("AffectedUnitArray")
        if isinstance(affected, str):
            affected = [affected]
        elif not affected:
            affected = []

        requires = []

        upgrades[name] = {
            "requires": requires,
            "affected_units": affected,
            "race": race,
        }

    for name, data in abil_data.items():
        if not isinstance(data, dict):
            continue

        categories = data.get("EditorCategories", "")
        race = parse_race(categories)

        requires = []
        if "Burrow" in name:
            requires.append("Burrow")

        if requires or race:
            abilities[name] = {
                "requires": requires,
                "race": race,
            }

            if name in buildable_units:
                abilities[name]["builds"] = buildable_units[name]

            if name == "LarvaTrain" and name in trainable_units_by_ability:
                abilities[name]["morphs"] = trainable_units_by_ability[name]

            if (
                name.startswith("MorphTo") or name.startswith("UpgradeTo") or name.endswith("LiftOff")
            ) and name in morphsto_map:
                abilities[name]["morphsto"] = morphsto_map[name]
                abilities[name]["requires"] = morph_requires.get(name, [])

    tech_tree = {
        "structures": structures,
        "units": units,
        "upgrades": upgrades,
        "abilities": abilities,
    }

    with OUTPUT_FILE.open("w") as f:
        dump_json(tech_tree, f, indent=2, sort_keys=True)

    print(f"Generated {OUTPUT_FILE}")
    print(f"  Structures: {len(structures)}")
    print(f"  Units: {len(units)}")
    print(f"  Upgrades: {len(upgrades)}")
    print(f"  Abilities: {len(abilities)}")


if __name__ == "__main__":
    main()
