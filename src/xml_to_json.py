#!/usr/bin/env python3
"""
Convert SC2 mod XML files to JSON format.
Place JSON files next to the input XML files.

Usage:
    uv run src/xml_to_json.py
"""

from pathlib import Path

from lxml import etree

from utils import dump_json

MOD_ORDER = [
    "liberty.sc2mod",
    "libertymulti.sc2mod",
    "swarm.sc2mod",
    "swarmmulti.sc2mod",
    "void.sc2mod",
    "voidmulti.sc2mod",
]

DATA_TYPES = ["UnitData", "AbilData", "UpgradeData", "WeaponData", "EffectData"]


def _postprocess_index_value(child_list: list[dict]) -> dict:
    return {c["index"]: c["value"] for c in child_list}


def _postprocess_value_only(child_list: list[dict]) -> dict:
    return {child_list[0].keys().__iter__().__next__(): c["value"] for c in child_list}


def _postprocess_entries(children_by_tag: dict) -> dict:
    result = {}
    for tag, child_list in children_by_tag.items():
        if len(child_list) > 1:
            all_simple = all(
                set(c.keys()) == {"index", "value"} or set(c.keys()) == {"value"}
                for c in child_list
            )
            if all_simple:
                if all("index" in c for c in child_list):
                    result[tag] = _postprocess_index_value(child_list)
                else:
                    result[tag] = _postprocess_value_only(child_list)
            else:
                result[tag] = child_list
        elif len(child_list) == 1:
            c = child_list[0]
            if set(c.keys()) == {"index", "value"}:
                result[tag] = _postprocess_index_value([c])
            elif set(c.keys()) == {"value"}:
                result[tag] = c["value"]
            else:
                result[tag] = c
    return result


def _grab_entries(elem: etree._Element) -> tuple[dict, dict]:
    attrib = dict(elem.attrib)
    children_by_tag: dict = {}
    for child in elem:
        if isinstance(child, etree._Comment):
            continue
        child_tag = child.tag
        if not isinstance(child_tag, str):
            continue
        child_data = elem_to_dict(child)
        if child_tag in children_by_tag:
            children_by_tag[child_tag].append(child_data)
        else:
            children_by_tag[child_tag] = [child_data]
    return attrib, children_by_tag


def elem_to_dict(elem: etree._Element) -> dict:
    attrib, children_by_tag = _grab_entries(elem)
    result = _postprocess_entries(children_by_tag)
    for k, v in attrib.items():
        if k not in result:
            result[k] = v
    return result


def convert_xml_to_json(xml_path: Path) -> bool:
    try:
        tree = etree.parse(str(xml_path))
        root = tree.getroot()
        data = elem_to_dict(root)
        json_path = xml_path.with_suffix(".json")
        with json_path.open("w", encoding="utf-8") as f:
            dump_json(data, f, indent=2, ensure_ascii=False)
        return True
    except (etree.XMLSyntaxError, OSError) as e:
        print(f"  [ERROR] Failed to convert {xml_path}: {e}")
        return False


def convert_mods():
    total = 0
    for mod_name in MOD_ORDER:
        for data_type in DATA_TYPES:
            xml_path = Path(__file__).parent / "xml/mods" / mod_name / "base.sc2data/GameData" / f"{data_type}.xml"
            if not xml_path.exists():
                print(f"  [SKIP] {xml_path} - not found")
                continue
            print(f"  [CONVERT] {mod_name}/{data_type}.xml")
            if convert_xml_to_json(xml_path):
                print(f"  [WRITE] {xml_path.with_suffix('.json')}")
                total += 1
    return total


def main():
    print("Converting SC2 mod XML files to JSON...")
    total = convert_mods()
    print(f"\nDone! Converted {total} files.")


if __name__ == "__main__":
    main()
