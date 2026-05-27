# FlyMax Orchestrator

> A Claude-powered orchestrator for drone swarms. One sentence in. A formation flies.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Status: pre-alpha](https://img.shields.io/badge/status-pre--alpha-orange)](#roadmap)

## What this is

A high-level command layer for autonomous drone fleets. You type a goal in English. A reasoning model (Anthropic's Claude) decomposes it into a flight plan (waypoints, formations, contingencies), dispatches the legs to one or many drones, and watches the kanban for completion.

The drones themselves stay dumb — they speak [Crazyflie Python API (cflib)](https://github.com/bitcraze/crazyflie-lib-python) and/or [PX4 + MAVLink](https://docs.px4.io/) over MAVSDK. The smart layer is portable: same orchestrator, swap the backend, simulate first, fly later.

## Why

The hard problem in drone fleets isn't flight controllers — those are solved. It's the **delegation, memory, and telemetry substrate**: who decides what each drone does, how a mission gets decomposed, how failure cascades back up the chain, how the operator sees the floor.

That substrate looks suspiciously identical to the one that runs a fleet of AI agents in a SaaS product. We're building it once and using it for both.

> **Dual-use, by design.** The orchestrator in this repo is the same shape as the one running our healthcare RCM agents at [getmaxglobal.com](https://getmaxglobal.com). Different effectors, same brain.

## Design principles

1. **Sim before silicon.** Every mission runs in Gazebo (or Isaac Sim later) before any prop spins.
2. **Backend-agnostic.** Crazyflie 2.1+ today, PX4 / Pixhawk later, Anduril SDK if it ever opens up.
3. **No closed clouds in the loop.** Sensitive missions stay on-prem or on a private GPU host. Cloud LLM call is optional and replaceable.
4. **Auditable.** Every decision the orchestrator makes (decomposition, dispatch, recovery) is logged with reasoning. We're not building a black box.
5. **Hard kill, always.** Big red button in the CLI. Big red button in the web UI when there is one. Big red button in the controller pairing.

## Architecture

```
                  ┌────────────────────────────────────┐
                  │  Operator (CLI / web UI / voice)   │
                  └────────────────┬───────────────────┘
                                   │ natural-language goal
                                   ▼
                  ┌────────────────────────────────────┐
                  │  Orchestrator (Claude + skills)    │
                  │   - decompose                      │
                  │   - dispatch                       │
                  │   - watch + nudge                  │
                  └────────────────┬───────────────────┘
                                   │ MissionPlan (typed)
                                   ▼
            ┌──────────────────────┴──────────────────────┐
            │                                             │
            ▼                                             ▼
   ┌────────────────┐                          ┌────────────────┐
   │  Backend: Sim  │                          │  Backend: HW   │
   │  (Gazebo +     │ ◀── shared mission ──▶  │  (Crazyflie,   │
   │   crazyflie-   │      schema, same        │   PX4 later)   │
   │   simulation)  │      orchestrator        │                │
   └────────────────┘                          └────────────────┘
```

A mission is JSON. Same JSON flies in sim and on hardware. The orchestrator never knows which backend it's talking to.

## Quickstart (Phase 1 — sim only)

> Hardware (Crazyflie) lands in Phase 2 once units ship. Phase 1 is sim-only and free.

```bash
# 1. clone
git clone https://github.com/<your-fork>/flymax-orchestrator.git
cd flymax-orchestrator

# 2. install (Python 3.11+)
pip install -e ".[sim]"

# 3. set your Anthropic key
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# 4. dry-run an example mission (no sim required)
flymax plan --mission examples/two_drone_patrol.json --dry-run

# 5. launch the sim (requires WSL2 Ubuntu 22.04 + ROS 2 Humble + Gazebo Harmonic)
flymax fly --mission examples/two_drone_patrol.json --backend gazebo
```

Full Gazebo + ROS 2 setup walkthrough in [`docs/setup-gazebo.md`](docs/setup-gazebo.md).

## Roadmap

| Phase | Outcome | ETA |
|---|---|---|
| **0** | Repo + skeleton + mission schema (this commit) | done |
| **1** | Sim-only: 1 drone flies a 4-waypoint Claude-generated mission in Gazebo | +30 days |
| **2** | Real Crazyflie 2.1+ flies the same mission via `--backend crazyflie` | +60 days |
| **3** | 2 drones in formation; ESP32-CAM visual trigger; first public demo video | +90 days |
| **4** | PX4 / Pixhawk backend; outdoor flight (India DGCA Digital Sky compliance) | Q4 2026 |
| **5** | Swarm of 5+; foundation-model-conditioned policy (π0 / GR00T-style); cross-fleet handoff | 2027 |

> Strategic context (stack, business model, hardware progression) lives in the private master roadmap — this repo is just Layer 1, the orchestrator.

## Hardware (Phase 2-3)

| Item | Source | Approx | Why |
|---|---|---|---|
| Crazyflie 2.1+ Bundle | MG Super Labs India / Bitcraze | ₹35,000 | Indoor, lightweight, no DGCA permit |
| Crazyradio 2.0 | Same | included | USB radio link |
| Flow Deck v2 | Same | included | Optical-flow + ToF — onboard positioning without an external system |
| Lighthouse Deck (optional, later) | Bitcraze | ₹15,000 | Cm-accurate positioning for tight formations |
| ESP32-CAM | robu.in | ₹500 | Visual trigger / external eye for Phase 3 |
| Lab desk + 1m × 1m × 1m safe-flight cube | (you provide) | — | Indoor envelope for 90% of testing |

Outdoor / GPS missions wait for the PX4 backend (Phase 4) and a DGCA Digital Sky registration.

## Non-goals (intentional)

- We are not building yet another flight controller. PX4 + ArduPilot are excellent.
- We are not building yet another SLAM stack. ETH Zurich + Bitcraze own this lane.
- We are not selling drones. We sell (eventually) the orchestrator and the skills/missions library on top.

## Inspiration / prior art

- [UZH Robotics & Perception Group](https://rpg.ifi.uzh.ch/) — Scaramuzza's group on agile flight and drone racing. Read [Champion-level drone racing using deep RL (Nature 2023)](https://www.nature.com/articles/s41586-023-06419-4).
- [Bitcraze Crazyswarm2](https://imrclab.github.io/crazyswarm2/) — the canonical multi-Crazyflie stack on ROS 2.
- [Skydio / Anduril autonomy](https://www.anduril.com/) — closed but the watermark for what "smart drones" can look like.
- [Hermes War Room (Naroh091)](https://github.com/Naroh091/hermes-war-room) — the visual metaphor for an operator floor watching agentic workers.

## License

MIT. See [LICENSE](LICENSE).

## Status

Pre-alpha. Author: [Sriram Raghavan](mailto:sriram@getmaxrcm.com). This is the early skeleton. Contributions, criticism, and "have you considered…" emails are all welcome.

## A note on the name

FlyMax was a side conversation that people thought was a joke. It's not.
