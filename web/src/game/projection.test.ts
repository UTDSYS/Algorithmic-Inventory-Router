import { describe, expect, it } from 'vitest'
import { projectPoint } from './projection'

const view = { viewWidth: 100, viewHeight: 100, padding: 0, worldWidth: 100, worldHeight: 100 }

describe('projectPoint', () => {
  it('maps world origin to bottom-left of the view (y flipped)', () => {
    expect(projectPoint(0, 0, view)).toEqual({ x: 0, y: 100 })
  })

  it('maps world top-right to view top-right', () => {
    expect(projectPoint(100, 100, view)).toEqual({ x: 100, y: 0 })
  })

  it('maps the centre to the centre', () => {
    expect(projectPoint(50, 50, view)).toEqual({ x: 50, y: 50 })
  })

  it('insets by padding', () => {
    const padded = { ...view, padding: 10 }
    // world 0 -> padding, world 100 -> viewWidth - padding
    expect(projectPoint(0, 100, padded)).toEqual({ x: 10, y: 10 })
    expect(projectPoint(100, 0, padded)).toEqual({ x: 90, y: 90 })
  })
})
