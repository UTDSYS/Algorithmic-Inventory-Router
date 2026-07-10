import { describe, expect, it } from 'vitest'
import { inventoryHealth } from './health'

describe('inventoryHealth', () => {
  it('is critical when nearly empty', () => {
    expect(inventoryHealth(0, 40).level).toBe('critical')
    expect(inventoryHealth(9, 40).level).toBe('critical') // 0.225
  })

  it('is low between a quarter and a half full', () => {
    expect(inventoryHealth(10, 40).level).toBe('low') // 0.25
    expect(inventoryHealth(19, 40).level).toBe('low') // 0.475
  })

  it('is ok at half full or more', () => {
    expect(inventoryHealth(20, 40).level).toBe('ok') // 0.5
    expect(inventoryHealth(40, 40).level).toBe('ok')
  })

  it('exposes a color for each level', () => {
    expect(inventoryHealth(0, 40).color).toMatch(/^#/)
  })

  it('exposes a human-readable label for each level', () => {
    expect(inventoryHealth(0, 40).label).toBe('Critical')
    expect(inventoryHealth(12, 40).label).toBe('Low')
    expect(inventoryHealth(30, 40).label).toBe('Stocked')
  })

  it('treats zero capacity as ok rather than dividing by zero', () => {
    expect(inventoryHealth(0, 0).level).toBe('ok')
  })
})
