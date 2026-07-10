import { describe, expect, it } from 'vitest'
import { pointAlongPath, headingAlongPath } from './path'

const L = [
  { x: 0, y: 0 },
  { x: 10, y: 0 },
  { x: 10, y: 10 },
]

describe('pointAlongPath', () => {
  it('returns the start at t=0', () => {
    expect(pointAlongPath(L, 0)).toEqual({ x: 0, y: 0 })
  })

  it('returns the end at t=1', () => {
    expect(pointAlongPath(L, 1)).toEqual({ x: 10, y: 10 })
  })

  it('interpolates by arc length across segments', () => {
    // total length 20; t=0.5 -> length 10 -> exactly the middle vertex
    expect(pointAlongPath(L, 0.5)).toEqual({ x: 10, y: 0 })
    // t=0.25 -> length 5 -> halfway along the first segment
    expect(pointAlongPath(L, 0.25)).toEqual({ x: 5, y: 0 })
    // t=0.75 -> length 15 -> halfway up the second segment
    expect(pointAlongPath(L, 0.75)).toEqual({ x: 10, y: 5 })
  })

  it('clamps t outside [0,1]', () => {
    expect(pointAlongPath(L, -1)).toEqual({ x: 0, y: 0 })
    expect(pointAlongPath(L, 2)).toEqual({ x: 10, y: 10 })
  })

  it('returns the single point for a one-point path', () => {
    expect(pointAlongPath([{ x: 3, y: 4 }], 0.5)).toEqual({ x: 3, y: 4 })
  })
})

describe('headingAlongPath', () => {
  it('is 0 along a horizontal (left-to-right) segment', () => {
    expect(headingAlongPath([{ x: 0, y: 0 }, { x: 10, y: 0 }], 0.5)).toBeCloseTo(0)
  })

  it('is +PI/2 along a downward segment (SVG y grows down)', () => {
    expect(headingAlongPath([{ x: 0, y: 0 }, { x: 0, y: 10 }], 0.5)).toBeCloseTo(Math.PI / 2)
  })

  it('is +PI/4 along a down-right diagonal', () => {
    expect(headingAlongPath([{ x: 0, y: 0 }, { x: 10, y: 10 }], 0.5)).toBeCloseTo(Math.PI / 4)
  })

  it('reflects the segment the position falls in (L path)', () => {
    // L: (0,0)->(10,0)->(10,10), total 20. t=0.75 -> length 15 -> on 2nd (downward) segment
    expect(headingAlongPath(L, 0.75)).toBeCloseTo(Math.PI / 2)
    // t=0.25 -> length 5 -> on 1st (horizontal) segment
    expect(headingAlongPath(L, 0.25)).toBeCloseTo(0)
  })

  it('clamps t outside [0,1]', () => {
    expect(headingAlongPath(L, -1)).toBeCloseTo(0) // first segment horizontal
    expect(headingAlongPath(L, 2)).toBeCloseTo(Math.PI / 2) // last segment downward
  })

  it('returns 0 for degenerate paths', () => {
    expect(headingAlongPath([{ x: 3, y: 4 }], 0.5)).toBe(0)
    expect(headingAlongPath([], 0.5)).toBe(0)
    expect(headingAlongPath([{ x: 1, y: 1 }, { x: 1, y: 1 }], 0.5)).toBe(0)
  })
})
