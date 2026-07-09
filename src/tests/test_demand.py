"""Tests for sim.demand: seeded demand generator and forecast (item 3)."""

import pytest

from sim.config import Scenario, StoreConfig, default_scenario
from sim.demand import DemandSchedule, generate_schedule
from sim.state import Fleet


def make_scenario(n_stores=4, horizon=12, seed=7, mean=10.0, spread=3.0):
    stores = tuple(
        StoreConfig(
            store_id=i,
            location=(float(i), float(i)),
            max_capacity=40,
            initial_inventory=10,
            holding_cost=1.0,
            stockout_penalty=20.0,
            demand_mean=mean,
            demand_spread=spread,
        )
        for i in range(n_stores)
    )
    return Scenario(
        name="demand",
        stores=stores,
        depot_location=(0.0, 0.0),
        fleet=Fleet(num_trucks=2, capacity=50),
        horizon=horizon,
        travel_cost_per_distance=1.0,
        depot_inventory=500,
        seed=seed,
    )


def test_generate_returns_schedule():
    schedule = generate_schedule(make_scenario())
    assert isinstance(schedule, DemandSchedule)


def test_actuals_shape_is_horizon_by_stores():
    scenario = make_scenario(n_stores=4, horizon=12)
    schedule = generate_schedule(scenario)
    assert len(schedule.actuals) == 12
    assert all(len(day) == 4 for day in schedule.actuals)


def test_actuals_are_non_negative_integers():
    schedule = generate_schedule(make_scenario())
    for day in schedule.actuals:
        for value in day:
            assert isinstance(value, int)
            assert value >= 0


def test_same_seed_reproduces_actuals_and_forecasts():
    scenario = make_scenario(seed=123)
    a = generate_schedule(scenario)
    b = generate_schedule(scenario)
    assert a.actuals == b.actuals
    assert all(a.forecast_at(t) == b.forecast_at(t) for t in range(scenario.horizon))


def test_different_seed_changes_demand():
    a = generate_schedule(make_scenario(seed=1))
    b = generate_schedule(make_scenario(seed=2))
    assert a.actuals != b.actuals


def test_explicit_seed_overrides_scenario_seed():
    scenario = make_scenario(seed=1)
    from_scenario = generate_schedule(scenario)
    overridden = generate_schedule(scenario, seed=999)
    assert from_scenario.actuals != overridden.actuals
    # overriding with the scenario's own seed reproduces it
    assert generate_schedule(scenario, seed=1).actuals == from_scenario.actuals


def test_demand_on_matches_actuals():
    schedule = generate_schedule(make_scenario())
    assert schedule.demand_on(3, 2) == schedule.actuals[3][2]


def test_forecast_window_shape():
    scenario = make_scenario(n_stores=4, horizon=12)
    schedule = generate_schedule(scenario, forecast_horizon=3)
    forecast = schedule.forecast_at(0)
    assert len(forecast) == 4  # one row per store
    assert all(len(row) == 3 for row in forecast)  # three days ahead


def test_forecast_truncates_at_season_end():
    scenario = make_scenario(n_stores=4, horizon=12)
    schedule = generate_schedule(scenario, forecast_horizon=3)
    last = schedule.forecast_at(11)  # only day 11 itself remains
    assert all(len(row) == 1 for row in last)


def test_forecast_values_are_floats_and_non_negative():
    schedule = generate_schedule(make_scenario(), forecast_horizon=3)
    for row in schedule.forecast_at(0):
        for value in row:
            assert isinstance(value, float)
            assert value >= 0.0


def test_forecast_tracks_actual_within_loose_bound():
    # Deterministic (fixed seed): forecast is a blurry look at real demand, so
    # the average absolute error over a season should stay within a few spreads.
    scenario = make_scenario(n_stores=6, horizon=14, seed=42, mean=10.0, spread=3.0)
    schedule = generate_schedule(scenario, forecast_horizon=1)
    errors = []
    for t in range(scenario.horizon):
        forecast_today = schedule.forecast_at(t)
        for store_id, row in enumerate(forecast_today):
            errors.append(abs(row[0] - schedule.actuals[t][store_id]))
    mean_error = sum(errors) / len(errors)
    assert mean_error < 3 * 3.0


def test_default_scenario_generates_schedule():
    scenario = default_scenario()
    schedule = generate_schedule(scenario)
    assert len(schedule.actuals) == scenario.horizon
    assert all(len(day) == scenario.num_stores for day in schedule.actuals)
