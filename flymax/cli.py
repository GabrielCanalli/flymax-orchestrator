"""Command-line entry point.

    flymax plan --goal "fly a 1m square" --out plan.json
    flymax plan --mission examples/two_drone_patrol.json --dry-run
    flymax fly  --mission examples/two_drone_patrol.json --backend dryrun
    flymax fly  --mission examples/two_drone_patrol.json --backend gazebo  # Phase 1
    flymax fly  --mission examples/two_drone_patrol.json --backend crazyflie  # Phase 2
"""

from __future__ import annotations
import asyncio
import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .missions import Mission
from .missions.schema import export_json_schema
from .orchestrator import Orchestrator, load_mission

# Windows consoles default to cp1252; rich emits unicode glyphs (✓, table borders).
# Force UTF-8 so output doesn't crash with UnicodeEncodeError.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

console = Console()


@click.group()
@click.version_option()
def main() -> None:
    """FlyMax — Claude-powered drone swarm orchestrator."""


@main.command()
@click.option("--goal", help="Natural-language mission goal.")
@click.option("--mission", "mission_path", type=click.Path(exists=True, path_type=Path),
              help="Pre-authored Mission JSON to validate.")
@click.option("--out", "out_path", type=click.Path(path_type=Path),
              help="Write the planned Mission JSON to this path.")
@click.option("--dry-run", is_flag=True, help="Print the plan, do not save.")
def plan(goal: str | None, mission_path: Path | None, out_path: Path | None, dry_run: bool) -> None:
    """Decompose a goal into a typed Mission. Or validate an existing Mission JSON."""
    if mission_path:
        m = load_mission(mission_path)
        console.print(f"[green]✓[/green] Loaded {m.name} ({len(m.fleet)} drones, {len(m.legs)} legs)")
        _print_mission(m)
        return
    if not goal:
        console.print("[red]error[/red] Provide --goal or --mission")
        sys.exit(1)
    orch = Orchestrator()
    m = orch.plan(goal)
    _print_mission(m)
    if dry_run or not out_path:
        return
    out_path.write_text(m.model_dump_json(indent=2), encoding="utf-8")
    console.print(f"[green]✓[/green] Wrote {out_path}")


@main.command()
@click.option("--mission", "mission_path", required=True,
              type=click.Path(exists=True, path_type=Path),
              help="Mission JSON to fly.")
@click.option("--backend", default="dryrun",
              type=click.Choice(["dryrun", "gazebo", "crazyflie"]),
              help="Where to fly: dryrun (no hw), gazebo (sim), crazyflie (real).")
def fly(mission_path: Path, backend: str) -> None:
    """Dispatch a Mission to a backend. Streams telemetry to stdout."""
    m = load_mission(mission_path)
    orch = Orchestrator()

    async def _run() -> None:
        async for ev in orch.fly(m, backend):
            console.print(
                f"[dim]{ev.timestamp:.1f}[/dim] "
                f"[cyan]{ev.drone_id}[/cyan] "
                f"[magenta]{ev.state}[/magenta] "
                f"({ev.position.x:.2f}, {ev.position.y:.2f}, {ev.position.z:.2f}) "
                f"[yellow]{ev.battery_pct:.0f}%[/yellow] "
                f"{ev.message or ''}"
            )

    asyncio.run(_run())


@main.command()
@click.option("--out", "out_path", type=click.Path(path_type=Path),
              help="Write the canonical Mission JSON Schema here (e.g. schema/mission.schema.json).")
def schema(out_path: Path | None) -> None:
    """Emit the canonical Mission JSON Schema — the single structural contract.

    Downstream consumers (the website's TypeScript types, the planner's Anthropic
    tool) regenerate from this one file so they can never silently drift.
    """
    doc = json.dumps(export_json_schema(), indent=2)
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(doc + "\n", encoding="utf-8")
        console.print(f"[green]✓[/green] Wrote {out_path}")
    else:
        console.print_json(doc)


def _print_mission(m: Mission) -> None:
    t = Table(title=f"Mission: {m.name}")
    t.add_column("Leg")
    t.add_column("Drones")
    t.add_column("Waypoints")
    t.add_column("Formation")
    t.add_column("On failure")
    for i, leg in enumerate(m.legs):
        t.add_row(
            str(i),
            ",".join(leg.drone_ids),
            str(len(leg.waypoints)),
            leg.formation.value,
            leg.on_failure,
        )
    console.print(t)
    if m.metadata.get("refusal_reason"):
        console.print(f"[red]Planner refused:[/red] {m.metadata['refusal_reason']}")


if __name__ == "__main__":
    main()
