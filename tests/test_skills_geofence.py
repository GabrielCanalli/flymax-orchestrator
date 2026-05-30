"""GeofenceSkill — the worked reference skill must pass safe plans and reject breaches."""

from __future__ import annotations

import asyncio

import pytest

from flymax.missions import (
    Drone,
    Formation,
    Leg,
    Mission,
    SafetyConstraints,
    Vec3,
    Waypoint,
)
from flymax.orchestrator import Orchestrator
from flymax.skills import GeofenceSkill, UnsafeMissionError


def _mission(*points: tuple[float, float, float], speed: float | None = None) -> Mission:
    """Build a one-drone mission with default (2m indoor cube) safety."""
    return Mission(
        name="test",
        fleet=[Drone(id="cf01")],
        legs=[
            Leg(
                drone_ids=["cf01"],
                waypoints=[
                    Waypoint(position=Vec3(x=x, y=y, z=z), speed_mps=speed) for (x, y, z) in points
                ],
                formation=Formation.SOLO,
            )
        ],
        safety=SafetyConstraints(),  # max_alt 2, cube +/-2, max_speed 1
    )


def test_geofence_passes_a_safe_mission() -> None:
    m = _mission((0, 0, 1.0), (1.0, -1.0, 1.5))
    result = GeofenceSkill().run(m)
    assert result.ok
    assert result.violations == []
    # enforce returns the mission unchanged
    assert GeofenceSkill().enforce(m) is m


def test_geofence_flags_altitude_ceiling() -> None:
    m = _mission((0, 0, 5.0))  # z=5 over the 2m ceiling
    result = GeofenceSkill().run(m)
    codes = {v.code for v in result.violations}
    assert "ALT_CEILING" in codes
    assert not result.ok


def test_geofence_flags_horizontal_breach_and_locates_it() -> None:
    m = _mission((0, 0, 1.0), (10.0, 0, 1.0))  # second waypoint outside the cube in x
    result = GeofenceSkill().run(m)
    breach = next(v for v in result.violations if v.code == "FENCE_X")
    assert breach.leg_index == 0
    assert breach.waypoint_index == 1


def test_geofence_flags_speed_cap() -> None:
    m = _mission((0, 0, 1.0), speed=9.0)  # 9 m/s over the 1 m/s cap
    codes = {v.code for v in GeofenceSkill().run(m).violations}
    assert "SPEED_CAP" in codes


def test_enforce_raises_with_all_violations() -> None:
    m = _mission((10.0, 0, 5.0))  # outside cube AND over ceiling
    with pytest.raises(UnsafeMissionError) as exc:
        GeofenceSkill().enforce(m)
    assert len(exc.value.violations) >= 2


def test_fly_refuses_unsafe_mission_before_arming() -> None:
    """The never-arm invariant: fly() must reject an unsafe plan before any backend runs."""
    orch = Orchestrator()
    unsafe = _mission((0, 0, 9.0))

    async def run() -> None:
        async for _ in orch.fly(unsafe, "dryrun"):
            pass

    with pytest.raises(UnsafeMissionError):
        asyncio.run(run())


def test_fly_allows_safe_mission_through_dryrun() -> None:
    orch = Orchestrator()
    safe = _mission((0, 0, 1.0), (1.0, 1.0, 1.0))

    async def run() -> list:
        return [ev async for ev in orch.fly(safe, "dryrun")]

    events = asyncio.run(run())
    assert events, "safe mission should stream telemetry"
    assert events[-1].state == "landed"
