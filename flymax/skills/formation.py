"""formation — deterministic multi-drone geometry. Pure math, never the LLM.

Given a Formation and a drone count, returns the horizontal (dx, dy) offset of
each drone from the leader, centred on the leader. The backend applies these to
a leg's leader path so a swarm holds shape. Altitude is left to the leg.
"""

from __future__ import annotations

import math

from ..missions import Formation


def formation_offsets(
    formation: Formation | str, n: int, spacing_m: float = 1.0
) -> list[tuple[float, float]]:
    """Per-drone (dx, dy) offsets for n drones in the given formation.

    Drone 0 is the leader at (0, 0). Offsets are in metres in the local frame.
    """
    if n <= 0:
        return []
    f = formation if isinstance(formation, Formation) else Formation(formation)

    if n == 1 or f == Formation.SOLO:
        return [(0.0, 0.0)]

    if f == Formation.LINE:
        start = -(n - 1) / 2 * spacing_m
        return [(round(start + i * spacing_m, 6), 0.0) for i in range(n)]

    if f == Formation.V:
        offs = [(0.0, 0.0)]
        for i in range(1, n):
            arm = (i + 1) // 2
            side = -1.0 if i % 2 else 1.0
            offs.append((round(side * arm * spacing_m, 6), round(-arm * spacing_m, 6)))
        return offs

    if f == Formation.DIAMOND:
        cardinals = [(0.0, 1.0), (1.0, 0.0), (0.0, -1.0), (-1.0, 0.0)]
        offs = [(0.0, 0.0)]
        for i in range(n - 1):
            ring = i // 4 + 1
            bx, by = cardinals[i % 4]
            offs.append((round(bx * ring * spacing_m, 6), round(by * ring * spacing_m, 6)))
        return offs[:n]

    if f == Formation.GRID:
        cols = math.ceil(math.sqrt(n))
        raw = [((i % cols) * spacing_m, -(i // cols) * spacing_m) for i in range(n)]
        cx = sum(p[0] for p in raw) / n
        cy = sum(p[1] for p in raw) / n
        return [(round(x - cx, 6), round(y - cy, 6)) for x, y in raw]

    return [(0.0, 0.0)] * n
