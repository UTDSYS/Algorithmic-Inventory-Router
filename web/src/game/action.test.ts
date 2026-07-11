import { describe, expect, it } from 'vitest'
import type { ActionView } from '../api/types'
import {
  addStop,
  emptyAction,
  moveStop,
  removeStop,
  setQty,
  truckLoad,
  validateAction,
} from './action'

describe('emptyAction', () => {
  it('creates one empty route per truck, ids 0..n-1', () => {
    expect(emptyAction(2)).toEqual({
      routes: [
        { truck_id: 0, stops: [] },
        { truck_id: 1, stops: [] },
      ],
    })
  })

  it('creates no routes for zero trucks', () => {
    expect(emptyAction(0)).toEqual({ routes: [] })
  })
})

describe('editing helpers are immutable', () => {
  const base: ActionView = emptyAction(2)

  it('addStop appends a stop to the named truck only', () => {
    const next = addStop(base, 1, 3, 5)
    expect(next.routes[1].stops).toEqual([{ store_id: 3, quantity: 5 }])
    expect(next.routes[0].stops).toEqual([])
    // original untouched
    expect(base.routes[1].stops).toEqual([])
    expect(next).not.toBe(base)
  })

  it('removeStop drops the stop at index', () => {
    const two = addStop(addStop(base, 0, 1, 2), 0, 4, 6)
    const next = removeStop(two, 0, 0)
    expect(next.routes[0].stops).toEqual([{ store_id: 4, quantity: 6 }])
    expect(two.routes[0].stops).toHaveLength(2) // original untouched
  })

  it('setQty updates only the targeted stop', () => {
    const one = addStop(base, 0, 1, 2)
    const next = setQty(one, 0, 0, 9)
    expect(next.routes[0].stops[0]).toEqual({ store_id: 1, quantity: 9 })
    expect(one.routes[0].stops[0].quantity).toBe(2) // original untouched
  })
})

describe('moveStop', () => {
  const two = addStop(addStop(emptyAction(1), 0, 1, 2), 0, 4, 6)

  it('swaps a stop with its neighbour', () => {
    const up = moveStop(two, 0, 1, -1)
    expect(up.routes[0].stops.map((s) => s.store_id)).toEqual([4, 1])
  })

  it('is a no-op past the top', () => {
    const up = moveStop(two, 0, 0, -1)
    expect(up.routes[0].stops.map((s) => s.store_id)).toEqual([1, 4])
  })

  it('is a no-op past the bottom', () => {
    const down = moveStop(two, 0, 1, 1)
    expect(down.routes[0].stops.map((s) => s.store_id)).toEqual([1, 4])
  })
})

describe('truckLoad', () => {
  it('sums stop quantities', () => {
    expect(truckLoad({ truck_id: 0, stops: [{ store_id: 1, quantity: 3 }, { store_id: 2, quantity: 4 }] })).toBe(7)
    expect(truckLoad({ truck_id: 0, stops: [] })).toBe(0)
  })
})

describe('validateAction', () => {
  it('accepts an all-empty idle action', () => {
    expect(validateAction(emptyAction(2), 10)).toEqual([])
  })

  it('accepts a within-capacity action', () => {
    const a = addStop(addStop(emptyAction(1), 0, 1, 4), 0, 2, 6)
    expect(validateAction(a, 10)).toEqual([])
  })

  it('flags an over-capacity truck', () => {
    const a = addStop(emptyAction(1), 0, 1, 11)
    expect(validateAction(a, 10)).toHaveLength(1)
    expect(validateAction(a, 10)[0]).toMatch(/capacity/i)
  })

  it('flags a stop with quantity below 1', () => {
    const a = addStop(emptyAction(1), 0, 1, 0)
    const errors = validateAction(a, 10)
    expect(errors.some((e) => /quantity/i.test(e))).toBe(true)
  })
})
