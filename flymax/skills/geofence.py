"""geofence — the worked reference skill. A fail-closed pre-arm safety check.

This is the canonical example to copy when writing your own skill (closes #7).
It takes a Mission and reports every waypoint that breaches the mission's OWN
SafetyConstraints — the altitude ceiling, the geofence cube, the speed cap.

A safety skill fails closed: it does not rewrite the plan to make a breach
"legal", it reports the breach so the orchestrator can refuse to arm. The check
runs host-side and never trusts the LLM that produced the plan.

    from flymax.skills.geofence import GeofenceSkill

    result = GeofenceSkill().run(mission)      # -> SkillResult, inspect result.violations
    GeofenceSkill().enforce(mission)            # -> Mission, or raises UnsafeMissionError
"""

from __future__ import annotations

from ..missions import Mission
from .base import SkillResult, UnsafeMissionError, Violation


class GeofenceSkill:
    """Reject any waypoint outside the mission's declared safety envelope."""

    name = "geofence"
    triggers = ("geofence", "fence", "indoor", "safe", "altitude", "envelope")

    def run(self, mission: Mission, context: dict | None = None) -> SkillResult:
        s = mission.safety
        violations: list[Violation] = []

        for li, leg in enumerate(mission.legs):
            for wi, wp in enumerate(leg.waypoints):
                p = wp.position

                if p.z > s.max_altitude_m:
                    violations.append(
                        Violation("ALT_CEILING", f"z={p.z} m exceeds max_altitude_m={s.max_altitude_m}", li, wi)
                    )
                if p.z < s.geofence_min.z:
                    violations.append(
                        Violation("ALT_FLOOR", f"z={p.z} m below geofence_min.z={s.geofence_min.z}", li, wi)
                    )
                if not (s.geofence_min.x <= p.x <= s.geofence_max.x):
                    violations.append(
                        Violation("FENCE_X", f"x={p.x} m outside [{s.geofence_min.x}, {s.geofence_max.x}]", li, wi)
                    )
                if not (s.geofence_min.y <= p.y <= s.geofence_max.y):
                    violations.append(
                        Violation("FENCE_Y", f"y={p.y} m outside [{s.geofence_min.y}, {s.geofence_max.y}]", li, wi)
                    )
                if wp.speed_mps is not None and wp.speed_mps > s.max_speed_mps:
                    violations.append(
                        Violation("SPEED_CAP", f"speed_mps={wp.speed_mps} exceeds max_speed_mps={s.max_speed_mps}", li, wi)
                    )

        return SkillResult(mission=mission, violations=violations)

    def enforce(self, mission: Mission, context: dict | None = None) -> Mission:
        """Hard gate before arming: return the mission if safe, else raise."""
        result = self.run(mission, context)
        if result.violations:
            raise UnsafeMissionError(result.violations)
        return mission
