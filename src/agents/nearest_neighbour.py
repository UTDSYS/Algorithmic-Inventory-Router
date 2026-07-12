"""Nearest-neighbour agent: optimize the route, ignore the future.

First it picks which stores need service -- those whose inventory is below a
reorder threshold (a fraction of their capacity). Then it builds each truck's
tour by distance via the shared nearest-neighbour construction in
:mod:`agents.routing`: good local travel cost, but blind to future demand (see
docs/PLAN.md).
"""

from __future__ import annotations

from agents.base import Agent
from agents.routing import build_routes
from sim.environment import Observation
from sim.state import Action


class NearestNeighbourAgent(Agent):
    def __init__(self, reorder_ratio: float = 0.5) -> None:
        self.reorder_ratio = reorder_ratio

    def act(self, observation: Observation) -> Action:
        stores = observation.scenario.stores

        # Stores below their reorder point, with how much they want to be filled.
        want: dict[int, int] = {}
        for i, cfg in enumerate(stores):
            inventory = observation.state.stores[i].inventory
            if inventory < self.reorder_ratio * cfg.max_capacity:
                want[cfg.store_id] = cfg.max_capacity - inventory

        return Action(
            routes=build_routes(
                want, observation.scenario.fleet, observation.distances
            )
        )
