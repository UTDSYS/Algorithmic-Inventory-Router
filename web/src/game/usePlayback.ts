import { useCallback, useEffect, useRef, useState } from 'react'
import type { AgentEpisodeResponse, RouteView, StateView } from '../api/types'
import { clampDay, cumulativeCost } from './playback'

const DAY_MS = 1400

export interface Playback {
  horizon: number
  completedDays: number
  progress: number
  playing: boolean
  speed: number
  displayState: StateView | null
  activeRoutes: RouteView[]
  runningCost: ReturnType<typeof cumulativeCost>
  play: () => void
  pause: () => void
  step: () => void
  reset: () => void
  setSpeed: (s: number) => void
}

/**
 * Drives day-by-day playback of an agent episode: advances a progress value
 * across each day so trucks can be animated, then commits the day's ending
 * state once its animation completes.
 */
export function usePlayback(
  episode: AgentEpisodeResponse | null,
  baseState: StateView | null,
): Playback {
  const horizon = episode ? episode.days.length : baseState?.horizon ?? 0
  const [completedDays, setCompletedDays] = useState(0)
  const [progress, setProgress] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const stepping = useRef(false)
  const lastFrame = useRef<number | null>(null)

  useEffect(() => {
    setCompletedDays(0)
    setProgress(0)
    setPlaying(false)
    stepping.current = false
  }, [episode])

  useEffect(() => {
    if (!playing || !episode) return
    lastFrame.current = null
    let frame = 0
    const tick = (t: number) => {
      if (lastFrame.current == null) lastFrame.current = t
      const dt = t - lastFrame.current
      lastFrame.current = t
      setProgress((p) => {
        const next = p + dt / (DAY_MS / speed)
        if (next < 1) return next
        setCompletedDays((d) => {
          const advanced = clampDay(d + 1, horizon)
          if (advanced >= horizon || stepping.current) {
            setPlaying(false)
            stepping.current = false
          }
          return advanced
        })
        return 0
      })
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [playing, speed, episode, horizon])

  const play = useCallback(() => {
    if (completedDays >= horizon) {
      setCompletedDays(0)
      setProgress(0)
    }
    setPlaying(true)
  }, [completedDays, horizon])

  const pause = useCallback(() => setPlaying(false), [])

  const step = useCallback(() => {
    if (completedDays >= horizon) return
    stepping.current = true
    setPlaying(true)
  }, [completedDays, horizon])

  const reset = useCallback(() => {
    setPlaying(false)
    stepping.current = false
    setCompletedDays(0)
    setProgress(0)
  }, [])

  const displayState =
    completedDays === 0
      ? baseState
      : episode?.days[completedDays - 1].state ?? baseState

  const midDay = playing || progress > 0
  const activeRoutes =
    episode && completedDays < horizon && midDay
      ? episode.days[completedDays].action.routes
      : []

  const runningCost = cumulativeCost(episode?.days ?? [], completedDays)

  return {
    horizon,
    completedDays,
    progress,
    playing,
    speed,
    displayState,
    activeRoutes,
    runningCost,
    play,
    pause,
    step,
    reset,
    setSpeed,
  }
}
