import { describe, expect, it } from 'vitest'
import { pointAlongPath } from './path'

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
