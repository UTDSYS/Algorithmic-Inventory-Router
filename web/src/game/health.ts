export type HealthLevel = 'critical' | 'low' | 'ok'

export interface Health {
  level: HealthLevel
  color: string
  label: string
}

const COLORS: Record<HealthLevel, string> = {
  critical: '#bf000f', // utdsys red
  low: '#d9822b', // amber
  ok: '#2e9e5b', // green
}

const LABELS: Record<HealthLevel, string> = {
  critical: 'Critical',
  low: 'Low',
  ok: 'Stocked',
}

/**
 * Classify a store's stock level by how full it is. Empty capacity is treated
 * as healthy (nothing to run out of) rather than dividing by zero.
 */
export function inventoryHealth(inventory: number, capacity: number): Health {
  const ratio = capacity > 0 ? inventory / capacity : 1
  const level: HealthLevel = ratio < 0.25 ? 'critical' : ratio < 0.5 ? 'low' : 'ok'
  return { level, color: COLORS[level], label: LABELS[level] }
}
