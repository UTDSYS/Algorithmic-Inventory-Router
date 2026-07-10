import type { CostView, DayView } from '../api/types'

/** Sum the costs of the first `completed` days into a running total. */
export function cumulativeCost(days: DayView[], completed: number): CostView {
  const total: CostView = { travel: 0, holding: 0, stockout: 0, total: 0, reward: 0 }
  for (let i = 0; i < completed && i < days.length; i++) {
    const c = days[i].cost
    total.travel += c.travel
    total.holding += c.holding
    total.stockout += c.stockout
    total.total += c.total
    total.reward += c.reward
  }
  return total
}

/** Clamp a day index to [0, length]. `length` (one past the last day) is valid,
 * meaning the whole season has finished playing. */
export function clampDay(day: number, length: number): number {
  return Math.max(0, Math.min(length, day))
}
