"""agents/rolling_horizon -- the temporal, adaptive baseline.

Looks ahead over the forecast horizon and solves a small mixed-integer program
that chooses per-day integer deliveries minimising holding + stockout + a fixed
per-visit charge, under store and fleet capacity, then executes only today's
deliveries and re-plans on the next call (the env invokes ``act`` fresh each
day). Routing of today's chosen quantities into truck tours reuses the shared
nearest-neighbour construction in :mod:`agents.routing`; the actual travel is
still priced by that router, not the MILP. The per-visit charge (``visit_cost``)
is a cheap stand-in for that travel so the program batches deliveries into fewer
trips instead of dribbling stock out just-in-time (see docs/PLAN.md step 11).
"""

from __future__ import annotations

import contextlib
import ctypes
import ctypes.util
import os
import sys
from typing import Iterator, Sequence

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from agents.base import Agent
from agents.routing import build_routes
from sim.demand import DEFAULT_FORECAST_HORIZON
from sim.environment import Observation
from sim.state import Action

_libc = ctypes.CDLL(ctypes.util.find_library("c"))

# Fixed charge per (store, day) the plan touches. Stands in for the travel the
# MILP does not model; tuned so the agent batches deliveries and beats the
# nearest-neighbour heuristic on the default scenario (see the sweep in the
# design notes). ``0.0`` recovers the old just-in-time behaviour.
DEFAULT_VISIT_COST = 30.0


@contextlib.contextmanager
def _silence_c_stdout() -> Iterator[None]:
    """Discard writes to the process's stdout file descriptor for the duration.

    The bundled HiGHS MIP solver prints a stray debug line to the C-level stdout
    on some instances -- buffered and flushed only at process exit, so Python
    stream redirection cannot catch it. We point fd 1 at ``os.devnull`` and force
    the C stdio flush (``std::cout`` is synced to it) before restoring, so the
    solver's noise never reaches real stdout (e.g. the API server's logs)."""
    sys.stdout.flush()
    _libc.fflush(None)
    saved_fd = os.dup(1)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull_fd, 1)
    try:
        yield
    finally:
        _libc.fflush(None)
        os.dup2(saved_fd, 1)
        os.close(saved_fd)
        os.close(devnull_fd)


