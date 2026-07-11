"""Tests for api.server: the FastAPI translation layer (item 8)."""

import pytest
from fastapi.testclient import TestClient

from agents.base import run_episode, trace_episode
from agents.greedy import GreedyAgent
from agents.nearest_neighbour import NearestNeighbourAgent
from api.server import app
from sim.config import default_scenario
from sim.environment import InventoryRoutingEnv
from sim.geometry import DistanceMatrix, travel_cost
from sim.state import Action, Route, Stop

client = TestClient(app)


def new_game(seed=None):
    body = {} if seed is None else {"seed": seed}
    response = client.post("/games", json=body)
    assert response.status_code == 200
    return response.json()


def deliver_nothing():
    return {"routes": []}


# --- new game / state ----------------------------------------------------


def test_new_game_returns_id_and_initial_state():
    data = new_game()
    assert "game_id" in data
    state = data["state"]
    assert state["day"] == 0
    assert state["done"] is False
    assert len(state["stores"]) == default_scenario().num_stores
    assert state["horizon"] == default_scenario().horizon
    # each store exposes what the UI renders
    store = state["stores"][0]
    assert {"store_id", "location", "inventory", "max_capacity", "forecast"} <= store.keys()
    assert len(store["forecast"]) > 0


def test_get_state_returns_current_state():
    game_id = new_game()["game_id"]
    response = client.get(f"/games/{game_id}")
    assert response.status_code == 200
    assert response.json()["day"] == 0


def test_get_unknown_game_returns_404():
    assert client.get("/games/does-not-exist").status_code == 404


# --- stepping ------------------------------------------------------------


def test_step_advances_day_and_returns_cost():
    game_id = new_game()["game_id"]
    response = client.post(f"/games/{game_id}/step", json=deliver_nothing())
    assert response.status_code == 200
    body = response.json()
    assert body["state"]["day"] == 1
    assert body["done"] is False
    assert body["reward"] == pytest.approx(-body["cost"]["total"])
    assert {"travel", "holding", "stockout", "total"} <= body["cost"].keys()


def test_full_episode_reaches_done():
    game_id = new_game()["game_id"]
    horizon = default_scenario().horizon
    body = None
    for _ in range(horizon):
        body = client.post(f"/games/{game_id}/step", json=deliver_nothing()).json()
    assert body["done"] is True
    assert body["state"]["day"] == horizon


def test_step_after_done_returns_400():
    game_id = new_game()["game_id"]
    horizon = default_scenario().horizon
    for _ in range(horizon):
        client.post(f"/games/{game_id}/step", json=deliver_nothing())
    late = client.post(f"/games/{game_id}/step", json=deliver_nothing())
    assert late.status_code == 400


def test_invalid_action_returns_400():
    game_id = new_game()["game_id"]
    # truck load far exceeds capacity 50
    action = {"routes": [{"truck_id": 0, "stops": [{"store_id": 0, "quantity": 9999}]}]}
    assert client.post(f"/games/{game_id}/step", json=action).status_code == 400


def test_step_on_unknown_game_returns_404():
    assert client.post("/games/nope/step", json=deliver_nothing()).status_code == 404


# --- backend is the source of truth --------------------------------------


def test_api_deliver_nothing_matches_no_ui_run():
    game_id = new_game()["game_id"]
    horizon = default_scenario().horizon
    body = None
    for _ in range(horizon):
        body = client.post(f"/games/{game_id}/step", json=deliver_nothing()).json()
    api_total = body["total_cost"]["total"]

    env = InventoryRoutingEnv(default_scenario())
    env.reset()
    done = False
    while not done:
        done = env.step(Action(routes=())).done

    assert api_total == pytest.approx(env.total_cost.total)


def test_hand_built_route_travel_matches_geometry():
    game_id = new_game()["game_id"]
    action = {
        "routes": [{"truck_id": 0, "stops": [{"store_id": 0, "quantity": 10},
                                             {"store_id": 3, "quantity": 5}]}]
    }
    body = client.post(f"/games/{game_id}/step", json=action).json()

    scenario = default_scenario()
    matrix = DistanceMatrix.from_scenario(scenario)
    expected = travel_cost(
        matrix,
        Action(routes=(Route(0, (Stop(0, 10), Stop(3, 5))),)),
        scenario.travel_cost_per_distance,
    )
    assert body["cost"]["travel"] == pytest.approx(expected)


