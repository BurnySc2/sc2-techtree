#!/usr/bin/env python3
"""Gather reachable units, structures, and upgrades from SC2 techtree."""

import json
from pathlib import Path
from typing import TypeAlias

from utils import dump_json

DATA_DIR = Path(__file__).parent / "json"
OUTPUT_FILE = Path(__file__).parent / "computed" / "data.json"

# Starting units and structures for each race
STARTING_UNITS = {
    "Terran": ["SCV", "CommandCenter"],
    "Zerg": ["Drone", "Hatchery", "Larva"],
    "Protoss": ["Probe", "Nexus"],
}

# Starting structures (tech labs) for each race - always discover these
STARTING_STRUCTURES = {
    "Terran": ["BarracksTechLab", "FactoryTechLab", "StarportTechLab"],
}

# Starting abilities that should always be discovered
STARTING_ABILITIES = [
    "MorphToBaneling",
    "MorphToBroodLord",
]

# Field names
FIELD_NAME = "name"
FIELD_BUILDS = "builds"
FIELD_PRODUCES = "produces"
FIELD_UNLOCKS = "unlocks"
FIELD_RESEARCHES = "researches"
FIELD_REQUIRES = "requires"
FIELD_ABILITIES = "abilities"
FIELD_ABIL_ARRAY = "AbilArray"
FIELD_WEAPON = "weapon"
FIELD_MORPHSTO = "morphsto"

# Special case filters
SCV_MERCENARY_BUILDINGS = {"BomberLaunchPad", "MercCompound"}
NEXUS_EXCLUDED_ABILITY = "NexusTrainMothershipCore"

# Type aliases
Category: TypeAlias = str
ItemName: TypeAlias = str
QueueItem: TypeAlias = tuple[Category, ItemName]
VisitedSets: TypeAlias = dict[str, set[ItemName]]


def load_json(filename: str) -> dict:
    """Load a JSON data file and transform to expected format."""
    with (DATA_DIR / filename).open() as f:
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


def enqueue_if_new(
    queue: list[QueueItem],
    visited: set[ItemName],
    category: Category,
    name: ItemName,
) -> None:
    """Add to queue if not already queued (visited is checked in BFS loop)."""
    # Check if already in queue to avoid duplicates
    if (category, name) not in queue:
        queue.append((category, name))


def merge_entry(name: ItemName, entry: dict, full_data: dict) -> dict:
    """Standard merge pattern for building result entries."""
    merged: dict = {FIELD_NAME: name}
    merged.update(entry)
    merged.update(full_data)
    return merged


def handle_morphsto(
    morphsto: str | list,
    visited_structures: set[ItemName],
    visited_units: set[ItemName],
    structures_section: dict,
    units_section: dict,
    queue: list[QueueItem],
) -> None:
    """Process morphsto field, enqueueing structures or units as needed."""
    if not morphsto:
        return

    if isinstance(morphsto, list):
        for m in morphsto:
            if m and m not in visited_structures:
                if m in structures_section:
                    enqueue_if_new(queue, visited_structures, "structure", m)
                elif m in units_section:
                    enqueue_if_new(queue, visited_units, "unit", m)
    elif morphsto not in visited_structures:
        if morphsto in structures_section:
            enqueue_if_new(queue, visited_structures, "structure", morphsto)
        elif morphsto in units_section:
            enqueue_if_new(queue, visited_units, "unit", morphsto)


def process_ability_morphsto(
    ability_name: ItemName,
    visited_abilities: set[ItemName],
    visited_structures: set[ItemName],
    visited_units: set[ItemName],
    structures_section: dict,
    units_section: dict,
    abilities_section: dict,
    queue: list[QueueItem],
) -> None:
    """Wrapper for handling ability morphsto processing."""
    if ability_name not in visited_abilities:
        visited_abilities.add(ability_name)
        ability_info = abilities_section.get(ability_name, {})
        morphsto = ability_info.get(FIELD_MORPHSTO)
        handle_morphsto(
            morphsto,
            visited_structures,
            visited_units,
            structures_section,
            units_section,
            queue,
        )


