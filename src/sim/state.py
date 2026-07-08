"""Sim-core data model.

Structural, framework-free data types shared by the environment, agents, and
(via translation) the API. Everything here is an immutable ``frozen`` dataclass
so ``step()`` can return a fresh :class:`WorldState` rather than mutating in
place, which keeps episodes reproducible and RL-friendly.

Fixed world parameters (locations, capacities, costs, demand distribution)
live in :mod:`sim.config`, not here. This module holds only structural shapes
and the values that change day to day.

See docs/PLAN.md and docs/superpowers/specs/2026-07-08-sim-state-config-design.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Stop:
    """A single delivery: drop ``quantity`` units at store ``store_id``."""

    store_id: int
    quantity: int


@dataclass(frozen=True)
class Route:
    """One truck's ordered tour. The depot start and return are implied."""

    truck_id: int
    stops: tuple[Stop, ...]


@dataclass(frozen=True)
class Action:
    """A full move for one day: a route per truck. Idle trucks may be omitted."""

    routes: tuple[Route, ...]


@dataclass(frozen=True)
class StoreState:
    """The dynamic per-store value: how much stock it holds right now."""

    store_id: int
    inventory: int


@dataclass(frozen=True)
class Fleet:
    """Fixed fleet descriptor: ``num_trucks`` trucks each with ``capacity``."""

    num_trucks: int
    capacity: int


@dataclass(frozen=True)
class WorldState:
    """The dynamic state observed before deciding a day's action.

    ``forecasts`` holds, per store, the lookahead demand estimates. It defaults
    to empty and is populated once :mod:`sim.demand` exists; it is typed as
    plain floats so this module has no dependency on the demand generator.
    """

    day: int
    stores: tuple[StoreState, ...]
    depot_inventory: int
    forecasts: tuple[tuple[float, ...], ...] = field(default_factory=tuple)
