# FlyMax Orchestrator

> An open autonomy layer for drones. You describe a mission; it plans the flight and runs it through a backend — a dry-run logger, a Gazebo/PX4 simulator, real hardware later. The same mission file flies in all three.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Status: early](https://img.shields.io/badge/status-early-orange)](#status--honesty)

## What this actually is

A mission is a JSON file — waypoints, formations, limits. The orchestrator validates it against a typed schema, runs a host-side geofence check, then hands it to a **backend** that executes it and streams telemetry back. The orchestrator never knows which backend is on the other end, so the same mission you dry-run on a laptop is the one that flies in the simulator, and (later) the one that flies a real airframe.

It's solo-built and early. The sections below are split honestly into *what runs today* and *what's still a plan*, because I'd rather you know which is which before you clone.

## What works today (verifiable in this repo)

- **`dryrun` backend** — flies any mission with no hardware and no API key. Logs every waypoint as a telemetry event. Try it in 2 minutes (below).
- **`gazebo` / PX4-SITL backend** — the brain arms, takes off, flies a square, returns to launch and lands an x500 quad in Gazebo Harmonic over MAVLink. Needs a sim stack (WSL2 + PX4 + Gazebo); setup is involved but real.
- **Six pre-authored missions** in [`examples/`](examples/) — patrol, agri survey, tower-orbit inspection, V-formation recce, perch-and-watch, and a swarm light-show. Each has a matching telemetry log under `flight_logs/` in the companion workspace.
- **A typed mission schema** ([`flymax/missions/schema.py`](flymax/missions/schema.py)) with geofence limits that are enforced *before* a backend is ever reached — an unsafe mission raises `UnsafeMissionError` and nothing flies.

## What's a plan, not a fact (yet)

- **Natural-language → mission** ("type a goal in English, get a flight plan"). The schema and dispatch are real; the Claude decomposition step is wired but not the thing I'd demo. Pre-authored missions are what fly reliably right now.
- **`crazyflie` backend** — stubbed. It raises `NotImplementedError` on purpose until hardware is in hand.
- **Real outdoor flight** — gated on a DGCA Digital Sky registration and a confirmed reason to spend on hardware. Not started.

> If a claim isn't in the "works today" list, treat it as intent.

## Why build it

The hard part of a drone fleet isn't the flight controller — PX4 and ArduPilot solved that. It's the layer above: who decides what each drone does, how a goal gets decomposed into legs, how a failure cascades back up, how an operator sees the floor. That delegation-and-telemetry substrate is nearly identical to the one that runs a fleet of software agents — which is the other thing I build (healthcare RCM agents at [getmaxglobal.com](https://getmaxglobal.com)). Same brain, different effectors. So it gets built once.

The code is open because the moat isn't the orchestrator — it's the flight data and the missions that accumulate on top of it.

## Design principles

1. **Sim before silicon.** Every mission runs in a simulator before a prop spins.
2. **Backend-agnostic.** One mission schema; swap dryrun ↔ gazebo ↔ hardware underneath.
3. **No closed cloud in the loop by default.** The LLM call is optional and replaceable; missions can run with no key at all.
4. **Auditable.** Every decision is logged. Not a black box.
5. **Hard kill, always.** A stop path in the CLI and in any UI.

## Architecture

```
        Operator (CLI / web / voice)
                  │  goal or mission file
                  ▼
        Orchestrator  ──  geofence check (host-side, pre-backend)
                  │  typed Mission
                  ▼
     ┌────────────┼────────────┐
     ▼            ▼            ▼
  dryrun       gazebo      hardware
 (no hw)      (PX4 SITL)   (later)
```

Same JSON, every backend. The orchestrator doesn't know which one it's talking to.

## Quickstart — 2 minutes, no hardware, no key

```bash
git clone https://github.com/jakesparow/flymax-orchestrator.git
cd flymax-orchestrator
pip install -e .

# fly a pre-authored mission with the dry-run backend
flymax fly --mission examples/two_drone_patrol.json --backend dryrun
```

You'll see each waypoint stream past as a telemetry event. That's the whole loop, minus the radio.

To fly the same mission in the simulator (`--backend gazebo`), you need WSL2 + PX4-SITL + Gazebo Harmonic. The walkthrough is in [`docs/setup-gazebo.md`](docs/setup-gazebo.md). It's not a 2-minute job — budget an afternoon.

## Roadmap

| Phase | Outcome | State |
|---|---|---|
| 0 | Repo, mission schema, dryrun backend | ✅ done |
| 1 | One drone flies a mission in Gazebo/PX4-SITL | ✅ working (square mission, RTL, land) |
| 2 | Multi-drone in sim; NL decomposition is demo-grade | 🔜 in progress |
| 3 | Real airframe flies the same mission via a hardware backend | ⏸ gated on a confirmed buyer + DGCA |
| 4 | Outdoor / GPS missions, compliance | ⏸ later |

I'm not putting dates on phases 3–4 because they depend on talking to real operators first, not on me writing more code.

## Non-goals (on purpose)

- Not building another flight controller — PX4 / ArduPilot are excellent.
- Not building another SLAM stack.
- Not selling drones. The drone is the commodity; the orchestrator and the missions on top are the point.

## Prior art worth reading

- [UZH Robotics & Perception Group](https://rpg.ifi.uzh.ch/) — agile flight, drone racing. ([Champion-level drone racing, Nature 2023](https://www.nature.com/articles/s41586-023-06419-4)).
- [Bitcraze Crazyswarm2](https://imrclab.github.io/crazyswarm2/) — the canonical multi-Crazyflie stack on ROS 2.
- [PX4 Autopilot](https://px4.io/) — the flight stack this project simulates against.

## Status & honesty

Early. Solo-built by [Sriram Raghavan](mailto:sriram@getmaxrcm.com). The dryrun and Gazebo paths are real and you can run them; most of the rest is a plan I'm being upfront about. Criticism, "have you considered…", and "this claim is overstated" are all genuinely welcome — open an issue.

## License

MIT. See [LICENSE](LICENSE).
