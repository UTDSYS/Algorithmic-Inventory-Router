"""Tests for sim.roads: the arterial road graph and pathfinding (item 10).

The grid under test has arterials at 25/50/75 on both axes over bounds 0..100:
vertical roads x=25,50,75 and horizontal roads y=25,50,75, each spanning the
full map. That gives 9 intersections and predictable, hand-checkable distances.
"""

import math

import pytest

from sim.config import RoadSpec
from sim.roads import RoadNetwork


def grid() -> RoadNetwork:
    return RoadNetwork(RoadSpec(arterials=(25.0, 50.0, 75.0), bounds=(0.0, 100.0)))


# --- static geometry -----------------------------------------------------


def test_intersections_are_the_arterial_crossings():
    net = grid()
    expected = {(x, y) for x in (25.0, 50.0, 75.0) for y in (25.0, 50.0, 75.0)}
    assert set(net.intersections()) == expected


def test_segments_are_the_six_full_arterials():
    net = grid()
    segments = {frozenset(seg) for seg in net.segments()}
    # three vertical roads span y 0..100, three horizontal span x 0..100
    verticals = {frozenset({(x, 0.0), (x, 100.0)}) for x in (25.0, 50.0, 75.0)}
    horizontals = {frozenset({(0.0, y), (100.0, y)}) for y in (25.0, 50.0, 75.0)}
    assert segments == verticals | horizontals


# --- shortest path on the bare grid --------------------------------------


def test_shortest_path_straight_along_one_arterial():
    net = grid()
    dist, path = net.shortest_path((25.0, 0.0), (25.0, 100.0))
    assert dist == pytest.approx(100.0)
    assert path[0] == (25.0, 0.0)
    assert path[-1] == (25.0, 100.0)
    # every step stays on x=25 and moves monotonically up
    assert all(x == 25.0 for x, _ in path)
    ys = [y for _, y in path]
    assert ys == sorted(ys)


def test_shortest_path_turns_at_an_intersection():
    net = grid()
    dist, path = net.shortest_path((25.0, 25.0), (50.0, 50.0))
    assert dist == pytest.approx(50.0)  # 25 across + 25 up, one turn
    assert path[0] == (25.0, 25.0)
    assert path[-1] == (50.0, 50.0)


def test_shortest_path_is_symmetric():
    net = grid()
    fwd, _ = net.shortest_path((25.0, 25.0), (75.0, 75.0))
    rev, _ = net.shortest_path((75.0, 75.0), (25.0, 25.0))
    assert fwd == pytest.approx(rev)


def test_shortest_path_coords_are_contiguous():
    net = grid()
    _, path = net.shortest_path((25.0, 0.0), (75.0, 50.0))
    # consecutive coords are joined by an actual road hop (axis-aligned here)
    for a, b in zip(path, path[1:]):
        assert a[0] == b[0] or a[1] == b[1]


# --- attach: projecting stores/depot onto the nearest road ---------------


def test_attach_projects_to_nearest_segment():
    net = grid()
    # (10, 40): nearest road is horizontal y=50 (perpendicular distance 10),
    # closer than x=25 (distance 15) or y=25 (distance 15).
    connector = net.attach((10.0, 40.0))
    assert connector == (10.0, 50.0)
    dist, path = net.shortest_path((10.0, 40.0), (10.0, 50.0))
    assert dist == pytest.approx(10.0)  # the driveway length
    assert path == [(10.0, 40.0), (10.0, 50.0)]


def test_attach_at_intersection_reuses_the_node():
    net = grid()
    connector = net.attach((25.0, 25.0))
    assert connector == (25.0, 25.0)
    # the point sits on an intersection: no zero-length split breaks routing
    dist, _ = net.shortest_path((25.0, 25.0), (50.0, 25.0))
    assert dist == pytest.approx(25.0)


def test_attach_clamps_to_an_arterial_endpoint():
    net = grid()
    # (20, 0) projects onto the x=25 road at its (25, 0) edge endpoint.
    connector = net.attach((20.0, 0.0))
    assert connector == (25.0, 0.0)


def test_attach_two_points_routes_between_them():
    net = grid()
    net.attach((10.0, 40.0))  # -> connector (10, 50) on y=50
    net.attach((90.0, 60.0))  # -> connector (90, 50) on y=50
    dist, path = net.shortest_path((10.0, 40.0), (90.0, 60.0))
    # 10 (driveway) + 80 (along y=50 from x=10 to x=90) + 10 (driveway)
    assert dist == pytest.approx(100.0)
    assert path[0] == (10.0, 40.0)
    assert path[-1] == (90.0, 60.0)


def test_attach_perpendicular_distance_matches_geometry():
    net = grid()
    # (60, 44): nearest road is y=50 (distance 6), closer than x=50 (distance 10).
    connector = net.attach((60.0, 44.0))
    assert connector == (60.0, 50.0)
    dist, _ = net.shortest_path((60.0, 44.0), (60.0, 50.0))
    assert dist == pytest.approx(6.0)


def test_shortest_path_raises_for_unattached_point():
    net = grid()
    with pytest.raises(KeyError):
        net.shortest_path((3.3, 7.7), (25.0, 25.0))
