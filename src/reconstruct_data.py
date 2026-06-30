#!/usr/bin/env python3
"""Gather reachable units, structures, and upgrades from SC2 techtree."""

from collections import deque
import json
from pathlib import Path
from typing import TypeAlias

from utils import dump_json, load_json, extract_abil_name

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

# Structure detection constants (from generate_techtree.py)
EDITOR_CAT_STRUCTURE = "ObjectType:Structure"
TECH_LABS = {
    "BarracksTechLab",
    "FactoryTechLab",
    "StarportTechLab",
}

# Type aliases
Category: TypeAlias = str
ItemName: TypeAlias = str
QueueItem: TypeAlias = tuple[Category, ItemName]
VisitedSets: TypeAlias = dict[str, set[ItemName]]


def is_structure(units_section: dict, name: ItemName, unit_data: dict | None = None) -> bool:
    """Check if an entry is a structure using EditorCategories or TECH_LABS, with fallback heuristic."""
    # Primary check: use unit_data EditorCategories (authoritative source)
    if unit_data is not None:
        entry_data = unit_data.get(name)
        if isinstance(entry_data, dict):
            editor_categories = entry_data.get("EditorCategories", "")
            if isinstance(editor_categories, list):
                if EDITOR_CAT_STRUCTURE in editor_categories:
                    return True
            elif EDITOR_CAT_STRUCTURE in str(editor_categories):
                return True
            # Check TECH_LABS (structures without ObjectType:Structure)
            return name in TECH_LABS

    # Fallback heuristic if unit_data not provided or entry not found
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
        if ability_id == "WarpGateTrain":
            continue  # Skip warp-in times; use regular train times from GatewayTrain
        # AbilData.json has entries where ability can be a list or a dict
        # If it's a list, iterate through; if it's a dict, process directly
        entries = ability if isinstance(ability, list) else [ability]

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            info_array = entry.get("InfoArray", [])
            if isinstance(info_array, dict):
                unit_name = info_array.get("Unit", "")
                if isinstance(unit_name, dict) and "value" in unit_name:
                    unit_name = unit_name["value"]

                if not isinstance(unit_name, str):
                    continue

                time_str = info_array.get("Time", "0")

                section_array = info_array.get("SectionArray", [])
                if isinstance(section_array, list) and unit_name:
                    max_delay: float | None = None
                    for section in section_array:
                        if not isinstance(section, dict):
                            continue
                        duration_array = section.get("DurationArray", {})
                        if isinstance(duration_array, dict):
                            delay = duration_array.get("Delay")
                            if delay is not None and delay != 0:
                                try:
                                    delay_val = (
                                        float(delay)
                                        if isinstance(delay, float) or (isinstance(delay, str) and "." in delay)
                                        else int(delay)
                                    )
                                    if max_delay is None or delay_val > max_delay:
                                        max_delay = delay_val
                                except (ValueError, TypeError):
                                    pass
                    if max_delay is not None and unit_name not in unit_build_times:
                        unit_build_times[unit_name] = max_delay
                        continue

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
                    if isinstance(unit_name, dict) and "value" in unit_name:
                        unit_name = unit_name["value"]
                    time_str = item.get("Time", "0")

                    if unit_name and time_str and time_str != "0":
                        try:
                            time_val = float(time_str) if "." in time_str else int(time_str)
                            unit_build_times[unit_name] = time_val
                        except (ValueError, TypeError):
                            pass

                    # Fall back to SectionArray.Delay pattern for list items (e.g., MorphToLurker)
                    # Keep max delay across all abilities (not just skip if already exists)
                    if not isinstance(unit_name, str) or not unit_name:
                        continue

                    section_array = item.get("SectionArray", [])
                    if isinstance(section_array, list):
                        max_delay: float | None = None
                        for section in section_array:
                            if not isinstance(section, dict):
                                continue
                            duration_array = section.get("DurationArray", {})
                            if isinstance(duration_array, dict):
                                delay = duration_array.get("Delay")
                                if delay is not None and delay != 0:
                                    try:
                                        delay_val = (
                                            float(delay)
                                            if isinstance(delay, float) or (isinstance(delay, str) and "." in delay)
                                            else int(delay)
                                        )
                                        if max_delay is None or delay_val > max_delay:
                                            max_delay = delay_val
                                    except (ValueError, TypeError):
                                        pass
                        if max_delay is not None and unit_name not in unit_build_times:
                            unit_build_times[unit_name] = max_delay

    return unit_build_times


