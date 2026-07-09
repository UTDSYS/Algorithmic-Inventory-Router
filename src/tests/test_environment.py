"""Tests for sim.environment: the reset/step day loop and cost math (item 5)."""

import math

import pytest

from sim.config import Scenario, StoreConfig, default_scenario
from sim.environment import InventoryRoutingEnv, Observation, StepResult
from sim.scoring import CostBreakdown
from sim.state import Action, Fleet, Route, Stop


def make_scenario(
    *,
    horizon=3,
    seed=7,
    spread=0.0,
    num_trucks=1,
    capacity=50,
    store_specs=None,
    depot=(0.0, 0.0),
):
    """store_specs: list of (x, y, initial). Costs/capacity are uniform."""
    if store_specs is None:
        store_specs = [(3.0, 4.0, 10), (6.0, 8.0, 10)]
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
        name="env",
        stores=stores,
        depot_location=depot,
        fleet=Fleet(num_trucks=num_trucks, capacity=capacity),
        horizon=horizon,
        travel_cost_per_distance=1.0,
        depot_inventory=1000,
        seed=seed,
    )


def deliver_nothing():
    return Action(routes=())


# --- reset ---------------------------------------------------------------


def test_reset_returns_observation_at_day_zero():
    env = InventoryRoutingEnv(make_scenario())
    obs = env.reset()
    assert isinstance(obs, Observation)
    assert obs.state.day == 0
    assert tuple(s.inventory for s in obs.state.stores) == (10, 10)


def test_reset_populates_forecasts():
    env = InventoryRoutingEnv(make_scenario(horizon=5), forecast_horizon=3)
    obs = env.reset()
    assert len(obs.state.forecasts) == 2  # one row per store
    assert all(len(row) == 3 for row in obs.state.forecasts)


# --- day loop ------------------------------------------------------------


def test_deliver_nothing_full_episode_completes():
    env = InventoryRoutingEnv(make_scenario(horizon=3))
    env.reset()
    result = None
    for _ in range(3):
        result = env.step(deliver_nothing())
    assert result.done is True
    assert result.observation.state.day == 3


def test_not_done_before_last_day():
    env = InventoryRoutingEnv(make_scenario(horizon=3))
    env.reset()
    first = env.step(deliver_nothing())
    assert first.done is False


def test_step_after_done_raises():
    env = InventoryRoutingEnv(make_scenario(horizon=2))
    env.reset()
    env.step(deliver_nothing())
    env.step(deliver_nothing())
    with pytest.raises(RuntimeError):
        env.step(deliver_nothing())


def test_step_before_reset_raises():
    env = InventoryRoutingEnv(make_scenario())
    with pytest.raises(RuntimeError):
        env.step(deliver_nothing())


def test_inventory_never_negative_over_episode():
    env = InventoryRoutingEnv(make_scenario(horizon=6, spread=3.0))
    obs = env.reset()
    for _ in range(6):
        result = env.step(deliver_nothing())
        for store in result.observation.state.stores:
            assert store.inventory >= 0


# --- capacity rules ------------------------------------------------------


def test_store_capacity_caps_delivery_overflow_wasted():
    # Store starts at 10, max 40; deliver 45 (within truck cap 50). After
    # delivery it should hold 40 (overflow wasted), then demand 10 -> 30 left.
    scenario = make_scenario(
        horizon=1, spread=0.0, capacity=50, store_specs=[(3.0, 4.0, 10)]
    )
    env = InventoryRoutingEnv(scenario)
    env.reset()
    action = Action(routes=(Route(truck_id=0, stops=(Stop(0, 45),)),))
    result = env.step(action)
    # ending inventory = min(40, 10+45) - demand(10) = 40 - 10 = 30
    assert result.observation.state.stores[0].inventory == 30
    assert result.info["cost"].holding == 30.0


def test_truck_capacity_exceeded_raises():
    scenario = make_scenario(capacity=30, store_specs=[(3.0, 4.0, 10), (6.0, 8.0, 10)])
    env = InventoryRoutingEnv(scenario)
    env.reset()
    action = Action(routes=(Route(0, (Stop(0, 20), Stop(1, 15))),))  # 35 > 30
    with pytest.raises(ValueError):
        env.step(action)


def test_unknown_store_raises():
    env = InventoryRoutingEnv(make_scenario())
    env.reset()
    with pytest.raises(ValueError):
        env.step(Action(routes=(Route(0, (Stop(99, 5),)),)))


def test_negative_quantity_raises():
    env = InventoryRoutingEnv(make_scenario())
    env.reset()
    with pytest.raises(ValueError):
        env.step(Action(routes=(Route(0, (Stop(0, -1),)),)))


