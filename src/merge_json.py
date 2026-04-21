#!/usr/bin/env python3
"""
Merge SC2 mod JSON files with second-file-wins conflict resolution.
Array tags without index are appended; those with index are updated.

Usage:
    uv run src/merge_json.py
"""

from copy import deepcopy
import json
from pathlib import Path

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

ARRAY_TAGS: set[str] = {
    "Attributes",
    "FlagArray",
    "WeaponArray",
    "CardLayouts",
}


def get_json_path(mod_name: str, data_type: str) -> Path:
    return Path(__file__).parent / "xml/mods" / mod_name / "base.sc2data/GameData" / f"{data_type}.json"


def merge_values(base: dict, override: dict, tag: str) -> dict:
    base_children = base.get(tag, [])
    if not isinstance(base_children, list):
        base_children = [base_children]
        base[tag] = base_children

    for override_child in override.get(tag, []):
        if not isinstance(override_child, dict):
            base[tag] = override_child
            continue
        idx = override_child.get("index")
        if idx is not None:
            for i, base_child in enumerate(base_children):
                if not isinstance(base_child, dict):
                    continue
                if base_child.get("index") == idx:
                    base_children[i] = override_child
                    break
            else:
                base_children.append(deepcopy(override_child))
        else:
            base_children.append(deepcopy(override_child))
    return base


def merge_objects(base: dict, override: dict) -> dict:
    for key, override_val in override.items():
        if key == "index":
            continue
        if key in base:
            base[key] = override_val
        else:
            base[key] = deepcopy(override_val)
    return base


def merge_records(base_list: list[dict], override_list: list[dict]) -> list[dict]:
    base_lookup = {rec.get("id"): rec for rec in base_list if rec.get("id")}
    for override_rec in override_list:
        rec_id = override_rec.get("id")
        if rec_id in base_lookup:
            base_rec = base_lookup[rec_id]
            for tag in ARRAY_TAGS:
                if tag in override_rec:
                    merge_values(base_rec, override_rec, tag)
            for key, val in override_rec.items():
                if key == "id" or key in ARRAY_TAGS:
                    continue
                base_rec[key] = deepcopy(val)
        else:
            base_list.append(deepcopy(override_rec))
    return base_list


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def merge_data_types(data_type: str) -> int:
    result = None
    merged = 0

    for mod_name in MOD_ORDER:
        json_path = get_json_path(mod_name, data_type)
        if not json_path.exists():
            print(f"  [SKIP] {json_path} - not found")
            continue
        print(f"  [MERGE] {mod_name}/{data_type}.json")
        try:
            data = load_json(json_path)
            if result is None:
                result = deepcopy(data)
            else:
                root_key = next(iter(data.keys()))
                if root_key in result and isinstance(result[root_key], list):
                    result[root_key] = merge_records(result[root_key], data[root_key])
                else:
                    result = merge_objects(result, data)
            merged += 1
        except Exception as e:
            print(f"  [ERROR] Failed to load {json_path}: {e}")

    if result is not None:
        output_path = Path(__file__).parent / "json" / f"{data_type}.json"
        output_path.parent.mkdir(exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            dump_json(result, f, indent=2, ensure_ascii=False)
        print(f"  [WRITE] {output_path}")

    return merged


def main():
    print("Merging all SC2 mod JSON files...")
    total = 0
    for data_type in DATA_TYPES:
        print(f"\n[{data_type}]")
        total += merge_data_types(data_type)
    print(f"\nDone! Merged {total} files across {len(DATA_TYPES)} data types.")


if __name__ == "__main__":
    main()
