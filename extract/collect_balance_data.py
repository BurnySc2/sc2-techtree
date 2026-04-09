#!/usr/bin/env python3
"""
SC2 Balance Data Collector

Collects StarCraft 2 balance data (units, abilities, upgrades, weapons)
from .sc2mod XML files and outputs structured JSON.

Mod layering (later overrides earlier):
  liberty.sc2mod -> libertymulti.sc2mod -> balancemulti.sc2mod -> voidmulti.sc2mod

All SC2 XML values are stored as element ATTRIBUTES (e.g. <Speed value="2.25"/>),
not as text content. This is why _attr() helpers read from element.attrib.
"""

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Configuration
BASE_DIR = Path(__file__).parent / "mods"
OUTPUT_DIR = Path(__file__).parent / "output"

# Mod loading order (later mods override earlier ones)
MOD_ORDER = [
    "liberty.sc2mod/base.sc2data/GameData/",
    "libertymulti.sc2mod/base.sc2data/GameData/",
    "balancemulti.sc2mod/base.sc2data/GameData/",
    "voidmulti.sc2mod/base.sc2data/GameData/",
]


# ── Attribute-based XML helpers ─────────────────────────────────────────────

def _attr(element: ET.Element, tag: str) -> str | None:
    """Get attrib['value'] from a child element, or None."""
    child = element.find(tag)
    if child is not None:
        return child.attrib.get("value")
    return None


def _attr_i(element: ET.Element, tag: str) -> int | None:
    """Get attrib['value'] as int, or None if missing / non-numeric."""
    val = _attr(element, tag)
    if val is None:
        return None
    try:
        return int(float(val))
    except (ValueError, ArithmeticError):
        return None


def _attr_f(element: ET.Element, tag: str) -> float | None:
    """Get attrib['value'] as float, or None."""
    val = _attr(element, tag)
    return float(val) if val is not None else None


def _omit_none(d: dict[str, Any]) -> dict[str, Any]:
    """Return a new dict with all None values removed."""
    return {k: v for k, v in d.items() if v is not None}


# ── Shared array extractors ───────────────────────────────────────────────────

def _link_array(element: ET.Element, tag: str) -> list[str]:
    """Extract all Link attribs from elements matching tag."""
    return [e.attrib["Link"] for e in element.findall(tag) if e.attrib.get("Link")]


def _value_array(element: ET.Element, tag: str) -> list[str]:
    """Extract all value attribs from elements matching tag."""
    return [e.attrib["value"] for e in element.findall(tag) if e.attrib.get("value")]


def _cost_resources(element: ET.Element) -> dict[str, Any]:
    """Extract CostResource index/value pairs as minerals/vespene."""
    costs = {}
    for cost in element.findall("CostResource"):
        idx = cost.attrib.get("index")
        val = cost.attrib.get("value")
        if idx and val:
            if idx == "Minerals":
                costs["minerals"] = int(val)
            elif idx == "Vespene":
                costs["vespene"] = int(val)
    return costs

def _info_array(element: ET.Element) -> dict[str, dict[str, Any]]:
    """Extract InfoArray entries from CAbilResearch as {index: {minerals, vespene, time, upgrade, requirements}}."""
    result = {}
    for info in element.findall("InfoArray"):
        idx = info.attrib.get("index")
        if not idx:
            continue
        # Extract resources
        minerals = None
        vespene = None
        for res in info.findall("Resource"):
            res_idx = res.attrib.get("index")
            res_val = res.attrib.get("value")
            if res_idx == "Minerals" and res_val:
                minerals = int(res_val)
            elif res_idx == "Vespene" and res_val:
                vespene = int(res_val)
        # Extract requirements from Button child
        btn = info.find("Button/")
        requirements = btn.attrib.get("Requirements") if btn is not None else None
        # Time is a direct attribute on InfoArray (e.g., Time="170" or Time="202.5"), not a child element
        time_val = info.attrib.get("Time")
        try:
            time_float = float(time_val) if time_val else None
            time_int = int(time_float) if time_float is not None else None
        except (ValueError, TypeError):
            time_int = None
        d = _omit_none({
            "minerals": minerals,
            "vespene": vespene,
            "time": time_int,
            "upgrade": info.attrib.get("Upgrade"),
            "requirements": requirements,
        })
        if d:
            result[idx] = d
    return result

