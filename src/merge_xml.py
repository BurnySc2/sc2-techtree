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


def get_fallback_tree(data_type: str) -> etree._ElementTree | None:
    """Load fallback XML tree for a data type if it exists."""
    fallback_path = Path(__file__).parent / "fallback" / f"{data_type}.xml"
    return etree.parse(str(fallback_path)) if fallback_path.exists() else None


def get_child_key(elem: etree._Element) -> tuple:
    """Get unique key for child element matching: (tag, index, link).
    - Cost/Range use (tag,) only
    - *Array tags include value
    """
    tag = str(elem.tag)

    if tag in OVERRIDE_TAGS:
        return (tag,)

    key = [tag, elem.get("index", ""), elem.get("Link", "")]
    if tag.endswith("Array"):
        key.append(elem.get("value", ""))
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

        tag = str(base_child.tag)
        if len(override_child) > 0 or len(base_child) > 0:
            merge_child_elements(base_child, override_child)
        elif tag.endswith("Array"):
            override_val = override_child.get("value")
            override_link = override_child.get("Link")

            if override_val:
                existing = {c.get("value") for c in base if str(c.tag) == tag}
                if override_val not in existing:
                    base.append(deepcopy(override_child))
            elif override_link:
                existing = {c.get("Link") for c in base if str(c.tag) == tag}
                if override_link not in existing:
                    base.append(deepcopy(override_child))
        else:
            base_child.text = override_child.text
            base_child.attrib.clear()
            base_child.attrib.update(override_child.attrib)

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


def fill_missing_from_fallback(result: etree._ElementTree, data_type: str) -> None:
    """Fill missing children from fallback source."""
    fallback = get_fallback_tree(data_type)
    if fallback is None:
        return

    for parent in result.findall(".//*[@id]"):
        parent_id = parent.get("id")
        fallback_parent = fallback.find(f".//*[@id='{parent_id}']")
        if fallback_parent is None:
            continue

        base_keys = {get_child_key(c) for c in parent}

        for fb_child in fallback_parent:
            key = get_child_key(fb_child)
            if key not in base_keys:
                idx = fb_child.get("index", fb_child.get("Link", ""))
                print(f"  [FALLBACK] Adding missing {fb_child.tag}[@{idx}] to {parent_id}")
                parent.append(deepcopy(fb_child))


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
        fill_missing_from_fallback(result, data_type)
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
