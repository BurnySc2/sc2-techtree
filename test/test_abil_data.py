import json
from pathlib import Path

import pytest


@pytest.fixture
def abil_data() -> dict:
    path = Path(__file__).parent.parent / "src" / "json" / "AbilData.json"
    with path.open() as f:
        raw = json.load(f)
    # Transform {CAbilX: [{id: ..., ...}]} into {id: record}
    result = {}
    for ability_list in raw.values():
        if isinstance(ability_list, list):
            for rec in ability_list:
                if isinstance(rec, dict) and "id" in rec:
                    result[rec["id"]] = rec
    return result


class TestStargateTrain:
    def test_stargate_train_key_exists(self, abil_data: dict) -> None:
        assert "StargateTrain" in abil_data

    @pytest.mark.parametrize("unit_name", ["Carrier", "Oracle", "Phoenix", "VoidRay", "Tempest"])
    def test_stargate_train_info_array_contains(self, abil_data: dict, unit_name: str) -> None:
        st = abil_data["StargateTrain"]
        indexes = {entry.get("Unit") for entry in st.get("InfoArray", []) if isinstance(entry, dict)}
        assert unit_name in indexes


class TestOracleRevelation:
    def test_oracle_revelation_key_exists(self, abil_data: dict) -> None:
        assert "OracleRevelation" in abil_data

    def test_oracle_revelation_cost(self, abil_data: dict) -> None:
        oracle = abil_data["OracleRevelation"]
        assert "Cost" in oracle
        cost = oracle["Cost"]
        assert cost.get("Cooldown", {}).get("TimeUse") == "14"
        assert cost.get("Vital", {}).get("Energy") == 25

    def test_oracle_revelation_range(self, abil_data: dict) -> None:
        oracle = abil_data["OracleRevelation"]
        assert "Range" in oracle
        range_val = oracle["Range"]
        if isinstance(range_val, dict):
            assert "0" in range_val
            assert range_val["0"] == 12
        else:
            assert range_val == 12


class TestBarracksAddOns:
    def test_barracks_add_ons_exists(self, abil_data: dict) -> None:
        assert "BarracksAddOns" in abil_data

    @pytest.mark.parametrize("unit_name", ["BarracksTechLab", "BarracksReactor"])
    def test_barracks_add_ons_contains(self, abil_data: dict, unit_name: str) -> None:
        bra = abil_data["BarracksAddOns"]
        indexes = {entry.get("Unit") for entry in bra.get("InfoArray", []) if isinstance(entry, dict)}
        assert unit_name in indexes
