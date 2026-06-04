"""survey — boustrophedon (lawnmower) coverage of a rectangle. Pure geometry.

Turns a bounding box + row spacing into a back-and-forth sweep at a fixed
altitude — the shape an agri-survey or inspection pass flies. Deterministic, no
LLM, so coverage is provable in a test.
"""

from __future__ import annotations

from ..missions import Vec3, Waypoint


def lawnmower(
    xmin: float,
    ymin: float,
    xmax: float,
    ymax: float,
    spacing_m: float,
    altitude_m: float,
    speed_mps: float | None = None,
) -> list[Waypoint]:
    """Boustrophedon waypoints covering [xmin,xmax] x [ymin,ymax] at altitude_m.

    Rows run along x, stepping in y by spacing_m, alternating direction so the
    path is continuous. The final row is clamped to ymax so the top edge is
    always covered even when the span is not a whole multiple of spacing_m.
    """
    if spacing_m <= 0:
        raise ValueError("spacing_m must be > 0")
    if xmax < xmin or ymax < ymin:
        raise ValueError("max must be >= min on both axes")

    ys: list[float] = []
    y = ymin
    while y < ymax:
        ys.append(round(y, 3))
        y += spacing_m
    ys.append(round(ymax, 3))  # always finish on the far edge

    wps: list[Waypoint] = []
    for row, yy in enumerate(ys):
        xs = [xmin, xmax] if row % 2 == 0 else [xmax, xmin]
        for xx in xs:
            wps.append(
                Waypoint(position=Vec3(x=round(xx, 3), y=yy, z=altitude_m), speed_mps=speed_mps)
            )
    return wps
