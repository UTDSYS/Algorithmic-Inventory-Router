import type { RouteView, StateView } from '../api/types'
import { inventoryHealth } from '../game/health'
import { pointAlongPath } from '../game/path'
import { projectPoint, type Point, type ProjectionOptions } from '../game/projection'
import { storeName, storeShortName } from '../game/store'

const VIEW = 600
const OPTS: ProjectionOptions = {
  worldWidth: 100,
  worldHeight: 100,
  viewWidth: VIEW,
  viewHeight: VIEW,
  padding: 56,
}
const TRUCK_COLORS = ['#2d5bff', '#0e1830', '#8324c9']

interface Props {
  state: StateView
  routes: RouteView[]
  progress: number
}

export function MapView({ state, routes, progress }: Props) {
  const depot = projectPoint(state.depot_location[0], state.depot_location[1], OPTS)
  const locations = new Map<number, Point>()
  for (const store of state.stores) {
    locations.set(store.store_id, projectPoint(store.location[0], store.location[1], OPTS))
  }

  const routePaths = routes.map((route) => {
    const points: Point[] = [
      depot,
      ...route.stops.map((s) => locations.get(s.store_id)!).filter(Boolean),
      depot,
    ]
    return { route, points }
  })

  return (
    <svg className="map" viewBox={`0 0 ${VIEW} ${VIEW}`} role="img" aria-label="Delivery map">
      {/* route polylines under everything */}
      {routePaths.map(({ route, points }) => (
        <polyline
          key={`r${route.truck_id}`}
          points={points.map((p) => `${p.x},${p.y}`).join(' ')}
          fill="none"
          stroke={TRUCK_COLORS[route.truck_id % TRUCK_COLORS.length]}
          strokeWidth={2}
          strokeOpacity={0.35}
          strokeDasharray="5 5"
        />
      ))}

      {/* stores */}
      {state.stores.map((store) => {
        const p = locations.get(store.store_id)!
        const { color, label } = inventoryHealth(store.inventory, store.max_capacity)
        return (
          <g key={store.store_id}>
            <title>
              {storeName(store.store_id)}: {store.inventory}/{store.max_capacity} in stock ({label})
            </title>
            <circle cx={p.x} cy={p.y} r={14} fill={color} fillOpacity={0.9} stroke="#fff" strokeWidth={2} />
            <text className="map__store-num" x={p.x} y={p.y + 4} textAnchor="middle">
              {storeShortName(store.store_id)}
            </text>
            <text className="map__label" x={p.x} y={p.y + 30} textAnchor="middle">
              {storeName(store.store_id)}
            </text>
          </g>
        )
      })}

      {/* depot */}
      <g transform={`translate(${depot.x} ${depot.y})`}>
        <rect x={-9} y={-9} width={18} height={18} rx={4} transform="rotate(45)" fill="#1b2a4a" />
        <text className="map__label map__label--depot" x={0} y={30} textAnchor="middle">
          DEPOT
        </text>
      </g>

      {/* trucks */}
      {routePaths.map(({ route, points }) => {
        const pos = pointAlongPath(points, progress)
        const color = TRUCK_COLORS[route.truck_id % TRUCK_COLORS.length]
        return (
          <g key={`t${route.truck_id}`} transform={`translate(${pos.x} ${pos.y})`}>
            <rect x={-11} y={-7} width={22} height={14} rx={4} fill={color} stroke="#fff" strokeWidth={1.5} />
            <text className="map__truck mono" x={0} y={3.5} textAnchor="middle">
              {route.truck_id}
            </text>
          </g>
        )
      })}
    </svg>
  )
}
