"""Deterministic geometry skills — formation offsets, lawnmower survey, RTH."""

from __future__ import annotations

import pytest

from flymax.missions import Formation, Vec3
from flymax.skills import formation_offsets, lawnmower, rth_waypoints

ALL_FORMATIONS = [
    Formation.SOLO,
    Formation.LINE,
    Formation.V,
    Formation.DIAMOND,
    Formation.GRID,
]


@pytest.mark.parametrize("f", [Formation.LINE, Formation.V, Formation.DIAMOND, Formation.GRID])
@pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
def test_formation_returns_one_offset_per_drone(f: Formation, n: int) -> None:
    offs = formation_offsets(f, n, spacing_m=1.5)
    assert len(offs) == n


def test_solo_is_always_a_single_offset() -> None:
    # SOLO means one drone — it collapses any count to a single leader offset.
    for n in [1, 3, 5]:
        assert formation_offsets(Formation.SOLO, n) == [(0.0, 0.0)]


def test_formation_empty_for_zero_drones() -> None:
    assert formation_offsets(Formation.GRID, 0) == []


@pytest.mark.parametrize("f", [Formation.SOLO, Formation.V, Formation.DIAMOND])
def test_apex_formations_have_leader_at_origin(f: Formation) -> None:
    assert formation_offsets(f, 3, spacing_m=1.0)[0] == (0.0, 0.0)


def test_line_is_symmetric_and_spaced() -> None:
    offs = formation_offsets(Formation.LINE, 4, spacing_m=2.0)
    xs = [o[0] for o in offs]
    assert abs(sum(xs)) < 1e-6  # centred on the leader
    assert round(xs[1] - xs[0], 6) == 2.0
    assert all(o[1] == 0.0 for o in offs)


def test_grid_is_centred() -> None:
    offs = formation_offsets(Formation.GRID, 9, spacing_m=1.0)
    assert abs(sum(o[0] for o in offs)) < 1e-6
    assert abs(sum(o[1] for o in offs)) < 1e-6


def test_lawnmower_covers_box_and_stays_inside() -> None:
    wps = lawnmower(0, 0, 40, 40, spacing_m=10, altitude_m=15)
    assert len(wps) >= 2 and len(wps) % 2 == 0
    xs = [w.position.x for w in wps]
    ys = [w.position.y for w in wps]
    assert min(xs) == 0 and max(xs) == 40
    assert min(ys) == 0 and max(ys) == 40
    assert all(w.position.z == 15 for w in wps)


def test_lawnmower_always_covers_far_edge() -> None:
    wps = lawnmower(0, 0, 10, 25, spacing_m=10, altitude_m=5)  # 25 is not a multiple of 10
    assert max(w.position.y for w in wps) == 25


def test_lawnmower_rejects_nonpositive_spacing() -> None:
    with pytest.raises(ValueError):
        lawnmower(0, 0, 10, 10, spacing_m=0, altitude_m=5)


def test_rth_is_climb_transit_descend() -> None:
    wps = rth_waypoints(Vec3(x=10, y=10, z=2), Vec3(x=0, y=0, z=0), cruise_alt_m=8, land_z=0.3)
    assert len(wps) == 3
    # climb in place
    assert (wps[0].position.x, wps[0].position.y, wps[0].position.z) == (10, 10, 8)
    # transit home at altitude
    assert (wps[1].position.x, wps[1].position.y, wps[1].position.z) == (0, 0, 8)
    # descend at home
    assert (wps[2].position.x, wps[2].position.y, wps[2].position.z) == (0, 0, 0.3)