def extract_batch_counts(abil_data: dict) -> dict[str, int]:
    """Extract batch training counts from AbilData.json.

    When a training ability trains multiple units at once (e.g., Zergling x2),
    the Unit field in InfoArray is a dict with "value" and "count" keys.

    Returns:
        dict mapping unit name -> batch count (only entries with count > 1)
    """
    batch_counts: dict[str, int] = {}

    for ability_id, ability in abil_data.items():
        entries = ability if isinstance(ability, list) else [ability]

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            info_array = entry.get("InfoArray", [])
            if isinstance(info_array, list):
                for item in info_array:
                    if not isinstance(item, dict):
                        continue
                    unit = item.get("Unit", "")
                    if isinstance(unit, dict):
                        count = unit.get("count", 1)
                        unit_name = unit.get("value", "")
                        if isinstance(count, (int, float)) and count > 1 and isinstance(unit_name, str) and unit_name:
                            batch_counts[unit_name] = int(count)
            elif isinstance(info_array, dict):
                unit = info_array.get("Unit", "")
                if isinstance(unit, dict):
                    count = unit.get("count", 1)
                    unit_name = unit.get("value", "")
                    if isinstance(count, (int, float)) and count > 1 and isinstance(unit_name, str) and unit_name:
                        batch_counts[unit_name] = int(count)

    return batch_counts


def enqueue_if_new(
    queue: deque[QueueItem],
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


def _build_cocoon_index(units_section: dict) -> dict[str, list[str]]:
    """Build a reverse index mapping morph target -> cocoon unit names.

    Cocoon units are intermediate morph forms (e.g., RavagerCocoon morphs to Ravager).
    They need to be discovered alongside their morph target during BFS traversal.
    """
    cocoon_index: dict[str, list[str]] = {}
    for unit_name, unit_info in units_section.items():
        if "Cocoon" in unit_name and isinstance(unit_info, dict):
            morphsto = unit_info.get(FIELD_MORPHSTO)
            if morphsto:
                if isinstance(morphsto, str):
                    targets = [morphsto]
                elif isinstance(morphsto, list):
                    targets = morphsto
                else:
                    continue
                for target in targets:
                    if isinstance(target, str):
                        cocoon_index.setdefault(target, []).append(unit_name)
    return cocoon_index


def handle_morphsto(
    morphsto: str | list,
    visited_structures: set[ItemName],
    visited_units: set[ItemName],
    units_section: dict,
    queue: deque[QueueItem],
    cocoon_index: dict[str, list[str]] | None = None,
    unit_data: dict | None = None,
) -> None:
    """Process morphsto field, enqueueing structures or units as needed."""
    if not morphsto:
        return

    if isinstance(morphsto, list):
        for m in morphsto:
            if m and m not in visited_structures and m in units_section:
                # Use is_structure to identify if this is a structure
                if is_structure(units_section, m, unit_data):
                    enqueue_if_new(queue, visited_structures, "structure", m)
                elif m not in visited_units:
                    enqueue_if_new(queue, visited_units, "unit", m)
    elif morphsto not in visited_structures and morphsto in units_section:
        if is_structure(units_section, morphsto, unit_data):
            enqueue_if_new(queue, visited_structures, "structure", morphsto)
        elif morphsto not in visited_units:
            enqueue_if_new(queue, visited_units, "unit", morphsto)

    # Also discover cocoon units that morph into the same target
    if cocoon_index:
        targets = [morphsto] if isinstance(morphsto, str) else morphsto
        if isinstance(targets, list):
            for target in targets:
                for cocoon_name in cocoon_index.get(target, []):
                    if cocoon_name not in visited_units:
                        enqueue_if_new(queue, visited_units, "unit", cocoon_name)


def process_ability_morphsto(
    ability_name: ItemName,
    visited_abilities: set[ItemName],
    visited_structures: set[ItemName],
    visited_units: set[ItemName],
    units_section: dict,
    abilities_section: dict,
    queue: deque[QueueItem],
    cocoon_index: dict[str, list[str]] | None = None,
    unit_data: dict | None = None,
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
            cocoon_index,
            unit_data,
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
    queue: deque[QueueItem],
    cocoon_index: dict[str, list[str]] | None = None,
) -> None:
    """Handle unit abilities, builds, produces, morphsto, requirements."""
    unit_info = units_section.get(name, {})
    unit_full_data = resolve_parent_fields(name, unit_data)

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
            cocoon_index,
            unit_data,
        )

    # Add abilities from this unit's AbilArray (extract Link from each entry)
    abil_array = unit_full_data.get(FIELD_ABIL_ARRAY, [])
    for ability_entry in abil_array:
        ability_name = extract_abil_name(ability_entry)

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
                cocoon_index,
                unit_data,
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
    queue: deque[QueueItem],
    cocoon_index: dict[str, list[str]] | None = None,
    unit_data: dict | None = None,
    abil_data: dict | None = None,
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
            cocoon_index,
            unit_data,
        )

    # Add units this structure produces
    produces = structure_info.get(FIELD_PRODUCES, [])
    for unit_name in produces:
        if unit_name not in visited_units:
            enqueue_if_new(queue, visited_units, "unit", unit_name)

    # Add units unlocked by this structure - check units_section
    unlocks = structure_info.get(FIELD_UNLOCKS, [])
    for unlocked_name in unlocks:
        is_struct = unlocked_name not in visited_structures and is_structure(units_section, unlocked_name, unit_data)
        if unlocked_name in units_section and is_struct:
            enqueue_if_new(queue, visited_structures, "structure", unlocked_name)
        is_unit = unlocked_name not in visited_units and not is_structure(units_section, unlocked_name, unit_data)
        if unlocked_name in units_section and is_unit:
            enqueue_if_new(queue, visited_units, "unit", unlocked_name)

    # Add structures this structure can build (e.g., NydusNetwork -> NydusCanal)
    builds = structure_info.get(FIELD_BUILDS, [])
    for structure_name in builds:
        if structure_name not in visited_structures:
            enqueue_if_new(queue, visited_structures, "structure", structure_name)

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

    # Add abilities from this structure's AbilArray (from UnitData.json)
    structure_full_data = resolve_parent_fields(name, unit_data) if unit_data else {}
    abil_array = structure_full_data.get(FIELD_ABIL_ARRAY, [])
    for ability_entry in abil_array:
        ability_name = extract_abil_name(ability_entry)
        if (
            ability_name
            and isinstance(ability_name, str)
            and abil_data
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
                cocoon_index,
                unit_data,
            )

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
            cocoon_index,
            unit_data,
        )


