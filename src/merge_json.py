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

# Marker value for entries marked for removal
REMOVED_MARKER = "1"


def parse_index(idx, default=None):
    """Parse index to int, returning default on failure."""
    if idx is None:
        return default
    try:
        return int(idx)
    except (ValueError, TypeError):
        return default


def _detect_removal_type(override_child: dict) -> str | None:
    """Detect removal type from override child.

    Returns:
        "direct" - flat pattern: {"index": N, "removed": "1"}
        "nested" - nested pattern: {SomeField: {index: N, "removed": "1"}, index: "Id"}
        None    - not a removal marker
    """
    if not isinstance(override_child, dict):
        return None

    if override_child.get("index") is None:
        return None

    # Pattern 2: flat removal marker
    if override_child.get("removed") == REMOVED_MARKER:
        return "direct"

    # Pattern 1: nested removal marker
    for field_name in override_child:
        if field_name == "index":
            continue
        field_val = override_child[field_name]
        if isinstance(field_val, dict) and field_val.get("removed") == REMOVED_MARKER:
            return "nested"

    return None


def _find_matching_child(base_children: list, idx) -> int | None:
    """Find index of matching child in base_children.

    Match logic:
    - Explicit index matches, OR
    - base has no index and this is the first entry and override wants index "0"
    """
    for i, base_child in enumerate(base_children):
        if not isinstance(base_child, dict):
            continue
        base_idx = base_child.get("index")
        if base_idx == idx or (base_idx is None and i == 0 and idx == "0"):
            return i
    return None


def _should_replace_all_buttons(override_lb: list, base_lb: list) -> bool:
    """Determine if override LayoutButtons should completely replace base.

    Replacement signal: override has fewer buttons, has explicit indices,
    and base has content.
    """
    if not isinstance(override_lb, list) or not base_lb:
        return False

    override_indices = [btn.get("index") for btn in override_lb if isinstance(btn, dict)]
    explicit_indices = [idx for idx in override_indices if idx is not None]

    return (
        len(override_lb) < len(base_lb)
        and bool(explicit_indices)
        and len(base_lb) > 0
    )


def get_json_path(mod_name: str, data_type: str) -> Path:
    return Path(__file__).parent / "xml/mods" / mod_name / "base.sc2data/GameData" / f"{data_type}.json"


def _merge_layout_buttons(base_lb: list, override_lb: dict) -> list:
    """Merge LayoutButtons entries. If base_lb is a single dict, convert to list first.

    Rules:
    - If override_lb has "removed": "1", remove button at "index"
    - If override_lb has explicit "index", replace/merge at that position
    - If override_lb has no "index" but has button fields (Type/AbilCmd), APPEND (not replace)
    - If override_lb has no "index" and no button fields, APPEND (partial update)
    """
    # Convert single dict to list for uniform handling
    if isinstance(base_lb, dict):
        base_lb = [base_lb]
    elif not isinstance(base_lb, list):
        base_lb = []

    # Handle removal marker
    if override_lb.get("removed") == REMOVED_MARKER:
        idx = override_lb.get("index")
        if idx is not None:
            remove_idx = parse_index(idx)
            if remove_idx is not None and 0 <= remove_idx < len(base_lb):
                base_lb.pop(remove_idx)
        return base_lb

    idx = override_lb.get("index")
    has_button_fields = bool(override_lb.get("Type") or override_lb.get("AbilCmd"))

    if idx is not None:
        # Explicit index provided - find or create target position
        target_idx = parse_index(idx)
        if target_idx is None:
            target_idx = len(base_lb)

        if target_idx < len(base_lb):
            # Position exists - replace fields (keep existing index if override doesn't set it)
            btn = base_lb[target_idx]
            for k, v in override_lb.items():
                if k != "index":
                    btn[k] = v
            btn["index"] = idx
        else:
            # Position doesn't exist - extend base_lb
            while len(base_lb) <= target_idx:
                base_lb.append({})
            base_lb[target_idx] = deepcopy(override_lb)
    else:
        # No explicit index - APPEND as new button
        base_lb.append(deepcopy(override_lb))

    return base_lb


def _merge_child_fields(base_child: dict, override_child: dict) -> None:
    """Merge fields from override_child into base_child (partial update).

    Skips: index, LayoutButtons, None values, removed markers.
    """
    for k, v in override_child.items():
        if k == "index" or k == "LayoutButtons":
            continue
        if v is None:
            continue
        if isinstance(v, dict) and v.get("removed") == REMOVED_MARKER:
            continue
        base_child[k] = v


