import type { RouteView, StateView } from '../api/types'
import { inventoryHealth } from '../game/health'
import { headingAlongPath, pointAlongPath } from '../game/path'
import { projectPoint, type Point, type ProjectionOptions } from '../game/projection'
import { storeName, storeShortName } from '../game/store'

const VIEW = 720
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
    // Prefer the backend's road polyline (agent runs); fall back to straight
    // depot -> stops -> depot lines for routes the human builds client-side.
    const points: Point[] =
      route.path && route.path.length > 0
        ? route.path.map(([x, y]) => projectPoint(x, y, OPTS))
        : [
            depot,
            ...route.stops.map((s) => locations.get(s.store_id)!).filter(Boolean),
            depot,
          ]
    return { route, points }
  })

  return (
    <svg className="map" viewBox={`0 0 ${VIEW} ${VIEW}`} role="img" aria-label="Delivery map">
      <defs>
        <filter id="truck-shadow" x="-40%" y="-40%" width="180%" height="180%">
          <feDropShadow dx="0" dy="2.5" stdDeviation="2" floodColor="#0e1830" floodOpacity="0.35" />
        </filter>
      </defs>

      {/* road network: arterials as light street strokes, intersections as dots */}
      <g>
        {state.road_segments.map(([a, b], i) => {
          const p1 = projectPoint(a[0], a[1], OPTS)
          const p2 = projectPoint(b[0], b[1], OPTS)
          return (
            <line
              key={`road${i}`}
              x1={p1.x}
              y1={p1.y}
              x2={p2.x}
              y2={p2.y}
              stroke="var(--line)"
              strokeWidth={6}
              strokeOpacity={0.7}
              strokeLinecap="round"
            />
          )
        })}
        {state.intersections.map(([x, y], i) => {
          const p = projectPoint(x, y, OPTS)
          return <circle key={`x${i}`} cx={p.x} cy={p.y} r={2.5} fill="var(--ink-40)" />
        })}
      </g>

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
        const angleDeg = (headingAlongPath(points, progress) * 180) / Math.PI
        const color = TRUCK_COLORS[route.truck_id % TRUCK_COLORS.length]
        return (
          <g key={`t${route.truck_id}`} transform={`translate(${pos.x} ${pos.y})`}>
            {/* body + cab rotate to face travel direction; label stays upright */}
            <g transform={`rotate(${angleDeg})`} filter="url(#truck-shadow)">
              {/* box trailer */}
              <rect x={-12} y={-7} width={18} height={14} rx={3} fill={color} stroke="#fff" strokeWidth={1.25} />
              {/* raised highlight strip along the top edge */}
              <rect x={-11} y={-6} width={16} height={4} rx={2} fill="#fff" fillOpacity={0.28} />
              {/* cab, leading the direction of travel */}
              <rect x={6} y={-5} width={7} height={10} rx={2} fill={color} stroke="#fff" strokeWidth={1.25} />
              {/* windshield accent on the cab */}
              <rect x={10} y={-3.5} width={2.5} height={7} rx={1} fill="#fff" fillOpacity={0.45} />
            </g>
            <text className="map__truck mono" x={0} y={3} textAnchor="middle">
              {route.truck_id}
            </text>
          </g>
        )
      })}
    </svg>
  )
}
