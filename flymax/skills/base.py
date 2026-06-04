"""Skill base types — the contract every FlyMax skill implements.

A skill is a small, focused unit of planning or checking logic the orchestrator
can apply to a Mission. There are two flavours:

  - *checking* skills (e.g. geofence) inspect a Mission and report Violations.
    They are fail-closed: they never mutate the plan to "fix" a breach, they
    report it and let the orchestrator refuse to arm.
  - *planning* skills (Phase 2+: formation, survey, rth) emit or rewrite
    waypoints deterministically, off the LLM path.

Copy flymax/skills/geofence.py as the worked reference when writing your own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ..missions import Mission


@dataclass(frozen=True)
class Violation:
    """A single safety/constraint breach, located precisely in the Mission."""

    code: str
    message: str
    leg_index: int | None = None
    waypoint_index: int | None = None


class UnsafeMissionError(ValueError):
    """Raised by a checking skill's enforce() when a Mission breaches its own constraints."""

    def __init__(self, violations: list[Violation]) -> None:
        self.violations = violations
        joined = "; ".join(f"[{v.code}] {v.message}" for v in violations)
        super().__init__(f"Mission rejected — {len(violations)} violation(s): {joined}")


@dataclass
class SkillResult:
    """What a skill returns: the (possibly unchanged) mission plus any findings."""

    mission: Mission
    violations: list[Violation] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations


@runtime_checkable
class Skill(Protocol):
    """Structural type a skill must satisfy. No inheritance required."""

    name: str

    def run(self, mission: Mission, context: dict | None = None) -> SkillResult:
        """Inspect or transform the mission. Pure — no I/O, no network."""
        ...
