"""Tests for agents.routing.build_routes (shared tour construction)."""

from agents.routing import build_routes
from sim.config import Scenario, StoreConfig
from sim.geometry import DistanceMatrix
from sim.state import Fleet


def _distances(store_specs, depot=(0.0, 0.0)):
    """DistanceMatrix for stores at given (x, y); store_id is the list index."""
    stores = tuple(
        StoreConfig(
            store_id=i,
            location=(x, y),
            max_capacity=40,
            initial_inventory=0,
            holding_cost=1.0,
            stockout_penalty=20.0,
            demand_mean=10.0,
            demand_spread=0.0,
        )
        for i, (x, y) in enumerate(store_specs)
    )
    scenario = Scenario(
        name="r",
        stores=stores,
        depot_location=depot,
        fleet=Fleet(num_trucks=1, capacity=1),
        horizon=1,
        travel_cost_per_distance=1.0,
        depot_inventory=1000,
        seed=1,
    )
    return DistanceMatrix.from_scenario(scenario)


def test_build_routes_visits_nearest_first():
    # depot (0,0); nearest is store1 (dist 1), then store2, then store0.
    distances = _distances([(0.0, 3.0), (0.0, 1.0), (0.0, 2.0)])
    routes = build_routes(
        {0: 10, 1: 10, 2: 10}, Fleet(num_trucks=1, capacity=200), distances
    )
    assert len(routes) == 1
    assert tuple(s.store_id for s in routes[0].stops) == (1, 2, 0)
    assert tuple(s.quantity for s in routes[0].stops) == (10, 10, 10)


def test_build_routes_splits_store_across_trucks():
    # One store wants 60; two trucks of capacity 50 -> 50 then 10.
    distances = _distances([(0.0, 1.0)])
    routes = build_routes(
        {0: 60}, Fleet(num_trucks=2, capacity=50), distances
    )
    delivered = sum(s.quantity for r in routes for s in r.stops)
    assert delivered == 60
    assert all(sum(s.quantity for s in r.stops) <= 50 for r in routes)


def test_build_routes_ignores_zero_and_negative_want():
    distances = _distances([(0.0, 1.0), (0.0, 2.0)])
    routes = build_routes(
        {0: 0, 1: 5}, Fleet(num_trucks=1, capacity=50), distances
    )
    delivered = {s.store_id: s.quantity for r in routes for s in r.stops}
    assert delivered == {1: 5}


def test_build_routes_does_not_mutate_want():
    distances = _distances([(0.0, 1.0)])
    want = {0: 10}
    build_routes(want, Fleet(num_trucks=1, capacity=50), distances)
    assert want == {0: 10}
