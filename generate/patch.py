from pathlib import Path

import toml
import json

from sc2.ids.ability_id import AbilityId

SOURCE_DIR = Path("generated") / "collect"
T_TOML_DIR = Path("generated") / "patched"
TARGET_DIR = Path("generated") / "results"
DATA_DIR = Path("data")


def patch() -> None:
    assert SOURCE_DIR.exists()
    TARGET_DIR.mkdir(exist_ok=True)
    T_TOML_DIR.mkdir(exist_ok=True)

    with (SOURCE_DIR / "ability.toml").open() as f:
        c_ability = toml.load(f)

    with (Path("generate") / "patches" / "ability_missing.toml").open() as f:
        ability_missing = toml.load(f)
        for a in ability_missing["Ability"]:
            c_ability["Ability"].append(a)

    with (SOURCE_DIR / "unit.toml").open() as f:
        c_unit = toml.load(f)

    with (SOURCE_DIR / "upgrade.toml").open() as f:
        c_upgrade = toml.load(f)

    with (Path("generate") / "patches" / "ability_requirement.toml").open() as f:
        patch_ability_requirement = toml.load(f)

    with (Path("generate") / "patches" / "ability_produces_replace.toml").open() as f:
        patch_ability_produces_replace = toml.load(f)

    with (Path("generate") / "patches" / "ability_produces_missing.toml").open() as f:
        patch_ability_produces_missing = toml.load(f)

    with (Path("generate") / "patches" / "unit_ability_missing.toml").open() as f:
        patch_unit_ability_missing = toml.load(f)

    with (Path("generate") / "patches" / "unit_ability_disallowed.toml").open() as f:
        patch_unit_ability_disallowed = toml.load(f)

    # Patch unit abilities
    for unit in c_unit["Unit"]:
        unit_id = unit["id"]
        current_abilities = [int(a["ability"]) for a in unit["abilities"]]

        for p in patch_unit_ability_missing.get(str(unit_id), []):
            assert (
                int(p["ability"]) not in current_abilities
            ), f"Already defined: ({unit['name']}) {unit_id} {p['ability']}"
            unit["abilities"].append(p)

    # Patch replacement ability products
    for abil in c_ability["Ability"]:
        abil_id = abil["id"]
        abil_name = abil["name"]

        if isinstance(abil["target"], dict):
            keys = abil["target"].keys()
            assert len(keys) == 1
            k = list(keys)[0]

            if k == "Research":
                assert abil["target"][k]["upgrade"] != 0
            else:
                if abil["target"][k]["produces"] == 0:
                    p = patch_ability_produces_replace.get(str(abil_id))
                    if p:
                        # assert p, f"Missing ability product: [{abil_id}] # {abil_name}"
                        abil["target"][k]["produces"] = p["produces"]
                        abil["target"][k]["produces_name"] = p.get("produces_name", "Unknown")

    # Patch missing ability products
    for abil in c_ability["Ability"]:
        abil_id = abil["id"]
        patch_target = patch_ability_produces_missing.get(str(abil_id))
        if patch_target is None:
            continue

        assert set(patch_target.keys()) == {"target"}
        abil.update(patch_target)

    # Patch unit requirements
    for unit in c_unit["Unit"]:
        unit_id = unit["id"]
        unit_name = unit["name"]
        for i, ability in list(enumerate(unit["abilities"]))[::-1]:
            assert set(ability.keys()) <= {"ability", "requirements"}, f"Keys? {ability.keys()}"
            ability_id = ability["ability"]

            # Check if disallowed
            d0 = patch_unit_ability_disallowed.get(str(unit_id))
            if d0:
                d1 = d0.get(str(ability_id))
                if d1 is not None:
                    assert d1["disallow"]
                    del unit["abilities"][i]
                    continue

            if ability.get("requirements") == "???":
                # Check if defined
                ability_name = AbilityId(ability_id).name
                patch_name = f"[{unit_id}.{ability_id}] # {unit_name} - {ability_name}"
                p0 = patch_ability_requirement.get(str(unit["id"]))
                assert p0, f"Missing ability: {patch_name}"
                p1 = p0.get(str(ability_id))
                assert p1, f"Missing ability requirement: {patch_name}"
                ability["requirements"] = p1["requirements"]
            else:
                # Check if defined even if not used
                ability_name = AbilityId(ability_id).name
                patch_name = f"[{unit_id}.{ability_id}] # {unit_name} - {ability_name}"
                p0 = patch_ability_requirement.get(str(unit["id"]))
                if p0:
                    p1 = p0.get(str(ability_id))
                    assert not p1, f"Redundant unit requirement: {patch_name}"
                    # assert not p1, f"Redundant unit requirement: {patch_name}"

    with (T_TOML_DIR / "ability.toml").open("w") as f:
        toml.dump(c_ability, f)

    with (T_TOML_DIR / "unit.toml").open("w") as f:
        toml.dump(c_unit, f)

    with (T_TOML_DIR / "upgrade.toml").open("w") as f:
        toml.dump(c_upgrade, f)

    with (TARGET_DIR / "ability.json").open("w") as f:
        json.dump(c_ability, f, separators=(",", ":"))

    with (TARGET_DIR / "unit.json").open("w") as f:
        json.dump(c_unit, f, separators=(",", ":"))

    with (TARGET_DIR / "upgrade.json").open("w") as f:
        json.dump(c_upgrade, f, separators=(",", ":"))

    c_data = {**c_ability, **c_unit, **c_upgrade}
    with (DATA_DIR / "data.json").open("w") as f:
        json.dump(c_data, f, separators=(",", ":"))
    with (DATA_DIR / "data_readable.json").open("w") as f:
        json.dump(c_data, f, separators=(",", ": "), indent=4, sort_keys=True)


if __name__ == "__main__":
    patch()
