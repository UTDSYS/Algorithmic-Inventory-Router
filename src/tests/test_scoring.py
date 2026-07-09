"""Tests for sim.scoring: per-day cost breakdown and episode total (item 4)."""

import pytest

from sim.config import StoreConfig
from sim.scoring import CostBreakdown, episode_total, holding_cost, price_day, stockout_cost


def make_stores(specs):
    """specs: list of (holding_cost, stockout_penalty)."""
    return tuple(
        StoreConfig(
            store_id=i,
            location=(0.0, 0.0),
            max_capacity=40,
            initial_inventory=10,
            holding_cost=h,
            stockout_penalty=p,
            demand_mean=10.0,
            demand_spread=3.0,
        )
        for i, (h, p) in enumerate(specs)
    )


def test_cost_breakdown_total():
    cost = CostBreakdown(travel=10.0, holding=3.0, stockout=20.0)
    assert cost.total == 33.0


def test_cost_breakdown_reward_is_negative_total():
    cost = CostBreakdown(travel=10.0, holding=3.0, stockout=20.0)
    assert cost.reward == -33.0


def test_cost_breakdown_addition_sums_components():
    a = CostBreakdown(travel=1.0, holding=2.0, stockout=3.0)
    b = CostBreakdown(travel=10.0, holding=20.0, stockout=30.0)
    total = a + b
    assert (total.travel, total.holding, total.stockout) == (11.0, 22.0, 33.0)


def test_holding_cost_weights_by_store():
    stores = make_stores([(1.0, 20.0), (2.0, 20.0)])
    # store 0 has 5 left @1, store 1 has 3 left @2 -> 5 + 6 = 11
    assert holding_cost(stores, [5, 3]) == 11.0


def test_holding_cost_zero_when_no_inventory():
    stores = make_stores([(1.0, 20.0), (2.0, 20.0)])
    assert holding_cost(stores, [0, 0]) == 0.0


def test_stockout_cost_weights_by_store():
    stores = make_stores([(1.0, 20.0), (1.0, 5.0)])
    # store 0 short 2 @20, store 1 short 4 @5 -> 40 + 20 = 60
    assert stockout_cost(stores, [2, 4]) == 60.0


def test_stockout_cost_zero_when_no_shortfall():
    stores = make_stores([(1.0, 20.0), (1.0, 5.0)])
    assert stockout_cost(stores, [0, 0]) == 0.0


def test_price_day_assembles_breakdown():
    stores = make_stores([(1.0, 20.0), (2.0, 5.0)])
    cost = price_day(
        stores,
        ending_inventory=[5, 3],
        shortfall=[2, 0],
        travel=12.5,
    )
    assert cost.travel == 12.5
    assert cost.holding == 5 * 1.0 + 3 * 2.0  # 11
    assert cost.stockout == 2 * 20.0 + 0 * 5.0  # 40
    assert cost.total == pytest.approx(12.5 + 11 + 40)


def test_episode_total_sums_daily_breakdowns():
    days = [
        CostBreakdown(travel=1.0, holding=2.0, stockout=3.0),
        CostBreakdown(travel=10.0, holding=20.0, stockout=30.0),
        CostBreakdown(travel=100.0, holding=200.0, stockout=300.0),
    ]
    total = episode_total(days)
    assert total.travel == 111.0
    assert total.holding == 222.0
    assert total.stockout == 333.0
    assert total.total == 666.0


def test_episode_total_of_empty_is_zero():
    total = episode_total([])
    assert total.total == 0.0
