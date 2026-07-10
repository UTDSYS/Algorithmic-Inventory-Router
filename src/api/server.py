"""FastAPI translation layer over the simulation.

A thin boundary: it stores games in memory, converts the sim's frozen dataclasses
to/from JSON via pydantic models, and exposes endpoints to start a game, submit a
day's action, read the state, and run a baseline agent on the same seed for the
scoreboard. All game logic stays in :mod:`sim`; this layer only translates.

See docs/PLAN.md.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.base import Agent, run_episode, trace_episode
from agents.greedy import GreedyAgent
from agents.nearest_neighbour import NearestNeighbourAgent
from sim.config import Scenario, default_scenario
from sim.environment import InventoryRoutingEnv, Observation
from sim.scoring import CostBreakdown
from sim.state import Action, Route, Stop

app = FastAPI(title="Inventory Routing Game")

# The Vite dev server runs on a different origin; allow it during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASELINE_AGENTS: dict[str, type[Agent]] = {
    "greedy": GreedyAgent,
    "nearest_neighbour": NearestNeighbourAgent,
}


@dataclass
class GameSession:
    env: InventoryRoutingEnv
    scenario: Scenario
    seed: int


GAMES: dict[str, GameSession] = {}


# --- request models ------------------------------------------------------


class NewGameRequest(BaseModel):
    seed: int | None = None


class StopRequest(BaseModel):
    store_id: int
    quantity: int


class RouteRequest(BaseModel):
    truck_id: int
    stops: list[StopRequest]


class ActionRequest(BaseModel):
    routes: list[RouteRequest]


class BaselineRequest(BaseModel):
    agent: str


# --- response models -----------------------------------------------------


class StoreView(BaseModel):
    store_id: int
    location: tuple[float, float]
    inventory: int
    max_capacity: int
    holding_cost: float
    stockout_penalty: float
    forecast: list[float]


class FleetView(BaseModel):
    num_trucks: int
    capacity: int


class StateView(BaseModel):
    day: int
    horizon: int
    done: bool
    depot_location: tuple[float, float]
    depot_inventory: int
    travel_cost_per_distance: float
    fleet: FleetView
    stores: list[StoreView]


class CostView(BaseModel):
    travel: float
    holding: float
    stockout: float
    total: float
    reward: float


class NewGameResponse(BaseModel):
    game_id: str
    seed: int
    state: StateView


class StepResponse(BaseModel):
    state: StateView
    reward: float
    done: bool
    cost: CostView
    total_cost: CostView


class BaselineResponse(BaseModel):
    agent: str
    cost: CostView


class StopView(BaseModel):
    store_id: int
    quantity: int


class RouteView(BaseModel):
    truck_id: int
    stops: list[StopView]


class ActionView(BaseModel):
    routes: list[RouteView]


class DayView(BaseModel):
    day: int
    action: ActionView
    cost: CostView
    state: StateView


class AgentEpisodeResponse(BaseModel):
    agent: str
    seed: int
    days: list[DayView]
    total_cost: CostView


# --- translation ---------------------------------------------------------


def _cost_view(cost: CostBreakdown) -> CostView:
    return CostView(
        travel=cost.travel,
        holding=cost.holding,
        stockout=cost.stockout,
        total=cost.total,
        reward=cost.reward,
    )


def _state_view(observation: Observation) -> StateView:
    scenario = observation.scenario
    state = observation.state
    forecasts = state.forecasts
    stores = [
        StoreView(
            store_id=cfg.store_id,
            location=cfg.location,
            inventory=state.stores[i].inventory,
            max_capacity=cfg.max_capacity,
            holding_cost=cfg.holding_cost,
            stockout_penalty=cfg.stockout_penalty,
            forecast=list(forecasts[i]) if i < len(forecasts) else [],
        )
        for i, cfg in enumerate(scenario.stores)
    ]
    return StateView(
        day=state.day,
        horizon=scenario.horizon,
        done=state.day >= scenario.horizon,
        depot_location=scenario.depot_location,
        depot_inventory=state.depot_inventory,
        travel_cost_per_distance=scenario.travel_cost_per_distance,
        fleet=FleetView(
            num_trucks=scenario.fleet.num_trucks, capacity=scenario.fleet.capacity
        ),
        stores=stores,
    )


def _action_view(action: Action) -> ActionView:
    return ActionView(
        routes=[
            RouteView(
                truck_id=route.truck_id,
                stops=[StopView(store_id=s.store_id, quantity=s.quantity) for s in route.stops],
            )
            for route in action.routes
        ]
    )


def _to_action(request: ActionRequest) -> Action:
    return Action(
        routes=tuple(
            Route(
                truck_id=route.truck_id,
                stops=tuple(Stop(s.store_id, s.quantity) for s in route.stops),
            )
            for route in request.routes
        )
    )


def _get_session(game_id: str) -> GameSession:
    session = GAMES.get(game_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"unknown game {game_id}")
    return session


# --- endpoints -----------------------------------------------------------


@app.post("/games", response_model=NewGameResponse)
def create_game(request: NewGameRequest | None = None) -> NewGameResponse:
    scenario = default_scenario()
    seed = scenario.seed if request is None or request.seed is None else request.seed
    env = InventoryRoutingEnv(scenario)
    observation = env.reset(seed=seed)
    game_id = uuid.uuid4().hex
    GAMES[game_id] = GameSession(env=env, scenario=scenario, seed=seed)
    return NewGameResponse(game_id=game_id, seed=seed, state=_state_view(observation))


@app.get("/games/{game_id}", response_model=StateView)
def get_state(game_id: str) -> StateView:
    session = _get_session(game_id)
    return _state_view(session.env.current_observation())


@app.post("/games/{game_id}/step", response_model=StepResponse)
def step_game(game_id: str, request: ActionRequest) -> StepResponse:
    session = _get_session(game_id)
    try:
        result = session.env.step(_to_action(request))
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StepResponse(
        state=_state_view(result.observation),
        reward=result.reward,
        done=result.done,
        cost=_cost_view(result.info["cost"]),
        total_cost=_cost_view(session.env.total_cost),
    )


@app.post("/games/{game_id}/baseline", response_model=BaselineResponse)
def run_baseline(game_id: str, request: BaselineRequest) -> BaselineResponse:
    session = _get_session(game_id)
    agent_cls = BASELINE_AGENTS.get(request.agent)
    if agent_cls is None:
        raise HTTPException(status_code=400, detail=f"unknown agent {request.agent}")
    result = run_episode(
        InventoryRoutingEnv(session.scenario), agent_cls(), seed=session.seed
    )
    return BaselineResponse(agent=request.agent, cost=_cost_view(result.total))


@app.post("/games/{game_id}/agent_episode", response_model=AgentEpisodeResponse)
def run_agent_episode(game_id: str, request: BaselineRequest) -> AgentEpisodeResponse:
    session = _get_session(game_id)
    agent_cls = BASELINE_AGENTS.get(request.agent)
    if agent_cls is None:
        raise HTTPException(status_code=400, detail=f"unknown agent {request.agent}")
    trace = trace_episode(
        InventoryRoutingEnv(session.scenario), agent_cls(), seed=session.seed
    )
    return AgentEpisodeResponse(
        agent=request.agent,
        seed=session.seed,
        days=[
            DayView(
                day=record.day,
                action=_action_view(record.action),
                cost=_cost_view(record.cost),
                state=_state_view(record.observation),
            )
            for record in trace.records
        ],
        total_cost=_cost_view(trace.total),
    )
