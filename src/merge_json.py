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
    "InfoArray",
    "AbilArray",
}


def get_json_path(mod_name: str, data_type: str) -> Path:
    return Path(__file__).parent / "xml/mods" / mod_name / "base.sc2data/GameData" / f"{data_type}.json"


def _merge_layout_buttons(base_lb: list, override_lb: dict) -> list:
    """Merge LayoutButtons entries. If base_lb is a single dict, convert to list first.

    The index field in override_lb specifies which button entry to update:
    - If a button with matching index exists in base_lb, update its fields
    - If no match and index is specified, extend base_lb to that index and set it
    - If no index, append as new button
    """
    # Convert single dict to list for uniform handling
    if isinstance(base_lb, dict):
        base_lb = [base_lb]
    elif not isinstance(base_lb, list):
        base_lb = []

    idx = override_lb.get("index")
    if idx is not None:
        # Look for existing button with matching explicit index
        matched = False
        for i, btn in enumerate(base_lb):
            if isinstance(btn, dict) and btn.get("index") == idx:
                # Update existing button's fields (except index)
                for k, v in override_lb.items():
                    if k != "index":
                        btn[k] = v
                matched = True
                break

        if not matched:
            # No button with matching explicit index
            # If override has explicit index and base has buttons without explicit indices,
            # try to match by array position
            try:
                target_idx = int(idx)
            except ValueError:
                target_idx = len(base_lb)

            if target_idx < len(base_lb):
                # There's a button at this position without explicit index - update it
                btn = base_lb[target_idx]
                for k, v in override_lb.items():
                    if k != "index":
                        btn[k] = v
                # Set the index field so future merges can match explicitly
                btn["index"] = idx
            else:
                # Extend base_lb if needed
                while len(base_lb) <= target_idx:
                    base_lb.append({})
                base_lb[target_idx] = deepcopy(override_lb)
    else:
        # No index: append as new button
        base_lb.append(deepcopy(override_lb))

    return base_lb


def merge_values(base: dict, override: dict, tag: str) -> dict:
    base_children = base.get(tag, [])
    if not isinstance(base_children, list):
        base_children = [base_children]
        base[tag] = base_children

    override_children = override.get(tag)
    if not isinstance(override_children, list):
        # Single dict entry (e.g., CardLayouts: {LayoutButtons: {...}, index: "0"})
        # Treat as a single item to merge at the specified index
        if isinstance(override_children, dict):
            override_children = [override_children]
        else:
            override_children = []

    for override_child in override_children:
        if not isinstance(override_child, dict):
            # Skip non-dict items (e.g., field name lists like ["Time", "index"])
            continue
        # Check if this override entry marks the base entry for removal
        # Pattern 1 (nested): {SomeField: {index: "0"/N, removed: "1"}, index: "SomeId"}
        # Pattern 2 (flat):   {index: "N", removed: "1"} -- direct removal marker
        # Both mean "remove the base entry at index N"
        should_remove = False
        if override_child.get("index") is not None:
            # Check for flat removal marker: {"index": N, "removed": "1"}
            if override_child.get("removed") == "1":
                should_remove = True
            else:
                # Check for nested removal pattern
                for field_name in override_child:
                    if field_name == "index":
                        continue
                    field_val = override_child[field_name]
                    if isinstance(field_val, dict) and field_val.get("removed") == "1":
                        # This entry marks a base entry for removal
                        should_remove = True
                        break
        if should_remove:
            # Find and remove the matching base entry
            idx = override_child.get("index")
            for i, base_child in enumerate(base_children):
                if isinstance(base_child, dict) and base_child.get("index") == idx:
                    base_children.pop(i)
                    break
            # Always skip - removal markers are directives, never entries to append
            continue
        idx = override_child.get("index")
        if idx is not None:
            matched = False
            for i, base_child in enumerate(base_children):
                if not isinstance(base_child, dict):
                    continue
                base_idx = base_child.get("index")
                # Match if: explicit index matches, OR
                # base has no index and this is the first entry and override wants index 0
                if base_idx == idx or (base_idx is None and i == 0 and idx == "0"):
                    override_lb = override_child.get("LayoutButtons")
                    # Always merge LayoutButtons when present - convert single dict to array if needed
                    if override_lb is not None and isinstance(override_lb, (dict, list)):
                        base_lb = base_child.get("LayoutButtons", [])
                        if isinstance(base_lb, dict):
                            base_lb = [base_lb]
                        if isinstance(override_lb, list):
                            # Override has array - merge each element
                            for override_btn in override_lb:
                                if isinstance(override_btn, dict):
                                    base_lb = _merge_layout_buttons(base_lb, override_btn)
                        else:
                            # Override has single dict
                            base_lb = _merge_layout_buttons(base_lb, override_lb)
                        base_child["LayoutButtons"] = base_lb
                    else:
                        # Override lacks LayoutButtons - merge fields (partial update)
                        # Only copy non-None, non-removed values from override
                        for k, v in override_child.items():
                            if k != "index":
                                # Skip None and {'index': '0', 'removed': '1'} (removal markers)
                                if v is None:
                                    continue
                                if isinstance(v, dict) and v.get("removed") == "1":
                                    continue
                                base_children[i][k] = v
                    matched = True
                    break
            if not matched:
                base_children.append(deepcopy(override_child))
        else:
            base_children.append(deepcopy(override_child))
    return base