# ── UnitData ─────────────────────────────────────────────────────────────────

def parse_unit(xml_path: Path) -> dict[str, dict[str, Any]]:
    tree = ET.parse(xml_path)
    units = {}
    for unit in tree.getroot().findall(".//CUnit"):
        uid = unit.attrib.get("id")
        if not uid:
            continue

        d = _omit_none({
            # Identification
            "id": uid,
            "name": _attr(unit, "Name"),
            "leader_alias": _attr(unit, "LeaderAlias"),
            "hotkey_alias": _attr(unit, "HotkeyAlias"),
            "race": _attr(unit, "Race"),
            "mob": _attr(unit, "Mob"),

            # Cost
            **_cost_resources(unit),
            "food": _attr_f(unit, "Food"),
            "food_provided": _attr_f(unit, "FoodProvided"),
            "build_time": _attr_i(unit, "BuildTime"),
            "repair_time": _attr_i(unit, "RepairTime"),
            "cost_category": _attr(unit, "CostCategory"),

            # Life / HP
            "life_start": _attr_i(unit, "LifeStart"),
            "life_max": _attr_i(unit, "LifeMax"),
            "life_armor": _attr_f(unit, "LifeArmor"),
            "life_regen_rate": _attr_f(unit, "LifeRegenRate"),

            # Shields
            "shields_start": _attr_i(unit, "ShieldsStart"),
            "shields_max": _attr_i(unit, "ShieldsMax"),
            "shields_armor": _attr_f(unit, "ShieldArmor"),
            "shield_regen_rate": _attr_f(unit, "ShieldRegenRate"),
            "shield_regen_delay": _attr_i(unit, "ShieldRegenDelay"),

            # Energy
            "energy_start": _attr_i(unit, "EnergyStart"),
            "energy_max": _attr_i(unit, "EnergyMax"),
            "energy_regen_rate": _attr_f(unit, "EnergyRegenRate"),

            # Movement
            "speed": _attr_f(unit, "Speed"),
            "speed_multiplier_creep": _attr_f(unit, "SpeedMultiplierCreep"),
            "acceleration": _attr_f(unit, "Acceleration"),
            "deceleration": _attr_f(unit, "Deceleration"),
            "turning_rate": _attr_f(unit, "TurningRate"),
            "stationary_turning_rate": _attr_f(unit, "StationaryTurningRate"),
            "lateral_acceleration": _attr_f(unit, "LateralAcceleration"),

            # Vision & navigation
            "sight": _attr_f(unit, "Sight"),
            "vision_height": _attr_f(unit, "VisionHeight"),
            "minimap_radius": _attr_f(unit, "MinimapRadius"),
            "fog_visibility": _attr(unit, "FogVisibility"),

            # Size & footprint
            "radius": _attr_f(unit, "Radius"),
            "inner_radius": _attr_f(unit, "InnerRadius"),
            "cargo_size": _attr_i(unit, "CargoSize"),
            "height": _attr_f(unit, "Height"),
            "mass": _attr_f(unit, "Mass"),
            "footprint": _attr(unit, "Footprint"),
            "dead_footprint": _attr(unit, "DeadFootprint"),
            "placement_footprint": _attr(unit, "PlacementFootprint"),

            # Combat
            "attack_target_priority": _attr_i(unit, "AttackTargetPriority"),
            "max_creeps": _attr_i(unit, "MaxCreeps"),
            "max_dying_squares": _attr_i(unit, "MaxDyingSquares"),

            # Production
            "builder": _attr(unit, "Builder"),
            "build_queue": _link_array(unit, "BuildQueueArray"),
            "produced_unit_id": _attr(unit, "ProducedUnitId"),
            "unit_weight": _attr_f(unit, "UnitWeight"),
            "mechanic_weight": _attr_f(unit, "MechanicWeight"),

            # Research/Upgrade links
            "researches_from": _link_array(unit, "ResearchesFromArray"),
            "upgrades_for": _link_array(unit, "UpgradesForArray"),

            # Weapons (weapons.json covers these, but extract array refs here)
            "weapon": _link_array(unit, "WeaponArray"),
            "targetFilters": _attr(unit, "TargetFilters"),
            "targetPriority": _attr_f(unit, "TargetPriority"),
            "defense": _attr_i(unit, "Defense"),
            "speed": _attr_f(unit, "Speed"),
            "turning_rate": _attr_f(unit, "TurningRate"),

            # Editor / UI
            "icon": _attr(unit, "Icon"),
            "editor_categories": _attr(unit, "EditorCategories"),
            "hotkey": _attr(unit, "Hotkey"),
            "tactical_ai": _attr(unit, "TacticalAI"),
            "random_layout": _attr(unit, "RandomLayout"),
        })

        if uid in units:
            units[uid].update(d)
        else:
            units[uid] = d
    return units


