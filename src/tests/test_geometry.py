"""Tests for sim.geometry: distances, tour length, travel cost (item 2)."""

import math

import pytest

from sim.config import Scenario, StoreConfig
from sim.geometry import (
    DEPOT,
    DistanceMatrix,
    euclidean,
    tour_length,
    travel_cost,
)
from sim.state import Action, Fleet, Route, Stop


def make_scenario(store_locations, depot=(0.0, 0.0)):
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
    )


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
