"""Greedy agent: serve the most stockout-prone stores first.

Each day it scores every store by days-of-cover (inventory divided by the
next-day demand forecast); the lower the cover, the sooner it runs out. It fills
the most at-risk stores toward capacity, packing trucks until they are full. It
is deliberately myopic -- it never plans ahead and does not care whether the
resulting route is efficient (see docs/PLAN.md).
"""

from __future__ import annotations

import math

from agents.base import Agent
from sim.environment import Observation
from sim.state import Action, Route, Stop


class GreedyAgent(Agent):
    def act(self, observation: Observation) -> Action:
        stores = observation.scenario.stores
        fleet = observation.scenario.fleet

        # Rank stores that need stock by urgency (lowest days-of-cover first).
        ranked = sorted(
            (i for i in range(len(stores)) if self._want(observation, i) > 0),
            key=lambda i: self._days_of_cover(observation, i),
        )

        remaining = [fleet.capacity] * fleet.num_trucks
        stops: list[list[Stop]] = [[] for _ in range(fleet.num_trucks)]

        for store_idx in ranked:
            want = self._want(observation, store_idx)
            store_id = stores[store_idx].store_id
            for truck in range(fleet.num_trucks):
                if want <= 0:
                    break
                give = min(want, remaining[truck])
                if give > 0:
                    stops[truck].append(Stop(store_id=store_id, quantity=give))
                    remaining[truck] -= give
                    want -= give

        routes = tuple(
            Route(truck_id=truck, stops=tuple(truck_stops))
            for truck, truck_stops in enumerate(stops)
            if truck_stops
        )
        return Action(routes=routes)

    @staticmethod
    def _want(observation: Observation, store_idx: int) -> int:
        cfg = observation.scenario.stores[store_idx]
        inventory = observation.state.stores[store_idx].inventory
        return max(0, cfg.max_capacity - inventory)

    @staticmethod
    def _days_of_cover(observation: Observation, store_idx: int) -> float:
        inventory = observation.state.stores[store_idx].inventory
        forecasts = observation.state.forecasts
        next_demand = forecasts[store_idx][0] if forecasts[store_idx] else 0.0
        if next_demand <= 0:
            return math.inf  # no forecast demand -> not at risk
        return inventory / next_demand
