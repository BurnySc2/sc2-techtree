#!/usr/bin/env python3
"""Gather reachable units, structures, and upgrades from SC2 techtree."""

import json
from pathlib import Path
from typing import TypeAlias

from utils import dump_json, load_json

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


def _load_stableid_lookups() -> dict:
    """Load stableid.json and return lookup dicts: abilities, units, upgrades."""
    stableid_path = Path(__file__).parent / "extracted" / "stableid.json"
    with stableid_path.open() as f:
        stableid = json.load(f)
    return {
        "abilities": {entry["name"]: entry["id"] for entry in stableid["Abilities"]},
        "units": {entry["name"]: entry["id"] for entry in stableid["Units"]},
        "upgrades": {entry["name"]: entry["id"] for entry in stableid["Upgrades"]},
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


def is_structure(units_section: dict, name: ItemName) -> bool:
    """Check if an entry in units_section is a structure (has builds or researches)."""
    entry = units_section.get(name, {})
    return bool(entry.get(FIELD_BUILDS) or entry.get(FIELD_RESEARCHES))


def extract_upgrade_costs(abil_data: dict) -> tuple[dict[str, dict], dict[str, dict]]:
    """Extract upgrade cost data from AbilData.json research abilities.

    Parses research abilities (id ends with 'Research' or contains research InfoArray),
    finds entries in InfoArray with an 'Upgrade' field, and extracts Resource,
    Time, and Button.Requirements.

    Returns two dicts:
    1. upgrade_costs: mapping upgrade name -> {minerals, gas, time, requires}
    2. button_face_to_upgrade: mapping button face name -> upgrade name
    """
    upgrade_costs: dict[str, dict] = {}
    button_face_to_upgrade: dict[str, dict] = {}

    for ability_id, ability in abil_data.items():
        # Check if this is a research ability (id ends with "Research")
        ability_id.endswith("Research")

        # Also check InfoArray for any entry containing an "Upgrade" field
        info_array = ability.get("InfoArray", [])
        if not isinstance(info_array, list):
            continue

        for entry in info_array:
            if not isinstance(entry, dict):
                continue

            upgrade_name = entry.get("Upgrade")
            if not upgrade_name:
                continue

            # Extract cost data
            resource = entry.get("Resource", {})
            minerals = resource.get("Minerals", 0)
            gas = resource.get("Vespene", 0)
            time_str = entry.get("Time", "0")
            # Coerce to int or float (time comes as string like "140")
            try:
                time = int(time_str)
            except ValueError:
                time = float(time_str)

            costs = {
                "minerals": minerals,
                "gas": gas,
                "time": time,
            }
            upgrade_costs[upgrade_name] = costs

            # Also build button face to upgrade mapping
            # The button face is stored in Button.DefaultButtonFace
            button = entry.get("Button", {})
            if isinstance(button, dict):
                button_face = button.get("DefaultButtonFace")
                if button_face:
                    button_face_to_upgrade[button_face] = upgrade_name

    return upgrade_costs, button_face_to_upgrade


def extract_unit_build_times(abil_data: dict) -> dict[str, float]:
    """Extract build times from AbilData.json for train/build abilities.

    Iterates through AbilData.json and looks for abilities with InfoArray entries
    that have both a "Unit" field and a "Time" field. These indicate units or
    structures that can be trained/built and their construction time.

    Returns:
        dict mapping unit/structure name -> build time in seconds
    """
    unit_build_times: dict[str, float] = {}

    for ability_id, ability in abil_data.items():
        # AbilData.json has entries where ability can be a list or a dict
        # If it's a list, iterate through; if it's a dict, process directly
        entries = ability if isinstance(ability, list) else [ability]

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            info_array = entry.get("InfoArray", [])
            if isinstance(info_array, dict):
                # Handle single-entry InfoArray (e.g., TrainQueen)
                unit_name = info_array.get("Unit", "")
                time_str = info_array.get("Time", "0")
                if unit_name and time_str and time_str != "0":
                    try:
                        time_val = float(time_str) if "." in time_str else int(time_str)
                        unit_build_times[unit_name] = time_val
                    except (ValueError, TypeError):
                        pass
            elif isinstance(info_array, list):
                for item in info_array:
                    if not isinstance(item, dict):
                        continue

                    unit_name = item.get("Unit", "")
                    time_str = item.get("Time", "0")

                    if unit_name and time_str and time_str != "0":
                        try:
                            time_val = float(time_str) if "." in time_str else int(time_str)
                            unit_build_times[unit_name] = time_val
                        except (ValueError, TypeError):
                            pass

    return unit_build_times


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
    units_section: dict,
    queue: list[QueueItem],
) -> None:
    """Process morphsto field, enqueueing structures or units as needed."""
    if not morphsto:
        return

    if isinstance(morphsto, list):
        for m in morphsto:
            if m and m not in visited_structures and m in units_section:
                # Use is_structure to identify if this is a structure
                if is_structure(units_section, m):
                    enqueue_if_new(queue, visited_structures, "structure", m)
                elif m not in visited_units:
                    enqueue_if_new(queue, visited_units, "unit", m)
    elif morphsto not in visited_structures and morphsto in units_section:
        if is_structure(units_section, morphsto):
            enqueue_if_new(queue, visited_structures, "structure", morphsto)
        elif morphsto not in visited_units:
            enqueue_if_new(queue, visited_units, "unit", morphsto)


