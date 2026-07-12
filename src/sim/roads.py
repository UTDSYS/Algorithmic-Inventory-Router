"""The arterial road graph the trucks drive on and its pathfinding.

A :class:`RoadNetwork` is built from a :class:`sim.config.RoadSpec`: a sparse
grid of straight arterials (a vertical road at each ``x`` and a horizontal road
at each ``y``), every road extended across the whole map. Its nodes are the road
intersections and the points where each road meets the map bounds; its edges run
along the arterials between consecutive nodes, weighted by length.

Stores and the depot are not on the grid, so :meth:`RoadNetwork.attach` projects
each onto the nearest road segment and joins it with a short "driveway" edge.
:meth:`RoadNetwork.shortest_path` then answers road-distance queries with
Dijkstra. Everything is pure Python (``heapq``, no numpy) and deterministic.

The backend owns this graph so the cost charged for a tour and the polyline drawn
for it are computed from the same source. See docs/PLAN.md.
"""

from __future__ import annotations

import heapq
import math

from sim.config import RoadSpec

Coord = tuple[float, float]

# Tolerance for treating two coordinates as the same node. Coordinates come from
# the fixed spec and from exact projections, so mismatches are pure float noise.
_EPS = 1e-9


def _close(a: Coord, b: Coord) -> bool:
    return math.isclose(a[0], b[0], abs_tol=_EPS) and math.isclose(
        a[1], b[1], abs_tol=_EPS
    )


def _project(point: Coord, a: Coord, b: Coord) -> tuple[Coord, float]:
    """Foot of the perpendicular from ``point`` onto segment ``a``->``b``
    (clamped to the segment) and the distance to it."""
    (px, py), (ax, ay), (bx, by) = point, a, b
    dx, dy = bx - ax, by - ay
    seg_sq = dx * dx + dy * dy
    if seg_sq == 0:
        foot = a
    else:
        t = ((px - ax) * dx + (py - ay) * dy) / seg_sq
        t = max(0.0, min(1.0, t))
        foot = (ax + t * dx, ay + t * dy)
    return foot, math.dist(point, foot)


class RoadNetwork:
    """A weighted graph of arterial roads with projection and shortest paths."""

    def __init__(self, spec: RoadSpec) -> None:
        self._adj: dict[Coord, list[tuple[Coord, float]]] = {}
        # Arterial pieces available for projection; splitting a piece when a
        # driveway attaches keeps this list in step with the graph.
        self._road_edges: list[tuple[Coord, Coord]] = []
        # Full-span arterials kept unsplit, purely for drawing.
        self._draw_segments: list[tuple[Coord, Coord]] = []
        self._build(spec)

    def _build(self, spec: RoadSpec) -> None:
        lo, hi = spec.bounds
        arterials = sorted(spec.arterials)
        # Nodes sit at the bounds and at every crossing along each arterial.
        stops = sorted({lo, *arterials, hi})
        for x in arterials:
            self._draw_segments.append(((x, lo), (x, hi)))
            for a, b in zip(stops, stops[1:]):
                self._add_road_edge((x, a), (x, b))
        for y in arterials:
            self._draw_segments.append(((lo, y), (hi, y)))
            for a, b in zip(stops, stops[1:]):
                self._add_road_edge((a, y), (b, y))
        self._intersections = [(x, y) for x in arterials for y in arterials]

    # --- graph construction ---------------------------------------------

    def _add_node(self, node: Coord) -> None:
        self._adj.setdefault(node, [])

    def _add_edge(self, a: Coord, b: Coord) -> None:
        weight = math.dist(a, b)
        self._add_node(a)
        self._add_node(b)
        self._adj[a].append((b, weight))
        self._adj[b].append((a, weight))

    def _add_road_edge(self, a: Coord, b: Coord) -> None:
        self._add_edge(a, b)
        self._road_edges.append((a, b))

    def _remove_road_edge(self, a: Coord, b: Coord) -> None:
        self._road_edges = [e for e in self._road_edges if e != (a, b)]
        self._adj[a] = [(n, w) for n, w in self._adj[a] if not _close(n, b)]
        self._adj[b] = [(n, w) for n, w in self._adj[b] if not _close(n, a)]

    # --- public geometry ------------------------------------------------

    def intersections(self) -> list[Coord]:
        """The arterial crossing points, for drawing."""
        return list(self._intersections)

    def segments(self) -> list[tuple[Coord, Coord]]:
        """Each full-span arterial as a single segment, for drawing."""
        return list(self._draw_segments)

    def attach(self, point: Coord) -> Coord:
        """Join ``point`` to the graph via a driveway to its nearest road.

        Projects ``point`` onto the closest road segment, splitting that segment
        at the projection unless it lands on an existing node, and links the two
        with a driveway edge. Returns the connector node the driveway meets.
        """
        best: tuple[float, int, Coord, tuple[Coord, Coord]] | None = None
        for order, (a, b) in enumerate(self._road_edges):
            foot, dist = _project(point, a, b)
            # `< best - eps` keeps the first road on ties, so results are stable.
            if best is None or dist < best[0] - _EPS:
                best = (dist, order, foot, (a, b))
        assert best is not None, "road network has no segments to attach to"
        _, _, foot, (a, b) = best
        connector = self._insert_connector(foot, a, b)
        self._add_node(point)
        if not _close(point, connector):
            self._add_edge(point, connector)
        return connector

    def _insert_connector(self, foot: Coord, a: Coord, b: Coord) -> Coord:
        # Reuse an endpoint when the projection lands on one (guards against a
        # zero-length split when a point projects onto an intersection).
        if _close(foot, a):
            return a
        if _close(foot, b):
            return b
        self._remove_road_edge(a, b)
        self._add_road_edge(a, foot)
        self._add_road_edge(foot, b)
        return foot

    def shortest_path(self, source: Coord, target: Coord) -> tuple[float, list[Coord]]:
        """Road distance and coordinate path from ``source`` to ``target``.

        Both endpoints must already be nodes (an intersection, an edge endpoint,
        or an attached point); a coordinate that was never attached raises
        ``KeyError``. Returns ``(distance, [coords])`` where the coords start at
        ``source`` and end at ``target``.
        """
        source = self._node_key(source)
        target = self._node_key(target)

        dist: dict[Coord, float] = {source: 0.0}
        prev: dict[Coord, Coord] = {}
        visited: set[Coord] = set()
        queue: list[tuple[float, Coord]] = [(0.0, source)]
        while queue:
            d, u = heapq.heappop(queue)
            if u in visited:
                continue
            visited.add(u)
            if u == target:
                break
            for v, w in self._adj[u]:
                nd = d + w
                if nd + _EPS < dist.get(v, math.inf):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(queue, (nd, v))

        if target not in visited:
            raise ValueError(f"no road path between {source} and {target}")
        path = [target]
        while path[-1] != source:
            path.append(prev[path[-1]])
        path.reverse()
        return dist[target], path

    def _node_key(self, coord: Coord) -> Coord:
        if coord in self._adj:
            return coord
        for node in self._adj:
            if _close(node, coord):
                return node
        raise KeyError(coord)
