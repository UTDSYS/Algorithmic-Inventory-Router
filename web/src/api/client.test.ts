import { afterEach, describe, expect, it, vi } from 'vitest'
import { getState, newGame, runAgentEpisode } from './client'

function mockFetch(body: unknown, ok = true, status = 200) {
  const fn = vi.fn().mockResolvedValue({
    ok,
    status,
    statusText: 'ERR',
    json: () => Promise.resolve(body),
  })
  vi.stubGlobal('fetch', fn)
  return fn
}

afterEach(() => vi.unstubAllGlobals())

describe('api client', () => {
  it('newGame posts the seed and returns the parsed response', async () => {
    const fn = mockFetch({ game_id: 'g1', seed: 42, state: { day: 0 } })
    const result = await newGame(7)
    expect(result.game_id).toBe('g1')
    const [url, init] = fn.mock.calls[0]
    expect(url).toContain('/games')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toEqual({ seed: 7 })
  })

  it('newGame without a seed sends an empty body', async () => {
    const fn = mockFetch({ game_id: 'g1', seed: 42, state: {} })
    await newGame()
    expect(JSON.parse(fn.mock.calls[0][1].body)).toEqual({})
  })

  it('getState issues a GET to the game url', async () => {
    const fn = mockFetch({ day: 3 })
    const state = await getState('abc')
    expect(state.day).toBe(3)
    const [url, init] = fn.mock.calls[0]
    expect(url).toContain('/games/abc')
    expect(init.method).toBe('GET')
  })

  it('runAgentEpisode posts the agent name', async () => {
    const fn = mockFetch({ agent: 'greedy', seed: 42, days: [], total_cost: {} })
    await runAgentEpisode('abc', 'greedy')
    const [url, init] = fn.mock.calls[0]
    expect(url).toContain('/games/abc/agent_episode')
    expect(JSON.parse(init.body)).toEqual({ agent: 'greedy' })
  })

  it('throws with the server detail on a non-ok response', async () => {
    mockFetch({ detail: 'unknown game' }, false, 404)
    await expect(getState('nope')).rejects.toThrow(/unknown game/)
  })
})
