#!/usr/bin/env python3
"""Scrape Liquipedia for StarCraft II unit data to create a ground-truth reference fixture."""

import gzip
import json
import re
import urllib.request
import urllib.error
from pathlib import Path

LIQUIPEDIA_BASE = "https://liquipedia.net/starcraft2/api.php"

TERRAN_UNITS = [
    "Marine",
    "Marauder",
    "Ghost",
    "Reaper",
    "Viking",
    "Medivac",
    "Raven",
    "Banshee",
    "Battlecruiser",
    "Cyclone",
    "Hellion",
    "Hellbat",
    "Widow Mine",
    "Liberator",
    "Siege Tank",
    "Thor",
    "OCal",
]

ZERG_UNITS = [
    "Zergling",
    "Roach",
    "Hydralisk",
    "Mutalisk",
    "Ultralisk",
    "Zergling",
    "Baneling",
    "Infestor",
    "Swarm Host",
    "Corruptor",
    "Viper",
    "Queen",
    "Lurker",
    "Brood Lord",
    "Overseer",
    "Changeling",
    "Locust",
]

PROTOSS_UNITS = [
    "Probe",
    "Zealot",
    "Stalker",
    "Sentry",
    "Adept",
    "High Templar",
    "Dark Templar",
    "Archon",
    "Immortal",
    "Disruptor",
    "Colossus",
    "Tempest",
    "Void Ray",
    "Oracle",
    "Phoenix",
    "Carrier",
    "Mothership",
    "MothershipCore",
    "Warp Prism",
    "Observer",
]

ALL_UNITS = TERRAN_UNITS + ZERG_UNITS + PROTOSS_UNITS
ALL_UNITS = list(dict.fromkeys(ALL_UNITS))


def fetch_page_wikitext(page_title: str) -> str | None:
    """Fetch wikitext for a page from Liquipedia API."""
    encoded_title = page_title.replace(" ", "_").replace("(", "%28").replace(")", "%29")
    url = f"{LIQUIPEDIA_BASE}?action=parse&page={encoded_title}&prop=wikitext&format=json"

    try:
        req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            if resp.info().get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            data = json.loads(raw.decode("utf-8"))
            return data.get("parse", {}).get("wikitext", {}).get("*")
    except urllib.error.URLError as e:
        print(f"  ERROR fetching {page_title}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"  ERROR decoding {page_title}: {e}")
        return None


def parse_unit_infobox(wikitext: str, unit_name: str) -> dict | None:
    """Parse a unit's infobox from wikitext."""
    if not wikitext or "#REDIRECT" in wikitext:
        return None

    info: dict = {
        "name": unit_name,
        "race": None,
        "minerals": None,
        "gas": None,
        "buildtime": None,
        "built_from": None,
        "requires": None,
        "morph_target": None,
    }

    for line in wikitext.split("\n"):
        line = line.strip()
        if line.startswith("|race="):
            race = line.split("=", 1)[1].strip().lower()
            if race in ("t", "terran"):
                info["race"] = "Terran"
            elif race in ("z", "zerg"):
                info["race"] = "Zerg"
            elif race in ("p", "protoss"):
                info["race"] = "Protoss"
        elif line.startswith("|min="):
            val = line.split("=", 1)[1].strip()
            info["minerals"] = int(val) if val.isdigit() else None
        elif line.startswith("|gas="):
            val = line.split("=", 1)[1].strip()
            info["gas"] = int(val) if val.isdigit() else None
        elif line.startswith("|buildtime="):
            val = line.split("=", 1)[1].strip()
            info["buildtime"] = val
        elif line.startswith("|builtfrom="):
            built_from = re.findall(r"\[\[([^\]]+)\]\]", line)
            if built_from:
                info["built_from"] = built_from
        elif line.startswith("|requires="):
            requires = re.findall(r"\[\[([^\]]+)\]\]", line)
            if requires:
                info["requires"] = requires
        elif line.startswith("|morph_to="):
            morph_to = re.findall(r"\[\[([^\]]+)\]\]", line)
            if morph_to:
                info["morph_target"] = morph_to[0] if morph_to else None

    return info


def scrape_liquipedia_units() -> list[dict]:
    """Scrape Liquipedia for all unit data."""
    results = []

    for unit in sorted(set(ALL_UNITS)):
        print(f"Fetching {unit}...", end=" ")
        wikitext = fetch_page_wikitext(f"{unit} (Legacy of the Void)")
        if not wikitext:
            wikitext = fetch_page_wikitext(unit)
        if not wikitext:
            print("SKIPPED")
            continue

        parsed = parse_unit_infobox(wikitext, unit)
        if parsed:
            results.append(parsed)
            print(f"OK (race={parsed['race']}, min={parsed['minerals']})")
        else:
            print("PARSE FAILED")

    return results


def main() -> None:
    out_path = Path(__file__).parent.parent / "test" / "fixtures" / "liquipedia_reference.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Scraping {len(ALL_UNITS)} units from Liquipedia...")
    units = scrape_liquipedia_units()

    print(f"\nCollected {len(units)} unit records")
    with out_path.open("w") as f:
        json.dump({"units": units, "metadata": {"source": "Liquipedia", "scraped": "2026-04-27"}}, f, indent=2)

    print(f"Written to {out_path}")


if __name__ == "__main__":
    main()