def _process_upgrade(
    name: ItemName,
    upgrades_section: dict,
    units_section: dict,
    visited_upgrades: set[ItemName],
    visited_structures: set[ItemName],
    queue: deque[QueueItem],
) -> None:
    """Handle upgrade requirements."""
    upgrade_info = upgrades_section.get(name, {})

    # Add requirements for this upgrade
    for req in upgrade_info.get(FIELD_REQUIRES, []):
        # Check if this requirement is a structure (if it exists in units_section)
        # Some upgrades require structures, not other upgrades
        if req in units_section and req not in visited_structures:
            enqueue_if_new(queue, visited_structures, "structure", req)
        elif req not in visited_upgrades:
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

    # Build cocoon index for discovering intermediate morph forms
    cocoon_index = _build_cocoon_index(units_section)

    # Queue for BFS: (category, name)
    queue: deque[QueueItem] = deque()

    # Initialize with starting units and structures (just queue, visited added when popped)
    # Determine category by checking if it's a structure (has builds/researches)
    for race, names in STARTING_UNITS.items():
        for name in names:
            if name in units_section:
                # Use is_structure to determine category
                if is_structure(units_section, name, unit_data):
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
        category, name = queue.popleft()

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
                cocoon_index,
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
                cocoon_index,
                unit_data,
                abil_data,
            )

        elif category == "upgrade":
            if name in visited_upgrades:
                continue
            # Skip if this is actually a structure (shouldn't happen, but guard anyway)
            if name in units_section:
                # Redirect to structure processing instead
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
                    cocoon_index,
                    unit_data,
                    abil_data,
                )
                continue
            # Add to visited BEFORE processing
            visited_upgrades.add(name)

            _process_upgrade(
                name,
                upgrades_section,
                units_section,
                visited_upgrades,
                visited_structures,
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
                cocoon_index,
                unit_data,
            )

    return {
        "units": visited_units,
        "structures": visited_structures,
        "upgrades": visited_upgrades,
        "abilities": visited_abilities,
    }


def resolve_parent_fields(unit_name: str, unit_data: dict, _visited: set | None = None) -> dict:
    """Resolve inherited fields from parent unit. Child fields take precedence."""
    if _visited is None:
        _visited = set()
    if unit_name in _visited:
        return {}
    _visited.add(unit_name)

    data = unit_data.get(unit_name, {})
    if not isinstance(data, dict):
        return {}

    parent = data.get("parent")
    if parent and parent in unit_data:
        parent_data = resolve_parent_fields(parent, unit_data, _visited)
        merged = {}
        merged.update(parent_data)
        merged.update(data)
        return merged
    return data


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

    # Extract batch training counts (e.g., Zergling trains 2 at a time)
    batch_counts = extract_batch_counts(abil_data)

    # Populate units with full data from UnitData.json
    for unit_name in visited_units:
        unit_entry = units_section.get(unit_name, {})
        full_data = resolve_parent_fields(unit_name, unit_data)
        merged = merge_entry(unit_name, unit_entry, full_data)
        merged["type"] = "unit"
        # Filter builds to exclude mercenary buildings for SCV
        if unit_name == "SCV" and FIELD_BUILDS in merged:
            merged[FIELD_BUILDS] = [b for b in merged[FIELD_BUILDS] if b not in SCV_MERCENARY_BUILDINGS]
        # Add build time if available
        if unit_name in unit_build_times:
            merged["time"] = unit_build_times[unit_name]
        # Apply batch training count to costs (e.g., Zergling x2 -> multiply Food, Minerals, Vespene)
        if unit_name in batch_counts:
            count = batch_counts[unit_name]
            if "Food" in merged and isinstance(merged["Food"], (int, float)):
                merged["Food"] = merged["Food"] * count
            if "CostResource" in merged and isinstance(merged["CostResource"], dict):
                for field in ("Minerals", "Vespene"):
                    if field in merged["CostResource"] and isinstance(merged["CostResource"][field], (int, float)):
                        merged["CostResource"][field] = merged["CostResource"][field] * count
        result["Units"][unit_name] = merged

    # Populate structures with full data - structures are now in units_section
    for structure_name in visited_structures:
        structure_entry = units_section.get(structure_name, {})
        full_data = resolve_parent_fields(structure_name, unit_data)
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
