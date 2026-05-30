"""Skills — focused units of planning/checking logic the orchestrator applies to a Mission.

A skill is a small Python object satisfying the Skill protocol (see base.py).
Checking skills (geofence) fail closed; planning skills (formation, survey, rth —
Phase 2+) emit waypoints deterministically off the LLM path.

The orchestrator selects relevant skills by the operator's goal (Phase 2). Today
the geofence check is wired as a hard pre-arm gate in Orchestrator.fly().

Copy flymax/skills/geofence.py as the worked reference when adding a skill.
"""

from __future__ import annotations

from .base import Skill, SkillResult, UnsafeMissionError, Violation
from .geofence import GeofenceSkill

__all__ = [
    "Skill",
    "SkillResult",
    "Violation",
    "UnsafeMissionError",
    "GeofenceSkill",
]