# ── UpgradeData ───────────────────────────────────────────────────────────────

def parse_upgrade(xml_path: Path) -> dict[str, dict[str, Any]]:
    tree = ET.parse(xml_path)
    upgrades = {}
    for upg in tree.getroot().findall(".//CUpgrade"):
        uid = upg.attrib.get("id")
        if not uid:
            continue
        d = _omit_none({
            "id": uid,
            "name": _attr(upg, "Name"),
            "race": _attr(upg, "Race"),
            "cost_category": _attr(upg, "CostCategory"),
            **_cost_resources(upg),
            "research_time": _attr_i(upg, "ResearchTime"),
            "level": _attr_i(upg, "Level"),
            "max_level": _attr_i(upg, "MaxLevel"),
            "icon": _attr(upg, "Icon"),
            "alert": _attr(upg, "Alert"),
            "flags": _attr(upg, "Flags"),
            "score_amount": _attr_i(upg, "ScoreAmount"),
            "score_count": _attr_i(upg, "ScoreCount"),
            "score_value": _attr_i(upg, "ScoreValue"),
            "score_result": _attr(upg, "ScoreResult"),
            "web_priority": _attr(upg, "WebPriority"),
            "editor_categories": _attr(upg, "EditorCategories"),
            "info_tooltip_priority": _attr_i(upg, "InfoTooltipPriority"),
        })
        affected_units = _link_array(upg, "AffectedUnitArray")
        if affected_units:
            d["affected_units"] = affected_units
        effects = []
        for effect in upg.findall("EffectArray"):
            ref = effect.attrib.get("Reference")
            if not ref:
                continue
            ed = {"reference": ref}
            if v := effect.attrib.get("Value"):
                ed["value"] = v
            if op := effect.attrib.get("Operation"):
                ed["operation"] = op
            effects.append(ed)
        if effects:
            d["effects"] = effects
        if uid in upgrades:
            upgrades[uid].update(d)
        else:
            upgrades[uid] = d
    return upgrades


# ── AbilityData ──────────────────────────────────────────────────────────────

def _parse_train_info_array(element: ET.Element) -> list[dict[str, Any]]:
    """Extract train InfoArray entries as list of {index, time, units, button, requirement_id}."""
    result = []
    for info in element.findall("InfoArray"):
        idx = info.attrib.get("index")
        if not idx:
            continue
        # Time is a direct attribute
        time_val = info.attrib.get("Time")
        try:
            time_int = int(float(time_val)) if time_val else None
        except (ValueError, TypeError):
            time_int = None
        # Extract units
        units = [u.attrib.get("value") for u in info.findall("Unit") if u.attrib.get("value")]
        # Extract button info and requirements
        btn = info.find("Button")
        button_face = btn.attrib.get("DefaultButtonFace") if btn is not None else None
        button_state = btn.attrib.get("State") if btn is not None else None
        req_id = btn.attrib.get("Requirements") if btn is not None else None
        d = _omit_none({
            "index": idx,
            "time": time_int,
            "units": units if units else None,
            "button_face": button_face,
            "button_state": button_state,
            "requirement_id": req_id,
        })
        if d:
            result.append(d)
    return result