def test_truck_id_out_of_range_raises():
    env = InventoryRoutingEnv(make_scenario(num_trucks=1))
    env.reset()
    with pytest.raises(ValueError):
        env.step(Action(routes=(Route(5, (Stop(0, 5),)),)))


def test_duplicate_truck_raises():
    env = InventoryRoutingEnv(make_scenario(num_trucks=2))
    env.reset()
    action = Action(routes=(Route(0, (Stop(0, 5),)), Route(0, (Stop(1, 5),))))
    with pytest.raises(ValueError):
        env.step(action)


# --- cost math -----------------------------------------------------------


def test_exact_cost_math_for_a_day():
    # depot (0,0), s0 (3,4) dist 5, s1 (6,8) dist 10, dist(s0,s1)=5. spread=0 so
    # demand is exactly 10 at each store.
    scenario = make_scenario(
        horizon=1, spread=0.0, capacity=50,
        store_specs=[(3.0, 4.0, 10), (6.0, 8.0, 10)],
    )
    env = InventoryRoutingEnv(scenario)
    env.reset()
    action = Action(routes=(Route(0, (Stop(0, 20), Stop(1, 5))),))
    result = env.step(action)
    cost = result.info["cost"]
    assert cost.travel == pytest.approx(5 + 5 + 10)  # 20
    # s0: 10+20=30 -10 = 20 left; s1: 10+5=15 -10 = 5 left; both no stockout
    assert cost.holding == pytest.approx(25.0)
    assert cost.stockout == pytest.approx(0.0)
    assert cost.total == pytest.approx(45.0)
    assert result.reward == pytest.approx(-45.0)


def test_deliver_nothing_stockout_math():
    # spread=0: demand 10/day. Day 0 inventory 10 meets demand exactly (no cost).
    # Day 1 inventory 0, demand 10 -> shortfall 10 each store, stockout 200/store.
    scenario = make_scenario(horizon=2, spread=0.0)
    env = InventoryRoutingEnv(scenario)
    env.reset()
    day0 = env.step(deliver_nothing())
    assert day0.info["cost"].total == pytest.approx(0.0)
    day1 = env.step(deliver_nothing())
    assert day1.info["cost"].stockout == pytest.approx(2 * 10 * 20.0)  # 400


def test_travel_cost_matches_geometry():
    from sim.geometry import DistanceMatrix, travel_cost

    scenario = make_scenario(horizon=1, capacity=50)
    env = InventoryRoutingEnv(scenario)
    env.reset()
    action = Action(routes=(Route(0, (Stop(0, 5), Stop(1, 5))),))
    result = env.step(action)
    matrix = DistanceMatrix.from_scenario(scenario)
    expected = travel_cost(matrix, action, scenario.travel_cost_per_distance)
    assert result.info["cost"].travel == pytest.approx(expected)


def test_total_cost_is_sum_of_daily():
    env = InventoryRoutingEnv(make_scenario(horizon=4, spread=2.0))
    env.reset()
    daily = []
    for _ in range(4):
        daily.append(env.step(deliver_nothing()).info["cost"])
    manual = sum((c.total for c in daily), 0.0)
    assert env.total_cost.total == pytest.approx(manual)


def test_reward_is_negative_cost_each_step():
    env = InventoryRoutingEnv(make_scenario(horizon=3, spread=2.0))
    env.reset()
    for _ in range(3):
        result = env.step(deliver_nothing())
        assert result.reward == pytest.approx(result.info["cost"].reward)


# --- reproducibility -----------------------------------------------------


def test_same_seed_reproduces_rewards():
    def run(seed):
        env = InventoryRoutingEnv(make_scenario(horizon=4, spread=3.0, seed=seed))
        env.reset()
        return [env.step(deliver_nothing()).reward for _ in range(4)]

    assert run(123) == run(123)


def test_different_seed_changes_rewards():
    def run(seed):
        env = InventoryRoutingEnv(make_scenario(horizon=6, spread=3.0, seed=seed))
        env.reset()
        return [env.step(deliver_nothing()).reward for _ in range(6)]

    assert run(1) != run(2)


def test_reset_seed_override():
    env = InventoryRoutingEnv(make_scenario(horizon=4, spread=3.0, seed=1))
    env.reset(seed=1)
    a = [env.step(deliver_nothing()).reward for _ in range(4)]
    env.reset(seed=2)
    b = [env.step(deliver_nothing()).reward for _ in range(4)]
    assert a != b


def test_default_scenario_runs_full_episode():
    env = InventoryRoutingEnv(default_scenario())
    env.reset()
    result = None
    steps = 0
    while not (result and result.done):
        result = env.step(deliver_nothing())
        steps += 1
    assert steps == default_scenario().horizon
    assert isinstance(env.total_cost, CostBreakdown)
