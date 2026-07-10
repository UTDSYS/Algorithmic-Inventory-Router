import { describe, expect, it } from 'vitest'
import { storeName, storeShortName } from './store'

describe('storeName', () => {
  it('presents store ids one-indexed and human-readable', () => {
    expect(storeName(0)).toBe('Store 1')
    expect(storeName(7)).toBe('Store 8')
  })

  it('has a short form for the map', () => {
    expect(storeShortName(0)).toBe('1')
    expect(storeShortName(7)).toBe('8')
  })
})