def _load_source_data() -> tuple[dict, dict, dict, dict, dict, dict, dict, dict]:
    """Load all source JSON files and extract sections from techtree."""
    techtree = load_json("../computed/techtree.json")
    unit_data = load_json("UnitData.json")
    abil_data = load_json("AbilData.json")
    upgrade_data = load_json("UpgradeData.json")
    weapon_data = load_json("WeaponData.json")

    units_section = techtree.get("units", {})
    structures_section = techtree.get("structures", {})
    upgrades_section = techtree.get("upgrades", {})
    abilities_section = techtree.get("abilities", {})

    return (
        unit_data,
        abil_data,
        upgrade_data,
        weapon_data,
        units_section,
        structures_section,
        upgrades_section,
        abilities_section,
    )


def _process_unit(
    name: ItemName,
    units_section: dict,
    structures_section: dict,
    upgrades_section: dict,
    abilities_section: dict,
    unit_data: dict,
    abil_data: dict,
    visited_units: set[ItemName],
    visited_structures: set[ItemName],
    visited_upgrades: set[ItemName],
    visited_abilities: set[ItemName],
    queue: list[QueueItem],
) -> None:
    """Handle unit abilities, builds, produces, morphsto, requirements."""
    unit_info = units_section.get(name, {})
    unit_full_data = unit_data.get(name, {})

    # Handle unit's produces field (e.g., Larva produces units)
    produces = unit_info.get(FIELD_PRODUCES, [])
    for unit_name in produces:
        if unit_name not in visited_units:
            enqueue_if_new(queue, visited_units, "unit", unit_name)

    # Handle unit's morphsto field (e.g., Larva can morph to various units)
    morphsto = unit_info.get(FIELD_MORPHSTO)
    if morphsto:
        handle_morphsto(
            morphsto,
            visited_structures,
            visited_units,
            structures_section,
            units_section,
            queue,
        )

    # Add abilities from this unit's AbilArray (extract Link from each entry)
    abil_array = unit_full_data.get(FIELD_ABIL_ARRAY, [])
    for ability_entry in abil_array:
        # Handle both old format (list of strings) and new format (list of dicts with 'Link')
        if isinstance(ability_entry, dict):
            ability_name = ability_entry.get("Link")
        elif isinstance(ability_entry, str):
            ability_name = ability_entry
        else:
            continue

        if (
            ability_name
            and isinstance(ability_name, str)
            and ability_name in abil_data
            and ability_name not in visited_abilities
        ):
            process_ability_morphsto(
                ability_name,
                visited_abilities,
                visited_structures,
                visited_units,
                structures_section,
                units_section,
                abilities_section,
                queue,
            )

    # Add structures this unit can build
    builds = unit_info.get(FIELD_BUILDS, [])
    for structure_name in builds:
        if structure_name not in visited_structures:
            enqueue_if_new(queue, visited_structures, "structure", structure_name)

        # Add abilities that build structures
        for ability_name, ability_info in abilities_section.items():
            if (
                FIELD_BUILDS in ability_info
                and structure_name in ability_info.get(FIELD_BUILDS, [])
                and ability_name not in visited_abilities
            ):
                visited_abilities.add(ability_name)

    # Add requirements (only if they're actual upgrades in upgrades_section)
    for req in unit_info.get(FIELD_REQUIRES, []):
        if req not in visited_upgrades and req in upgrades_section:
            enqueue_if_new(queue, visited_upgrades, "upgrade", req)


def _process_structure(
    name: ItemName,
    structures_section: dict,
    units_section: dict,
    upgrades_section: dict,
    abilities_section: dict,
    visited_structures: set[ItemName],
    visited_units: set[ItemName],
    visited_upgrades: set[ItemName],
    visited_abilities: set[ItemName],
    queue: list[QueueItem],
) -> None:
    """Handle structure produces, unlocks, researches, abilities."""
    structure_info = structures_section.get(name, {})

    # Handle structure's own morphsto (e.g., Hatchery -> Lair)
    morphsto = structure_info.get(FIELD_MORPHSTO)
    if morphsto:
        handle_morphsto(
            morphsto,
            visited_structures,
            visited_units,
            structures_section,
            units_section,
            queue,
        )

    # Add units this structure produces
    produces = structure_info.get(FIELD_PRODUCES, [])
    for unit_name in produces:
        if unit_name not in visited_units:
            enqueue_if_new(queue, visited_units, "unit", unit_name)

    # Add units unlocked by this structure
    unlocks = structure_info.get(FIELD_UNLOCKS, [])
    for unlocked_name in unlocks:
        if unlocked_name in structures_section and unlocked_name not in visited_structures:
            enqueue_if_new(queue, visited_structures, "structure", unlocked_name)
        elif unlocked_name in units_section and unlocked_name not in visited_units:
            enqueue_if_new(queue, visited_units, "unit", unlocked_name)

    # Add upgrades researched at this structure
    researches = structure_info.get(FIELD_RESEARCHES, [])
    for upgrade_name in researches:
        if upgrade_name not in visited_upgrades:
            enqueue_if_new(queue, visited_upgrades, "upgrade", upgrade_name)

    # Add abilities for this structure
    for ability_name, ability_info in abilities_section.items():
        if FIELD_BUILDS in ability_info:
            for built in ability_info.get(FIELD_BUILDS, []):
                if built == name and ability_name not in visited_abilities:
                    visited_abilities.add(ability_name)
                    # Add units this ability builds
                    for unit_name in ability_info.get(FIELD_BUILDS, []):
                        if unit_name not in visited_units:
                            enqueue_if_new(queue, visited_units, "unit", unit_name)

    # Add abilities directly listed on this structure
    abilities_list = structure_info.get(FIELD_ABILITIES, [])
    for ability_name in abilities_list:
        process_ability_morphsto(
            ability_name,
            visited_abilities,
            visited_structures,
            visited_units,
            structures_section,
            units_section,
            abilities_section,
            queue,
        )


