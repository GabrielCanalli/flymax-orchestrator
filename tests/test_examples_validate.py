"""Every example template must parse against the schema AND stay in its own geofence.

This is the CI acceptance bar for the mission-template library: a contributor's
new examples/*.json is picked up automatically and must pass both checks.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flymax.missions import Mission
from flymax.orchestrator import load_mission
from flymax.skills import GeofenceSkill

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
EXAMPLE_FILES = sorted(EXAMPLES_DIR.glob("*.json"))


def test_examples_directory_is_not_empty() -> None:
    assert EXAMPLE_FILES, "expected at least one example mission in examples/"


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=[p.stem for p in EXAMPLE_FILES])
def test_example_validates_and_is_in_geofence(path: Path) -> None:
    m = load_mission(path)
    assert isinstance(m, Mission)
    assert m.legs, f"{path.name} has no legs"
    assert all(len(leg.waypoints) >= 2 for leg in m.legs), f"{path.name} has a leg with <2 waypoints"

    result = GeofenceSkill().run(m)
    assert result.ok, (
        f"{path.name} breaches its own safety envelope: "
        f"{[(v.code, v.leg_index, v.waypoint_index) for v in result.violations]}"
    )
