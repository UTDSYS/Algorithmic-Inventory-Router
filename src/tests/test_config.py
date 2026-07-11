"""Tests for sim.config: scenario definition and the default map (item 1)."""

import dataclasses

import pytest

from sim.config import RoadSpec, Scenario, StoreConfig, default_scenario
from sim.state import Fleet, WorldState


def make_store(store_id=0, initial=20, cap=40):
    return StoreConfig(
        store_id=store_id,
        location=(10.0, 20.0),
        max_capacity=cap,
        initial_inventory=initial,
        holding_cost=1.0,
        stockout_penalty=20.0,
        demand_mean=10.0,
        demand_spread=3.0,
    )


def make_scenario(stores=None, **overrides):
    stores = stores if stores is not None else (make_store(0), make_store(1))
    params = dict(
        name="test",
        stores=stores,
        depot_location=(50.0, 50.0),
        fleet=Fleet(num_trucks=2, capacity=50),
        horizon=12,
        travel_cost_per_distance=1.0,
        depot_inventory=500,
        seed=7,
    )
    params.update(overrides)
    return Scenario(**params)


def test_store_config_fields():
    store = make_store(store_id=3, initial=15, cap=40)
    assert store.store_id == 3
    assert store.initial_inventory == 15
    assert store.max_capacity == 40
    assert store.location == (10.0, 20.0)


def test_scenario_num_stores():
    assert make_scenario().num_stores == 2


def test_scenario_is_frozen():
    scenario = make_scenario()
    with pytest.raises(dataclasses.FrozenInstanceError):
        scenario.horizon = 5


def test_scenario_rejects_empty_stores():
    with pytest.raises(ValueError):
        make_scenario(stores=())


def test_scenario_rejects_nonpositive_horizon():
    with pytest.raises(ValueError):
        make_scenario(horizon=0)


def test_scenario_rejects_nonpositive_fleet():
    with pytest.raises(ValueError):
        make_scenario(fleet=Fleet(num_trucks=0, capacity=50))
    with pytest.raises(ValueError):
        make_scenario(fleet=Fleet(num_trucks=2, capacity=0))


def test_scenario_rejects_negative_costs():
    with pytest.raises(ValueError):
        make_scenario(travel_cost_per_distance=-1.0)


def test_scenario_rejects_initial_over_capacity():
    with pytest.raises(ValueError):
        make_scenario(stores=(make_store(0, initial=50, cap=40),))


def test_scenario_rejects_nonpositive_capacity():
    with pytest.raises(ValueError):
        make_scenario(stores=(make_store(0, initial=0, cap=0),))


def test_scenario_rejects_duplicate_store_ids():
    with pytest.raises(ValueError):
        make_scenario(stores=(make_store(0), make_store(0)))


def test_initial_state_matches_scenario():
    scenario = make_scenario(
        stores=(make_store(0, initial=20), make_store(1, initial=5)),
        depot_inventory=300,
    )
    state = scenario.initial_state()
    assert isinstance(state, WorldState)
    assert state.day == 0
    assert state.depot_inventory == 300
    assert tuple(s.store_id for s in state.stores) == (0, 1)
    assert tuple(s.inventory for s in state.stores) == (20, 5)
    assert state.forecasts == ()


def test_default_scenario_within_plan_ranges():
    scenario = default_scenario()
    assert 6 <= scenario.num_stores <= 10
    assert scenario.fleet.num_trucks == 2
    assert 10 <= scenario.horizon <= 14


def test_scenario_road_spec_defaults_to_none():
    assert make_scenario().road_spec is None


def test_default_scenario_has_arterial_road_spec():
    spec = default_scenario().road_spec
    assert isinstance(spec, RoadSpec)
    assert spec.arterials == (25.0, 50.0, 75.0)
    assert spec.bounds == (0.0, 100.0)


def test_default_scenario_store_ids_are_contiguous():
    scenario = default_scenario()
    assert [s.store_id for s in scenario.stores] == list(range(scenario.num_stores))


def test_default_scenario_initial_state_is_valid():
    scenario = default_scenario()
    state = scenario.initial_state()
    assert len(state.stores) == scenario.num_stores
    for store_cfg, store_state in zip(scenario.stores, state.stores):
        assert 0 <= store_state.inventory <= store_cfg.max_capacity
