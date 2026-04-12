#!/usr/bin/env python3
"""
Merge SC2 mod XML files with second-file-wins conflict resolution.

This script merges StarCraft 2 mod XML files (like UnitData.xml) following
the MOD_LOAD_ORDER where later files override earlier ones for matching elements.

Key difference from simple merge: This does DEEP CHILD MERGING, not full element replacement.
For elements with the same @id, child elements are merged individually:
- If override has a child element, it replaces the base child element
- If override doesn't have a child element, the base child element is preserved

This is crucial for SC2 delta files where:
- liberty might have CostResource[Minerals]=150 and CostResource[Vespene]=75
- voidmulti only changes CostResource[Minerals]=125 (delta, no Vespene)
- Result should have CostResource[Minerals]=125 and CostResource[Vespene]=75

Usage:
    uv run merge_xml [--data-type UnitData] [--output merged_UnitData.xml]
    uv run merge_xml --all  # Merge all 5 data types

Dependencies:
    pip install lxml
"""

import argparse
from pathlib import Path
from lxml import etree
from copy import deepcopy

# MOD_LOAD_ORDER: later files override earlier ones
MOD_ORDER = [
    # "core.sc2mod",  # With this enabled, armory unlocks WidowMine instead of Thor in techtree.json
    "liberty.sc2mod",
    "libertymulti.sc2mod",
    "swarm.sc2mod",  # Oracle, HellionTank
    "swarmmulti.sc2mod",  # Cyclone
    "void.sc2mod",  # Adept
    "voidmulti.sc2mod",
    "balancemulti.sc2mod",
]

DATA_TYPES = ["UnitData", "AbilData", "UpgradeData", "WeaponData", "EffectData"]


def get_fallback_path(data_type: str) -> Path | None:
    """Get path to local fallback file for a data type if it exists."""
    fallback_dir = Path(__file__).parent / "fallback"
    fallback_path = fallback_dir / f"{data_type}.xml"
    return fallback_path if fallback_path.exists() else None


def get_fallback_tree(data_type: str) -> etree._ElementTree | None:
    """Load fallback XML tree for a data type."""
    fallback_path = get_fallback_path(data_type)
    if fallback_path:
        return etree.parse(str(fallback_path))
    return None


def load_child_tracking(data_type: str) -> dict:
    """
    Scan all source mods and build a dict of {parent_id: {child_key: set of mods}}.
    This tracks which children each parent has in each source mod.
    """
    tracking = {}
    for mod_name in MOD_ORDER:
        xml_path = get_xml_path(mod_name, data_type)
        if not xml_path.exists():
            continue
        try:
            tree = etree.parse(str(xml_path))
            for parent in tree.findall(".//*[@id]"):
                parent_id = parent.get("id")
                if parent_id not in tracking:
                    tracking[parent_id] = {}
                for child in parent:
                    key = get_child_key(child)
                    if key not in tracking[parent_id]:
                        tracking[parent_id][key] = set()
                    tracking[parent_id][key].add(mod_name)
        except etree.XMLSyntaxError:
            continue
    return tracking


def get_xml_path(mod_name: str, data_type: str) -> Path:
    """Get path to XML file in a mod."""
    return Path(__file__).parent / f"xml/mods/{mod_name}/base.sc2data/GameData/{data_type}.xml"


OVERRIDE_TAGS = {"Cost", "Range"}


def get_child_key(elem: etree._Element) -> tuple:
    """
    Get a unique key for a child element to enable matching.

    For elements with @index, use (tag, index).
    For other elements, use (tag,) with empty string index.
    For *Array tags, include value to differentiate (accumulate multiple values).
    For Cost elements, ignore index since Cost doesn't use indexed children.
    For elements with removed="1", use just (tag,) since they signal removal of that slot.
    """
    tag = str(elem.tag)
    index = elem.get("index", "")
    link = elem.get("Link", "")
    value = elem.get("value", "")
    removed = elem.get("removed", "")

    if tag in OVERRIDE_TAGS:
        return (tag,)

    # Elements with removed="1" signal removal - match by tag only
    if removed == "1":
        return (tag,)

    if tag.endswith("Array"):
        return (tag, index, link, value)
    return (tag, index, link)


