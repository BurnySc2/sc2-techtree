#!/usr/bin/env python3
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "json"
OUTPUT_FILE = Path(__file__).parent / "techtree.json"

RACE_MAP = {
    "Terr": "Terran",
    "Zerg": "Zerg",
    "Prot": "Protoss",
}


def load_json(filename: str) -> dict:
    with open(DATA_DIR / filename) as f:
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


def extract_train_building(abil_array: list) -> str | None:
    if not abil_array:
        return None
    for abil in abil_array:
        if not abil:
            continue
        if abil.endswith("Train"):
            return abil.replace("Train", "")
        if abil.endswith("TrainLarge"):
            return abil.replace("TrainLarge", "")
        if abil.endswith("TrainMorph"):
            return abil.replace("TrainMorph", "")
    return None


def is_techlab_unit(unit_data: dict) -> bool:
    tech_alias = unit_data.get("TechAliasArray")
    if isinstance(tech_alias, list):
        return any("TechLab" in alias for alias in tech_alias)
    return isinstance(tech_alias, str) and "TechLab" in tech_alias


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

    for name, data in unit_data.items():
        if not isinstance(data, dict):
            continue

        categories = data.get("EditorCategories", "")
        race = parse_race(categories, data.get("Race"))
        is_structure = "ObjectType:Structure" in categories
        is_unit = "ObjectType:Unit" in categories

        if is_structure:
            unlocks = []
            produced = building_produces.get(name, [])
            unlocks.extend(produced)

            unlocked = building_unlocks.get(name, [])
            unlocks.extend(unlocked)

            structures[name] = {
                "unlocks": list(set(unlocks)),
                "race": race,
            }

        elif is_unit:
            abil_array = data.get("AbilArray", [])
            train_building = extract_train_building(abil_array)
            requires = set()

            if train_building:
                requires.add(train_building)
                if is_techlab_unit(data):
                    requires.add(f"{train_building}TechLab")

            for building, unlocked_units in building_unlocks.items():
                if name in unlocked_units:
                    requires.add(building)

            for building, produced_units in building_produces.items():
                if name in produced_units:
                    requires.add(building)

            units[name] = {
                "requires": sorted(requires),
                "race": race,
            }

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

    tech_tree = {
        "structures": structures,
        "units": units,
        "upgrades": upgrades,
        "abilities": abilities,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(tech_tree, f, indent=2)

    print(f"Generated {OUTPUT_FILE}")
    print(f"  Structures: {len(structures)}")
    print(f"  Units: {len(units)}")
    print(f"  Upgrades: {len(upgrades)}")
    print(f"  Abilities: {len(abilities)}")


if __name__ == "__main__":
    main()
