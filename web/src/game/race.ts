import type { AgentEpisodeResponse, CostView, RouteView, StateView } from '../api/types'
import { cumulativeCost } from './playback'

export interface Contender {
  label: string
  agent: string
  displayState: StateView | null
  activeRoutes: RouteView[]
  runningCost: CostView
  done: boolean
}

/** The longest episode's day count — the race finish line. */
export function raceHorizon(episodes: AgentEpisodeResponse[]): number {
  return episodes.reduce((max, ep) => Math.max(max, ep.days.length), 0)
}

/**
 * Derive one contender's view at the shared race clock. Mirrors usePlayback's
 * single-episode derivation: the ending state of the last completed day, the
 * currently-animating day's routes, and cumulative cost so far. Episodes shorter
 * than the clock are finished (final state, no routes, full cost).
 */
export function contenderAt(
  label: string,
  episode: AgentEpisodeResponse,
  baseState: StateView | null,
  completedDays: number,
  progress: number,
  playing: boolean,
): Contender {
  const horizon = episode.days.length
  const local = Math.min(completedDays, horizon)
  const displayState = local === 0 ? baseState : episode.days[local - 1].state
  const midDay = playing || progress > 0
  const activeRoutes =
    completedDays < horizon && midDay ? episode.days[completedDays].action.routes : []
  return {
    label,
    agent: episode.agent,
    displayState,
    activeRoutes,
    runningCost: cumulativeCost(episode.days, local),
    done: completedDays >= horizon,
  }
}

/** Cheapest total cost first. */
export function rankContenders(contenders: Contender[]): Contender[] {
  return [...contenders].sort((a, b) => a.runningCost.total - b.runningCost.total)
}
