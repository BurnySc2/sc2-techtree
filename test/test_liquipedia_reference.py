import json
from pathlib import Path

import pytest


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "liquipedia_reference.json"


@pytest.fixture
def fixture_data() -> dict:
    with FIXTURE_PATH.open() as f:
        return json.load(f)


@pytest.fixture
def units(fixture_data: dict) -> list[dict]:
    return fixture_data["units"]


class TestFixtureExists:
    def test_fixture_file_exists(self) -> None:
        assert FIXTURE_PATH.exists()

    def test_fixture_has_units_key(self, fixture_data: dict) -> None:
        assert "units" in fixture_data

    def test_fixture_has_metadata(self, fixture_data: dict) -> None:
        assert "metadata" in fixture_data


class TestMarineSanity:
    def test_marine_exists(self, units: list[dict]) -> None:
        assert any(u["name"] == "Marine" for u in units)

    def test_marine_mineral_cost(self, units: list[dict]) -> None:
        marine = next(u for u in units if u["name"] == "Marine")
        assert marine["minerals"] == 50

    def test_marine_gas_cost(self, units: list[dict]) -> None:
        marine = next(u for u in units if u["name"] == "Marine")
        assert marine["gas"] == 0

    def test_marine_race(self, units: list[dict]) -> None:
        marine = next(u for u in units if u["name"] == "Marine")
        assert marine["race"] == "Terran"


class TestKeyUnitsExist:
    @pytest.mark.parametrize(
        "name,race",
        [
            ("Marine", "Terran"),
            ("Zergling", "Zerg"),
            ("Zealot", "Protoss"),
            ("SCV", "Terran"),
            ("Probe", "Protoss"),
            ("Drone", "Zerg"),
        ],
    )
    def test_unit_exists(self, units: list[dict], name: str, race: str) -> None:
        assert any(u["name"] == name and u["race"] == race for u in units), f"{name} ({race}) not found"


class TestRaceBreakdown:
    def test_all_units_have_valid_race(self, units: list[dict]) -> None:
        races = {"Terran", "Zerg", "Protoss"}
        for u in units:
            assert u["race"] in races, f"Unit {u['name']} has unknown race: {u['race']}"

    def test_race_counts(self, fixture_data: dict) -> None:
        units = fixture_data["units"]
        races = [u["race"] for u in units]
        counts = {r: races.count(r) for r in set(races)}
        assert counts["Terran"] > 0
        assert counts["Zerg"] > 0
        assert counts["Protoss"] > 0
        print(f"Race counts: {counts}")


class TestMineralCosts:
    def test_no_null_minerals(self, units: list[dict]) -> None:
        for u in units:
            if u["minerals"] is not None:
                assert u["minerals"] >= 0

    def test_starter_units_reasonable_cost(self, units: list[dict]) -> None:
        for name in ["Marine", "Zergling", "Zealot", "SCV", "Probe", "Drone"]:
            u = next((x for x in units if x["name"] == name), None)
            assert u is not None, f"{name} not in fixture"
            assert u["minerals"] is not None and u["minerals"] > 0
