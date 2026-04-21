#!/usr/bin/env python3
"""
Merge SC2 mod XML files with second-file-wins conflict resolution.
Deep child merging: elements with same @id merge children individually.

Usage:
    uv run src/merge_xml.py
"""

from copy import deepcopy
from pathlib import Path

from lxml import etree

MOD_ORDER = [
    "liberty.sc2mod",
    "libertymulti.sc2mod",
    "swarm.sc2mod",
    "swarmmulti.sc2mod",
    "void.sc2mod",
    "voidmulti.sc2mod",
    "balancemulti.sc2mod",
]

DATA_TYPES = ["UnitData", "AbilData", "UpgradeData", "WeaponData", "EffectData"]

OVERRIDE_TAGS = {"Cost", "Range"}


def get_xml_path(mod_name: str, data_type: str) -> Path:
    return Path(__file__).parent / f"xml/mods/{mod_name}/base.sc2data/GameData/{data_type}.xml"


def get_child_key(elem: etree._Element) -> tuple:
    """Get unique key for child element matching: (tag, index, link).
    - Cost/Range use (tag,) only
    - *Array tags include value
    - LayoutButtons includes Face for unique identification
    - index="0" treated as "" (default/unset) since they are semantically equivalent
    """
    tag = str(elem.tag)

    if tag in OVERRIDE_TAGS:
        return (tag,)

    index = elem.get("index", "")
    if index == "0":
        index = ""
    key = [tag, index, elem.get("Link", "")]
    if tag.endswith("Array"):
        key.append(elem.get("value", ""))
    if tag == "LayoutButtons":
        key.append(elem.get("Row", ""))
        key.append(elem.get("Column", ""))
    return tuple(key)


def _build_lookup(parent: etree._Element) -> dict[tuple, etree._Element]:
    """Build child key -> element lookup for a parent element."""
    return {get_child_key(child): child for child in parent}


def merge_child_elements(base: etree._Element, override: etree._Element) -> None:
    """Deep merge override children into base. Second file wins."""
    override_lookup = _build_lookup(override)

    for base_child in list(base):
        key = get_child_key(base_child)
        override_child = override_lookup.get(key)

        if override_child is None:
            continue

        if override_child.get("removed") == "1":
            base.remove(base_child)
            continue

        base_child.attrib.update(override_child.attrib)
        if len(override_child) > 0:
            merge_child_elements(base_child, override_child)

    # Add remaining override children not in base
    base_keys = _build_lookup(base)
    for key, override_child in override_lookup.items():
        if override_child.get("removed") == "1":
            continue
        if key not in base_keys:
            base.append(deepcopy(override_child))


def merge_trees(base: etree._ElementTree, override: etree._ElementTree) -> etree._ElementTree:
    """Merge two XML trees. Override wins for matching @id elements."""
    override_lookup = {e.get("id"): e for e in override.findall(".//*[@id]")}
    merged_ids = set()

    for base_elem in base.findall(".//*[@id]"):
        base_id = base_elem.get("id")
        if base_id in override_lookup:
            merge_child_elements(base_elem, override_lookup[base_id])
            merged_ids.add(base_id)

    root = base.getroot()
    for override_id, elem in override_lookup.items():
        if override_id not in merged_ids:
            root.append(deepcopy(elem))

    return base


def merge_mods(data_type: str, output_path: Path) -> int:
    """Merge all mod XML files for a data type. Returns count of merged mods."""
    result = None
    merged = 0

    for mod_name in MOD_ORDER:
        xml_path = get_xml_path(mod_name, data_type)

        if not xml_path.exists():
            print(f"  [SKIP] {xml_path} - not found")
            continue

        print(f"  [MERGE] {mod_name}/{data_type}.xml")

        try:
            current = etree.parse(str(xml_path))
            result = current if result is None else merge_trees(result, current)
            merged += 1
        except etree.XMLSyntaxError as e:
            print(f"  [ERROR] Failed to parse {xml_path}: {e}")

    if result is not None:
        result.write(str(output_path), xml_declaration=True, encoding="UTF-8", pretty_print=True)
        print(f"  [WRITE] {output_path}")

    return merged


def main():
    print("Merging all SC2 mod data types...")
    total = 0
    for data_type in DATA_TYPES:
        output_path = Path(__file__).parent / "merged" / f"{data_type}.xml"
        output_path.parent.mkdir(exist_ok=True)
        print(f"\n[{data_type}]")
        total += merge_mods(data_type, output_path)
    print(f"\nDone! Merged {total} mod files across {len(DATA_TYPES)} data types.")


if __name__ == "__main__":
    main()
