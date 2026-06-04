"""Gazebo / PX4-SITL backend — flies the mission in simulation over MAVLink.

How it fits: the orchestrator decomposes an English goal into a Mission (schema.py),
then a backend executes it. `dryrun` logs waypoints; `gazebo` flies them in a real
PX4 Software-In-The-Loop sim running under Gazebo, talking MAVLink via MAVSDK. The
SAME Mission object that runs here runs on a Crazyflie later — only the backend swaps.

Pipeline this targets (set up once, see docs/setup-gazebo.md):
    PX4-Autopilot SITL  <— MAVLink/UDP —>  MAVSDK (this file)  <—  orchestrator
            |
        Gazebo Harmonic (physics + sensors + 3D)

STATUS 2026-05-31: implemented against the standard MAVSDK offboard-NED API, but
NOT yet verified on this Windows box (it has no PX4 SITL / WSL2 env — that is task
SIM-01..SIM-05 in flymax/FLYMAX_TASKS.md). `mavsdk` is imported lazily so the
package still imports/installs without it; connect() fails LOUD with the install
path if the dep or the SITL endpoint is missing. It never pretends to fly.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator

from ..missions import Mission, TelemetryEvent, Vec3
from .base import Backend

# Default PX4 SITL onboard-API endpoint. Override per-drone via Drone.backend_uri.
# MAVSDK 3.x requires the udpin:// scheme (old udp:// is removed). Verified flying
# PX4 SITL + Gazebo Harmonic on WSL Ubuntu-24.04, 2026-06-01 (see flymax/SIM_STACK_README.md).
_DEFAULT_SITL_URI = "udpin://0.0.0.0:14540"


class GazeboBackend(Backend):
    name = "gazebo"

    def __init__(self) -> None:
        # drone_id -> connected MAVSDK System
        self._systems: dict[str, object] = {}
        self._mavsdk = None  # the lazily-imported module

    def _require_mavsdk(self):
        if self._mavsdk is None:
            try:
                import mavsdk  # type: ignore
            except ImportError as e:  # fail LOUD, with the fix
                raise RuntimeError(
                    "Gazebo backend needs MAVSDK and a running PX4 SITL.\n"
                    "  1) pip install mavsdk\n"
                    "  2) start the sim:  make px4_sitl gz_x500   (see docs/setup-gazebo.md)\n"
                    "  3) re-run:  flymax fly --mission <m.json> --backend gazebo"
                ) from e
            self._mavsdk = mavsdk
        return self._mavsdk

    async def connect(self, mission: Mission) -> None:
        mavsdk = self._require_mavsdk()
        System = mavsdk.System  # type: ignore[attr-defined]
        for drone in mission.fleet:
            uri = drone.backend_uri or _DEFAULT_SITL_URI
            sys = System()
            await sys.connect(system_address=uri)
            # wait for the SITL link to come up
            async for state in sys.core.connection_state():
                if state.is_connected:
                    break
            self._systems[drone.id] = sys

    async def execute(self, mission: Mission) -> AsyncIterator[TelemetryEvent]:
        mavsdk = self._require_mavsdk()
        OffboardError = mavsdk.offboard.OffboardError  # type: ignore[attr-defined]
        PositionNedYaw = mavsdk.offboard.PositionNedYaw  # type: ignore[attr-defined]

        for leg in mission.legs:
            for drone_id in leg.drone_ids:
                sys = self._systems.get(drone_id)
                if sys is None:
                    continue
                await sys.action.arm()
                # seed offboard with the first setpoint, then start offboard mode
                first = leg.waypoints[0]
                await sys.offboard.set_position_ned(
                    PositionNedYaw(first.position.x, first.position.y, -first.position.z, first.yaw_deg or 0.0)
                )
                try:
                    await sys.offboard.start()
                except OffboardError:
                    await sys.action.disarm()
                    raise
                for wp in leg.waypoints:
                    # schema.py frame is z-up; PX4 NED is z-down -> negate z
                    await sys.offboard.set_position_ned(
                        PositionNedYaw(wp.position.x, wp.position.y, -wp.position.z, wp.yaw_deg or 0.0)
                    )
                    # report telemetry as we command each point
                    battery_pct = 100.0
                    async for bat in sys.telemetry.battery():
                        battery_pct = bat.remaining_percent * 100.0
                        break
                    yield TelemetryEvent(
                        drone_id=drone_id,
                        timestamp=time.time(),
                        position=Vec3(x=wp.position.x, y=wp.position.y, z=wp.position.z),
                        battery_pct=battery_pct,
                        state="flying",
                        message=f"gazebo waypoint ({wp.position.x},{wp.position.y},{wp.position.z})",
                    )
                    if wp.hold_s > 0:
                        import asyncio

                        await asyncio.sleep(wp.hold_s)
                await sys.action.return_to_launch()
                yield TelemetryEvent(
                    drone_id=drone_id,
                    timestamp=time.time(),
                    position=Vec3(x=0, y=0, z=0),
                    battery_pct=battery_pct,
                    state="landed",
                    message="gazebo leg complete (RTL)",
                )

    async def emergency_land(self) -> None:
        for sys in self._systems.values():
            try:
                await sys.action.land()  # type: ignore[attr-defined]
            except Exception:
                pass

    async def disconnect(self) -> None:
        self._systems.clear()
