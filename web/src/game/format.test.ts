import { describe, expect, it } from 'vitest'
import { formatCost } from './format'

describe('formatCost', () => {
  it('formats to one decimal place', () => {
    expect(formatCost(412.37)).toBe('412.4')
    expect(formatCost(0)).toBe('0.0')
    expect(formatCost(64)).toBe('64.0')
  })
})