def _process_upgrade(
    name: ItemName,
    upgrades_section: dict,
    visited_upgrades: set[ItemName],
    queue: list[QueueItem],
) -> None:
    """Handle upgrade requirements."""
    upgrade_info = upgrades_section.get(name, {})

    # Add requirements for this upgrade
    for req in upgrade_info.get(FIELD_REQUIRES, []):
        if req not in visited_upgrades:
            enqueue_if_new(queue, visited_upgrades, "upgrade", req)


def compute_starting_abilities(abilities_section: dict) -> list[str]:
    """Discover all abilities that have a morphsto field."""
    return [name for name, info in abilities_section.items() if isinstance(info, dict) and info.get(FIELD_MORPHSTO)]


def _bfs_traversal(
    units_section: dict,
    structures_section: dict,
    upgrades_section: dict,
    abilities_section: dict,
    unit_data: dict,
    abil_data: dict,
) -> VisitedSets:
    """BFS traversal to collect all reachable units, structures, upgrades, abilities."""
    visited_units: set[str] = set()
    visited_structures: set[str] = set()
    visited_upgrades: set[str] = set()
    visited_abilities: set[str] = set()

    # Queue for BFS: (category, name)
    queue: list[QueueItem] = []

    # Initialize with starting units and structures (just queue, visited added when popped)
    for race, names in STARTING_UNITS.items():
        for name in names:
            if name in units_section:
                queue.append(("unit", name))
            elif name in structures_section:
                queue.append(("structure", name))
            else:
                print(f"Warning: Starting item {name} not found in techtree")

    # Initialize with starting structures (tech labs)
    for race, names in STARTING_STRUCTURES.items():
        for name in names:
            if name in structures_section:
                queue.append(("structure", name))
            else:
                print(f"Warning: Starting structure {name} not found in techtree")

    # Dynamically compute starting abilities from abilities with morphsto
    starting_abilities = compute_starting_abilities(abilities_section)
    for ability_name in starting_abilities:
        if ability_name in abilities_section:
            queue.append(("ability", ability_name))
        else:
            print(f"Warning: Starting ability {ability_name} not found in techtree")

    # BFS traversal
    while queue:
        category, name = queue.pop(0)

        if category == "unit":
            if name in visited_units:
                continue
            # Add to visited BEFORE processing
            visited_units.add(name)

            _process_unit(
                name,
                units_section,
                structures_section,
                upgrades_section,
                abilities_section,
                unit_data,
                abil_data,
                visited_units,
                visited_structures,
                visited_upgrades,
                visited_abilities,
                queue,
            )

        elif category == "structure":
            if name in visited_structures:
                continue
            # Add to visited BEFORE processing
            visited_structures.add(name)

            _process_structure(
                name,
                structures_section,
                units_section,
                upgrades_section,
                abilities_section,
                visited_structures,
                visited_units,
                visited_upgrades,
                visited_abilities,
                queue,
            )

        elif category == "upgrade":
            if name in visited_upgrades:
                continue
            # Add to visited BEFORE processing
            visited_upgrades.add(name)

            _process_upgrade(
                name,
                upgrades_section,
                visited_upgrades,
                queue,
            )

        elif category == "ability":
            if name in visited_abilities:
                continue
            # Add to visited BEFORE processing
            visited_abilities.add(name)

            # Process ability morphsto (abilities can morph to units/structures)
            ability_info = abilities_section.get(name, {})
            morphsto = ability_info.get(FIELD_MORPHSTO)
            handle_morphsto(
                morphsto,
                visited_structures,
                visited_units,
                structures_section,
                units_section,
                queue,
            )

    return {
        "units": visited_units,
        "structures": visited_structures,
        "upgrades": visited_upgrades,
        "abilities": visited_abilities,
    }


