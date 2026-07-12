"""Shared truck-tour construction.

Nearest-neighbour packing used by both the nearest-neighbour and rolling-horizon
agents (and reusable by a future RL policy): given how much each store should
receive, build each truck's tour by repeatedly driving to the nearest store that
still wants stock, until the truck is full. See docs/PLAN.md.
"""

from __future__ import annotations

from sim.geometry import DEPOT, DistanceMatrix, Point
from sim.state import Fleet, Route, Stop


def build_routes(
    want: dict[int, int], fleet: Fleet, distances: DistanceMatrix
) -> tuple[Route, ...]:
    """Nearest-first truck tours delivering the requested per-store quantities.

    ``want`` maps ``store_id`` to units to deliver. Each truck starts at the
    depot and repeatedly serves the nearest store with remaining want, splitting
    a store across trucks when one truck cannot carry all of it. Returns one
    :class:`Route` per truck that makes at least one stop. ``want`` is not
    mutated."""
    remaining_want = {sid: qty for sid, qty in want.items() if qty > 0}
    routes: list[Route] = []
    for truck in range(fleet.num_trucks):
        remaining = fleet.capacity
        current: Point = DEPOT
        stops: list[Stop] = []
        while remaining > 0:
            candidates = [sid for sid, w in remaining_want.items() if w > 0]
            if not candidates:
                break
            nearest = min(
                candidates, key=lambda sid: distances.distance(current, sid)
            )
            give = min(remaining_want[nearest], remaining)
            if give <= 0:
                break
            stops.append(Stop(store_id=nearest, quantity=give))
            remaining_want[nearest] -= give
            remaining -= give
            current = nearest
        if stops:
            routes.append(Route(truck_id=truck, stops=tuple(stops)))
    return tuple(routes)
