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
    uv run merge_xml --all  # Merge all 4 data types

Dependencies:
    pip install lxml
"""

import argparse
from pathlib import Path
from lxml import etree
from copy import deepcopy

# MOD_LOAD_ORDER: later files override earlier ones
MOD_ORDER = [
    "liberty.sc2mod",
    "libertymulti.sc2mod",
    "balancemulti.sc2mod",
    "voidmulti.sc2mod",
]

DATA_TYPES = ["UnitData", "AbilData", "UpgradeData", "WeaponData"]


def get_xml_path(mod_name: str, data_type: str) -> Path:
    """Get path to XML file in a mod."""
    return Path(__file__).parent / f"xml/mods/{mod_name}/base.sc2data/GameData/{data_type}.xml"


def get_child_key(elem: etree._Element) -> tuple:
    """
    Get a unique key for a child element to enable matching.

    For elements with @index, use (tag, index).
    For other elements, use (tag,) with empty string index.
    """
    tag = elem.tag
    index = elem.get("index", "")
    link = elem.get("Link", "")
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

            # If both have children, recurse for deep merge
            if len(override_child) > 0 or len(base_child) > 0:
                merge_child_elements(base_child, override_child)
            else:
                # Leaf elements - override replaces base's text and attributes
                base_child.text = override_child.text
                # Replace all attributes from override
                for attr in list(base_child.attrib.keys()):
                    del base_child.attrib[attr]
                for attr, val in override_child.attrib.items():
                    base_child.set(attr, val)

            # Mark override as processed
            del override_lookup[key]
        # else: keep base child as-is

    # Add remaining override children that weren't in base
    for key, override_child in override_lookup.items():
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

    # Process all elements in base tree that have @id
    for base_elem in base_tree.findall(".//*[@id]"):
        base_id = base_elem.get("id")
        if base_id in override_lookup:
            override_elem = override_lookup[base_id]
            # Deep merge child elements instead of full replacement
            merge_child_elements(base_elem, override_elem)

    return base_tree


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
