"""Tests for agents.base and agents.greedy (item 6)."""

import pytest

from agents.base import Agent, EpisodeResult, run_episode
from agents.greedy import GreedyAgent
from sim.config import Scenario, StoreConfig, default_scenario
from sim.environment import InventoryRoutingEnv
from sim.scoring import CostBreakdown
from sim.state import Action, Fleet


def make_scenario(
    *,
    horizon=3,
    seed=7,
    spread=0.0,
    num_trucks=1,
    capacity=30,
    store_specs=None,
    depot=(0.0, 0.0),
):
    """store_specs: list of (x, y, initial, mean)."""
    if store_specs is None:
        store_specs = [(10.0, 0.0, 10, 10.0), (0.0, 10.0, 10, 10.0)]
    stores = tuple(
        StoreConfig(
            store_id=i,
            location=(x, y),
            max_capacity=40,
            initial_inventory=initial,
            holding_cost=1.0,
            stockout_penalty=20.0,
            demand_mean=mean,
            demand_spread=spread,
        )
        for i, (x, y, initial, mean) in enumerate(store_specs)
    )
    return Scenario(
        name="greedy",
        stores=stores,
        depot_location=depot,
        fleet=Fleet(num_trucks=num_trucks, capacity=capacity),
        horizon=horizon,
        travel_cost_per_distance=1.0,
        depot_inventory=1000,
        seed=seed,
    )


# --- base ----------------------------------------------------------------


def test_agent_is_abstract():
    with pytest.raises(TypeError):
        Agent()  # cannot instantiate the interface


def test_run_episode_returns_result_with_daily_per_day():
    env = InventoryRoutingEnv(make_scenario(horizon=4, spread=2.0))
    result = run_episode(env, GreedyAgent())
    assert isinstance(result, EpisodeResult)
    assert len(result.daily) == 4


def test_run_episode_total_is_sum_of_daily():
    env = InventoryRoutingEnv(make_scenario(horizon=4, spread=2.0))
    result = run_episode(env, GreedyAgent())
    assert isinstance(result.total, CostBreakdown)
    assert result.total.total == pytest.approx(sum(c.total for c in result.daily))


# --- greedy behavior -----------------------------------------------------


def test_greedy_returns_valid_action_accepted_by_env():
    env = InventoryRoutingEnv(make_scenario(horizon=3, spread=2.0))
    obs = env.reset()
    action = GreedyAgent().act(obs)
    assert isinstance(action, Action)
    # env accepting it (no ValueError) proves capacity/validity are respected
    env.step(action)


def test_greedy_prioritizes_most_at_risk_store():
    # store 0 empty with real demand (cover 0), store 1 nearly full (cover high).
    # One truck, capacity 30 < what both want, so greedy serves store 0 first.
    scenario = make_scenario(
        horizon=1,
        spread=0.0,
        num_trucks=1,
        capacity=30,
        store_specs=[(10.0, 0.0, 0, 10.0), (0.0, 10.0, 35, 10.0)],
    )
    env = InventoryRoutingEnv(scenario)
    obs = env.reset()
    action = GreedyAgent().act(obs)
    delivered = {
        stop.store_id: stop.quantity
        for route in action.routes
        for stop in route.stops
    }
    assert delivered.get(0, 0) == 30  # fills the truck for the at-risk store
    assert delivered.get(1, 0) == 0  # nothing left for the safe store


def test_greedy_does_not_over_deliver_past_capacity():
    # store already at capacity should receive nothing.
    scenario = make_scenario(
        horizon=1,
        spread=0.0,
        num_trucks=1,
        capacity=30,
        store_specs=[(10.0, 0.0, 40, 10.0)],
    )
    env = InventoryRoutingEnv(scenario)
    obs = env.reset()
    action = GreedyAgent().act(obs)
    delivered = sum(stop.quantity for route in action.routes for stop in route.stops)
    assert delivered == 0


def test_greedy_beats_delivering_nothing():
    scenario = default_scenario()
    greedy_total = run_episode(
        InventoryRoutingEnv(scenario), GreedyAgent()
    ).total.total

    nothing_env = InventoryRoutingEnv(scenario)
    nothing_env.reset()
    done = False
    while not done:
        done = nothing_env.step(Action(routes=())).done
    nothing_total = nothing_env.total_cost.total

    assert greedy_total < nothing_total


def test_greedy_is_deterministic_on_same_seed():
    scenario = make_scenario(horizon=5, spread=3.0, seed=99)
    a = run_episode(InventoryRoutingEnv(scenario), GreedyAgent())
    b = run_episode(InventoryRoutingEnv(scenario), GreedyAgent())
    assert a.total.total == pytest.approx(b.total.total)


def test_greedy_uses_multiple_trucks_when_available():
    # Two empty at-risk stores, two trucks; greedy should load both trucks.
    scenario = make_scenario(
        horizon=1,
        spread=0.0,
        num_trucks=2,
        capacity=30,
        store_specs=[(10.0, 0.0, 0, 10.0), (0.0, 10.0, 0, 10.0)],
    )
    env = InventoryRoutingEnv(scenario)
    obs = env.reset()
    action = GreedyAgent().act(obs)
    trucks_used = {route.truck_id for route in action.routes if route.stops}
    assert len(trucks_used) == 2
