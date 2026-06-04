"""Mission schema — the typed contract between the orchestrator and any backend.

Same JSON flies in Gazebo and on a real Crazyflie. The orchestrator never knows
which backend is on the other end of the wire.
"""

from __future__ import annotations
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class Frame(str, Enum):
    """Coordinate frame for a Waypoint."""
    LOCAL = "local"  # meters from takeoff origin, x-forward, y-left, z-up (ENU)
    GLOBAL = "global"  # WGS-84 lat/lon/alt — outdoor only, Phase 4+


class Vec3(BaseModel):
    x: float
    y: float
    z: float


class Waypoint(BaseModel):
    """Single point in space the drone must visit."""
    position: Vec3
    frame: Frame = Frame.LOCAL
    yaw_deg: float | None = None  # if None, keep current heading
    hold_s: float = 0.0  # seconds to hover at the point before moving on
    speed_mps: float | None = None  # if None, backend default


class Formation(str, Enum):
    """Multi-drone geometric arrangements."""
    SOLO = "solo"
    LINE = "line"
    V = "v"
    DIAMOND = "diamond"
    GRID = "grid"


class Drone(BaseModel):
    """One drone in the fleet, with a stable id."""
    id: str  # e.g. "cf01", "cf02"
    callsign: str | None = None  # e.g. "Recon-1"
    backend_uri: str | None = None  # e.g. "radio://0/80/2M/E7E7E7E7E7"


class Leg(BaseModel):
    """One segment of a mission — a sequence of waypoints, possibly for many drones."""
    drone_ids: list[str]
    waypoints: list[Waypoint]
    formation: Formation = Formation.SOLO
    timeout_s: float = 60.0
    on_failure: Literal["abort", "rtl", "land", "hover"] = "rtl"

    @field_validator("waypoints")
    @classmethod
    def at_least_one_waypoint(cls, v: list[Waypoint]) -> list[Waypoint]:
        if not v:
            raise ValueError("Leg must have at least one waypoint")
        return v


class Mission(BaseModel):
    """A complete flight plan, decomposed by the orchestrator from a natural-language goal."""
    name: str
    description: str = ""
    fleet: list[Drone]
    legs: list[Leg]
    safety: SafetyConstraints
    metadata: dict = Field(default_factory=dict)

    @field_validator("fleet")
    @classmethod
    def fleet_unique_ids(cls, v: list[Drone]) -> list[Drone]:
        ids = [d.id for d in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Fleet drone ids must be unique")
        return v


class SafetyConstraints(BaseModel):
    """Hard limits the orchestrator and backends must enforce."""
    max_altitude_m: float = 2.0  # indoor cube default
    geofence_min: Vec3 = Field(default_factory=lambda: Vec3(x=-2, y=-2, z=0))
    geofence_max: Vec3 = Field(default_factory=lambda: Vec3(x=2, y=2, z=2))
    max_speed_mps: float = 1.0
    low_battery_pct: float = 25.0  # auto-RTL below this
    emergency_land_keyword: str = "ABORT"  # operator types this -> immediate land


# Backend-emitted telemetry, streamed back to the orchestrator.
class TelemetryEvent(BaseModel):
    drone_id: str
    timestamp: float  # unix seconds
    position: Vec3
    battery_pct: float
    state: Literal["idle", "armed", "flying", "hovering", "landing", "landed", "emergency"]
    leg_id: str | None = None
    message: str | None = None


def export_json_schema() -> dict:
    """The canonical Mission JSON Schema.

    This is the single structural contract. It feeds the Anthropic tool the
    planner forces (orchestrator.plan), and the TypeScript types the website's
    /sim ports. `flymax schema --out schema/mission.schema.json` writes it to disk
    so downstream consumers can regenerate from one source and never drift.
    """
    return Mission.model_json_schema()
