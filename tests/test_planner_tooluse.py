"""Planner — Orchestrator.plan() forces submit_mission tool-use and validates the result.

No live key, no network: a fake Anthropic client returns a canned tool_use block.
This locks in the contract (forced tool-use + Pydantic validation) so a regression
back to brittle free-text json.loads is caught.
"""

from __future__ import annotations

import pytest

from flymax.missions import Mission
from flymax.orchestrator import Orchestrator

VALID_MISSION = {
    "name": "square-1m",
    "description": "fly a 1m square indoors",
    "fleet": [{"id": "cf01"}],
    "legs": [
        {
            "drone_ids": ["cf01"],
            "waypoints": [
                {"position": {"x": 0, "y": 0, "z": 1}},
                {"position": {"x": 1, "y": 0, "z": 1}},
                {"position": {"x": 1, "y": 1, "z": 1}},
                {"position": {"x": 0, "y": 0, "z": 1}},
            ],
            "formation": "solo",
            "timeout_s": 60,
            "on_failure": "rtl",
        }
    ],
    "safety": {
        "max_altitude_m": 2.0,
        "geofence_min": {"x": -2, "y": -2, "z": 0},
        "geofence_max": {"x": 2, "y": 2, "z": 2},
        "max_speed_mps": 1.0,
        "low_battery_pct": 25.0,
        "emergency_land_keyword": "ABORT",
    },
    "metadata": {},
}


class _Block:
    def __init__(self, *, type: str, name: str | None = None, input: dict | None = None,
                 text: str | None = None) -> None:
        self.type = type
        self.name = name
        self.input = input
        self.text = text


class _Msg:
    def __init__(self, content: list[_Block]) -> None:
        self.content = content


class _Messages:
    def __init__(self, content: list[_Block]) -> None:
        self._content = content
        self.calls: list[dict] = []

    def create(self, **kwargs: object) -> _Msg:
        self.calls.append(kwargs)
        return _Msg(self._content)


class FakeAnthropic:
    def __init__(self, content: list[_Block]) -> None:
        self.messages = _Messages(content)


def test_plan_returns_validated_mission_from_tool_use() -> None:
    fake = FakeAnthropic([_Block(type="tool_use", name="submit_mission", input=VALID_MISSION)])
    orch = Orchestrator(anthropic_client=fake)

    mission = orch.plan("fly a 1m square")

    assert isinstance(mission, Mission)
    assert mission.name == "square-1m"
    assert len(mission.legs[0].waypoints) == 4


def test_plan_forces_the_submit_mission_tool() -> None:
    fake = FakeAnthropic([_Block(type="tool_use", name="submit_mission", input=VALID_MISSION)])
    Orchestrator(anthropic_client=fake).plan("fly a 1m square")

    call = fake.messages.calls[0]
    assert call["tool_choice"] == {"type": "tool", "name": "submit_mission"}
    assert any(t["name"] == "submit_mission" for t in call["tools"])
    # the tool's input_schema is the real Mission schema, not a prose hint
    schema = call["tools"][0]["input_schema"]
    assert schema["type"] == "object"
    assert "legs" in schema["properties"]


def test_plan_raises_when_no_tool_use_block() -> None:
    fake = FakeAnthropic([_Block(type="text", text="here is your plan")])
    with pytest.raises(ValueError, match="submit_mission"):
        Orchestrator(anthropic_client=fake).plan("fly a 1m square")
