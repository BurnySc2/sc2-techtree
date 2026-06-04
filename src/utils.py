import json
from pathlib import Path

BUTTON_INDEX_EXECUTE = "Execute"

REQUIREMENT_NAME_FIXES = {
    "RoboticsFa": "RoboticsFacility",
    "TemplarArchives": "TemplarArchive",
    "LurkerDen": "LurkerDenMP",
    "BanelingNest2": "RoachWarren",
}


def parse_requirement(req: str) -> list[str]:
    """Parse a requirement string into structure names.

    Examples:
        'HaveBarracks' -> ['Barracks']
        'HaveArmoryAndAttachedTechLab' -> ['Armory', 'AttachedTechLab']
        'HaveRoboticsBay' -> ['RoboticsBay']
    """
    if not req:
        return []

    parts = req.split("And")
    result = []
    for part in parts:
        if part.startswith("Have"):
            name = part[4:]
            name = REQUIREMENT_NAME_FIXES.get(name, name)
            result.append(name)
        elif part.startswith("Learn"):
            pass
        else:
            result.append(part)
    return result


def get_execute_button_requirements(abil_data: dict) -> list[str]:
    """Extract requirements from CmdButtonArray entries with index 'Execute'."""
    requires = []
    cmd_buttons = abil_data.get("CmdButtonArray", [])
    if isinstance(cmd_buttons, list):
        for btn in cmd_buttons:
            if isinstance(btn, dict) and btn.get("index") == BUTTON_INDEX_EXECUTE:
                req = btn.get("Requirements", "")
                if req:
                    requires.extend(parse_requirement(req))
    return requires


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
            elif isinstance(abilities, dict) and "id" in abilities:
                result[abilities["id"]] = abilities
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


def extract_abil_name(abil_entry) -> str | None:
    """Extract ability name from AbilArray entry.

    AbilArray entries can be:
    - dict with 'Link' key: {"Link": "BuildInProgress"}
    - string: "BuildInProgress"
    Returns None for invalid entries.
    """
    if isinstance(abil_entry, dict) and "Link" in abil_entry:
        return abil_entry["Link"]
    if isinstance(abil_entry, str):
        return abil_entry
    return None