def merge_objects(base: dict, override: dict) -> dict:
    for key, override_val in override.items():
        if key == "index":
            continue
        if key not in base:
            base[key] = deepcopy(override_val)
            continue

        # Handle index-based array updates: {Key: {sub_key: value, index: N}}
        # means "update base[Key][sub_key][N] with value"
        if isinstance(override_val, dict) and "index" in override_val:
            idx = override_val["index"]
            base_val = base[key]

            # Find the sibling key that has an array (skip "index")
            array_key = None
            for sub_key in override_val:
                if sub_key != "index" and isinstance(override_val[sub_key], dict) and "index" in override_val[sub_key]:
                    # Nested index: recursively handle
                    if isinstance(base_val, list) and 0 <= idx < len(base_val):
                        merge_objects(base_val[idx], {sub_key: override_val[sub_key], "index": override_val["index"]})
                    elif isinstance(base_val, dict) and sub_key in base_val and isinstance(base_val[sub_key], list):
                        merge_objects(base_val, {sub_key: override_val[sub_key], "index": override_val["index"]})
                    array_key = sub_key
                    break

            if array_key is None:
                # Simple case: find sibling array and replace/merge element at index
                # Only use numeric indices; non-numeric indices (like 'Ammo1') are field values
                try:
                    numeric_idx = int(idx)
                except (ValueError, TypeError):
                    numeric_idx = None

                if numeric_idx is not None:
                    for sub_key in override_val:
                        if (
                            sub_key != "index"
                            and isinstance(base_val, dict)
                            and isinstance(base_val.get(sub_key), list)
                        ):
                            arr = base_val[sub_key]
                            if 0 <= numeric_idx < len(arr):
                                if isinstance(override_val[sub_key], dict):
                                    # Dict value = partial update, merge into array element
                                    arr[numeric_idx].update(override_val[sub_key])
                                else:
                                    # Non-dict value = replace array element
                                    arr[numeric_idx] = deepcopy(override_val[sub_key])
                            array_key = sub_key
                            break
                    if array_key is not None:
                        continue  # We handled this key via array index, skip normal assignment
            continue

        base[key] = override_val
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
                for root_key in data.keys():
                    if root_key in result:
                        if isinstance(result[root_key], list) and isinstance(data[root_key], list):
                            result[root_key] = merge_records(result[root_key], data[root_key])
                        elif isinstance(result[root_key], dict) and isinstance(data[root_key], dict):
                            result[root_key] = merge_objects(result[root_key], data[root_key])
                        else:
                            # Type mismatch: override wins
                            result[root_key] = deepcopy(data[root_key])
                    else:
                        result[root_key] = deepcopy(data[root_key])
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