def _handle_layout_buttons_merge(base_child: dict, override_child: dict, override_lb) -> bool:
    """Handle LayoutButtons merge for a matched child.

    Returns True if LayoutButtons were processed.

    Handles:
    - Removal markers inside LayoutButtons
    - None base (complete replacement)
    - Array vs dict override
    - Complete replacement detection
    """
    base_lb = base_child.get("LayoutButtons", [])

    # Handle removal marker inside LayoutButtons
    if isinstance(override_lb, dict) and override_lb.get("removed") == REMOVED_MARKER:
        lb_idx = override_lb.get("index")
        parsed_idx = parse_index(lb_idx)
        if parsed_idx is not None and isinstance(base_lb, list):
            if 0 <= parsed_idx < len(base_lb):
                base_lb.pop(parsed_idx)
        return True

    # Special case: base_children[i] is None (base was null), replace entirely
    if base_child is None:
        base_child.update(override_child)
        return True

    # Convert to list for uniform handling
    if isinstance(base_lb, dict):
        base_lb = [base_lb]

    if isinstance(override_lb, list):
        # Check if this signals complete replacement
        if _should_replace_all_buttons(override_lb, base_lb):
            base_lb = []
            for i, override_btn in enumerate(override_lb):
                if isinstance(override_btn, dict):
                    btn_copy = dict(override_btn)
                    if btn_copy.get("index") is None:
                        btn_copy["index"] = str(i)
                    base_lb.append(btn_copy)
        else:
            for override_btn in override_lb:
                if isinstance(override_btn, dict):
                    base_lb = _merge_layout_buttons(base_lb, override_btn)
    else:
        base_lb = _merge_layout_buttons(base_lb, override_lb)

    base_child["LayoutButtons"] = base_lb
    return True


def merge_values(base: dict, override: dict, tag: str) -> dict:
    """Merge ARRAY_TAGS entries (Attributes, FlagArray, WeaponArray, CardLayouts, InfoArray, AbilArray)."""
    base_children = base.get(tag, [])
    if not isinstance(base_children, list):
        base_children = [base_children]
        base[tag] = base_children

    override_children = override.get(tag)
    # Track if override explicitly set this to None (e.g., CardLayouts: null)
    override_was_null = override_children is None
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
        removal_type = _detect_removal_type(override_child)

        if removal_type == "direct":
            # Pattern 2: flat removal - remove from base_children
            idx = override_child.get("index")
            matched_idx = _find_matching_child(base_children, idx)
            if matched_idx is not None:
                base_children.pop(matched_idx)
            continue
        elif removal_type == "nested":
            # Pattern 1: nested removal - fall through to index-based matching
            # which will handle removal via LayoutButtons
            pass  # Fall through to normal processing
        # removal_type is None: not a removal marker, proceed normally

        idx = override_child.get("index")
        if idx is not None:
            matched_idx = _find_matching_child(base_children, idx)

            if matched_idx is not None:
                base_child = base_children[matched_idx]
                override_lb = override_child.get("LayoutButtons")
                # Handle LayoutButtons merge (returns True if processed)
                if override_lb is not None and isinstance(override_lb, (dict, list)):
                    lb_processed = _handle_layout_buttons_merge(base_child, override_child, override_lb)
                else:
                    # Override lacks LayoutButtons - merge fields (partial update)
                    _merge_child_fields(base_child, override_child)
            else:
                base_children.append(deepcopy(override_child))
        else:
            base_children.append(deepcopy(override_child))
    # If override explicitly set this to null (override had tag: null), preserve that
    # Otherwise, if base_children is a single-element list containing a dict with index,
    # it was originally a single dict (wrapped for processing) - unwrap it back
    if override_was_null:
        # Override explicitly set this to null - preserve that
        base[tag] = None
    elif len(base_children) == 1 and isinstance(base_children[0], dict):
        base[tag] = base_children[0]
    return base


def _find_array_key_for_index(override_val: dict, base_val, idx) -> str | None:
    """Find the array key used for index-based array updates.

    Handles two cases:
    1. Nested: {Key: {sub_key: value, index: N}} - update base[Key][sub_key][N]
    2. Simple: {ArrayKey: [...], index: N} - update base[ArrayKey][N]

    Returns the array key if found, None otherwise.
    """
    # First, check for nested index pattern
    for sub_key in override_val:
        if sub_key == "index":
            continue
        if isinstance(override_val[sub_key], dict) and "index" in override_val[sub_key]:
            # Nested index: recursively handle
            if isinstance(base_val, list) and 0 <= idx < len(base_val):
                merge_objects(base_val[idx], {sub_key: override_val[sub_key], "index": override_val["index"]})
            elif isinstance(base_val, dict) and sub_key in base_val and isinstance(base_val[sub_key], list):
                merge_objects(base_val, {sub_key: override_val[sub_key], "index": override_val["index"]})
            return sub_key

    # Simple case: find sibling array and replace/merge element at index
    numeric_idx = parse_index(idx)
    if numeric_idx is None:
        return None

    for sub_key in override_val:
        if sub_key == "index":
            continue
        if not isinstance(base_val, dict):
            continue
        arr = base_val.get(sub_key)
        if not isinstance(arr, list):
            continue
        if 0 <= numeric_idx < len(arr):
            if isinstance(override_val[sub_key], dict):
                arr[numeric_idx].update(override_val[sub_key])
            else:
                arr[numeric_idx] = deepcopy(override_val[sub_key])
            return sub_key

    return None


def merge_objects(base: dict, override: dict) -> dict:
    for key, override_val in override.items():
        if key == "index":
            continue
        if key in ARRAY_TAGS:
            continue
        if key not in base:
            base[key] = deepcopy(override_val)
            continue

        if isinstance(override_val, dict) and "index" in override_val:
            idx = override_val["index"]
            base_val = base[key]
            array_key = _find_array_key_for_index(override_val, base_val, idx)
            if array_key is not None:
                continue  # Handled via array index

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
