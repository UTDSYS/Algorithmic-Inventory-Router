"""Tests for sim.geometry: distances, tour length, travel cost (item 2)."""

import math

import pytest

from sim.config import RoadSpec, Scenario, StoreConfig
from sim.geometry import (
    DEPOT,
    DistanceMatrix,
    euclidean,
    route_path,
    tour_length,
    travel_cost,
)
from sim.state import Action, Fleet, Route, Stop


def make_scenario(store_locations, depot=(0.0, 0.0), road_spec=None):
    stores = tuple(
        StoreConfig(
            store_id=i,
            location=loc,
            max_capacity=40,
            initial_inventory=10,
            holding_cost=1.0,
            stockout_penalty=20.0,
            demand_mean=10.0,
            demand_spread=3.0,
        )
        for i, loc in enumerate(store_locations)
    )
    return Scenario(
        name="geo",
        stores=stores,
        depot_location=depot,
        fleet=Fleet(num_trucks=2, capacity=50),
        horizon=12,
        travel_cost_per_distance=1.0,
        depot_inventory=500,
        seed=1,
        road_spec=road_spec,
    )


ROAD_SPEC = RoadSpec(arterials=(25.0, 50.0, 75.0), bounds=(0.0, 100.0))


def test_euclidean_basic():
    assert euclidean((0.0, 0.0), (3.0, 4.0)) == 5.0


def test_euclidean_zero_for_same_point():
    assert euclidean((2.0, 7.0), (2.0, 7.0)) == 0.0


def test_distance_matrix_depot_to_store():
    scenario = make_scenario([(3.0, 4.0)], depot=(0.0, 0.0))
    matrix = DistanceMatrix.from_scenario(scenario)
    assert matrix.distance(DEPOT, 0) == 5.0


def test_distance_matrix_store_to_store():
    scenario = make_scenario([(0.0, 0.0), (0.0, 10.0)])
    matrix = DistanceMatrix.from_scenario(scenario)
    assert matrix.distance(0, 1) == 10.0


def test_distance_matrix_is_symmetric():
    scenario = make_scenario([(1.0, 2.0), (4.0, 6.0)])
    matrix = DistanceMatrix.from_scenario(scenario)
    assert matrix.distance(0, 1) == matrix.distance(1, 0)
    assert matrix.distance(DEPOT, 1) == matrix.distance(1, DEPOT)


def test_distance_matrix_self_is_zero():
    scenario = make_scenario([(5.0, 5.0)])
    matrix = DistanceMatrix.from_scenario(scenario)
    assert matrix.distance(0, 0) == 0.0
    assert matrix.distance(DEPOT, DEPOT) == 0.0


def test_tour_length_empty_is_zero():
    scenario = make_scenario([(3.0, 4.0)])
    matrix = DistanceMatrix.from_scenario(scenario)
    assert tour_length(matrix, []) == 0.0


def test_tour_length_single_store_is_round_trip():
    scenario = make_scenario([(3.0, 4.0)], depot=(0.0, 0.0))
    matrix = DistanceMatrix.from_scenario(scenario)
    assert tour_length(matrix, [0]) == 10.0  # depot->store->depot = 5 + 5


def test_tour_length_multi_store():
    # depot (0,0) -> s0 (0,3) -> s1 (4,3) -> depot
    scenario = make_scenario([(0.0, 3.0), (4.0, 3.0)], depot=(0.0, 0.0))
    matrix = DistanceMatrix.from_scenario(scenario)
    expected = 3.0 + 4.0 + math.hypot(4.0, 3.0)  # 3 + 4 + 5
    assert tour_length(matrix, [0, 1]) == pytest.approx(expected)


def test_travel_cost_sums_routes_and_scales():
    scenario = make_scenario([(3.0, 4.0), (6.0, 8.0)], depot=(0.0, 0.0))
    matrix = DistanceMatrix.from_scenario(scenario)
    action = Action(
        routes=(
            Route(truck_id=0, stops=(Stop(0, 5),)),  # 5 + 5 = 10
            Route(truck_id=1, stops=(Stop(1, 5),)),  # 10 + 10 = 20
        )
    )
    assert travel_cost(matrix, action, cost_per_distance=1.0) == pytest.approx(30.0)
    assert travel_cost(matrix, action, cost_per_distance=2.0) == pytest.approx(60.0)


def test_travel_cost_empty_action_is_zero():
    scenario = make_scenario([(3.0, 4.0)])
    matrix = DistanceMatrix.from_scenario(scenario)
    assert travel_cost(matrix, Action(routes=()), cost_per_distance=1.0) == 0.0


# --- road-network distances (item 10) ------------------------------------


