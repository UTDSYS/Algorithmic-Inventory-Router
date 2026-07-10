/** Format a cost value to one decimal place for the readout. */
export function formatCost(value: number): string {
  return value.toFixed(1)
}
