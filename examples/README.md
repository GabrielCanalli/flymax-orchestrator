# Mission templates

Validated, copyable `MissionPlan` JSON — one per use-case. Every file here is
checked in CI: it must parse against the Pydantic schema **and** stay inside its
own `safety` envelope (the `GeofenceSkill` runs over it). Copy one, change the
goal, fly it.

Run any of them with no hardware:

```bash
flymax fly --mission examples/<file>.json --backend dryrun
flymax plan --mission examples/<file>.json   # validate + print the leg table
```

| File | Use case | Drones · formation | Indoor / outdoor | What it flies |
|---|---|---|---|---|
| `two_drone_patrol.json` | smoke test | 2 · line | indoor | 1m square at 1m, the original seed |
| `guardian_perch_watch.json` | personal-guardian (flagship) | 1 · solo | indoor | perch → 6m watch → short sweep → return to perch |
| `recce_v_formation.json` | defence-recce | 3 · V | outdoor | 30×30m box patrol at 25m in V |
| `agri_survey_grid.json` | agriculture | 1 · solo | outdoor | boustrophedon survey of a 40×40m field at 15m |
| `inspection_tower_orbit.json` | inspection (DaaS) | 1 · solo | outdoor | 8m-radius orbit of a structure at 20m |
| 'grid_survey.json' | survey | 1 - solo | outdoor | grid pattern at fixed altitude |

The geometric templates are the same shapes the deterministic skills emit
(`flymax/skills/formation.py`, `survey.py`, `rth.py`) — author by hand or
generate, the schema and the geofence check are the acceptance bar either way.

**Contributing a template:** open a `mission-template` issue, add one
`examples/*.json`, make sure `pytest -q` stays green (the validation test picks
it up automatically). A single JSON file can be your first merge.
