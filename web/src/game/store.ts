/**
 * Store ids are 0-indexed internally (matching the backend). For display we
 * present them one-indexed and human-readable so "Store 1" is the first store.
 */
export function storeName(storeId: number): string {
  return `Store ${storeId + 1}`
}

/** Compact one-indexed name for the map markers. */
export function storeShortName(storeId: number): string {
  return String(storeId + 1)
}
