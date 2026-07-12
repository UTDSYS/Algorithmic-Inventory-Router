import { test, expect } from 'vitest'
import { contenderAt, raceHorizon, rankContenders } from './race'
import type { AgentEpisodeResponse, CostView, DayView, StateView } from '../api/types'

const cost = (t: number): CostView => ({ travel: t, holding: 0, stockout: 0, total: t, reward: -t })
const st = (day: number): StateView => ({ day } as unknown as StateView)
const dayRec = (i: number): DayView => ({
  day: i,
  action: { routes: [{ truck_id: 0, stops: [{ store_id: 0, quantity: 1 }], path: [] }] },
  cost: cost(1),
  state: st(i + 1),
})
const ep = (agent: string, n: number): AgentEpisodeResponse => ({
  agent, seed: 0, days: Array.from({ length: n }, (_, i) => dayRec(i)), total_cost: cost(n),
})

const base = st(0)

test('raceHorizon is the longest episode length', () => {
  expect(raceHorizon([ep('a', 3), ep('b', 5), ep('c', 4)])).toBe(5)
})

test('contenderAt at day 0 shows the base state and no cost', () => {
  const c = contenderAt('A', ep('a', 3), base, 0, 0, false)
  expect(c.displayState).toBe(base)
  expect(c.runningCost.total).toBe(0)
  expect(c.done).toBe(false)
  expect(c.activeRoutes).toHaveLength(0)
})

test("contenderAt mid-day exposes that day's routes and prior cumulative cost", () => {
  const c = contenderAt('A', ep('a', 3), base, 1, 0.5, true)
  expect(c.displayState?.day).toBe(1) // ending state of day 0
  expect(c.runningCost.total).toBe(1) // one completed day
  expect(c.activeRoutes).toHaveLength(1) // day 1 is animating
})

test('contenderAt past a short episode is done, no routes, full cost', () => {
  const c = contenderAt('A', ep('a', 3), base, 5, 0.5, true)
  expect(c.done).toBe(true)
  expect(c.activeRoutes).toHaveLength(0)
  expect(c.runningCost.total).toBe(3)
})

test('rankContenders orders cheapest first', () => {
  const a = contenderAt('A', ep('a', 3), base, 3, 0, false) // total 3
  const b = contenderAt('B', ep('b', 5), base, 5, 0, false) // total 5
  expect(rankContenders([b, a]).map((c) => c.label)).toEqual(['A', 'B'])
})
