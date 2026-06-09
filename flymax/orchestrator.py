"""The orchestrator — natural language goal → typed Mission → backend dispatch.

The Claude call is constrained by Pydantic JSON schema so the model can ONLY emit
valid Mission objects. There is no free-form output — the planning prompt forces
tool-use against the mission schema.

Phase 1: single-leg, single-drone, indoor missions only. Multi-leg + multi-drone
decomposition lands in Phase 3 once formation execution is solved at the backend.
"""

from __future__ import annotations
import json
import os
from collections.abc import AsyncIterator
from pathlib import Path
import asyncio

import structlog
from anthropic import Anthropic
from dotenv import load_dotenv

from .backends import Backend, get_backend
from .missions import Mission, SafetyConstraints, TelemetryEvent
from .missions.schema import export_json_schema
from .skills import GeofenceSkill
from flymax.bridge import BrowserBridge

logger = structlog.get_logger(__name__)


SYSTEM_PROMPT = """\
You are FlyMax-Planner, a flight-planning subagent. You take a short
natural-language mission goal and emit a strictly-typed Mission JSON object.

Hard rules:
  1. Always answer by CALLING the submit_mission tool. Never reply with prose.
  2. NEVER exceed Mission.safety.max_altitude_m or Mission.safety.geofence_*.
  3. NEVER plan outdoor missions unless mission_context.outdoor is true.
  4. Default to indoor 2m cube safety constraints if the operator doesn't say otherwise.
  5. If the operator asks for something physically impossible or unsafe, return a
     Mission with an empty `legs` list and put the refusal in `metadata.refusal_reason`.

You are NOT controlling drones in real time. You are emitting a flight plan.
A separate executor reads the JSON and dispatches it to drones (sim or hardware).
"""


def _default_safety() -> SafetyConstraints:
    return SafetyConstraints()


class Orchestrator:
    """Plans missions with Claude. Executes them via a chosen Backend."""

    def __init__(
        self,
        anthropic_client: Anthropic | None = None,
        model: str = "claude-sonnet-4-6",
        safety: SafetyConstraints | None = None,
    ) -> None:
        load_dotenv()
        # # Build the Anthropic client lazily - only `plan()` needs it. Executing a
        # # pre-authored mission (`fly` on dryrun/gazebo/crazyflie) must work with no key.
        self._client = anthropic_client
        self.model = model
        self.safety = safety or _default_safety()

        # --- Add WebSocket Bridge initialization ---
        self.bridge = BrowserBridge()
        self.bridge.on_mission_received = self.handle_incoming_mission
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.bridge.start())
        except RuntimeError:
            asyncio.ensure_future(self.bridge.start())

    @property
    def client(self) -> Anthropic:
        """The Anthropic client, constructed on first use. Raises only if planning is attempted without a key."""
        if self._client is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "ANTHROPIC_API_KEY not set. Add to .env or environment before planning."
                )
            self._client = Anthropic(api_key=api_key)
        return self._client

    # ----- Planning -----

    def plan(self, goal: str, context: dict | None = None) -> Mission:
        """Turn a natural-language goal into a typed Mission via Claude tool-use.

        The model is FORCED to call submit_mission, whose input_schema is the
        canonical Mission JSON Schema. It cannot emit prose or malformed JSON —
        the only legal output is a Mission-shaped tool call, which Pydantic then
        validates. The geofence skill re-checks the result host-side at dispatch
        (see fly); the planner's output is never trusted to be safe.
        """
        ctx = context or {}
        user_content = (
            f"Operator goal:\n{goal}\n\n"
            f"Context:\n{json.dumps(ctx, indent=2)}\n\n"
            f"Default safety:\n{self.safety.model_dump_json(indent=2)}"
        )
        logger.info("orchestrator.plan.start", goal=goal, model=self.model)

        msg = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=[_mission_tool()],
            tool_choice={"type": "tool", "name": "submit_mission"},
            messages=[{"role": "user", "content": user_content}],
        )
        block = next(
            (
                b
                for b in msg.content
                if getattr(b, "type", None) == "tool_use"
                and getattr(b, "name", None) == "submit_mission"
            ),
            None,
        )
        if block is None:
            logger.error("orchestrator.plan.no_tool_use")
            raise ValueError("Claude did not return a submit_mission tool call")

        mission = Mission.model_validate(block.input)
        logger.info(
            "orchestrator.plan.ok",
            name=mission.name,
            fleet=len(mission.fleet),
            legs=len(mission.legs),
        )
        return mission

    # ----- Execution -----

    async def fly(self, mission: Mission, backend_name: str) -> AsyncIterator[TelemetryEvent]:
            """Dispatch a mission to a backend. Streams telemetry until completion or abort."""
            # A host-side geofence check runs BEFORE any backend is reached – the
            # never-arm-without-a-safe-plan invariant. Fails closed: an out-of-envelope
            # mission raises UnsafeMissionError and no backend ever sees it.
            GeofenceSkill().enforce(mission)
            backend: Backend = get_backend(backend_name)
            logger.info("orchestrator.fly.start", backend=backend.name, mission=mission.name)
            await backend.connect(mission)
            try:
                async for event in backend.execute(mission):
                    asyncio.create_task(self.bridge.broadcast_telemetry(event))
                    yield event
            finally:
                await backend.disconnect()
                logger.info("orchestrator.fly.disconnect", backend=backend.name)

    async def handle_incoming_mission(self, mission: Mission) -> None:
            """Callback to handle missions received over the WebSocket bridge from the browser."""
            logger.info(f"Executing mission received from browser bridge: {mission.name}")
            
            backend_name = "dryrun"
            async for event in self.fly(mission, backend_name):
                pass
def load_mission(path: Path | str) -> Mission:
    """Load a Mission from a JSON file. Useful for replaying or hand-authored plans."""
    p = Path(path)
    return Mission.model_validate_json(p.read_text(encoding="utf-8"))

def _mission_tool() -> dict:
    """The Anthropic tool the planner is forced to call.

    Its input_schema IS the canonical Mission JSON Schema, so the model can only
    produce a Mission-shaped object — no prose, no fences, no drift from the
    Pydantic source of truth.
    """
    return {
        "name": "submit_mission",
        "description": (
            "Emit the typed FlyMax Mission that satisfies the operator's goal. "
            "Coordinates are metres in the local ENU frame (x east, y north, z up) "
            "unless the context marks the mission outdoor. Stay within the provided "
            "safety constraints; a waypoint outside them will be rejected before arming."
        ),
        "input_schema": export_json_schema(),
    }
