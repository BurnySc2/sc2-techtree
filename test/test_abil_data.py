import json
from pathlib import Path

import pytest


@pytest.fixture
def abil_data() -> dict:
    path = Path(__file__).parent.parent / "src" / "json" / "AbilData.json"
    with path.open() as f:
        return json.load(f)


class TestStargateTrain:
    def test_stargate_train_key_exists(self, abil_data: dict) -> None:
        assert "StargateTrain" in abil_data

    def test_stargate_train_info_array_contains_carrier(self, abil_data: dict) -> None:
        info_units = {entry["Unit"] for entry in abil_data["StargateTrain"]["InfoArray"] if "Unit" in entry}
        assert "Carrier" in info_units

    def test_stargate_train_info_array_contains_oracle(self, abil_data: dict) -> None:
        info_units = {entry["Unit"] for entry in abil_data["StargateTrain"]["InfoArray"] if "Unit" in entry}
        assert "Oracle" in info_units

    def test_stargate_train_info_array_contains_phoenix(self, abil_data: dict) -> None:
        info_units = {entry["Unit"] for entry in abil_data["StargateTrain"]["InfoArray"] if "Unit" in entry}
        assert "Phoenix" in info_units

    def test_stargate_train_info_array_contains_tempest(self, abil_data: dict) -> None:
        info_units = {entry["Unit"] for entry in abil_data["StargateTrain"]["InfoArray"] if "Unit" in entry}
        assert "Tempest" in info_units

    def test_stargate_train_info_array_contains_void_ray(self, abil_data: dict) -> None:
        info_units = {entry["Unit"] for entry in abil_data["StargateTrain"]["InfoArray"] if "Unit" in entry}
        assert "VoidRay" in info_units


class TestOracleRevelation:
    def test_oracle_revelation_key_exists(self, abil_data: dict) -> None:
        assert "OracleRevelation" in abil_data

    def test_oracle_revelation_cost(self, abil_data: dict) -> None:
        oracle = abil_data["OracleRevelation"]
        assert "Cost" in oracle
        assert oracle["Cost"] == {
            "Cooldown": {"TimeUse": "14"},
            "Energy": 25,
            "index": 0,
        }

    def test_oracle_revelation_range(self, abil_data: dict) -> None:
        oracle = abil_data["OracleRevelation"]
        assert "Range" in oracle
        assert oracle["Range"] == 12


class TestBarracksAddOns:
    def test_barracks_add_ons_exists(self, abil_data: dict) -> None:
        assert "BarracksAddOns" in abil_data

    def test_barracks_add_ons_contains_barracks_tech_lab(self, abil_data: dict) -> None:
        info_units = {
            entry["Unit"]
            for entry in abil_data["BarracksAddOns"]["InfoArray"]
            if "Unit" in entry and isinstance(entry["Unit"], str)
        }
        assert "BarracksTechLab" in info_units

    def test_barracks_add_ons_contains_barracks_reactor(self, abil_data: dict) -> None:
        info_units = {
            entry["Unit"]
            for entry in abil_data["BarracksAddOns"]["InfoArray"]
            if "Unit" in entry and isinstance(entry["Unit"], str)
        }
        assert "BarracksReactor" in info_units
