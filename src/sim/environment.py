"""InventoryRoutingEnv: reset() and step(action), the single source of truth.

The environment orchestrates one day of the game (see the day loop in
docs/PLAN.md): it prices travel via :mod:`sim.geometry`, applies deliveries
(capped at store capacity, overflow wasted), realizes the seeded demand, and
prices the day via :mod:`sim.scoring`. Everyone -- the human through the API,
the scripted agents, and later an RL policy -- drives the game through these two
methods.

State is threaded immutably: each ``step`` produces a fresh :class:`WorldState`.
Stores are handled by position in ``scenario.stores``; ``store_id`` is only a
label, mapped back to a position when applying a route's drops.

Depot supply is unlimited in the first version -- ``depot_inventory`` is carried
as an observable value but is not consumed, matching the plan's cost model
(travel + holding + stockout, with no depot stockout).

See docs/superpowers/specs/2026-07-08-sim-state-config-design.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sim.config import Scenario
from sim.demand import DEFAULT_FORECAST_HORIZON, DemandSchedule, generate_schedule
from sim.geometry import DistanceMatrix, travel_cost
from sim.scoring import CostBreakdown, episode_total, price_day
from sim.state import Action, StoreState, WorldState


@dataclass(frozen=True)
class Observation:
    """Everything an agent sees before deciding: the dynamic state plus the
    fixed world (scenario and precomputed distances)."""

    state: WorldState
    scenario: Scenario
    distances: DistanceMatrix


@dataclass(frozen=True)
class StepResult:
    """The Gym-style outcome of one day."""

    observation: Observation
    reward: float
    done: bool
    info: dict[str, Any]


class InventoryRoutingEnv:
    """A seeded episode of the inventory routing game."""

    def __init__(
        self, scenario: Scenario, forecast_horizon: int = DEFAULT_FORECAST_HORIZON
    ) -> None:
        self.scenario = scenario
        self.distances = DistanceMatrix.from_scenario(scenario)
        self._forecast_horizon = forecast_horizon
        self._store_index = {s.store_id: i for i, s in enumerate(scenario.stores)}
        self._schedule: DemandSchedule | None = None
        self._state: WorldState | None = None
        self._history: list[CostBreakdown] = []

    # -- public API -------------------------------------------------------

    def reset(self, seed: int | None = None) -> Observation:
        """Start a fresh season. Same seed reproduces the episode exactly."""
        if seed is None:
            seed = self.scenario.seed
        self._schedule = generate_schedule(
            self.scenario, seed=seed, forecast_horizon=self._forecast_horizon
        )
        self._history = []
        self._state = WorldState(
            day=0,
            stores=tuple(
                StoreState(store_id=s.store_id, inventory=s.initial_inventory)
                for s in self.scenario.stores
            ),
            depot_inventory=self.scenario.depot_inventory,
            forecasts=self._schedule.forecast_at(0),
        )
        return self._observation()

    def step(self, action: Action) -> StepResult:
        """Play one day and return the new observation, reward, done, and info."""
        if self._state is None or self._schedule is None:
            raise RuntimeError("call reset() before step()")
        if self.done:
            raise RuntimeError("episode is finished; call reset() to start again")

        day = self._state.day
        self._validate_action(action)

        travel = travel_cost(
            self.distances, action, self.scenario.travel_cost_per_distance
        )
        post_delivery = self._apply_deliveries(action)
        ending_inventory, shortfall, demand = self._realize_demand(day, post_delivery)

        cost = price_day(self.scenario.stores, ending_inventory, shortfall, travel)
        self._history.append(cost)

        next_day = day + 1
        done = next_day >= self.scenario.horizon
        forecasts = () if done else self._schedule.forecast_at(next_day)
        self._state = WorldState(
            day=next_day,
            stores=tuple(
                StoreState(store_id=s.store_id, inventory=inv)
                for s, inv in zip(self.scenario.stores, ending_inventory)
            ),
            depot_inventory=self.scenario.depot_inventory,
            forecasts=forecasts,
        )

        info: dict[str, Any] = {
            "cost": cost,
            "day": day,
            "demand": tuple(demand),
            "shortfall": tuple(shortfall),
            "done": done,
        }
        return StepResult(self._observation(), cost.reward, done, info)

    def current_observation(self) -> Observation:
        """The current observation. Requires :meth:`reset` to have been called."""
        if self._state is None:
            raise RuntimeError("call reset() before observing")
        return self._observation()

    @property
    def done(self) -> bool:
        return self._state is not None and self._state.day >= self.scenario.horizon

    @property
    def total_cost(self) -> CostBreakdown:
        """Running episode total across the days played so far."""
        return episode_total(self._history)

    # -- internals --------------------------------------------------------

    def _observation(self) -> Observation:
        assert self._state is not None
        return Observation(
            state=self._state, scenario=self.scenario, distances=self.distances
        )

    def _validate_action(self, action: Action) -> None:
        seen_trucks: set[int] = set()
        num_trucks = self.scenario.fleet.num_trucks
        capacity = self.scenario.fleet.capacity
        for route in action.routes:
            if not 0 <= route.truck_id < num_trucks:
                raise ValueError(
                    f"truck_id {route.truck_id} out of range [0, {num_trucks})"
                )
            if route.truck_id in seen_trucks:
                raise ValueError(f"truck {route.truck_id} used in more than one route")
            seen_trucks.add(route.truck_id)

            load = 0
            for stop in route.stops:
                if stop.store_id not in self._store_index:
                    raise ValueError(f"unknown store_id {stop.store_id}")
                if stop.quantity < 0:
                    raise ValueError(
                        f"negative quantity {stop.quantity} at store {stop.store_id}"
                    )
                load += stop.quantity
            if load > capacity:
                raise ValueError(
                    f"truck {route.truck_id} load {load} exceeds capacity {capacity}"
                )

    def _apply_deliveries(self, action: Action) -> list[int]:
        assert self._state is not None
        inventory = [s.inventory for s in self._state.stores]
        for route in action.routes:
            for stop in route.stops:
                idx = self._store_index[stop.store_id]
                cap = self.scenario.stores[idx].max_capacity
                inventory[idx] = min(cap, inventory[idx] + stop.quantity)
        return inventory

    def _realize_demand(
        self, day: int, inventory: list[int]
    ) -> tuple[list[int], list[int], list[int]]:
        assert self._schedule is not None
        ending: list[int] = []
        shortfall: list[int] = []
        demand: list[int] = []
        for i, inv in enumerate(inventory):
            d = self._schedule.actuals[day][i]
            demand.append(d)
            ending.append(max(0, inv - d))
            shortfall.append(max(0, d - inv))
        return ending, shortfall, demand
