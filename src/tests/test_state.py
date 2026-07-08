"""Tests for sim.state data model (item 1)."""

import dataclasses

import pytest

from sim.state import Action, Fleet, Route, Stop, StoreState, WorldState


def test_stop_holds_store_and_quantity():
    stop = Stop(store_id=3, quantity=12)
    assert stop.store_id == 3
    assert stop.quantity == 12


def test_route_holds_ordered_stops_for_a_truck():
    route = Route(truck_id=1, stops=(Stop(0, 5), Stop(2, 7)))
    assert route.truck_id == 1
    assert route.stops == (Stop(0, 5), Stop(2, 7))


def test_action_holds_routes():
    action = Action(routes=(Route(0, (Stop(1, 4),)),))
    assert len(action.routes) == 1
    assert action.routes[0].truck_id == 0


def test_empty_action_is_valid():
    action = Action(routes=())
    assert action.routes == ()


def test_store_state_holds_id_and_inventory():
    store = StoreState(store_id=2, inventory=15)
    assert store.store_id == 2
    assert store.inventory == 15


def test_fleet_holds_trucks_and_capacity():
    fleet = Fleet(num_trucks=2, capacity=50)
    assert fleet.num_trucks == 2
    assert fleet.capacity == 50


def test_world_state_holds_day_stores_and_depot():
    state = WorldState(
        day=0,
        stores=(StoreState(0, 20), StoreState(1, 10)),
        depot_inventory=200,
    )
    assert state.day == 0
    assert len(state.stores) == 2
    assert state.depot_inventory == 200


def test_world_state_forecasts_default_empty():
    state = WorldState(day=0, stores=(), depot_inventory=0)
    assert state.forecasts == ()


def test_world_state_carries_forecasts_when_given():
    state = WorldState(
        day=1,
        stores=(StoreState(0, 5),),
        depot_inventory=100,
        forecasts=((10.0, 9.5, 11.0),),
    )
    assert state.forecasts == ((10.0, 9.5, 11.0),)


@pytest.mark.parametrize(
    ("obj", "field"),
    [
        (Stop(0, 1), "quantity"),
        (Route(0, ()), "truck_id"),
        (Action(()), "routes"),
        (StoreState(0, 0), "inventory"),
        (Fleet(1, 1), "capacity"),
        (WorldState(0, (), 0), "day"),
    ],
)
def test_state_types_are_frozen(obj, field):
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(obj, field, 99)