def test_from_scenario_uses_road_distance_when_road_spec_present():
    # depot (10,40) attaches to y=50 at (10,50); store (90,60) attaches at
    # (90,50). Road path: 10 (driveway) + 80 (along y=50) + 10 (driveway) = 100,
    # well above the straight-line distance of ~82.46.
    scenario = make_scenario([(90.0, 60.0)], depot=(10.0, 40.0), road_spec=ROAD_SPEC)
    matrix = DistanceMatrix.from_scenario(scenario)
    assert matrix.distance(DEPOT, 0) == pytest.approx(100.0)
    assert matrix.distance(DEPOT, 0) > euclidean((10.0, 40.0), (90.0, 60.0))


def test_road_distance_is_symmetric():
    scenario = make_scenario([(90.0, 60.0)], depot=(10.0, 40.0), road_spec=ROAD_SPEC)
    matrix = DistanceMatrix.from_scenario(scenario)
    assert matrix.distance(DEPOT, 0) == pytest.approx(matrix.distance(0, DEPOT))


def test_path_follows_roads_between_two_points():
    scenario = make_scenario([(90.0, 60.0)], depot=(10.0, 40.0), road_spec=ROAD_SPEC)
    matrix = DistanceMatrix.from_scenario(scenario)
    path = matrix.path(DEPOT, 0)
    assert path[0] == (10.0, 40.0)
    assert path[-1] == (90.0, 60.0)
    # every hop is axis-aligned (a straight road leg or a perpendicular driveway)
    for a, b in zip(path, path[1:]):
        assert a[0] == b[0] or a[1] == b[1]


def test_path_is_straight_line_without_road_spec():
    scenario = make_scenario([(3.0, 4.0)], depot=(0.0, 0.0))
    matrix = DistanceMatrix.from_scenario(scenario)
    assert matrix.path(DEPOT, 0) == [(0.0, 0.0), (3.0, 4.0)]


def test_route_path_concatenates_legs_into_a_closed_tour():
    scenario = make_scenario([(90.0, 60.0)], depot=(10.0, 40.0), road_spec=ROAD_SPEC)
    matrix = DistanceMatrix.from_scenario(scenario)
    path = route_path(matrix, [0])
    # a closed tour starts and ends at the depot
    assert path[0] == (10.0, 40.0)
    assert path[-1] == (10.0, 40.0)
    # the store is visited somewhere along the way
    assert (90.0, 60.0) in path
    # no duplicated coordinate where consecutive legs meet
    for a, b in zip(path, path[1:]):
        assert a != b


def test_route_path_empty_route_is_empty():
    scenario = make_scenario([(90.0, 60.0)], depot=(10.0, 40.0), road_spec=ROAD_SPEC)
    matrix = DistanceMatrix.from_scenario(scenario)
    assert route_path(matrix, []) == []


def test_matrix_exposes_road_geometry_for_drawing():
    scenario = make_scenario([(90.0, 60.0)], depot=(10.0, 40.0), road_spec=ROAD_SPEC)
    matrix = DistanceMatrix.from_scenario(scenario)
    assert len(matrix.road_segments()) == 6  # three arterials on each axis
    assert set(matrix.intersections()) == {
        (x, y) for x in (25.0, 50.0, 75.0) for y in (25.0, 50.0, 75.0)
    }


def test_matrix_road_geometry_empty_without_road_spec():
    scenario = make_scenario([(3.0, 4.0)])
    matrix = DistanceMatrix.from_scenario(scenario)
    assert matrix.road_segments() == []
    assert matrix.intersections() == []


def test_matrix_exposes_driveways_from_each_point_to_its_connector():
    scenario = make_scenario([(90.0, 60.0)], depot=(10.0, 40.0), road_spec=ROAD_SPEC)
    matrix = DistanceMatrix.from_scenario(scenario)
    # depot first, then each store: (point, connector-on-the-road)
    assert matrix.driveways() == [
        ((10.0, 40.0), (10.0, 50.0)),
        ((90.0, 60.0), (90.0, 50.0)),
    ]


def test_matrix_omits_zero_length_driveway_for_point_on_a_road():
    # store (50, 60) sits exactly on the x=50 arterial: no driveway to draw.
    scenario = make_scenario([(50.0, 60.0)], depot=(10.0, 40.0), road_spec=ROAD_SPEC)
    matrix = DistanceMatrix.from_scenario(scenario)
    points = [point for point, _ in matrix.driveways()]
    assert (50.0, 60.0) not in points
    assert (10.0, 40.0) in points  # the depot still has one


def test_matrix_driveways_empty_without_road_spec():
    scenario = make_scenario([(3.0, 4.0)])
    matrix = DistanceMatrix.from_scenario(scenario)
    assert matrix.driveways() == []
