#!/usr/bin/env python3
"""
Convert merged StarCraft 2 XML data files to JSON format.

Usage: uv run convert_xml_to_json.py
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


# Tags where index+value="1" pairs become arrays of index names
FLAG_ARRAY_TAGS = {
    "FlagArray",
    "PlaneArray",
    "Collide",
    "Attributes",
    "BehaviorArray",
    "EditorFlags",
    "ResourceFlags",
    "GlossaryStrongArray",
    "GlossaryWeakArray",
    "ChanceArray",
    "TauntDuration",
}

# Tags that should always be arrays (even single element)
LINK_ARRAY_TAGS = {"WeaponArray", "AbilArray", "EffectArray"}

# Tags where index is used as the key for the value (not flag style)
INDEX_AS_KEY_TAGS = {"CostResource"}

# Tags where the index name is returned regardless of value (for enum-like attributes)
# e.g., <AttributeBonus index="Light" value="6"/> -> "Light" (not "6" or {"Light": 6})
FLAG_VALUE_TAGS = {"AttributeBonus"}


def element_to_value(element: ET.Element, tag_name: str = "") -> Any:
    """Convert a single XML element to its JSON value."""
    attrs = {k: v for k, v in element.attrib.items() if k != "id"}

    # Link-only element (e.g., <AbilArray Link="stop"/>) -> string
    if set(attrs.keys()) == {"Link"}:
        return attrs["Link"]

    # Has children - recurse
    if len(element) > 0:
        children = list(element)
        child_tags = [c.tag for c in children]
        unique_tags = set(child_tags)

        result = {}
        for tag in unique_tags:
            matching = [c for c in children if c.tag == tag]
            child_val = [element_to_value(c, tag) for c in matching]
            # Flag arrays should always be arrays (even single element)
            if tag in FLAG_ARRAY_TAGS or len(matching) > 1:
                result[tag] = child_val
            else:
                result[tag] = child_val[0]
        return result

    # No children - handle index+value pairs
    if "index" in attrs and "value" in attrs:
        # Flag pattern: index + value="1" -> just the index name (string)
        if attrs["value"] == "1" or tag_name in FLAG_VALUE_TAGS:
            return attrs["index"]
        # Index-as-key pattern: index + value (not "1") -> {"key": value}
        # e.g., <CostResource index="Minerals" value="50"/> -> {"Minerals": 50}
        if tag_name in INDEX_AS_KEY_TAGS:
            try:
                val = int(attrs["value"])
            except ValueError:
                try:
                    val = float(attrs["value"])
                except ValueError:
                    val = attrs["value"]
            return {attrs["index"]: val}
        # Default: return just the value
        try:
            return int(attrs["value"])
        except ValueError:
            try:
                return float(attrs["value"])
            except ValueError:
                return attrs["value"]

    # No children and no index+value - try to extract typed value
    value = attrs.get("value")
    if value is not None:
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value

    # Text content
    text = element.text.strip() if element.text else None
    if text:
        try:
            return int(text)
        except ValueError:
            pass
        try:
            return float(text)
        except ValueError:
            pass
        return text

    return None


def post_process(data: dict) -> dict:
    """Post-process converted data."""

    def process_item(v, tag_name=""):
        if isinstance(v, dict):
            # Check if this is a flag array pattern
            if tag_name in FLAG_ARRAY_TAGS:
                vals = list(v.values())
                if vals and all(isinstance(x, str) for x in vals):
                    return list(v.values())
            return {k: process_item(v[k], k) for k in v}
        elif isinstance(v, list):
            return [process_item(item, tag_name) for item in v]
        return v

    # Process all entries
    for key in data:
        data[key] = process_item(data[key], key)

    # Ensure LINK_ARRAY_TAGS are always arrays
    for key in data:
        if isinstance(data[key], dict):
            for tag in LINK_ARRAY_TAGS:
                if tag in data[key]:
                    val = data[key][tag]
                    if isinstance(val, str):
                        data[key][tag] = [val]

    # Merge INDEX_AS_KEY_TAGS (e.g., CostResource) into single dict
    for key in data:
        if isinstance(data[key], dict):
            for tag in INDEX_AS_KEY_TAGS:
                if tag in data[key]:
                    val = data[key][tag]
                    if isinstance(val, list):
                        # Merge list of dicts into single dict
                        merged = {}
                        for item in val:
                            if isinstance(item, dict):
                                merged.update(item)
                        data[key][tag] = merged

    return data


def convert_xml_to_json(xml_path: Path, output_path: Path) -> dict:
    """Convert a single XML file to JSON."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    result = {}

    # Find all elements with 'id' attribute
    for element in root.iter():
        element_id = element.get("id")
        if element_id is None:
            continue

        parsed = element_to_value(element)
        result[element_id] = parsed

    # Post-process
    result = post_process(result)

    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    return result


def validate_json(json_path: Path) -> bool:
    """Validate that JSON file is parseable."""
    try:
        json.loads(json_path.read_text(encoding="utf-8"))
        return True
    except json.JSONDecodeError as e:
        print(f"  WARNING: JSON validation failed for {json_path}: {e}")
        return False


def main():
    input_dir = Path(__file__).parent / "merged"
    output_dir = Path(__file__).parent / "json"
    output_dir.mkdir(exist_ok=True)

    files = [
        ("AbilData.xml", "AbilData.json"),
        ("UnitData.xml", "UnitData.json"),
        ("UpgradeData.xml", "UpgradeData.json"),
        ("WeaponData.xml", "WeaponData.json"),
        ("EffectData.xml", "EffectData.json"),
    ]

    print("Converting SC2 XML files to JSON...\n")

    for xml_name, json_name in files:
        xml_path = input_dir / xml_name
        json_path = output_dir / json_name

        if not xml_path.exists():
            print(f"SKIP: {xml_name} not found")
            continue

        print(f"Converting: {xml_name} -> {json_name}")

        result = convert_xml_to_json(xml_path, json_path)
        entry_count = len(result)

        if validate_json(json_path):
            print(f"  ✓ {entry_count} entries, JSON valid")
        else:
            print(f"  ✗ {entry_count} entries, JSON INVALID")

        print()

    print("Done!")


if __name__ == "__main__":
    main()
