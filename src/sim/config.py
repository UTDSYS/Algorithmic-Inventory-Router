"""Scenario definition and the one hand-authored map for the first version.

A :class:`Scenario` is the fixed world: store definitions, depot, fleet,
horizon, cost model, and seed. Only the daily demand realization varies per
episode (see docs/PLAN.md). :func:`default_scenario` returns the single map the
first playable version ships with.

See docs/superpowers/specs/2026-07-08-sim-state-config-design.md.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from sim.state import Fleet, StoreState, WorldState


@dataclass(frozen=True)
class StoreConfig:
    """Fixed parameters of one store. Its inventory is dynamic and lives in
    :class:`sim.state.StoreState`; everything here stays constant for a game."""

    store_id: int
    location: tuple[float, float]
    max_capacity: int
    initial_inventory: int
    holding_cost: float
    stockout_penalty: float
    demand_mean: float
    demand_spread: float


@dataclass(frozen=True)
class Scenario:
    """The fixed world a match is played on."""

    name: str
    stores: tuple[StoreConfig, ...]
    depot_location: tuple[float, float]
    fleet: Fleet
    horizon: int
    travel_cost_per_distance: float
    depot_inventory: int
    seed: int

    def __post_init__(self) -> None:
        if not self.stores:
            raise ValueError("scenario must have at least one store")
        if self.horizon <= 0:
            raise ValueError(f"horizon must be positive, got {self.horizon}")
        if self.fleet.num_trucks <= 0:
            raise ValueError(
                f"fleet must have at least one truck, got {self.fleet.num_trucks}"
            )
        if self.fleet.capacity <= 0:
            raise ValueError(
                f"truck capacity must be positive, got {self.fleet.capacity}"
            )
        if self.travel_cost_per_distance < 0:
            raise ValueError("travel_cost_per_distance must be non-negative")
        if self.depot_inventory < 0:
            raise ValueError("depot_inventory must be non-negative")

        seen_ids: set[int] = set()
        for store in self.stores:
            if store.store_id in seen_ids:
                raise ValueError(f"duplicate store_id {store.store_id}")
            seen_ids.add(store.store_id)
            if store.max_capacity <= 0:
                raise ValueError(
                    f"store {store.store_id} max_capacity must be positive"
                )
            if not 0 <= store.initial_inventory <= store.max_capacity:
                raise ValueError(
                    f"store {store.store_id} initial_inventory "
                    f"{store.initial_inventory} out of range [0, {store.max_capacity}]"
                )
            if store.holding_cost < 0 or store.stockout_penalty < 0:
                raise ValueError(f"store {store.store_id} costs must be non-negative")

    @property
    def num_stores(self) -> int:
        return len(self.stores)

    def initial_state(self) -> WorldState:
        """Build the day-0 :class:`WorldState` from the scenario's fixed values."""
        return WorldState(
            day=0,
            stores=tuple(
                StoreState(store_id=s.store_id, inventory=s.initial_inventory)
                for s in self.stores
            ),
            depot_inventory=self.depot_inventory,
        )


_LAYOUT_SEED = 42


def default_scenario() -> Scenario:
    """The single hand-authored map the first version ships with.

    Eight stores scattered across a 100x100 grid with the depot in the
    bottom-left corner, two trucks of capacity 50 (about 100 units/day) against
    roughly 80 units/day of expected demand, so the fleet is tight and the
    player must prioritise. Stockouts (penalty 20) dominate holding cost (1),
    and travel is charged per unit distance.

    Store positions are drawn from a fixed seed (:data:`_LAYOUT_SEED`), so the
    scatter is irregular but identical on every call.
    """
    rng = random.Random(_LAYOUT_SEED)
    # One irregular map: random positions, hand-set starting inventories so the
    # opening stock spread stays deliberate. Positions stay inside [15, 95] on
    # both axes, clear of the bottom-left depot and the grid edges.
    initial_inventories = (20, 18, 22, 20, 15, 25, 20, 20)
    stores = tuple(
        StoreConfig(
            store_id=i,
            location=(round(rng.uniform(15.0, 95.0), 1), round(rng.uniform(15.0, 95.0), 1)),
            max_capacity=40,
            initial_inventory=initial,
            holding_cost=1.0,
            stockout_penalty=20.0,
            demand_mean=10.0,
            demand_spread=3.0,
        )
        for i, initial in enumerate(initial_inventories)
    )
    return Scenario(
        name="default",
        stores=stores,
        depot_location=(10.0, 10.0),
        fleet=Fleet(num_trucks=2, capacity=50),
        horizon=12,
        travel_cost_per_distance=1.0,
        depot_inventory=1000,
        seed=_LAYOUT_SEED,
    )
