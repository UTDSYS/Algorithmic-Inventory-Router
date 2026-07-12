import type { AgentEpisodeResponse, CostView, DayView } from '../api/types'

/** Base time to animate one day at 1x, in ms. Shared by watch and play. */
export const DAY_MS = 3500

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

/**
 * Wrap the human's recorded days into an episode shaped exactly like an agent
 * run, so replay and the race can consume it unchanged. Returns null until the
 * season is finished. `seed` is cosmetic (the UI never reads it).
 */
export function buildHumanEpisode(
  days: DayView[],
  total: CostView,
  done: boolean,
  seed: number,
): AgentEpisodeResponse | null {
  if (!done || days.length === 0) return null
  return { agent: 'you', seed, days, total_cost: total }
}
