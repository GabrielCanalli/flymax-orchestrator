"""rth — return-to-home trajectory. The recovery primitive every mission needs.

Climb to a safe cruise altitude in place, transit home at that altitude, then
descend to a landing height. Pure geometry — the same three legs whether it is
triggered by low battery, an ABORT, or end-of-mission.
"""

from __future__ import annotations

from ..missions import Vec3, Waypoint


def rth_waypoints(
    frm: Vec3,
    home: Vec3,
    cruise_alt_m: float,
    land_z: float = 0.3,
    speed_mps: float | None = None,
) -> list[Waypoint]:
    """Climb-transit-descend back to home. Returns three waypoints."""
    return [
        Waypoint(position=Vec3(x=frm.x, y=frm.y, z=cruise_alt_m), speed_mps=speed_mps),
        Waypoint(position=Vec3(x=home.x, y=home.y, z=cruise_alt_m), speed_mps=speed_mps),
        Waypoint(position=Vec3(x=home.x, y=home.y, z=land_z), speed_mps=speed_mps),
    ]