def process_ability_morphsto(
    ability_name: ItemName,
    visited_abilities: set[ItemName],
    visited_structures: set[ItemName],
    visited_units: set[ItemName],
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
            units_section,
            queue,
        )


def _load_source_data() -> tuple[dict, dict, dict, dict, dict, dict, dict, dict]:
    """Load all source JSON files and extract sections from techtree."""
    techtree = load_json("../computed/techtree.json")
    unit_data = load_json("UnitData.json", DATA_DIR)
    abil_data = load_json("AbilData.json", DATA_DIR)
    upgrade_data = load_json("UpgradeData.json", DATA_DIR)
    weapon_data = load_json("WeaponData.json", DATA_DIR)

    # Units now contains both structures and units (merged)
    units_section = techtree.get("Units", {})
    structures_section = {}  # No longer separate - merged into Units
    upgrades_section = techtree.get("Upgrades", {})
    abilities_section = techtree.get("Abilities", {})

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
    # Structures are now in units_section
    structure_info = units_section.get(name, {})

    # Handle structure's own morphsto (e.g., Hatchery -> Lair)
    morphsto = structure_info.get(FIELD_MORPHSTO)
    if morphsto:
        handle_morphsto(
            morphsto,
            visited_structures,
            visited_units,
            units_section,
            queue,
        )

    # Add units this structure produces
    produces = structure_info.get(FIELD_PRODUCES, [])
    for unit_name in produces:
        if unit_name not in visited_units:
            enqueue_if_new(queue, visited_units, "unit", unit_name)

    # Add units unlocked by this structure - check units_section
    unlocks = structure_info.get(FIELD_UNLOCKS, [])
    for unlocked_name in unlocks:
        is_struct = unlocked_name not in visited_structures and is_structure(units_section, unlocked_name)
        if unlocked_name in units_section and is_struct:
            enqueue_if_new(queue, visited_structures, "structure", unlocked_name)
        is_unit = unlocked_name not in visited_units and not is_structure(units_section, unlocked_name)
        if unlocked_name in units_section and is_unit:
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
    # Determine category by checking if it's a structure (has builds/researches)
    for race, names in STARTING_UNITS.items():
        for name in names:
            if name in units_section:
                # Use is_structure to determine category
                if is_structure(units_section, name):
                    queue.append(("structure", name))
                else:
                    queue.append(("unit", name))
            else:
                print(f"Warning: Starting item {name} not found in techtree")

    # Initialize with starting structures (tech labs) - check in units_section
    for race, names in STARTING_STRUCTURES.items():
        for name in names:
            if name in units_section:
                queue.append(("structure", name))
            else:
                print(f"Warning: Starting structure {name} not found in techtree")

    # Add explicit STARTING_ABILITIES (e.g., research abilities that aren't discovered via morphsto)
    # These might be button faces (like ResearchStalkerTeleport) that aren't separate ability IDs
    for ability_name in STARTING_ABILITIES:
        if ability_name in abilities_section:
            queue.append(("ability", ability_name))
        else:
            # Add directly to abilities_section with minimal data
            abilities_section[ability_name] = {}
            queue.append(("ability", ability_name))

    # Auto-discover research abilities (abilities whose InfoArray has Resource/Time with upgrade)
    for ability_id, ability in abil_data.items():
        info_array = ability.get("InfoArray", [])
        if not isinstance(info_array, list):
            continue
        for entry in info_array:
            if not isinstance(entry, dict):
                continue
            # Check if this entry has both upgrade and costs
            upgrade = entry.get("Upgrade", "")
            resource = entry.get("Resource", {})
            time_val = entry.get("Time", "0")
            if upgrade and (resource or time_val):
                # This is a research ability with costs
                button_face = entry.get("Button", {}).get("DefaultButtonFace", "")
                ability_name = button_face if button_face else ability_id
                if ability_name not in visited_abilities and ability_name in abilities_section:
                    queue.append(("ability", ability_name))
                elif ability_name not in visited_abilities:
                    abilities_section[ability_name] = {}
                    queue.append(("ability", ability_name))
                break  # Found costs for this ability

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
        "Units": {},
        "Upgrades": {},
        "Abilities": {},
    }

    # Extract upgrade costs from AbilData.json
    upgrade_costs, button_face_to_upgrade = extract_upgrade_costs(abil_data)

    # Extract unit/structure build times from AbilData.json
    unit_build_times = extract_unit_build_times(abil_data)

    # Populate units with full data from UnitData.json
    for unit_name in visited_units:
        unit_entry = units_section.get(unit_name, {})
        full_data = unit_data.get(unit_name, {})
        merged = merge_entry(unit_name, unit_entry, full_data)
        merged["type"] = "unit"
        # Filter builds to exclude mercenary buildings for SCV
        if unit_name == "SCV" and FIELD_BUILDS in merged:
            merged[FIELD_BUILDS] = [b for b in merged[FIELD_BUILDS] if b not in SCV_MERCENARY_BUILDINGS]
        # Add build time if available
        if unit_name in unit_build_times:
            merged["time"] = unit_build_times[unit_name]
        result["Units"][unit_name] = merged

    # Populate structures with full data - structures are now in units_section
    for structure_name in visited_structures:
        structure_entry = units_section.get(structure_name, {})
        full_data = unit_data.get(structure_name, {})
        merged = merge_entry(structure_name, structure_entry, full_data)
        merged["type"] = "structure"
        # Filter builds to exclude mercenary buildings for SCV (handles structures loop)
        if structure_name == "SCV" and FIELD_BUILDS in merged:
            merged[FIELD_BUILDS] = [b for b in merged[FIELD_BUILDS] if b not in SCV_MERCENARY_BUILDINGS]
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
        # Add build time if available
        if structure_name in unit_build_times:
            merged["time"] = unit_build_times[structure_name]
        result["Units"][structure_name] = merged

    # Populate upgrades with full data
    for upgrade_name in visited_upgrades:
        upgrade_entry = upgrades_section.get(upgrade_name, {})
        full_data = upgrade_data.get(upgrade_name, {})
        merged = merge_entry(upgrade_name, upgrade_entry, full_data)
        # Add cost data if available
        if upgrade_name in upgrade_costs:
            merged.update(upgrade_costs[upgrade_name])
        result["Upgrades"][upgrade_name] = merged

    # Populate abilities with full data
    for ability_name in visited_abilities:
        ability_entry = abilities_section.get(ability_name, {})
        full_data = abil_data.get(ability_name) or {}
        merged = merge_entry(ability_name, ability_entry, full_data)
        result["Abilities"][ability_name] = merged

        # Add cost data for research abilities if their upgrade has costs
        if ability_name.endswith("Research"):
            # Check if this ability has an InfoArray with Upgrade entries
            info_array = full_data.get("InfoArray", [])
            if isinstance(info_array, list):
                for entry in info_array:
                    if isinstance(entry, dict) and "Upgrade" in entry:
                        upgrade_name = entry["Upgrade"]
                        if upgrade_name in upgrade_costs:
                            merged.update(upgrade_costs[upgrade_name])
                            break

        # Also add costs for abilities that share an upgrade name (e.g., Stimpack)
        # The upgrade costs (research) should also appear on the unit ability
        if ability_name in upgrade_costs:
            merged.update(upgrade_costs[ability_name])

        # Also look up costs using button face to upgrade mapping
        # (handles abilities like ResearchStalkerTeleport that are button faces in InfoArray)
        if ability_name in button_face_to_upgrade:
            upgrade_name = button_face_to_upgrade[ability_name]
            if upgrade_name in upgrade_costs:
                merged.update(upgrade_costs[upgrade_name])

    # Add weapons data for units that have them
    for unit_name, unit_data_out in result["Units"].items():
        weapons = unit_data_out.get(FIELD_WEAPON, [])
        if isinstance(weapons, list):
            for weapon_name in weapons:
                if weapon_name in weapon_data:
                    _weapons: dict[str, object] = unit_data_out.setdefault("_weapons", {})  # type: ignore[arg-type]
                    _weapons[weapon_name] = weapon_data[weapon_name]

    # Add stableid integer ids (only if not already an integer)
    lookups = _load_stableid_lookups()

    for name, entry in result["Abilities"].items():
        if name in lookups["abilities"] and not isinstance(entry.get("id"), int):
            entry["id"] = lookups["abilities"][name]

    for name, entry in result["Units"].items():
        if entry.get("type") != "unit":
            continue
        if name in lookups["units"] and not isinstance(entry.get("id"), int):
            entry["id"] = lookups["units"][name]

    for name, entry in result["Units"].items():
        if entry.get("type") != "structure":
            continue
        if name in lookups["units"] and not isinstance(entry.get("id"), int):
            entry["id"] = lookups["units"][name]

    for name, entry in result["Upgrades"].items():
        if name in lookups["upgrades"] and not isinstance(entry.get("id"), int):
            entry["id"] = lookups["upgrades"][name]

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
        upgrades_section,
        abilities_section,
        unit_data,
        abil_data,
    )

    # Phase 3: Build final result
    result = _build_result(
        visited_sets,
        units_section,
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
    unit_count = sum(1 for e in data["Units"].values() if e.get("type") == "unit")
    struct_count = sum(1 for e in data["Units"].values() if e.get("type") == "structure")
    print(
        f"Wrote {unit_count} units, {struct_count} structs, "
        f"{len(data['Upgrades'])} upgrades, {len(data['Abilities'])} abilities"
        f" -> {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
