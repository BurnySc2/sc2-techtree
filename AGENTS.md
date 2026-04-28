# SC2 Techtree Project

## Overview

This project converts StarCraft 2 mod data (XML) into a structured techtree JSON file.

## Pipeline

```
XML (mod files) → JSON → Merged JSON → techtree.json
```

### 1. xml_to_json.py

Converts SC2 mod XML files to JSON format. Each mod's XML is converted to JSON in-place (same directory).

**Mod processing order** (important for merge conflict resolution):
1. liberty.sc2mod
2. libertymulti.sc2mod
3. swarm.sc2mod
4. swarmmulti.sc2mod
5. void.sc2mod
6. voidmulti.sc2mod

**Data types converted**: UnitData, AbilData, UpgradeData, WeaponData, EffectData

### 2. merge_json.py

Merges the converted JSON files using **second-file-wins** conflict resolution. The mod order above means later mods override earlier ones (void > voidmulti > swarm > ...).

**Key merge behaviors:**
- **Records matched by `id`**: Units with the same id are merged rather than duplicated
- **Index-based arrays**: Entries with an `index` field update existing entries at that index
- **Removal markers**: `{SomeField: {index: N, removed: "1"}}` removes the base entry at index N
- **LayoutButtons**: Special merging logic for button layouts
- **Array tags** (Attributes, FlagArray, WeaponArray, CardLayouts, InfoArray): handled specially

### Index-Based Array Operations

The merge uses `index` fields to target specific entries in arrays:

#### Updating (`index` + value)
```json
// In override record targeting base at index "0":
{
  "LayoutButtons": { "SomeButton": "value", "index": "0" },
  "index": "0"
}
```
- `merge_values` matches entries by `base[index] == override[index]` (lines 118, 142)
- Matches also occur when base has no explicit index and override requests index "0" at position 0 (line 145)
- `_merge_layout_buttons` handles LayoutButtons specially, updating matched button fields or extending the array

#### Adding (index without removal marker)
```json
// Adding at index 2 (extends base_lb if needed):
{ "Button": {...}, "index": "2" }
```
- `_merge_layout_buttons` at lines 67-88: if no button matches the index, extends base and places at that position
- `merge_values` at lines 174-175: unmatched indexed entries are appended to the base array

#### Removing (`removed: "1"` pattern)
```json
// In override record, marking base entry at index "SomeId" for removal:
{
  "SomeField": { "index": "0", "removed": "1" },
  "index": "SomeId"
}
```
- `merge_values` at lines 118-135: detects `{field: {index: N, removed: "1"}}` pattern
- When found, finds and pops the base entry where `base_child["index"] == override_child["index"]`
- The `index` in `SomeField` value is the target position; the outer `index` is the entry identifier

### 3. generate_techtree.py

Processes the merged JSON into a clean techtree structure with:
- **structures**: Buildings (detected via EditorCategories or TECH_LABS set)
- **units**: Non-structure entities
- **abilities**: MorphTo, UpgradeTo, LiftOff abilities

**Entry structure per unit/structure:**
```json
{
  "race": "Terran|Zerg|Protoss",
  "produces": ["UnitNames"],      // trained units
  "builds": ["BuildingNames"],    // built structures
  "researches": ["UpgradeNames"], // researched upgrades
  "unlocks": ["UnitNames"],       // units this structure unlocks
  "morphsto": "Target|[]",       // morph/transform target
  "requires": ["StructureNames"] // required structures
}
```

**Key mappings in generate_techtree.py:**
- `RACE_MAP`: Terr/Zerg/Prot → Terran/Zerg/Protoss
- `UNIT_REQUIREMENT_FIXES`: Manual fixes for inconsistent game data (e.g., Roach requires RoachWarren)
- `MORPH_EXCLUDE`: Cocoon-type units to exclude from morph targets
- `REQUIREMENT_NAME_FIXES`: Corrects garbled names (e.g., "RoboticsFa" → "RoboticsFacility")
- `RESEARCH_NAME_MAP`: Maps upgrade ability names to canonical upgrade names
- `ABILITY_STRUCTURE_MAP`: Shared abilities (e.g., SpireResearch belongs to GreaterSpire)
- `SHARED_RESEARCH_EXCLUDE`: Research that shouldn't appear on certain structures

**Filtering:**
- Campaign units excluded (EditorCategories contains "ObjectFamily:Campaign")
- Mercenary buildings excluded (Race is N/A or NOT_FOUND)

## Usage

```bash
uv run src/xml_to_json.py    # Convert XMLs to JSON
uv run src/merge_json.py     # Merge JSONs
uv run src/generate_techtree.py  # Generate computed/techtree.json
uv run src/reconstruct_data.py  # Generate computed/data.json
```

## Verify
```bash
uv run pytest
```

## Formatting and linting
```bash
uv run ruff check
uv run ruff format
uv run pyrefly check
```
