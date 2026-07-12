"""Tests for agents.rolling_horizon (item 11)."""

import pytest

from agents.base import run_episode
from agents.rolling_horizon import RollingHorizonAgent, plan_deliveries
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
        store_specs = [(0.0, 1.0, 0), (0.0, 2.0, 0)]
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
        name="rh",
        stores=stores,
        depot_location=depot,
        fleet=Fleet(num_trucks=num_trucks, capacity=capacity),
        horizon=horizon,
        travel_cost_per_distance=1.0,
        depot_inventory=1000,
        seed=seed,
    )


# ---- plan_deliveries (the MILP) --------------------------------------------


def test_plan_delivers_just_in_time_not_fill_to_capacity():
    # One store, inv 0, demand 10/day for 3 days, ample fleet. The horizon plan
    # covers only the next day's need (holding-minimal), not a full 40.
    q = plan_deliveries(
        inventory=[0],
        forecasts=[[10.0, 10.0, 10.0]],
        max_capacity=[40],
        holding=[1.0],
        stockout=[20.0],
        fleet_capacity_per_day=100,
        horizon=3,
    )
    assert q == [10]


def test_plan_prestocks_when_fleet_cannot_cover_future_spike():
    # Spike of 30 on day 1, only 20 of fleet capacity per day: the plan must
    # deliver 10 today so tomorrow's (otherwise unavoidable) stockout is averted.
    tight = plan_deliveries(
        inventory=[0],
        forecasts=[[0.0, 30.0]],
        max_capacity=[40],
        holding=[1.0],
        stockout=[20.0],
        fleet_capacity_per_day=20,
        horizon=2,
    )
    assert tight == [10]
    # With ample fleet the same spike is covered just-in-time -> nothing today.
    ample = plan_deliveries(
        inventory=[0],
        forecasts=[[0.0, 30.0]],
        max_capacity=[40],
        holding=[1.0],
        stockout=[20.0],
        fleet_capacity_per_day=30,
        horizon=2,
    )
    assert ample == [0]


def test_plan_respects_fleet_capacity_today():
    q = plan_deliveries(
        inventory=[0, 0],
        forecasts=[[20.0], [20.0]],
        max_capacity=[40, 40],
        holding=[1.0, 1.0],
        stockout=[20.0, 20.0],
        fleet_capacity_per_day=25,
        horizon=1,
    )
    assert sum(q) <= 25
    assert all(isinstance(v, int) for v in q)


def test_plan_never_exceeds_store_capacity():
    q = plan_deliveries(
        inventory=[35],
        forecasts=[[20.0]],
        max_capacity=[40],
        holding=[1.0],
        stockout=[20.0],
        fleet_capacity_per_day=100,
        horizon=1,
    )
    assert q[0] <= 5  # can only top up to capacity 40 from inventory 35


def test_plan_empty_horizon_delivers_nothing():
    assert plan_deliveries(
        inventory=[5],
        forecasts=[[]],
        max_capacity=[40],
        holding=[1.0],
        stockout=[20.0],
        fleet_capacity_per_day=100,
        horizon=3,
    ) == [0]


# ---- RollingHorizonAgent (integration with the env) ------------------------


def test_agent_returns_valid_action_accepted_by_env():
    env = InventoryRoutingEnv(make_scenario(horizon=3, spread=2.0))
    obs = env.reset()
    action = RollingHorizonAgent().act(obs)
    assert isinstance(action, Action)
    env.step(action)  # env validates capacity/store ids; must not raise


def test_agent_is_deterministic():
    scenario = default_scenario()
    a = run_episode(InventoryRoutingEnv(scenario), RollingHorizonAgent())
    b = run_episode(InventoryRoutingEnv(scenario), RollingHorizonAgent())
    assert a.total.total == pytest.approx(b.total.total)


def test_agent_beats_delivering_nothing():
    scenario = default_scenario()
    rh_total = run_episode(
        InventoryRoutingEnv(scenario), RollingHorizonAgent()
    ).total.total

    nothing = InventoryRoutingEnv(scenario)
    nothing.reset()
    done = False
    while not done:
        done = nothing.step(Action(routes=())).done
    assert rh_total < nothing.total_cost.total


def test_agent_delivers_nothing_when_all_full():
    # Every store already at capacity -> the plan cannot deliver (cap binds).
    scenario = make_scenario(
        horizon=1, spread=0.0, store_specs=[(0.0, 1.0, 40), (0.0, 2.0, 40)]
    )
    env = InventoryRoutingEnv(scenario)
    obs = env.reset()
    action = RollingHorizonAgent().act(obs)
    delivered = sum(s.quantity for r in action.routes for s in r.stops)
    assert delivered == 0


def test_agent_action_respects_fleet_capacity():
    scenario = default_scenario()
    env = InventoryRoutingEnv(scenario)
    obs = env.reset()
    action = RollingHorizonAgent().act(obs)
    per_truck = [sum(s.quantity for s in r.stops) for r in action.routes]
    assert all(load <= scenario.fleet.capacity for load in per_truck)