def parse_ability(xml_path: Path) -> dict[str, dict[str, Any]]:
    tree = ET.parse(xml_path)
    abilities = {}
    for abil in (tree.getroot().findall(".//CAbil") +
                tree.getroot().findall(".//CAbilEffectTarget") +
                tree.getroot().findall(".//CAbilResearch") +
                tree.getroot().findall(".//CAbilTrain")):
        aid = abil.attrib.get("id")
        if not aid:
            continue
        costs = _cost_resources(abil)
        d = _omit_none({
            "id": aid,
            "name": _attr(abil, "Name"),
            "hotkey": _attr(abil, "Hotkey"),
            "abil_set_id": _attr(abil, "AbilSetId"),
            "tech_player": _attr(abil, "TechPlayer"),
            **costs,
            "build_time": _attr_i(abil, "BuildTime"),
            "research_time": _attr_i(abil, "ResearchTime"),
            "prep_time": _attr_i(abil, "PrepTime"),
            "finish_time": _attr_i(abil, "FinishTime"),
            "cast_intro_time": _attr_i(abil, "CastIntroTime"),
            "cast_outro_time": _attr_i(abil, "CastOutroTime"),
            "cooldown": _attr_f(abil, "Cooldown"),
            "range": _attr_f(abil, "Range"),
            "arc": _attr_f(abil, "Arc"),
            "arc_slop": _attr_f(abil, "ArcSlop"),
            "range_slop": _attr_f(abil, "RangeSlop"),
            "energy_cost": _attr_i(abil, "EnergyCost"),
            "auto_cast_range": _attr_f(abil, "AutoCastRange"),
            "target_filters": _attr(abil, "TargetFilters"),
            "default_error": _attr(abil, "DefaultError"),
            "error_alert": _attr(abil, "ErrorAlert"),
            "flags": _attr(abil, "Flags"),
            "acquire_attackers": _attr(abil, "AcquireAttackers"),
            "icon": _attr(abil, "Icon"),
            "editor_categories": _attr(abil, "EditorCategories"),
            "info_tooltip_priority": _attr_i(abil, "InfoTooltipPriority"),
            "target_sorts": _attr(abil, "TargetSorts"),
            "acquire_prioritization": _attr(abil, "AcquirePrioritization"),
        })
        produced_units = _link_array(abil, "ProducedUnitArray")
        if produced_units:
            d["produced_units"] = produced_units
        # Extract InfoArray for CAbilResearch (research upgrade costs)
        if abil.tag == "CAbilResearch":
            info_arrays = _info_array(abil)
            if info_arrays:
                d["info_arrays"] = info_arrays
        # Extract train InfoArray for CAbilTrain
        if abil.tag == "CAbilTrain":
            train_entries = _parse_train_info_array(abil)
            if train_entries:
                d["train_entries"] = train_entries
        if aid in abilities:
            abilities[aid].update(d)
        else:
            abilities[aid] = d
    return abilities


# ── RequirementData ──────────────────────────────────────────────────────────

def _parse_requirement(xml_path: Path) -> dict[str, dict[str, Any]]:
    """Parse RequirementData.xml and return requirement definitions keyed by ID."""
    tree = ET.parse(xml_path)
    requirements = {}
    for creq in tree.getroot().findall(".//CRequirement"):
        req_id = creq.attrib.get("id")
        if not req_id:
            continue
        # Get EditorCategories if present
        editor_cat = creq.find("EditorCategories")
        categories = editor_cat.attrib.get("value", "") if editor_cat is not None else ""
        # Get all NodeArray entries (Use, Show, Hide, etc.)
        node_arrays = {}
        for node in creq.findall("NodeArray"):
            index = node.attrib.get("index")
            link = node.attrib.get("Link")
            if index and link:
                node_arrays[index] = link
        requirements[req_id] = _omit_none({
            "categories": categories or None,
            "links": node_arrays if node_arrays else None,
        })
    return requirements


