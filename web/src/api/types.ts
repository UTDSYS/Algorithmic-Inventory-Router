// TypeScript mirrors of the FastAPI response models in src/api/server.py.

export type Coord = [number, number]

// A straight arterial road: its two endpoints in world coordinates.
export type RoadSegment = [Coord, Coord]

export interface CostView {
  travel: number
  holding: number
  stockout: number
  total: number
  reward: number
}

export interface StoreView {
  store_id: number
  location: Coord
  inventory: number
  max_capacity: number
  holding_cost: number
  stockout_penalty: number
  forecast: number[]
}

export interface FleetView {
  num_trucks: number
  capacity: number
}

export interface StateView {
  day: number
  horizon: number
  done: boolean
  depot_location: Coord
  depot_inventory: number
  travel_cost_per_distance: number
  fleet: FleetView
  stores: StoreView[]
  // Static road geometry for drawing; empty when the scenario has no roads.
  road_segments: RoadSegment[]
  intersections: Coord[]
  // Short stub linking each store/depot to the road it fronts.
  driveways: RoadSegment[]
}

export interface NewGameResponse {
  game_id: string
  seed: number
  state: StateView
}

export interface StopView {
  store_id: number
  quantity: number
}

export interface RouteView {
  truck_id: number
  stops: StopView[]
  // Full road polyline depot -> stops -> depot. Present on backend-run agent
  // routes; absent for routes the human builds client-side (drawn straight).
  path?: Coord[]
}

export interface ActionView {
  routes: RouteView[]
}

export interface StepResponse {
  state: StateView
  reward: number
  done: boolean
  cost: CostView
  total_cost: CostView
  action: ActionView
}

export interface BaselineResponse {
  agent: string
  cost: CostView
}

export interface DayView {
  day: number
  action: ActionView
  cost: CostView
  state: StateView
}

export interface AgentEpisodeResponse {
  agent: string
  seed: number
  days: DayView[]
  total_cost: CostView
}

export type AgentName = 'greedy' | 'nearest_neighbour' | 'rolling_horizon'

export interface CompareResponse {
  seed: number
  episodes: AgentEpisodeResponse[]
}
