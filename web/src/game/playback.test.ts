import { describe, expect, it } from 'vitest'
import type { DayView } from '../api/types'
import { clampDay, cumulativeCost } from './playback'

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
