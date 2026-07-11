import type { ActionView, RouteView, StopView } from '../api/types'

/** One empty route per truck, ids 0..numTrucks-1. */
export function emptyAction(numTrucks: number): ActionView {
  const routes: RouteView[] = []
  for (let truckId = 0; truckId < numTrucks; truckId++) {
    routes.push({ truck_id: truckId, stops: [] })
  }
  return { routes }
}

/** Return a copy of `action` with `fn` applied to one truck's stops. */
function mapRoute(
  action: ActionView,
  truckId: number,
  fn: (stops: StopView[]) => StopView[],
): ActionView {
  return {
    routes: action.routes.map((route) =>
      route.truck_id === truckId ? { ...route, stops: fn(route.stops) } : route,
    ),
  }
}

export function addStop(
  action: ActionView,
  truckId: number,
  storeId: number,
  quantity: number,
): ActionView {
  return mapRoute(action, truckId, (stops) => [...stops, { store_id: storeId, quantity }])
}

export function removeStop(action: ActionView, truckId: number, index: number): ActionView {
  return mapRoute(action, truckId, (stops) => stops.filter((_, i) => i !== index))
}

/** Swap the stop at `index` with its neighbour in `dir`; no-op at the ends. */
export function moveStop(
  action: ActionView,
  truckId: number,
  index: number,
  dir: -1 | 1,
): ActionView {
  return mapRoute(action, truckId, (stops) => {
    const target = index + dir
    if (target < 0 || target >= stops.length) return stops
    const next = stops.slice()
    ;[next[index], next[target]] = [next[target], next[index]]
    return next
  })
}

export function setQty(
  action: ActionView,
  truckId: number,
  index: number,
  quantity: number,
): ActionView {
  return mapRoute(action, truckId, (stops) =>
    stops.map((stop, i) => (i === index ? { ...stop, quantity } : stop)),
  )
}

/** Sum of a route's stop quantities. */
export function truckLoad(route: RouteView): number {
  return route.stops.reduce((sum, stop) => sum + stop.quantity, 0)
}

/**
 * Human-readable validation errors. Empty array means valid (including the
 * all-empty idle action). Flags trucks over `capacity` and stops with
 * quantity < 1.
 */
export function validateAction(action: ActionView, capacity: number): string[] {
  const errors: string[] = []
  for (const route of action.routes) {
    const load = truckLoad(route)
    if (load > capacity) {
      errors.push(`Truck ${route.truck_id} is over capacity (${load}/${capacity}).`)
    }
    for (const stop of route.stops) {
      if (stop.quantity < 1) {
        errors.push(`Truck ${route.truck_id} has a stop with quantity below 1.`)
      }
    }
  }
  return errors
}
