import json
from pathlib import Path


def load_json(filename: str, base_dir: Path | None = None) -> dict:
    """Load JSON file and apply transformations for UnitData and AbilData."""
    if base_dir is None:
        base_dir = Path(__file__).parent / "json"
    path = base_dir / filename
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if filename == "UnitData.json" and "CUnit" in data:
        return {unit["id"]: unit for unit in data["CUnit"]}
    if filename == "AbilData.json":
        result = {}
        for class_name, abilities in data.items():
            if isinstance(abilities, list):
                for ability in abilities:
                    if isinstance(ability, dict) and "id" in ability:
                        result[ability["id"]] = ability
        return result
    return data


def _recursive_sort(obj):
    if isinstance(obj, dict):
        return {k: _recursive_sort(v) for k, v in sorted(obj.items())}
    elif isinstance(obj, list):
        items = [_recursive_sort(item) for item in obj]
        if items and all(isinstance(item, str) for item in items):
            items = list(dict.fromkeys(items))
        return sorted(items, key=str)
    return obj


def dump_json(obj, fp, **kwargs):
    json.dump(_recursive_sort(obj), fp, **kwargs)


def dumps_json(obj, **kwargs) -> str:
    return json.dumps(_recursive_sort(obj), **kwargs)
