"""Per-day cost breakdown and episode total.

Scoring is pure pricing: it does not mutate state. The environment applies
deliveries and realizes demand (the day-loop steps in docs/PLAN.md), then hands
the resulting per-store ending inventory and shortfall, plus the travel cost from
:mod:`sim.geometry`, to :func:`price_day`. The day's cost is
``travel + holding + stockout`` and the reward is its negative.

See docs/PLAN.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from sim.config import StoreConfig


@dataclass(frozen=True)
class CostBreakdown:
    """A cost split into its three components. ``reward`` is minus the total."""

    travel: float
    holding: float
    stockout: float

    @property
    def total(self) -> float:
        return self.travel + self.holding + self.stockout

    @property
    def reward(self) -> float:
        return -self.total

    def __add__(self, other: "CostBreakdown") -> "CostBreakdown":
        return CostBreakdown(
            travel=self.travel + other.travel,
            holding=self.holding + other.holding,
            stockout=self.stockout + other.stockout,
        )


def holding_cost(
    stores: Sequence[StoreConfig], ending_inventory: Sequence[int]
) -> float:
    """Cost of stock left over: each store's leftover times its holding rate."""
    return sum(
        store.holding_cost * inventory
        for store, inventory in zip(stores, ending_inventory)
    )


def stockout_cost(stores: Sequence[StoreConfig], shortfall: Sequence[int]) -> float:
    """Penalty for unmet demand: each store's shortfall times its penalty."""
    return sum(
        store.stockout_penalty * short for store, short in zip(stores, shortfall)
    )


def price_day(
    stores: Sequence[StoreConfig],
    ending_inventory: Sequence[int],
    shortfall: Sequence[int],
    travel: float,
) -> CostBreakdown:
    """Assemble one day's cost breakdown from the realized quantities."""
    return CostBreakdown(
        travel=travel,
        holding=holding_cost(stores, ending_inventory),
        stockout=stockout_cost(stores, shortfall),
    )


def episode_total(breakdowns: Sequence[CostBreakdown]) -> CostBreakdown:
    """Sum daily breakdowns into a season total, component by component."""
    total = CostBreakdown(travel=0.0, holding=0.0, stockout=0.0)
    for day in breakdowns:
        total = total + day
    return total
