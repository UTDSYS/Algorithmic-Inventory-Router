"""Nearest-neighbour agent: optimize the route, ignore the future.

First it picks which stores need service -- those whose inventory is below a
reorder threshold (a fraction of their capacity). Then it builds each truck's
tour by distance: start at the depot and repeatedly drive to the closest
unvisited store that still needs stock, filling it toward capacity, until the
truck's capacity is used up. This is the standard nearest-neighbour tour
construction: good local travel cost, but blind to future demand (see
docs/PLAN.md).
"""

from __future__ import annotations

from agents.base import Agent
from sim.environment import Observation
from sim.geometry import DEPOT
from sim.state import Action, Route, Stop


class NearestNeighbourAgent(Agent):
    def __init__(self, reorder_ratio: float = 0.5) -> None:
        self.reorder_ratio = reorder_ratio

    def act(self, observation: Observation) -> Action:
        stores = observation.scenario.stores
        fleet = observation.scenario.fleet
        distances = observation.distances

        # Stores below their reorder point, with how much they want to be filled.
        want: dict[int, int] = {}
        for i, cfg in enumerate(stores):
            inventory = observation.state.stores[i].inventory
            if inventory < self.reorder_ratio * cfg.max_capacity:
                want[cfg.store_id] = cfg.max_capacity - inventory

        routes: list[Route] = []
        for truck in range(fleet.num_trucks):
            remaining = fleet.capacity
            current = DEPOT
            stops: list[Stop] = []
            while remaining > 0:
                candidates = [sid for sid, w in want.items() if w > 0]
                if not candidates:
                    break
                nearest = min(candidates, key=lambda sid: distances.distance(current, sid))
                give = min(want[nearest], remaining)
                if give <= 0:
                    break
                stops.append(Stop(store_id=nearest, quantity=give))
                want[nearest] -= give
                remaining -= give
                current = nearest
            if stops:
                routes.append(Route(truck_id=truck, stops=tuple(stops)))

        return Action(routes=tuple(routes))