def merge_child_elements(base_elem: etree._Element, override_elem: etree._Element) -> None:
    """
    Deep merge child elements from override into base.

    Second file (override) wins:
    - If override has a child, it replaces base's child with same key
    - If override doesn't have a child, base's child is preserved
    - Children only in override are added to base

    Matching is done by (tag, @index, @Link) tuple.
    """
    # Build lookup for override children by their key
    override_lookup = {}
    for child in override_elem:
        key = get_child_key(child)
        override_lookup[key] = child

    # Process base children - replace with override if key matches
    for base_child in list(base_elem):
        key = get_child_key(base_child)
        if key in override_lookup:
            override_child = override_lookup[key]

            # If override has removed="1", remove base child entirely
            if override_child.get("removed") == "1":
                base_elem.remove(base_child)
                del override_lookup[key]
                continue

            # If both have children, recurse for deep merge
            if len(override_child) > 0 or len(base_child) > 0:
                merge_child_elements(base_child, override_child)
                del override_lookup[key]
            elif str(base_child.tag).endswith("Array"):
                # Accumulate *Array values instead of replacing
                base_value = base_child.get("value", "")
                override_value = override_child.get("value", "")
                base_link = base_child.get("Link", "")
                override_link = override_child.get("Link", "")
                if override_value and override_value != base_value:
                    # Check if this value already exists in base's children
                    base_tag = str(base_child.tag)
                    existing_values = {c.get("value") for c in base_elem if str(c.tag) == base_tag}
                    if override_value not in existing_values:
                        new_elem = deepcopy(override_child)
                        base_elem.append(new_elem)
                elif override_link and override_link != base_link:
                    # Link-based array item (e.g., CmdButtonArray) - accumulate if link differs
                    base_tag = str(base_child.tag)
                    existing_links = {c.get("Link") for c in base_elem if str(c.tag) == base_tag}
                    if override_link not in existing_links:
                        new_elem = deepcopy(override_child)
                        base_elem.append(new_elem)
                del override_lookup[key]
            else:
                # Leaf elements - override replaces base's text and attributes
                base_child.text = override_child.text
                # Replace all attributes from override
                for attr in list(base_child.attrib.keys()):
                    del base_child.attrib[attr]
                for attr, val in override_child.attrib.items():
                    base_child.set(attr, val)

                del override_lookup[key]
        # else: keep base child as-is

    # Add remaining override children that weren't in base
    for key, override_child in override_lookup.items():
        # Skip removed="1" elements - they signal removal, not addition
        if override_child.get("removed") == "1":
            continue
        base_elem.append(deepcopy(override_child))


def merge_xml_trees(base_tree: etree._ElementTree, override_tree: etree._ElementTree) -> etree._ElementTree:
    """
    Merge two XML trees - second file (override) wins for matching elements.

    Elements are matched by their 'id' attribute. When an element with the
    same id exists in both trees, child elements are deep merged individually.

    This is DEEP CHILD MERGING:
    - Child elements from override replace matching children in base
    - Children only in base are preserved
    - Children only in override are added
    """
    # Build lookup for all override elements with @id
    override_lookup = {}
    for elem in override_tree.findall(".//*[@id]"):
        override_lookup[elem.get("id")] = elem

    # Track which override elements have been consumed/merged
    consumed_override_ids = set()

    # Process all elements in base tree that have @id
    for base_elem in base_tree.findall(".//*[@id]"):
        base_id = base_elem.get("id")
        if base_id in override_lookup:
            override_elem = override_lookup[base_id]
            # Deep merge child elements instead of full replacement
            merge_child_elements(base_elem, override_elem)
            consumed_override_ids.add(base_id)

    # Add elements that only exist in override (not in base)
    for override_id, override_elem in override_lookup.items():
        if override_id not in consumed_override_ids:
            base_tree.getroot().append(deepcopy(override_elem))

    return base_tree


