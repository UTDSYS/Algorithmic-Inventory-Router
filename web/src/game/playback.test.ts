import { describe, expect, it, test } from 'vitest'
import type { CostView, DayView, StateView } from '../api/types'
import { buildHumanEpisode, clampDay, cumulativeCost } from './playback'

function day(travel: number, holding: number, stockout: number): DayView {
  return {
    day: 0,
    action: { routes: [] },
    cost: { travel, holding, stockout, total: travel + holding + stockout, reward: -(travel + holding + stockout) },
    state: {} as DayView['state'],
  }
}

const days = [day(1, 2, 3), day(10, 20, 30), day(100, 200, 300)]

describe('cumulativeCost', () => {
  it('is all zeros before any day completes', () => {
    expect(cumulativeCost(days, 0)).toMatchObject({ travel: 0, holding: 0, stockout: 0, total: 0 })
  })

  it('sums the first N completed days', () => {
    expect(cumulativeCost(days, 2)).toMatchObject({ travel: 11, holding: 22, stockout: 33, total: 66 })
  })

  it('sums the whole episode', () => {
    expect(cumulativeCost(days, 3)).toMatchObject({ total: 666, reward: -666 })
  })
})

describe('clampDay', () => {
  it('keeps the day within [0, length]', () => {
    expect(clampDay(-1, 3)).toBe(0)
    expect(clampDay(5, 3)).toBe(3)
    expect(clampDay(2, 3)).toBe(2)
  })
})

const humanCost = (total: number): CostView => ({
  travel: total, holding: 0, stockout: 0, total, reward: -total,
})
const humanState = { day: 1 } as unknown as StateView
const humanDay = (d: number): DayView => ({
  day: d, action: { routes: [] }, cost: humanCost(d + 1), state: humanState,
})

describe('buildHumanEpisode', () => {
  test('buildHumanEpisode returns null before the season is done', () => {
    expect(buildHumanEpisode([humanDay(0)], humanCost(1), false, 0)).toBeNull()
  })

  test('buildHumanEpisode returns null with no recorded days', () => {
    expect(buildHumanEpisode([], humanCost(0), true, 0)).toBeNull()
  })

  test('buildHumanEpisode wraps recorded days as the you-episode', () => {
    const ep = buildHumanEpisode([humanDay(0), humanDay(1)], humanCost(5), true, 7)
    expect(ep).not.toBeNull()
    expect(ep!.agent).toBe('you')
    expect(ep!.seed).toBe(7)
    expect(ep!.days).toHaveLength(2)
    expect(ep!.total_cost).toEqual(humanCost(5))
  })
})
