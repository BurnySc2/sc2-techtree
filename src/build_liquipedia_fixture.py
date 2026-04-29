#!/usr/bin/env python3
"""Build ground-truth reference fixture from processed SC2 data.

Extracts unit data from the already-merged JSON (data/data_readable.json)
and the UnitData source (src/json/UnitData.json) to create a fixture that
mirrors what Liquipedia would provide.

The goal is to have a cross-validation reference - test_computed_data.py
can compare the generated techtree against this fixture to catch regressions.
"""

import json
from pathlib import Path

from utils import load_json

SRC_JSON = Path(__file__).parent / "json"
DATA_DIR = Path(__file__).parent.parent / "data"
OUT_PATH = Path(__file__).parent.parent / "test" / "fixtures" / "liquipedia_reference.json"

TERRAN_STRUCTURES = {
    "CommandCenter",
    "OrbitalCommand",
    "PlanetaryFortress",
    "SupplyDepot",
    "Refinery",
    "Barracks",
    "Factory",
    "Starport",
    "Armory",
    "FusionCore",
    "TechLab",
    "Reactor",
    "Bunker",
    "SensorTower",
    "MissileTurret",
    "AutoTurret",
    "GhostAcademy",
    "StarportTechLab",
    "FactoryTechLab",
}

ZERG_STRUCTURES = {
    "Hatchery",
    "Lair",
    "Hive",
    "NydusWorm",
    "NydusNetwork",
    "SpawningPool",
    "RoachWarren",
    "HydraliskDen",
    "Spire",
    "GreaterSpire",
    "UltraliskCavern",
    "InfestationPit",
    "NeuralParasite",
    "BanelingNest",
    "CreepTumor",
}

PROTOSS_STRUCTURES = {
    "Nexus",
    "Gateway",
    "WarpGate",
    "CyberneticsCore",
    "Forge",
    "PhotonCannon",
    "Stargate",
    "FleetBeacon",
    "RoboticsBay",
    "RoboticsFacility",
    "TemplarArchives",
    "DarkShrine",
    "Battlecruiser",
    "Mothership",
}


def load_unit_data() -> dict:
    raw = load_json("UnitData.json")
    if isinstance(raw, dict) and "CUnit" in raw:
        return {rec["id"]: rec for rec in raw["CUnit"]}
    return raw


def load_computed_data() -> dict:
    with (DATA_DIR / "data_readable.json").open() as f:
        return json.load(f)


def extract_unit_name(name_field: str) -> str:
    """Extract clean name from Unit/Name/X field."""
    if not name_field:
        return ""
    if name_field.startswith("Unit/Name/"):
        return name_field.split("Unit/Name/", 1)[1]
    return name_field


def build_fixture() -> list[dict]:
    computed = load_computed_data()
    unit_list = computed.get("Unit", [])

    units = []
    seen_ids = set()

    for entry in unit_list:
        uid = entry.get("id")
        name = entry.get("name", "")
        race = entry.get("race", "")

        if uid in seen_ids or not name:
            continue
        seen_ids.add(uid)

        minerals = entry.get("minerals")
        gas = entry.get("gas")
        build_time = entry.get("time")

        tech_alias = entry.get("tech_alias", [])

        built_from = []
        if entry.get("is_structure") or tech_alias:
            built_from = tech_alias[:1] if tech_alias else []

        units.append(
            {
                "name": name,
                "race": race,
                "minerals": minerals,
                "gas": gas,
                "buildtime": build_time,
                "built_from": built_from,
                "is_structure": entry.get("is_structure", False),
            }
        )

    units.sort(key=lambda x: x["name"])
    return units


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    print("Building ground-truth fixture from processed data...")
    fixture_data = build_fixture()

    metadata = {
        "source": "sc2-techtree processed data",
        "note": "One-time ground-truth extracted from game XML via pipeline",
        "extracted": "2026-04-27",
        "total_units": len(fixture_data),
    }

    output = {"units": fixture_data, "metadata": metadata}

    with OUT_PATH.open("w") as f:
        json.dump(output, f, indent=2)

    print(f"Written {len(fixture_data)} unit records to {OUT_PATH}")

    race_counts = {}
    for u in fixture_data:
        race_counts[u["race"]] = race_counts.get(u["race"], 0) + 1
    print(f"Race breakdown: {race_counts}")


if __name__ == "__main__":
    main()
