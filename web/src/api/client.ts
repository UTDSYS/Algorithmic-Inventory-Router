import type {
  AgentEpisodeResponse,
  AgentName,
  ActionView,
  BaselineResponse,
  NewGameResponse,
  StateView,
  StepResponse,
} from './types'

const BASE_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = await response.json()
      if (body?.detail) detail = body.detail
    } catch {
      // response had no JSON body; keep statusText
    }
    throw new Error(`API ${response.status}: ${detail}`)
  }
  return (await response.json()) as T
}

export function newGame(seed?: number): Promise<NewGameResponse> {
  const body = seed == null ? {} : { seed }
  return request<NewGameResponse>('/games', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function getState(gameId: string): Promise<StateView> {
  return request<StateView>(`/games/${gameId}`, { method: 'GET' })
}

export function runAgentEpisode(
  gameId: string,
  agent: AgentName,
): Promise<AgentEpisodeResponse> {
  return request<AgentEpisodeResponse>(`/games/${gameId}/agent_episode`, {
    method: 'POST',
    body: JSON.stringify({ agent }),
  })
}

export function stepGame(gameId: string, action: ActionView): Promise<StepResponse> {
  return request<StepResponse>(`/games/${gameId}/step`, {
    method: 'POST',
    body: JSON.stringify(action),
  })
}

export function runBaseline(
  gameId: string,
  agent: AgentName,
): Promise<BaselineResponse> {
  return request<BaselineResponse>(`/games/${gameId}/baseline`, {
    method: 'POST',
    body: JSON.stringify({ agent }),
  })
}