def _build_requirement_lookup(mod_order: list[str]) -> dict[str, dict[str, Any]]:
    """Build a lookup of requirement definitions, applying mod layering."""
    result = {}
    for mod_path in mod_order:
        xml_path = BASE_DIR / mod_path / "RequirementData.xml"
        if not xml_path.exists():
            continue
        reqs = _parse_requirement(xml_path)
        # Field-level merge for mod layering
        for req_id, req_data in reqs.items():
            if req_id in result:
                # Merge fields
                existing = dict(result[req_id])
                for key, val in req_data.items():
                    if val is not None:
                        existing[key] = val
                result[req_id] = existing
            else:
                result[req_id] = dict(req_data)
    return result


def _resolve_train_requirements(
    abilities: dict[str, dict[str, Any]],
    requirement_lookup: dict[str, dict[str, Any]]
) -> None:
    """Resolve requirement IDs to full definitions in train abilities."""
    for ability in abilities.values():
        train_entries = ability.get("train_entries")
        if not train_entries:
            continue
        for entry in train_entries:
            req_id = entry.get("requirement_id")
            if req_id:
                req_def = requirement_lookup.get(req_id)
                if req_def:
                    entry["requirement"] = req_def


# ── WeaponData ───────────────────────────────────────────────────────────────

def parse_weapon(xml_path: Path) -> dict[str, dict[str, Any]]:
    tree = ET.parse(xml_path)
    weapons = {}
    for weapon in tree.getroot().findall(".//CWeapon"):
        wid = weapon.attrib.get("id")
        if not wid:
            continue
        d = _omit_none({
            "id": wid,
            "name": _attr(weapon, "Name"),
            "flags": _attr(weapon, "Flags"),
            "target_filters": _attr(weapon, "TargetFilters"),
            "damage": _attr_f(weapon, "Damage"),
            "damage_radius": _attr_f(weapon, "DamageRadius"),
            "damage_scale": _attr_f(weapon, "DamageScale"),
            "damage_frequency": _attr_f(weapon, "DamageFrequency"),
            "damage_delay": _attr_i(weapon, "DamageDelay"),
            "range": _attr_f(weapon, "Range"),
            "range_slop": _attr_f(weapon, "RangeSlop"),
            "arc": _attr_f(weapon, "Arc"),
            "arc_slop": _attr_f(weapon, "ArcSlop"),
            "speed": _attr_f(weapon, "Speed"),
            "hotkey": _attr(weapon, "Hotkey"),
            "editor_categories": _attr(weapon, "EditorCategories"),
        })
        if wid in weapons:
            weapons[wid].update(d)
        else:
            weapons[wid] = d
    return weapons


# ── Merge helpers ───────────────────────────────────────────────────────────

