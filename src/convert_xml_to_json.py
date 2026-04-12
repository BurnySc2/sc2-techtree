#!/usr/bin/env python3
"""
Convert merged StarCraft 2 XML data files to JSON format.

Usage: uv run convert_xml_to_json.py
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from utils import dumps_json

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

LINK_ARRAY_TAGS = {"WeaponArray", "AbilArray", "EffectArray"}

# Index as key: <CostResource index="Minerals" value="50"/> -> {"Minerals": 50}
INDEX_AS_KEY_TAGS = {"CostResource", "Vital"}

# Tags returning just the index name regardless of value
# e.g., <AttributeBonus index="Light" value="6"/> -> "Light"
FLAG_VALUE_TAGS = {
    "AttributeBonus",
    "Attributes",
    "CancelableArray",
    "CmdButtonArray",
    "CmdFlags",
    "Collide",
    "CreateFlags",
    "EditorFlags",
    "FlagArray",
    "Flags",
    "LegacyOptions",
    "MatchFlags",
    "Options",
    "PlaneArray",
    "ResponseFlags",
    "SearchFlags",
    "SelectTransferFlags",
    "UninterruptibleArray",
}


def to_number(value: str) -> int | float | str:
    """Try to convert string to int or float, else return as-is."""
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def element_to_value(element: ET.Element, tag_name: str = "") -> Any:
    """Convert a single XML element to its JSON value."""
    attrs = {k: v for k, v in element.attrib.items() if k != "id"}

    # Link-only element: <AbilArray Link="stop"/> -> string
    if set(attrs.keys()) == {"Link"} or set(attrs.keys()) == {"index", "Link"}:
        return attrs["Link"]

    if len(element) > 0:
        children = list(element)
        by_tag: dict[str, list[ET.Element]] = {}
        for child in children:
            by_tag.setdefault(child.tag, []).append(child)

        result: dict[str, Any] = {}
        for tag, matching in by_tag.items():
            values = [element_to_value(c, tag) for c in matching]
            if tag in FLAG_ARRAY_TAGS or len(matching) > 1:
                result[tag] = values
            elif tag_name == "Cost" and tag == "Vital":
                result.update(values[0])
            else:
                result[tag] = values[0]

        for k, v in attrs.items():
            result[k] = to_number(v)
        return result

    # Leaf element handling
    if "index" in attrs and "value" in attrs:
        if tag_name in FLAG_VALUE_TAGS:
            return attrs["index"]
        if tag_name in INDEX_AS_KEY_TAGS:
            return {attrs["index"]: to_number(attrs["value"])}
        return to_number(attrs["value"])

    if (value := attrs.get("value")) is not None:
        return to_number(value)

    if attrs:
        return attrs

    if element.text and (text := element.text.strip()):
        return to_number(text)

    return None


def post_process(data: dict) -> dict:
    """Post-process converted data."""
    for entry in data.values():
        if not isinstance(entry, dict):
            continue

        for tag in LINK_ARRAY_TAGS:
            if tag in entry and isinstance(entry[tag], str):
                entry[tag] = [entry[tag]]

        for tag in INDEX_AS_KEY_TAGS:
            if tag in entry and isinstance(entry[tag], list):
                merged = {}
                for item in entry[tag]:
                    if isinstance(item, dict):
                        merged.update(item)
                entry[tag] = merged

    return data


def convert_xml_to_json(xml_path: Path, output_path: Path) -> dict:
    """Convert a single XML file to JSON."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    result = {elem.get("id"): element_to_value(elem) for elem in root.iter() if elem.get("id")}
    result = post_process(result)

    output_path.write_text(dumps_json(result, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return result


def main():
    input_dir = Path(__file__).parent / "merged"
    output_dir = Path(__file__).parent / "json"
    output_dir.mkdir(exist_ok=True)

    files = ["AbilData", "UnitData", "UpgradeData", "WeaponData", "EffectData"]

    print("Converting SC2 XML files to JSON...\n")

    for name in files:
        xml_path = input_dir / f"{name}.xml"
        json_path = output_dir / f"{name}.json"

        if not xml_path.exists():
            print(f"SKIP: {name}.xml not found")
            continue

        print(f"Converting: {name}.xml -> {name}.json")
        result = convert_xml_to_json(xml_path, json_path)

        try:
            json.loads(json_path.read_text(encoding="utf-8"))
            print(f"  ✓ {len(result)} entries, JSON valid")
        except json.JSONDecodeError as e:
            print(f"  ✗ {len(result)} entries, JSON INVALID: {e}")
        print()

    print("Done!")


if __name__ == "__main__":
    main()