def plan_deliveries(
    inventory: Sequence[int],
    forecasts: Sequence[Sequence[float]],
    max_capacity: Sequence[int],
    holding: Sequence[float],
    stockout: Sequence[float],
    fleet_capacity_per_day: int,
    horizon: int,
    visit_cost: float = 0.0,
) -> list[int]:
    """Today's delivery quantity per store, from a horizon MILP.

    ``forecasts[i]`` is store ``i``'s demand estimate for the next few days. The
    planning horizon ``T`` is the smaller of ``horizon`` and the shortest
    forecast row; with no forecast (``T == 0``) nothing is delivered. Only the
    first planned day is returned -- the agent re-plans each day.

    Variables per (store i, day t): integer delivery ``x[i,t] >= 0``, continuous
    leftover ``h[i,t] >= 0`` (holding base), continuous shortfall ``u[i,t] >= 0``
    (stockout base), and binary visit indicator ``z[i,t] in {0,1}``. Inventory
    carried into day t is ``inv[i,0]`` for t == 0 and ``h[i,t-1]`` afterwards, so
    no separate inventory variable is needed.

    ``visit_cost`` is a fixed charge added to the objective for every store the
    plan touches on a day (``z[i,t] == 1``). It stands in for the travel the MILP
    itself does not model: with ``visit_cost == 0`` the plan delivers just-in-time
    (holding-minimal), and a positive charge makes it batch demand into fewer,
    larger deliveries to avoid paying to visit the same store day after day."""
    n = len(inventory)
    if n == 0:
        return []
    t_horizon = min(horizon, min((len(row) for row in forecasts), default=0))
    if t_horizon <= 0:
        return [0] * n
    T = t_horizon
    nvar = 4 * n * T

    def xi(i: int, t: int) -> int:
        return i * T + t

    def hi(i: int, t: int) -> int:
        return n * T + i * T + t

    def ui(i: int, t: int) -> int:
        return 2 * n * T + i * T + t

    def zi(i: int, t: int) -> int:
        return 3 * n * T + i * T + t

    # Objective: holding on leftover, stockout on shortfall, visit_cost on every
    # touched (store, day); the delivered quantity itself is free.
    c = np.zeros(nvar)
    for i in range(n):
        for t in range(T):
            c[hi(i, t)] = holding[i]
            c[ui(i, t)] = stockout[i]
            c[zi(i, t)] = visit_cost

    # Balance (equality): h - u = inv_prev + x - d, with inv_prev = inv0 or h[t-1].
    a_eq = np.zeros((n * T, nvar))
    b_eq = np.zeros(n * T)
    row = 0
    for i in range(n):
        for t in range(T):
            a_eq[row, hi(i, t)] = 1.0
            a_eq[row, ui(i, t)] = -1.0
            a_eq[row, xi(i, t)] = -1.0
            if t == 0:
                b_eq[row] = inventory[i] - forecasts[i][0]
            else:
                a_eq[row, hi(i, t - 1)] = -1.0
                b_eq[row] = -forecasts[i][t]
            row += 1

    # Inequalities: store capacity (inv_prev + x <= cap) then fleet capacity/day.
    ub_rows: list[np.ndarray] = []
    ub_vals: list[float] = []
    for i in range(n):
        for t in range(T):
            r = np.zeros(nvar)
            r[xi(i, t)] = 1.0
            if t == 0:
                ub_vals.append(float(max_capacity[i] - inventory[i]))
            else:
                r[hi(i, t - 1)] = 1.0
                ub_vals.append(float(max_capacity[i]))
            ub_rows.append(r)
    for t in range(T):
        r = np.zeros(nvar)
        for i in range(n):
            r[xi(i, t)] = 1.0
        ub_rows.append(r)
        ub_vals.append(float(fleet_capacity_per_day))
    # Link delivery to its visit indicator: x[i,t] <= cap_i * z[i,t], so any
    # positive delivery forces z[i,t] = 1 and thus pays visit_cost once.
    for i in range(n):
        for t in range(T):
            r = np.zeros(nvar)
            r[xi(i, t)] = 1.0
            r[zi(i, t)] = -float(max_capacity[i])
            ub_rows.append(r)
            ub_vals.append(0.0)
    a_ub = np.vstack(ub_rows)
    b_ub = np.array(ub_vals)

    integrality = np.zeros(nvar)
    for i in range(n):
        for t in range(T):
            integrality[xi(i, t)] = 1  # deliveries are integer
            integrality[zi(i, t)] = 1  # visit indicators are binary

    ub = np.full(nvar, np.inf)
    for i in range(n):
        for t in range(T):
            ub[zi(i, t)] = 1.0  # z is a 0/1 indicator

    constraints = [
        LinearConstraint(a_eq, b_eq, b_eq),
        LinearConstraint(a_ub, -np.inf, b_ub),
    ]
    with _silence_c_stdout():
        res = milp(
            c=c,
            constraints=constraints,
            integrality=integrality,
            bounds=Bounds(lb=0, ub=ub),
        )
    if not res.success or res.x is None:
        return [0] * n
    return [int(round(res.x[xi(i, 0)])) for i in range(n)]


class RollingHorizonAgent(Agent):
    """Plan the forecast horizon with a MILP; deliver today; re-plan tomorrow."""

    def __init__(
        self,
        horizon: int = DEFAULT_FORECAST_HORIZON,
        visit_cost: float = DEFAULT_VISIT_COST,
    ) -> None:
        self.horizon = horizon
        self.visit_cost = visit_cost

    def act(self, observation: Observation) -> Action:
        scenario = observation.scenario
        stores = scenario.stores
        state = observation.state
        quantities = plan_deliveries(
            inventory=[s.inventory for s in state.stores],
            forecasts=[list(row) for row in state.forecasts],
            max_capacity=[s.max_capacity for s in stores],
            holding=[s.holding_cost for s in stores],
            stockout=[s.stockout_penalty for s in stores],
            fleet_capacity_per_day=(
                scenario.fleet.num_trucks * scenario.fleet.capacity
            ),
            horizon=self.horizon,
            visit_cost=self.visit_cost,
        )
        want = {
            stores[i].store_id: qty
            for i, qty in enumerate(quantities)
            if qty > 0
        }
        return Action(
            routes=build_routes(want, scenario.fleet, observation.distances)
        )
