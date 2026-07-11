import { useCallback, useEffect, useState } from 'react'
import { stepGame } from '../api/client'
import type { ActionView, CostView, RouteView, StateView } from '../api/types'
import {
  addStop as addStopTo,
  emptyAction,
  moveStop as moveStopIn,
  removeStop as removeStopFrom,
  setQty as setQtyIn,
  validateAction,
} from './action'
import { DAY_MS } from './playback'

const ZERO_COST: CostView = { travel: 0, holding: 0, stockout: 0, total: 0, reward: 0 }

export interface PlayGame {
  state: StateView | null
  day: number
  horizon: number
  capacity: number
  total: CostView
  lastCost: CostView | null
  done: boolean
  action: ActionView
  phase: 'building' | 'animating'
  progress: number
  error: string | null
  activeRoutes: RouteView[]
  addStop: (truckId: number, storeId: number, quantity: number) => void
  removeStop: (truckId: number, index: number) => void
  moveStop: (truckId: number, index: number, dir: -1 | 1) => void
  setQty: (truckId: number, index: number, quantity: number) => void
  clearDay: () => void
  dispatch: () => void
}

/**
 * Human play: build each day's routes, dispatch (validate -> animate -> POST
 * /step), and advance until the season is done. Re-initialises whenever a fresh
 * game (new `initialState` identity) arrives.
 */
export function usePlayGame(gameId: string | null, initialState: StateView | null): PlayGame {
  const numTrucks = initialState?.fleet.num_trucks ?? 0
  const capacity = initialState?.fleet.capacity ?? 0
  const horizon = initialState?.horizon ?? 0

  const [state, setState] = useState<StateView | null>(initialState)
  const [day, setDay] = useState(0)
  const [total, setTotal] = useState<CostView>(ZERO_COST)
  const [lastCost, setLastCost] = useState<CostView | null>(null)
  const [done, setDone] = useState(false)
  const [action, setAction] = useState<ActionView>(() => emptyAction(numTrucks))
  const [phase, setPhase] = useState<'building' | 'animating'>('building')
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)

  // Re-initialise when a new game (fresh initial state) arrives.
  useEffect(() => {
    setState(initialState)
    setDay(0)
    setTotal(ZERO_COST)
    setLastCost(null)
    setDone(false)
    setAction(emptyAction(initialState?.fleet.num_trucks ?? 0))
    setPhase('building')
    setProgress(0)
    setError(null)
  }, [initialState])

  // The dispatch tween: while animating, sweep progress 0->1, then POST /step.
  useEffect(() => {
    if (phase !== 'animating' || !gameId) return
    let frame = 0
    let last: number | null = null
    let acc = 0
    let fired = false
    const tick = (t: number) => {
      if (last == null) last = t
      acc += (t - last) / DAY_MS
      last = t
      const p = Math.min(acc, 1)
      setProgress(p)
      if (p >= 1) {
        if (!fired) {
          fired = true
          void stepGame(gameId, action)
            .then((res) => {
              setState(res.state)
              setTotal(res.total_cost)
              setLastCost(res.cost)
              setDone(res.done)
              setDay((d) => d + 1)
              setAction(emptyAction(res.state.fleet.num_trucks))
              setProgress(0)
              setPhase('building')
            })
            .catch((e: unknown) => {
              setError(e instanceof Error ? e.message : 'Dispatch failed')
              setProgress(0)
              setPhase('building')
            })
        }
        return
      }
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [phase, gameId, action])

  const addStop = useCallback((truckId: number, storeId: number, quantity: number) => {
    setAction((a) => addStopTo(a, truckId, storeId, quantity))
    setError(null)
  }, [])

  const removeStop = useCallback((truckId: number, index: number) => {
    setAction((a) => removeStopFrom(a, truckId, index))
    setError(null)
  }, [])

  const moveStop = useCallback((truckId: number, index: number, dir: -1 | 1) => {
    setAction((a) => moveStopIn(a, truckId, index, dir))
    setError(null)
  }, [])

  const setQty = useCallback((truckId: number, index: number, quantity: number) => {
    setAction((a) => setQtyIn(a, truckId, index, quantity))
    setError(null)
  }, [])

  const clearDay = useCallback(() => {
    setAction(emptyAction(numTrucks))
    setError(null)
  }, [numTrucks])

  const dispatch = useCallback(() => {
    if (phase === 'animating' || done) return
    const errors = validateAction(action, capacity)
    if (errors.length > 0) {
      setError(errors.join(' '))
      return
    }
    setError(null)
    setProgress(0)
    setPhase('animating')
  }, [phase, done, action, capacity])

  const activeRoutes = phase === 'animating' ? action.routes : []

  return {
    state,
    day,
    horizon,
    capacity,
    total,
    lastCost,
    done,
    action,
    phase,
    progress,
    error,
    activeRoutes,
    addStop,
    removeStop,
    moveStop,
    setQty,
    clearDay,
    dispatch,
  }
}
