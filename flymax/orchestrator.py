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

import structlog
from anthropic import Anthropic
from dotenv import load_dotenv

from .backends import Backend, get_backend
from .missions import Mission, SafetyConstraints, TelemetryEvent

logger = structlog.get_logger(__name__)


SYSTEM_PROMPT = """\
You are FlyMax-Planner, a flight-planning subagent. You take a short
natural-language mission goal and emit a strictly-typed Mission JSON object.

Hard rules:
  1. ONLY emit JSON conforming to the provided Mission schema. No prose. No code fences.
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
        # Build the Anthropic client lazily — only `plan()` needs it. Executing a
        # pre-authored mission (`fly` on dryrun/gazebo/crazyflie) must work with no key.
        self._client = anthropic_client
        self.model = model
        self.safety = safety or _default_safety()

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
        """Turn a natural-language goal into a Mission via Claude.

        Phase 1: single-shot, no multi-turn reasoning. Pydantic validation gives us
        the guardrail — anything Claude returns that doesn't parse is rejected,
        the operator retries with a clearer prompt.
        """
        ctx = context or {}
        user_content = (
            f"Operator goal:\n{goal}\n\n"
            f"Context:\n{json.dumps(ctx, indent=2)}\n\n"
            f"Default safety:\n{self.safety.model_dump_json(indent=2)}\n\n"
            f"Return ONLY a Mission JSON object matching the schema."
        )
        logger.info("orchestrator.plan.start", goal=goal, model=self.model)

        # Phase 1 keeps this simple: ask for JSON, parse it, validate.
        # Phase 2 will switch to tool-use with the Mission schema as the tool input
        # for harder constraint enforcement.
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT + "\n\nMission schema (Pydantic):\n" + _mission_schema_hint(),
            messages=[{"role": "user", "content": user_content}],
        )
        text = "".join(b.text for b in msg.content if hasattr(b, "text"))
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.error("orchestrator.plan.json_error", text=text[:500])
            raise ValueError(f"Claude did not return parseable JSON: {e}") from e

        mission = Mission.model_validate(data)
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
        backend: Backend = get_backend(backend_name)
        logger.info("orchestrator.fly.start", backend=backend.name, mission=mission.name)
        await backend.connect(mission)
        try:
            async for event in backend.execute(mission):
                yield event
        finally:
            await backend.disconnect()
            logger.info("orchestrator.fly.disconnect", backend=backend.name)


def load_mission(path: Path | str) -> Mission:
    """Load a Mission from a JSON file. Useful for replaying or hand-authored plans."""
    p = Path(path)
    return Mission.model_validate_json(p.read_text(encoding="utf-8"))


def _mission_schema_hint() -> str:
    """Compact schema hint to feed Claude alongside the system prompt.

    Kept terse — full schema is too verbose for every planning call. We rely on
    Pydantic validation on the way back to catch anything malformed.
    """
    return (
        "Mission fields: name (str), description (str), fleet (list[Drone]), "
        "legs (list[Leg]), safety (SafetyConstraints), metadata (dict).\n"
        "Drone: id (str), callsign (str|null), backend_uri (str|null).\n"
        "Leg: drone_ids (list[str]), waypoints (list[Waypoint]), "
        "formation ('solo'|'line'|'v'|'diamond'|'grid'), timeout_s (float), "
        "on_failure ('abort'|'rtl'|'land'|'hover').\n"
        "Waypoint: position {x,y,z}, frame ('local'|'global'), yaw_deg (float|null), "
        "hold_s (float), speed_mps (float|null).\n"
        "SafetyConstraints: max_altitude_m, geofence_min {x,y,z}, geofence_max {x,y,z}, "
        "max_speed_mps, low_battery_pct, emergency_land_keyword."
    )
