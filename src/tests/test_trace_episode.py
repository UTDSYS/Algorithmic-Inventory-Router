"""Tests for agents.base.trace_episode (item 9 backend addition)."""

import pytest

from agents.base import DayRecord, EpisodeTrace, run_episode, trace_episode
from agents.greedy import GreedyAgent
from sim.config import default_scenario
from sim.environment import InventoryRoutingEnv
from sim.state import Action


def test_trace_has_one_record_per_day():
    scenario = default_scenario()
    trace = trace_episode(InventoryRoutingEnv(scenario), GreedyAgent())
    assert isinstance(trace, EpisodeTrace)
    assert len(trace.records) == scenario.horizon
    assert all(isinstance(r, DayRecord) for r in trace.records)


def test_trace_records_are_in_day_order():
    trace = trace_episode(InventoryRoutingEnv(default_scenario()), GreedyAgent())
    assert [r.day for r in trace.records] == list(range(default_scenario().horizon))


def test_trace_record_carries_action_cost_and_state_after():
    trace = trace_episode(InventoryRoutingEnv(default_scenario()), GreedyAgent())
    first = trace.records[0]
    assert isinstance(first.action, Action)
    # observation is the state AFTER the day was played
    assert first.observation.state.day == 1
    assert first.cost.total >= 0


def test_trace_total_matches_sum_of_daily():
    trace = trace_episode(InventoryRoutingEnv(default_scenario()), GreedyAgent())
    assert trace.total.total == pytest.approx(sum(r.cost.total for r in trace.records))


def test_trace_total_matches_run_episode():
    scenario = default_scenario()
    traced = trace_episode(InventoryRoutingEnv(scenario), GreedyAgent()).total
    plain = run_episode(InventoryRoutingEnv(scenario), GreedyAgent()).total
    assert traced.total == pytest.approx(plain.total)


def test_trace_respects_seed_override():
    scenario = default_scenario()
    a = trace_episode(InventoryRoutingEnv(scenario), GreedyAgent(), seed=1).total
    b = trace_episode(InventoryRoutingEnv(scenario), GreedyAgent(), seed=2).total
    assert a.total != b.total