def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Merge overlay INTO base at field level. Lists replaced entirely."""
    result = dict(base)
    for key, val in overlay.items():
        if isinstance(val, list) or val is not None:
            result[key] = val
    return result


def merge_units(unit_dicts: list[dict[str, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    """Field-level merge so balancemulti/voidmulti only override changed fields."""
    result = {}
    for unit_map in unit_dicts:
        for uid, data in unit_map.items():
            if uid in result:
                result[uid] = _deep_merge(result[uid], data)
            else:
                result[uid] = dict(data)
    return result


def merge_overwrite(dict_list: list[dict[str, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    """Generic overwrite merge for abilities/upgrades/weapons."""
    result = {}
    for d in dict_list:
        result.update(d)
    return result


def _has_complete_train(entry: dict) -> bool:
    """Check if a train entry has actual unit data (not just index)."""
    return bool(entry.get("units") or entry.get("requirement_id"))


def _merge_train_entries(base_entries: list[dict], overlay_entries: list[dict]) -> list[dict]:
    """Merge train entries by their index. Prefer base entries when overlay has empty data."""
    if not base_entries:
        return overlay_entries
    if not overlay_entries:
        return base_entries

    # Build lookup by index
    merged = {e["index"]: dict(e) for e in base_entries}
    for overlay in overlay_entries:
        idx = overlay["index"]
        if idx in merged:
            # If base has units but overlay doesn't, keep base
            base_has_units = bool(merged[idx].get("units"))
            overlay_has_units = bool(overlay.get("units"))
            if base_has_units and not overlay_has_units:
                # Keep base, skip overlay
                continue
            # Merge fields - overlay supplements missing fields
            for key, val in overlay.items():
                if val is not None and merged[idx].get(key) is None:
                    merged[idx][key] = val
        else:
            # New index from overlay
            merged[idx] = dict(overlay)

    # Sort by index for consistent output
    result = sorted(merged.values(), key=lambda x: x.get("index", ""))
    return result


def merge_abilities(dict_list: list[dict[str, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    """Field-level merge for abilities so balancemulti/voidmulti only override changed fields.
    Special handling for train_entries: if base has complete data and overlay is incomplete, keep base."""
    result = {}
    for ability_map in dict_list:
        for aid, data in ability_map.items():
            if aid in result:
                # Check train_entries special case
                base_train = result[aid].get("train_entries")
                overlay_train = data.get("train_entries")

                if base_train and overlay_train:
                    # Check if base has complete entries but overlay doesn't
                    base_complete = any(_has_complete_train(e) for e in base_train)
                    overlay_complete = any(_has_complete_train(e) for e in overlay_train)

                    if base_complete and not overlay_complete:
                        # Skip overlay's train_entries entirely, keep base's
                        data = dict(data)
                        del data["train_entries"]
                    elif not base_complete and overlay_complete:
                        # Use overlay's train_entries
                        result[aid] = _deep_merge(result[aid], data)
                        continue
                    else:
                        # Both have data - merge by index
                        data = dict(data)
                        data["train_entries"] = _merge_train_entries(base_train, overlay_train)

                result[aid] = _deep_merge(result[aid], data)
            else:
                result[aid] = dict(data)
    return result


# ── Research lookup (CAbilResearch InfoArray) ──────────────────────────────────

def _build_research_lookup(mod_order: list[str]) -> dict[str, dict[str, Any]]:
    """
    Build a lookup of research upgrade costs from CAbilResearch InfoArray entries.
    Key: "{ability_id}_{research_index}" (e.g., "BarracksTechLabResearch_Research1")
    Value: {minerals, vespene, time, upgrade, requirements}

    Uses field-level merge so later mods only override specific fields.
    Tracks Upgrade link across mods (libertymulti removes it but inherits from liberty).
    """
    result = {}
    for mod_path in mod_order:
        xml_path = BASE_DIR / mod_path / "AbilData.xml"
        if not xml_path.exists():
            continue
        tree = ET.parse(xml_path)
        for abil in tree.getroot().findall(".//CAbilResearch"):
            aid = abil.attrib.get("id")
            if not aid:
                continue
            info_arrays = _info_array(abil)
            for idx, data in info_arrays.items():
                key = f"{aid}_{idx}"
                if key in result:
                    # Merge at field level to preserve inheritance
                    existing = result[key]
                    for k, v in data.items():
                        if v is not None:
                            existing[k] = v
                    result[key] = existing
                else:
                    result[key] = dict(data)
    return result


def _inject_research_costs(
    upgrades: dict[str, dict[str, Any]],
    research_lookup: dict[str, dict[str, Any]],
    mod_order: list[str]
) -> dict[str, dict[str, Any]]:
    """
    Inject research costs from CAbilResearch InfoArray into upgrade definitions.
    
    InfoArray costs are injected when:
    - The upgrade exists in upgrades.json
    - The upgrade has NO minerals/vespene in UpgradeData.xml
    - A matching CAbilResearch entry exists (ability_suffix matches upgrade name)
    """
    result = dict(upgrades)

    # Build research lookup: upgrade_id -> research_data
    upgrade_to_research = {}
    for name, research_data in research_lookup.items():
        upgrade = research_data.get("upgrade")
        if upgrade:
            upgrade_to_research[upgrade] = research_data

    for name, merged in result.items():
        research_data = upgrade_to_research.get(name)
        if not research_data:
            continue

        # Check if UpgradeData already has complete cost info
        has_minerals = merged.get("minerals") is not None
        has_vespene = merged.get("vespene") is not None

        if not has_minerals or not has_vespene:
            # Supplement from InfoArray
            merged["_research_source"] = research_data

        # Supplement missing costs from InfoArray
        if merged.get("minerals") is None and research_data.get("minerals") is not None:
            merged["minerals"] = research_data["minerals"]
        if merged.get("vespene") is None and research_data.get("vespene") is not None:
            merged["vespene"] = research_data["vespene"]
        if merged.get("time") is None and research_data.get("time") is not None:
            merged["time"] = research_data["time"]
        if merged.get("research_time") is None and research_data.get("time") is not None:
            merged["research_time"] = research_data["time"]
        if merged.get("requirements") is None and research_data.get("requirements") is not None:
            merged["requirements"] = research_data["requirements"]

    return result


# ── Patch version ─────────────────────────────────────────────────────────────

def get_patch_version() -> str:
    """Try to read patch version from the last mod's .info file."""
    last_mod = MOD_ORDER[-1].split("/")[0]
    info_file = BASE_DIR / last_mod / ".info"
    if info_file.exists():
        parts = info_file.read_text().strip().split("|")
        if len(parts) > 12:
            return parts[12]
        if parts:
            return parts[-1]
    return "unknown"