def _build_result(
    visited_sets: VisitedSets,
    units_section: dict,
    structures_section: dict,
    upgrades_section: dict,
    abilities_section: dict,
    unit_data: dict,
    upgrade_data: dict,
    abil_data: dict,
    weapon_data: dict,
) -> dict:
    """Build final output structure with full data."""
    visited_units = visited_sets["units"]
    visited_structures = visited_sets["structures"]
    visited_upgrades = visited_sets["upgrades"]
    visited_abilities = visited_sets["abilities"]

    result: dict = {
        "units": {},
        "structures": {},
        "upgrades": {},
        "abilities": {},
    }

    # Populate units with full data from UnitData.json
    for unit_name in visited_units:
        unit_entry = units_section.get(unit_name, {})
        full_data = unit_data.get(unit_name, {})
        merged = merge_entry(unit_name, unit_entry, full_data)
        # Filter builds to exclude mercenary buildings for SCV
        if unit_name == "SCV" and FIELD_BUILDS in merged:
            merged[FIELD_BUILDS] = [b for b in merged[FIELD_BUILDS] if b not in SCV_MERCENARY_BUILDINGS]
        result["units"][unit_name] = merged

    # Populate structures with full data
    for structure_name in visited_structures:
        structure_entry = structures_section.get(structure_name, {})
        full_data = unit_data.get(structure_name, {})
        merged = merge_entry(structure_name, structure_entry, full_data)
        # Filter AbilArray to exclude NexusTrainMothershipCore for Nexus
        if structure_name == "Nexus" and FIELD_ABIL_ARRAY in merged:
            filtered: list[dict | str] = []
            for a in merged[FIELD_ABIL_ARRAY]:
                if isinstance(a, dict):
                    link = a.get("Link")
                    if link and link != NEXUS_EXCLUDED_ABILITY:
                        filtered.append(a)
                elif isinstance(a, str) and a != NEXUS_EXCLUDED_ABILITY:
                    filtered.append(a)
            merged[FIELD_ABIL_ARRAY] = filtered
        result["structures"][structure_name] = merged

    # Populate upgrades with full data
    for upgrade_name in visited_upgrades:
        upgrade_entry = upgrades_section.get(upgrade_name, {})
        full_data = upgrade_data.get(upgrade_name, {})
        merged = merge_entry(upgrade_name, upgrade_entry, full_data)
        result["upgrades"][upgrade_name] = merged

    # Populate abilities with full data
    for ability_name in visited_abilities:
        ability_entry = abilities_section.get(ability_name, {})
        full_data = abil_data.get(ability_name) or {}
        merged = merge_entry(ability_name, ability_entry, full_data)
        result["abilities"][ability_name] = merged

    # Add weapons data for units that have them
    for unit_name, unit_data_out in result["units"].items():
        weapons = unit_data_out.get(FIELD_WEAPON, [])
        if isinstance(weapons, list):
            for weapon_name in weapons:
                if weapon_name in weapon_data:
                    _weapons: dict[str, object] = unit_data_out.setdefault("_weapons", {})  # type: ignore[arg-type]
                    _weapons[weapon_name] = weapon_data[weapon_name]

    return result


def gather_data():
    # Phase 1: Load source data
    (
        unit_data,
        abil_data,
        upgrade_data,
        weapon_data,
        units_section,
        structures_section,
        upgrades_section,
        abilities_section,
    ) = _load_source_data()

    # Phase 2: BFS traversal
    visited_sets = _bfs_traversal(
        units_section,
        structures_section,
        upgrades_section,
        abilities_section,
        unit_data,
        abil_data,
    )

    # Phase 3: Build final result
    result = _build_result(
        visited_sets,
        units_section,
        structures_section,
        upgrades_section,
        abilities_section,
        unit_data,
        upgrade_data,
        abil_data,
        weapon_data,
    )

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
