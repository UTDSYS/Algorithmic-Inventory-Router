"""Coordinates, distance matrix, tour length, and travel cost.

Points on the map are the depot and the stores. Stores are identified by their
integer ``store_id``; the depot is the :data:`DEPOT` sentinel. A
:class:`DistanceMatrix` precomputes the fixed all-pairs Euclidean distances once
from a :class:`sim.config.Scenario`; the environment and agents then look
distances up rather than recomputing them.

See docs/PLAN.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final, Iterable, Union

import numpy as np

from sim.config import Scenario
from sim.state import Action


class _Depot:
    """Singleton sentinel identifying the depot as a map point."""

    _instance: "_Depot | None" = None

    def __new__(cls) -> "_Depot":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return "DEPOT"


DEPOT: Final = _Depot()

# A point is either a store id or the depot sentinel.
Point = Union[int, _Depot]


def euclidean(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Straight-line distance between two 2D coordinates."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


@dataclass(frozen=True)
class DistanceMatrix:
    """Precomputed all-pairs distances between the depot and every store."""

    _index: dict[Point, int]
    _matrix: np.ndarray

    @classmethod
    def from_scenario(cls, scenario: Scenario) -> "DistanceMatrix":
        points: list[Point] = [DEPOT, *(s.store_id for s in scenario.stores)]
        coords = [scenario.depot_location, *(s.location for s in scenario.stores)]
        index = {point: i for i, point in enumerate(points)}
        n = len(points)
        matrix = np.zeros((n, n), dtype=float)
        for i in range(n):
            for j in range(i + 1, n):
                d = euclidean(coords[i], coords[j])
                matrix[i, j] = d
                matrix[j, i] = d
        return cls(_index=index, _matrix=matrix)

    def distance(self, a: Point, b: Point) -> float:
        return float(self._matrix[self._index[a], self._index[b]])


def tour_length(matrix: DistanceMatrix, store_ids: Iterable[int]) -> float:
    """Length of the tour depot -> each store in order -> depot.

    An empty tour has length zero (the truck never leaves the depot)."""
    order = list(store_ids)
    if not order:
        return 0.0
    total = matrix.distance(DEPOT, order[0])
    for prev, nxt in zip(order, order[1:]):
        total += matrix.distance(prev, nxt)
    total += matrix.distance(order[-1], DEPOT)
    return total


def travel_cost(
    matrix: DistanceMatrix, action: Action, cost_per_distance: float
) -> float:
    """Total travel cost of an action: every truck's tour length times cost."""
    total_length = sum(
        tour_length(matrix, (stop.store_id for stop in route.stops))
        for route in action.routes
    )
    return total_length * cost_per_distance
