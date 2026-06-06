# Backend Integration Template

This document provides a standard 5-step template to implement a new hardware or simulation backend for the FlyMax Orchestrator, using `flymax/backends/dryrun.py` as a reference.

All backends must inherit from the base `Backend` class and implement its core lifecycle methods.

---

## Step 1: Inherit from the Base Backend Class

Create a new file under `flymax/backends/your_backend.py` and define your class by inheriting from `Backend`. You must also define a unique string identifier for the `name` attribute.

```python
from ..missions import Mission, TelemetryEvent, Vec3
from .base import Backend

class YourBackend(Backend):
    name = "your_backend_name"

    def __init__(self) -> None:
        self._connected: list[str] = []

## Step 2: Implement Connection Logic (`connect`)

The `connect` method receives a `Mission` object before execution begins. Use this step to initialize communication with your hardware fleet, target simulation, or radios, and keep track of connected drones.

```python
    async def connect(self, mission: Mission) -> None:
        # Initialize your radios, sockets, or SDK clients here
        self._connected = [d.id for d in mission.fleet]

## Step 3: Implement Mission Execution Flow (`execute`)

The `execute` method is an asynchronous iterator (`AsyncIterator`) that processes flight paths (`legs` and `waypoints`) and yields real-time `TelemetryEvent` updates back to the orchestrator.

```python
    async def execute(self, mission: Mission) -> AsyncIterator[TelemetryEvent]:
        for leg in mission.legs:
            for wp in leg.waypoints:
                for drone_id in leg.drone_ids:
                    # Send flight commands to hardware or simulator here
                    yield TelemetryEvent(
                        drone_id=drone_id,
                        timestamp=time.time(),
                        position=Vec3(x=wp.position.x, y=wp.position.y, z=wp.position.z),
                        battery_pct=100.0,
                        state="flying",
                        message=f"Executing waypoint at ({wp.position.x}, {wp.position.y})",
                    )
                if wp.hold_s > 0:
                    await asyncio.sleep(wp.hold_s)

## Step 4: Handle Post-Mission and Emergency Scenarios

You must define what happens when unexpected critical interventions occur via `emergency_land`. This acts as a panic button to immediately land all active aircraft.

```python
    async def emergency_land(self) -> None:
        # CRITICAL: Send immediate broadcast command to land all vehicles
        pass

## Step 5: Implement Cleanup and Disconnection (`disconnect`)

When the orchestrator tears down the session, `disconnect` is triggered. Use this to safely close network sockets, drop radio connection feeds, and reset internal states.

```python
    async def disconnect(self) -> None:
        # Safely shut down connections and clear active trackers
        self._connected = []