# ── Output ───────────────────────────────────────────────────────────────────

def write_output(filename: str, data: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Wrote {path}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Collecting SC2 balance data...")
    patch = get_patch_version()
    generated_at = datetime.now(timezone.utc).isoformat()
    meta = {"patch": patch, "generated_at": generated_at}

    # Units (field-level merge critical)
    print("  Parsing UnitData...")
    units = merge_units([parse_unit(BASE_DIR / p / "UnitData.xml") for p in MOD_ORDER])
    write_output("units.json", {"_meta": meta, "units": units})

    # Abilities (use field-level merge to preserve train_entries from base mods)
    print("  Parsing AbilData...")
    abilities = merge_abilities([parse_ability(BASE_DIR / p / "AbilData.xml") for p in MOD_ORDER])
    # Build requirement lookup and resolve train requirements
    print("  Building requirement lookup from RequirementData.xml...")
    requirement_lookup = _build_requirement_lookup(MOD_ORDER)
    print("  Resolving train requirements...")
    _resolve_train_requirements(abilities, requirement_lookup)
    write_output("abilities.json", {"_meta": meta, "abilities": abilities})

    # Upgrades + research costs from AbilData InfoArray
    print("  Parsing UpgradeData...")
    upgrades = merge_overwrite([parse_upgrade(BASE_DIR / p / "UpgradeData.xml") for p in MOD_ORDER])
    print("  Building research lookup from AbilData InfoArray...")
    research_lookup = _build_research_lookup(MOD_ORDER)
    print("  Injecting research costs into upgrades...")
    upgrades = _inject_research_costs(upgrades, research_lookup, MOD_ORDER)
    write_output("upgrades.json", {"_meta": meta, "upgrades": upgrades})

    # Weapons
    print("  Parsing WeaponData...")
    weapons = merge_overwrite([parse_weapon(BASE_DIR / p / "WeaponData.xml") for p in MOD_ORDER])
    write_output("weapons.json", {"_meta": meta, "weapons": weapons})

    # Sanity check
    if "Marine" in units:
        m = units["Marine"]
        print(f"\n  ✓ Marine found (minerals={m.get('minerals')}, speed={m.get('speed')}, "
              f"acceleration={m.get('acceleration')}, life_max={m.get('life_max')})")
    else:
        print("\n  ⚠ Marine not found in units.json")

    # Upgrade cost check
    if "Stimpack" in upgrades:
        s = upgrades["Stimpack"]
        print(f"  ✓ Stimpack found (minerals={s.get('minerals')}, vespene={s.get('vespene')}, "
              f"research_time={s.get('research_time')})")
    else:
        print("  ⚠ Stimpack not found in upgrades.json")

    # Train ability check
    if "LarvaTrain" in abilities:
        print(f"  ✓ LarvaTrain found with {len(abilities['LarvaTrain'].get('train_entries', []))} train entries")
    else:
        print("  ⚠ LarvaTrain not found in abilities.json")

    print("\nDone.")


if __name__ == "__main__":
    main()
