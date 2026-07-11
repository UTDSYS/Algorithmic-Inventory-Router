"""Scenario definition and the one hand-authored map for the first version.

A :class:`Scenario` is the fixed world: store definitions, depot, fleet,
horizon, cost model, and seed. Only the daily demand realization varies per
episode (see docs/PLAN.md). :func:`default_scenario` returns the single map the
first playable version ships with.

See docs/PLAN.md.
"""

from __future__ import annotations

from dataclasses import dataclass

from sim.state import Fleet, StoreState, WorldState


@dataclass(frozen=True)
class RoadSpec:
    """Sparse arterial road grid the trucks drive on.

    ``arterials`` are the positions of the straight roads on both axes: a
    vertical road at each ``x`` and a horizontal road at each ``y``, every road
    extended across the whole map. ``bounds`` is the ``(min, max)`` extent the
    roads span on both axes. The intersections of these roads plus their edge
    endpoints are the nodes of the road graph built in :mod:`sim.roads`.
    """

    arterials: tuple[float, ...]
    bounds: tuple[float, float]

    def __post_init__(self) -> None:
        if not self.arterials:
            raise ValueError("road spec must have at least one arterial")
        lo, hi = self.bounds
        if lo >= hi:
            raise ValueError(f"road bounds must be increasing, got {self.bounds}")
        for position in self.arterials:
            if not lo <= position <= hi:
                raise ValueError(
                    f"arterial {position} lies outside bounds {self.bounds}"
                )


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
    road_spec: RoadSpec | None = None

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


_DEMAND_SEED = 42

# Hand-placed layout: one store fronting each district of the arterial grid,
# each sitting ~7 units off an arterial (never on one) so it has a real driveway
# onto the road. Paired with the starting inventories below by index.
_STORE_LOCATIONS = (
    (32.0, 32.0),  # SW, fronts x=25
    (60.0, 18.0),  # S,  fronts y=25
    (82.0, 32.0),  # SE, fronts x=75
    (68.0, 60.0),  # E,  fronts x=75
    (82.0, 82.0),  # NE, fronts x=75
    (40.0, 82.0),  # N,  fronts y=75
    (18.0, 68.0),  # NW, fronts x=25
    (43.0, 43.0),  # centre, fronts x=50
)


def default_scenario() -> Scenario:
    """The single hand-authored map the first version ships with.

    Eight stores deliberately placed around a 100x100 arterial grid with the
    depot in the bottom-left corner, two trucks of capacity 50 (about 100
    units/day) against roughly 80 units/day of expected demand, so the fleet is
    tight and the player must prioritise. Stockouts (penalty 20) dominate holding
    cost (1), and travel is charged per unit of road distance.

    The layout is fixed (see :data:`_STORE_LOCATIONS`): each store fronts a
    street so the city reads as designed and every store has a driveway onto the
    road network. Only the daily demand varies, via the seed.
    """
    # Hand-set starting inventories so the opening stock spread stays deliberate.
    initial_inventories = (20, 18, 22, 20, 15, 25, 20, 20)
    stores = tuple(
        StoreConfig(
            store_id=i,
            location=location,
            max_capacity=40,
            initial_inventory=initial,
            holding_cost=1.0,
            stockout_penalty=20.0,
            demand_mean=10.0,
            demand_spread=3.0,
        )
        for i, (location, initial) in enumerate(
            zip(_STORE_LOCATIONS, initial_inventories)
        )
    )
    return Scenario(
        name="default",
        stores=stores,
        depot_location=(10.0, 10.0),
        fleet=Fleet(num_trucks=2, capacity=50),
        horizon=12,
        travel_cost_per_distance=1.0,
        depot_inventory=1000,
        seed=_DEMAND_SEED,
        road_spec=RoadSpec(arterials=(25.0, 50.0, 75.0), bounds=(0.0, 100.0)),
    )
