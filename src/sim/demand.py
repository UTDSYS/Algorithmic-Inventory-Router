"""Seeded demand generator and forecast.

The whole season's demand is drawn up front from a single seeded RNG, so a given
seed reproduces an episode exactly (see docs/PLAN.md: everyone in a match shares
one seed). Each store's daily demand is a discretized Normal using its
``demand_mean`` and ``demand_spread``. The forecast the player sees is that same
upcoming demand blurred with Gaussian noise, kept as a float and clipped to be
non-negative -- a helpful but imperfect hint.

The distribution is fixed by the scenario; only the numbers it rolls change with
the seed.

See docs/PLAN.md.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sim.config import Scenario

DEFAULT_FORECAST_HORIZON = 3


@dataclass(frozen=True)
class DemandSchedule:
    """A fully realized season of demand plus the forecasts the player sees.

    ``actuals[day][store]`` is the integer demand at that store on that day.
    ``_forecasts[day][store][offset]`` is the forecast made on ``day`` for the
    demand ``offset`` days later; rows shrink near the end of the season.
    """

    actuals: tuple[tuple[int, ...], ...]
    _forecasts: tuple[tuple[tuple[float, ...], ...], ...]

    def demand_on(self, day: int, store_id: int) -> int:
        return self.actuals[day][store_id]

    def forecast_at(self, day: int) -> tuple[tuple[float, ...], ...]:
        """Per-store forecast rows for the days from ``day`` onward."""
        return self._forecasts[day]


def generate_schedule(
    scenario: Scenario,
    seed: int | None = None,
    forecast_horizon: int = DEFAULT_FORECAST_HORIZON,
) -> DemandSchedule:
    """Draw an entire season of demand and its forecasts from one seeded RNG."""
    if seed is None:
        seed = scenario.seed
    rng = np.random.default_rng(seed)

    horizon = scenario.horizon
    means = np.array([s.demand_mean for s in scenario.stores], dtype=float)
    spreads = np.array([s.demand_spread for s in scenario.stores], dtype=float)

    # Actual demand: discretized, non-negative Normal per store.
    raw = rng.normal(loc=means, scale=spreads, size=(horizon, scenario.num_stores))
    actuals_arr = np.clip(np.rint(raw), 0, None).astype(int)

    # Forecast noise, drawn from the same RNG so replays match exactly. Blur is
    # proportional to each store's inherent spread.
    noise = rng.normal(
        loc=0.0,
        scale=spreads.reshape(1, scenario.num_stores, 1),
        size=(horizon, scenario.num_stores, forecast_horizon),
    )

    actuals = tuple(tuple(int(v) for v in day) for day in actuals_arr)

    forecasts: list[tuple[tuple[float, ...], ...]] = []
    for day in range(horizon):
        available = min(forecast_horizon, horizon - day)
        rows: list[tuple[float, ...]] = []
        for store in range(scenario.num_stores):
            row = tuple(
                float(
                    max(
                        0.0,
                        actuals_arr[day + offset, store] + noise[day, store, offset],
                    )
                )
                for offset in range(available)
            )
            rows.append(row)
        forecasts.append(tuple(rows))

    return DemandSchedule(actuals=actuals, _forecasts=tuple(forecasts))