def fill_missing_children_from_fallback(result_tree: etree._ElementTree, data_type: str) -> None:
    """
    After merging, check for missing children and fill them in from fallback source.

    For each parent element with @id, look at all its children with @index.
    If a child key was not found in ANY source mod (tracked by load_child_tracking),
    but a fallback source is available, copy that child from the fallback.
    """
    fallback_tree = get_fallback_tree(data_type)
    if fallback_tree is None:
        return

    tracking = load_child_tracking(data_type)

    for parent in result_tree.findall(".//*[@id]"):
        parent_id = parent.get("id")

        fallback_parent = fallback_tree.find(f".//*[@id='{parent_id}']")
        if fallback_parent is None:
            continue

        parent_tracking = tracking.get(parent_id, {})

        for fallback_child in fallback_parent:
            child_key = get_child_key(fallback_child)

            # Check if this child was missing from ALL source mods
            if child_key not in parent_tracking or not parent_tracking[child_key]:
                # This child wasn't in any source - check if parent has it
                existing = None
                for existing_child in parent:
                    if get_child_key(existing_child) == child_key:
                        existing = existing_child
                        break

                if existing is None:
                    child_idx = fallback_child.get("index", fallback_child.get("Link", ""))
                    print(f"  [FALLBACK] Adding missing {fallback_child.tag}[@{child_idx}] to {parent_id}")
                    parent.append(deepcopy(fallback_child))


def merge_mods(data_type: str, output_path: Path) -> int:
    """
    Merge all mod XML files for a given data type.

    Args:
        data_type: Type of data (e.g., 'UnitData')
        output_path: Path to write merged output

    Returns:
        Number of mods successfully merged
    """
    result_tree = None
    mods_merged = 0

    for mod_name in MOD_ORDER:
        xml_path = get_xml_path(mod_name, data_type)

        if not xml_path.exists():
            print(f"  [SKIP] {xml_path} - not found")
            continue

        print(f"  [MERGE] {mod_name}/{data_type}.xml")

        try:
            current_tree = etree.parse(str(xml_path))

            result_tree = current_tree if result_tree is None else merge_xml_trees(result_tree, current_tree)

            mods_merged += 1

        except etree.XMLSyntaxError as e:
            print(f"  [ERROR] Failed to parse {xml_path}: {e}")

    if result_tree is not None:
        # Fill in missing children from fallback source
        fill_missing_children_from_fallback(result_tree, data_type)

        # Write merged result
        result_tree.write(str(output_path), xml_declaration=True, encoding="UTF-8", pretty_print=True)
        print(f"  [WRITE] {output_path}")

    return mods_merged


def main():
    parser = argparse.ArgumentParser(description="Merge SC2 mod XML files with second-file-wins deep child merging")
    parser.add_argument(
        "--data-type", choices=DATA_TYPES, default="UnitData", help="Type of data to merge (default: UnitData)"
    )
    parser.add_argument("--output", type=Path, help="Output file path (default: merged_{data_type}.xml)")
    parser.add_argument("--all", action="store_true", help="Merge all 4 data types")

    args = parser.parse_args()

    if args.all:
        print("Merging all SC2 mod data types...")
        total_mods = 0
        for data_type in DATA_TYPES:
            output_folder = Path(__file__).parent / "merged"
            output_folder.mkdir(exist_ok=True)
            output_path = output_folder / f"{data_type}.xml"
            print(f"\n[{data_type}]")
            count = merge_mods(data_type, output_path)
            total_mods += count
        print(f"\nDone! Merged {total_mods} mod files across {len(DATA_TYPES)} data types.")
    else:
        data_type = args.data_type
        output_path = args.output or Path(f"merged_{data_type}.xml")

        print(f"Merging {data_type}.xml from MOD_ORDER:")
        for mod in MOD_ORDER:
            print(f"  - {mod}")
        print()

        mods_merged = merge_mods(data_type, output_path)
        print(f"\nDone! Merged {mods_merged} mod files -> {output_path}")


if __name__ == "__main__":
    main()
