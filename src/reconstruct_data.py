#!/usr/bin/env python3
"""Gather reachable units, structures, and upgrades from SC2 techtree."""

import json
from pathlib import Path

from utils import dump_json

DATA_DIR = Path(__file__).parent / "json"
OUTPUT_FILE = Path(__file__).parent / "computed" / "data.json"

# Starting units and structures for each race
STARTING_UNITS = {
    "Terran": ["SCV", "CommandCenter"],
    "Zerg": ["Drone", "Hatchery", "Larva"],
    "Protoss": ["Probe", "Nexus"],
}


def load_json(filename: str) -> dict:
    with (DATA_DIR / filename).open() as f:
        return json.load(f)


def gather_data():
    # Load source data
    techtree = load_json("techtree.json")
    unit_data = load_json("UnitData.json")
    abil_data = load_json("AbilData.json")
    upgrade_data = load_json("UpgradeData.json")
    weapon_data = load_json("WeaponData.json")

    units_section = techtree.get("units", {})
    structures_section = techtree.get("structures", {})
    upgrades_section = techtree.get("upgrades", {})
    abilities_section = techtree.get("abilities", {})

    # Track visited items
    visited_units: set[str] = set()
    visited_structures: set[str] = set()
    visited_upgrades: set[str] = set()
    visited_abilities: set[str] = set()

    # Queue for BFS: (category, name)
    queue: list[tuple[str, str]] = []

    # Initialize with starting units and structures
    for race, names in STARTING_UNITS.items():
        for name in names:
            if name in units_section:
                queue.append(("unit", name))
            elif name in structures_section:
                queue.append(("structure", name))
            else:
                print(f"Warning: Starting item {name} not found in techtree")

    # BFS traversal
    while queue:
        category, name = queue.pop(0)

        if category == "unit":
            if name in visited_units:
                continue
            visited_units.add(name)

            unit_info = units_section.get(name, {})
            unit_full_data = unit_data.get(name, {})

            # Add abilities from this unit's AbilArray (only if in AbilData)
            abil_array = unit_full_data.get("AbilArray", [])
            for ability_name in abil_array:
                if (
                    ability_name
                    and isinstance(ability_name, str)
                    and ability_name in abil_data
                    and ability_name not in visited_abilities
                ):
                    visited_abilities.add(ability_name)
                    ability_info = abilities_section.get(ability_name, {})
                    morphsto = ability_info.get("morphsto")
                    if morphsto:
                        if isinstance(morphsto, list):
                            for m in morphsto:
                                if m and m not in visited_structures:
                                    if m in structures_section:
                                        queue.append(("structure", m))
                                    elif m in units_section:
                                        queue.append(("unit", m))
                        elif morphsto not in visited_structures:
                            if morphsto in structures_section:
                                queue.append(("structure", morphsto))
                            elif morphsto in units_section:
                                queue.append(("unit", morphsto))

            # Add structures this unit can build
            builds = unit_info.get("builds", [])
            for structure_name in builds:
                if structure_name not in visited_structures:
                    queue.append(("structure", structure_name))

                # Add abilities that build structures
                for ability_name, ability_info in abilities_section.items():
                    if (
                        "builds" in ability_info
                        and structure_name in ability_info.get("builds", [])
                        and ability_name not in visited_abilities
                    ):
                        visited_abilities.add(ability_name)

            # Add requirements (upgrades)
            for req in unit_info.get("requires", []):
                if req not in visited_upgrades:
                    queue.append(("upgrade", req))

        elif category == "structure":
            if name in visited_structures:
                continue
            visited_structures.add(name)

            structure_info = structures_section.get(name, {})

            # Add units this structure produces
            produces = structure_info.get("produces", [])
            for unit_name in produces:
                if unit_name not in visited_units:
                    queue.append(("unit", unit_name))

            # Add units unlocked by this structure
            unlocks = structure_info.get("unlocks", [])
            for unit_name in unlocks:
                if unit_name not in visited_units:
                    queue.append(("unit", unit_name))

            # Add upgrades researched at this structure
            researches = structure_info.get("researches", [])
            for upgrade_name in researches:
                if upgrade_name not in visited_upgrades:
                    queue.append(("upgrade", upgrade_name))

            # Add abilities for this structure
            for ability_name, ability_info in abilities_section.items():
                if "builds" in ability_info:
                    for built in ability_info.get("builds", []):
                        if built == name and ability_name not in visited_abilities:
                            visited_abilities.add(ability_name)
                            # Add units this ability builds
                            for unit_name in ability_info.get("builds", []):
                                if unit_name not in visited_units:
                                    queue.append(("unit", unit_name))

            # Add abilities directly listed on this structure
            abilities_list = structure_info.get("abilities", [])
            for ability_name in abilities_list:
                if ability_name not in visited_abilities:
                    visited_abilities.add(ability_name)
                    ability_info = abilities_section.get(ability_name, {})
                    morphsto = ability_info.get("morphsto")
                    if morphsto and morphsto in structures_section and morphsto not in visited_structures:
                        queue.append(("structure", morphsto))
                    elif morphsto and morphsto in units_section and morphsto not in visited_units:
                        queue.append(("unit", morphsto))

        elif category == "upgrade":
            if name in visited_upgrades:
                continue
            visited_upgrades.add(name)

            upgrade_info = upgrades_section.get(name, {})

            # Add requirements for this upgrade
            for req in upgrade_info.get("requires", []):
                if req not in visited_upgrades:
                    queue.append(("upgrade", req))

    # Build output structure with full data
    result = {
        "units": {},
        "structures": {},
        "upgrades": {},
        "abilities": {},
    }

    # Populate units with full data from UnitData.json
    for unit_name in visited_units:
        unit_entry = units_section.get(unit_name, {})
        full_data = unit_data.get(unit_name, {})
        merged = {"name": unit_name}
        merged.update(unit_entry)
        merged.update(full_data)
        result["units"][unit_name] = merged

    # Populate structures with full data
    for structure_name in visited_structures:
        structure_entry = structures_section.get(structure_name, {})
        full_data = unit_data.get(structure_name, {})
        merged = {"name": structure_name}
        merged.update(structure_entry)
        merged.update(full_data)
        result["structures"][structure_name] = merged

    # Populate upgrades with full data
    for upgrade_name in visited_upgrades:
        upgrade_entry = upgrades_section.get(upgrade_name, {})
        full_data = upgrade_data.get(upgrade_name, {})
        merged = {"name": upgrade_name}
        merged.update(upgrade_entry)
        merged.update(full_data)
        result["upgrades"][upgrade_name] = merged

    # Populate abilities with full data
    for ability_name in visited_abilities:
        ability_entry = abilities_section.get(ability_name, {})
        full_data = abil_data.get(ability_name) or {}
        merged = {"name": ability_name}
        merged.update(ability_entry)
        merged.update(full_data)
        result["abilities"][ability_name] = merged

    # Add weapons data for units that have them
    for unit_name, unit_data_out in result["units"].items():
        weapons = unit_data_out.get("weapon", [])
        if isinstance(weapons, list):
            for weapon_name in weapons:
                if weapon_name in weapon_data:
                    _weapons: dict[str, object] = unit_data_out.setdefault("_weapons", {})  # type: ignore[arg-type]
                    _weapons[weapon_name] = weapon_data[weapon_name]

    return result


def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = gather_data()
    with OUTPUT_FILE.open("w") as f:
        dump_json(data, f, indent=2)
    print(
        f"Wrote {len(data['units'])} units, {len(data['structures'])} structures, "
        f"{len(data['upgrades'])} upgrades, {len(data['abilities'])} abilities to {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
