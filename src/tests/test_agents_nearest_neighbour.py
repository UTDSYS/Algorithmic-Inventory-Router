"""Tests for agents.nearest_neighbour (item 7)."""

import pytest

from agents.base import run_episode
from agents.greedy import GreedyAgent
from agents.nearest_neighbour import NearestNeighbourAgent
from sim.config import Scenario, StoreConfig, default_scenario
from sim.environment import InventoryRoutingEnv
from sim.state import Action, Fleet


def make_scenario(
    *,
    horizon=3,
    seed=7,
    spread=0.0,
    num_trucks=1,
    capacity=200,
    store_specs=None,
    depot=(0.0, 0.0),
):
    """store_specs: list of (x, y, initial)."""
    if store_specs is None:
        store_specs = [(0.0, 3.0, 0), (0.0, 1.0, 0), (0.0, 2.0, 0)]
    stores = tuple(
        StoreConfig(
            store_id=i,
            location=(x, y),
            max_capacity=40,
            initial_inventory=initial,
            holding_cost=1.0,
            stockout_penalty=20.0,
            demand_mean=10.0,
            demand_spread=spread,
        )
        for i, (x, y, initial) in enumerate(store_specs)
    )
    return Scenario(
        name="nn",
        stores=stores,
        depot_location=depot,
        fleet=Fleet(num_trucks=num_trucks, capacity=capacity),
        horizon=horizon,
        travel_cost_per_distance=1.0,
        depot_inventory=1000,
        seed=seed,
    )


def test_nn_returns_valid_action_accepted_by_env():
    env = InventoryRoutingEnv(make_scenario(horizon=3, spread=2.0))
    obs = env.reset()
    action = NearestNeighbourAgent().act(obs)
    assert isinstance(action, Action)
    env.step(action)


def test_nn_builds_tour_in_nearest_first_order():
    # depot (0,0); nearest is store1 (dist 1), then store2 (dist 1 from store1),
    # then store0. Store index order (0,1,2) differs from distance order.
    scenario = make_scenario(
        horizon=1,
        spread=0.0,
        num_trucks=1,
        capacity=200,
        store_specs=[(0.0, 3.0, 0), (0.0, 1.0, 0), (0.0, 2.0, 0)],
    )
    env = InventoryRoutingEnv(scenario)
    obs = env.reset()
    action = NearestNeighbourAgent().act(obs)
    assert len(action.routes) == 1
    visited = tuple(stop.store_id for stop in action.routes[0].stops)
    assert visited == (1, 2, 0)


def test_nn_only_services_stores_below_threshold():
    # store 0 low (needs service), store 1 well-stocked (above 50% threshold).
    scenario = make_scenario(
        horizon=1,
        spread=0.0,
        num_trucks=1,
        capacity=50,
        store_specs=[(0.0, 1.0, 5), (0.0, 2.0, 30)],
    )
    env = InventoryRoutingEnv(scenario)
    obs = env.reset()
    action = NearestNeighbourAgent(reorder_ratio=0.5).act(obs)
    delivered = {
        stop.store_id: stop.quantity
        for route in action.routes
        for stop in route.stops
    }
    assert delivered.get(0, 0) == 35  # filled toward capacity 40
    assert delivered.get(1, 0) == 0  # above threshold, not serviced


def test_nn_delivers_nothing_when_all_well_stocked():
    scenario = make_scenario(
        horizon=1,
        spread=0.0,
        num_trucks=1,
        store_specs=[(0.0, 1.0, 40), (0.0, 2.0, 38)],
    )
    env = InventoryRoutingEnv(scenario)
    obs = env.reset()
    action = NearestNeighbourAgent(reorder_ratio=0.5).act(obs)
    delivered = sum(stop.quantity for route in action.routes for stop in route.stops)
    assert delivered == 0


def test_nn_beats_delivering_nothing():
    scenario = default_scenario()
    nn_total = run_episode(
        InventoryRoutingEnv(scenario), NearestNeighbourAgent()
    ).total.total

    nothing_env = InventoryRoutingEnv(scenario)
    nothing_env.reset()
    done = False
    while not done:
        done = nothing_env.step(Action(routes=())).done
    assert nn_total < nothing_env.total_cost.total


def test_nn_is_deterministic():
    scenario = make_scenario(horizon=5, spread=3.0, seed=99, num_trucks=2)
    a = run_episode(InventoryRoutingEnv(scenario), NearestNeighbourAgent())
    b = run_episode(InventoryRoutingEnv(scenario), NearestNeighbourAgent())
    assert a.total.total == pytest.approx(b.total.total)


def test_greedy_and_nn_give_sensible_differing_totals():
    scenario = default_scenario()
    greedy = run_episode(InventoryRoutingEnv(scenario), GreedyAgent()).total
    nn = run_episode(InventoryRoutingEnv(scenario), NearestNeighbourAgent()).total
    assert greedy.total > 0
    assert nn.total > 0
    # they optimize different things, so totals should differ
    assert greedy.total != pytest.approx(nn.total)
    # nearest-neighbour optimizes travel, so its travel should not exceed greedy's
    assert nn.travel <= greedy.travel
