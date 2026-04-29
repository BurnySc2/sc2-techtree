import json
from pathlib import Path

import pytest


@pytest.fixture
def computed_data() -> dict:
    path = Path(__file__).parent.parent / "src" / "computed" / "data.json"
    with path.open() as f:
        return json.load(f)


class TestCocoonUnits:
    """Cocoon units should be present in computed data.json."""

    @pytest.mark.parametrize(
        "cocoon",
        [
            "BanelingCocoon",
            "DevourerCocoonMP",
            "GuardianCocoonMP",
            "OverlordCocoon",
            "OverlordCocoon",
            "RavagerCocoon",
            "TransportOverlordCocoon",
        ],
    )
    def test_cocoon_exists(self, computed_data: dict, cocoon: str) -> None:
        """Each cocoon unit should exist in Units."""
        assert cocoon in computed_data["Units"]

    def test_cocoons_are_zerg(self, computed_data: dict) -> None:
        """Cocoon units should have Zerg race."""
        cocoons = [
            "BanelingCocoon",
            "DevourerCocoonMP",
            "GuardianCocoonMP",
            "OverlordCocoon",
            "OverlordCocoon",
            "RavagerCocoon",
            "TransportOverlordCocoon",
        ]
        for cocoon in cocoons:
            unit = computed_data["Units"][cocoon]
            assert unit.get("Race") == "Zerg"