# --- baselines -----------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "agent_factory"),
    [("greedy", GreedyAgent), ("nearest_neighbour", NearestNeighbourAgent)],
)
def test_baseline_matches_no_ui_run(name, agent_factory):
    game = new_game()
    game_id = game["game_id"]
    response = client.post(f"/games/{game_id}/baseline", json={"agent": name})
    assert response.status_code == 200
    api_cost = response.json()["cost"]["total"]

    expected = run_episode(
        InventoryRoutingEnv(default_scenario()), agent_factory(), seed=game["seed"]
    ).total.total
    assert api_cost == pytest.approx(expected)


def test_unknown_baseline_agent_returns_400():
    game_id = new_game()["game_id"]
    response = client.post(f"/games/{game_id}/baseline", json={"agent": "wizard"})
    assert response.status_code == 400


# --- agent episode (trace for playback) ----------------------------------


def test_agent_episode_returns_one_day_per_horizon():
    game_id = new_game()["game_id"]
    response = client.post(f"/games/{game_id}/agent_episode", json={"agent": "greedy"})
    assert response.status_code == 200
    body = response.json()
    assert body["agent"] == "greedy"
    assert len(body["days"]) == default_scenario().horizon
    day0 = body["days"][0]
    assert day0["day"] == 0
    assert "routes" in day0["action"]
    assert {"travel", "holding", "stockout", "total"} <= day0["cost"].keys()
    assert day0["state"]["day"] == 1  # state after the day


def test_agent_episode_total_matches_no_ui_trace():
    game = new_game()
    game_id = game["game_id"]
    body = client.post(
        f"/games/{game_id}/agent_episode", json={"agent": "nearest_neighbour"}
    ).json()
    expected = trace_episode(
        InventoryRoutingEnv(default_scenario()),
        NearestNeighbourAgent(),
        seed=game["seed"],
    ).total.total
    assert body["total_cost"]["total"] == pytest.approx(expected)


def test_agent_episode_actions_match_no_ui_trace():
    game = new_game()
    game_id = game["game_id"]
    body = client.post(
        f"/games/{game_id}/agent_episode", json={"agent": "greedy"}
    ).json()
    trace = trace_episode(
        InventoryRoutingEnv(default_scenario()), GreedyAgent(), seed=game["seed"]
    )
    # first day's routes should match the no-UI trace exactly
    api_day0 = body["days"][0]["action"]["routes"]
    ref_day0 = trace.records[0].action.routes
    assert len(api_day0) == len(ref_day0)
    for api_route, ref_route in zip(api_day0, ref_day0):
        assert api_route["truck_id"] == ref_route.truck_id
        api_stops = [(s["store_id"], s["quantity"]) for s in api_route["stops"]]
        ref_stops = [(s.store_id, s.quantity) for s in ref_route.stops]
        assert api_stops == ref_stops


def test_agent_episode_unknown_agent_returns_400():
    game_id = new_game()["game_id"]
    response = client.post(
        f"/games/{game_id}/agent_episode", json={"agent": "wizard"}
    )
    assert response.status_code == 400


# --- road geometry (item 10) ---------------------------------------------


def test_state_exposes_static_road_geometry():
    state = new_game()["state"]
    # default scenario has arterials at 25/50/75: 6 segments, 9 intersections
    assert len(state["road_segments"]) == 6
    assert len(state["intersections"]) == 9
    # each segment is a pair of [x, y] coordinates
    seg = state["road_segments"][0]
    assert len(seg) == 2 and len(seg[0]) == 2


def test_agent_episode_routes_carry_road_path():
    game_id = new_game()["game_id"]
    body = client.post(
        f"/games/{game_id}/agent_episode", json={"agent": "nearest_neighbour"}
    ).json()
    # find a day whose first route actually visits a store
    served = next(
        route
        for day in body["days"]
        for route in day["action"]["routes"]
        if route["stops"]
    )
    path = served["path"]
    assert len(path) >= 2
    depot = default_scenario().depot_location
    # a non-empty tour is a closed loop starting and ending at the depot
    assert tuple(path[0]) == depot
    assert tuple(path[-1]) == depot


def test_agent_episode_empty_route_has_empty_path():
    game_id = new_game()["game_id"]
    body = client.post(
        f"/games/{game_id}/agent_episode", json={"agent": "greedy"}
    ).json()
    for day in body["days"]:
        for route in day["action"]["routes"]:
            if not route["stops"]:
                assert route["path"] == []


def test_seed_override_changes_demand():
    a = new_game(seed=1)
    b = new_game(seed=2)
    fa = a["state"]["stores"][0]["forecast"]
    fb = b["state"]["stores"][0]["forecast"]
    assert fa != fb
