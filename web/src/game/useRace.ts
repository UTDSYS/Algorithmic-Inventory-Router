import { useCallback, useEffect, useRef, useState } from 'react'
import type { AgentEpisodeResponse, StateView } from '../api/types'
import { clampDay, DAY_MS } from './playback'
import { contenderAt, raceHorizon, type Contender } from './race'

export interface LabeledEpisode {
  label: string
  episode: AgentEpisodeResponse
}

export interface Race {
  contenders: Contender[]
  completedDays: number
  progress: number
  playing: boolean
  speed: number
  horizon: number
  play: () => void
  pause: () => void
  step: () => void
  reset: () => void
  setSpeed: (s: number) => void
}

/**
 * Drive N episodes on one shared day clock (a multiplexed usePlayback). Each
 * entry becomes a Contender view derived at the current clock; the finish line
 * is the longest episode.
 */
export function useRace(entries: LabeledEpisode[], baseState: StateView | null): Race {
  const horizon = raceHorizon(entries.map((e) => e.episode))
  const [completedDays, setCompletedDays] = useState(0)
  const [progress, setProgress] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const stepping = useRef(false)
  const lastFrame = useRef<number | null>(null)

  // Reset whenever a fresh race (new entries identity) is loaded.
  useEffect(() => {
    setCompletedDays(0)
    setProgress(0)
    setPlaying(false)
    stepping.current = false
  }, [entries])

  useEffect(() => {
    if (!playing || horizon === 0) return
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
  }, [playing, speed, horizon])

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

  const contenders = entries.map((e) =>
    contenderAt(e.label, e.episode, baseState, completedDays, progress, playing),
  )

  return {
    contenders,
    completedDays,
    progress,
    playing,
    speed,
    horizon,
    play,
    pause,
    step,
    reset,
    setSpeed,
  }
}
