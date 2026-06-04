# Contributing to FlyMax Orchestrator

Thanks for picking this up — the orchestrator is the layer where the most leveraged work happens. One PR here changes how a drone (Crazyflie, Pixhawk hex, a Phase-5 swarm, an eventual eVTOL) is asked to do something.

## What this is

A Claude-powered command layer for autonomous drone fleets. English goal → typed `MissionPlan` → dispatch to one or many drones → watch and recover. Sim before silicon. Backend-agnostic.

Live browser demo: **https://flymax.getmaxglobal.com/sim**

## Quick setup

```bash
# Python 3.11+
git clone https://github.com/jakesparow/flymax-orchestrator.git
cd flymax-orchestrator
python -m venv .venv
. .venv/bin/activate            # or: .venv\Scripts\activate on Windows
pip install -e ".[dev,sim]"

# Smoke test (no hardware, no API key required)
pytest -q
flymax fly --mission examples/two_drone_patrol.json --backend dryrun
```

If you have an Anthropic key, set `ANTHROPIC_API_KEY` in `.env` and the `plan` command will Claude-decompose your English goal:

```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
flymax plan "patrol Marina beach in a triangle at 30m altitude"
```

## What "good first issue" looks like

We tag five tracks:

| Label | What it means |
|---|---|
| `phase-1` | Sim work — Gazebo backend wiring, example missions, schema tweaks |
| `phase-2` | First-silicon work — Crazyflie cflib backend |
| `skill` | A new skill on top of the orchestrator (GeofenceSkill, TrackSkill, PerchSkill, ClusterSkill, Skybrush export…) |
| `backend` | A new backend (DJI SDK if it opens, Skydio if it opens, custom PGD) |
| `community` | Docs, examples, contributor experience |
| `good first issue` | Curated entry points for first PRs |

Open the [Issues tab](https://github.com/jakesparow/flymax-orchestrator/issues?q=label%3A%22good-first-issue%22) and pick one labelled `good-first-issue`.

## Architecture in 60 seconds

```
Operator (CLI / web UI / voice)
    │
    ▼
Orchestrator (Claude + skills)
  - plan(goal)   → typed MissionPlan
  - fly(plan)    → dispatches per drone
  - watch        → telemetry events
    │
    ▼
Backend ABC (flymax/backends/base.py)
  ├── DryrunBackend     (working — logs events)
  ├── GazeboBackend     (stub — wire to rclpy + crazyflie_simulation)
  ├── CrazyflieBackend  (stub — wire to cflib)
  └── (your new backend goes here)
```

A `MissionPlan` (JSON) is the only contract. The orchestrator never knows which backend it's talking to. Sim → hardware swap is one flag (`--backend gazebo` vs `--backend crazyflie`).

## How to add a new backend

1. Subclass `flymax.backends.base.Backend`.
2. Implement `async def fly(self, mission: Mission) -> AsyncIterator[TelemetryEvent]`.
3. Yield `TelemetryEvent(drone_id, ts, kind, payload)` for each waypoint reached / failure / completion.
4. Register the backend in `flymax/backends/__init__.py`.
5. Add a smoke test in `tests/`.
6. Add a `docs/backend-<name>.md` walkthrough.

See `flymax/backends/dryrun.py` for the reference implementation.

## How to add a new skill

Skills sit between the operator goal and the dispatcher. They run pre-arm (Geofence, energy budget) or post-plan (Skybrush export, voice confirm).

1. Add `flymax/skills/<your_skill>.py` exporting a callable `run(mission, context) -> Mission | RejectionReason`.
2. Wire it into the orchestrator's skill chain (next sprint — currently a placeholder).
3. Add tests covering at least one accept and one reject.

## Code style

- Python 3.11+ with type hints everywhere.
- `ruff format` (config in `pyproject.toml`) — runs in pre-commit and CI.
- `mypy --strict` (target — not all modules yet, but new code should pass).
- Pytest for tests. Network-touching tests must mock; no live Anthropic calls in unit tests.

## Commits + PRs

- Conventional commit messages preferred: `feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`.
- One concept per PR.
- Tests for new code; if it's a bugfix, include the failing-before-fix test.
- Update `README.md` and any docs you change.
- Note the issue you're closing in the PR body.

## Getting your PR merged

1. **Fork** the repo and clone locally.
2. **Branch:** `git checkout -b feat/your-feature-name` (use `feat:`, `fix:`, `docs:`, `test:` prefixes).
3. **Code:** Follow the style guide above. Add tests for new code.
4. **Push:** `git push origin feat/your-feature-name`
5. **PR:** Open a pull request. **Include the issue number in the body** (e.g., `Closes #15`).
6. **Review:** Sriram or a maintainer will review within 2 days.
7. **Merged:** Your commit is co-authored on the public MIT repo.

Questions? Open a [Discussion](https://github.com/jakesparow/flymax-orchestrator/discussions) or email sriram@getmaxrcm.com.

## Hardware safety

If you're testing with real Crazyflies / Pixhawks / anything that flies:

- Indoor, netted enclosure, until you have a DGCA pilot certificate AND the airframe is registered on DigitalSky.
- Geofence in software AND a physical kill switch.
- Battery management: never leave LiPo charging unattended.
- Insurance: `flytbase.com/insurance` or equivalent for outdoor.

## License

MIT. By contributing you agree your work is MIT-licensed.

## Community

- Discussions: https://github.com/jakesparow/flymax-orchestrator/discussions
- The Pilots Hub: https://flymax.getmaxglobal.com/community
- Public registry: https://flymax.getmaxglobal.com/registry
- Email: sriram@getmaxrcm.com (CEO, GetMax Healthcare Solutions — FlyMax is his side venture)
