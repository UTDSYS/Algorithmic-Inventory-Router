import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'
import { newGame, runAgentEpisode } from './api/client'
import type { AgentEpisodeResponse, AgentName, StateView } from './api/types'
import { ControlPanel } from './components/ControlPanel'
import { GameHeader } from './components/GameHeader'
import { MapView } from './components/MapView'
import { StoreStrip } from './components/StoreStrip'
import { usePlayback } from './game/usePlayback'
import { usePlayGame } from './game/usePlayGame'

type Mode = 'play' | 'watch'

const AGENT_LABELS: Record<AgentName, string> = {
  greedy: 'Greedy',
  nearest_neighbour: 'Nearest-Neighbour',
}

function App() {
  const [gameId, setGameId] = useState<string | null>(null)
  const [seed, setSeed] = useState('42')
  const [baseState, setBaseState] = useState<StateView | null>(null)
  const [episode, setEpisode] = useState<AgentEpisodeResponse | null>(null)
  const [agent, setAgent] = useState<AgentName | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<Mode>('play')
  const autoPlay = useRef(false)

  const game = usePlayGame(gameId, baseState)
  const playback = usePlayback(episode, baseState)

  const startGame = useCallback(async (seedValue?: number) => {
    setBusy(true)
    setError(null)
    try {
      const created = await newGame(seedValue)
      setGameId(created.game_id)
      setBaseState(created.state)
      setSeed(String(created.seed))
      setEpisode(null)
      setAgent(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not start a game')
    } finally {
      setBusy(false)
    }
  }, [])

  useEffect(() => {
    void startGame()
  }, [startGame])

  const handleNewGame = () => {
    const parsed = Number.parseInt(seed, 10)
    void startGame(Number.isNaN(parsed) ? undefined : parsed)
  }

  const handleRunAgent = async (which: AgentName) => {
    if (!gameId) return
    setBusy(true)
    setError(null)
    try {
      const result = await runAgentEpisode(gameId, which)
      setAgent(which)
      autoPlay.current = true
      setEpisode(result)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not run the agent')
    } finally {
      setBusy(false)
    }
  }

  // Auto-play a freshly loaded episode.
  useEffect(() => {
    if (episode && autoPlay.current) {
      autoPlay.current = false
      playback.play()
    }
  }, [episode, playback])

  const watchState = playback.displayState ?? baseState
  const state = mode === 'play' ? game.state : watchState
  const routes = mode === 'play' ? game.activeRoutes : playback.activeRoutes
  const progress = mode === 'play' ? game.progress : playback.progress
  const day = mode === 'play' ? game.day : episode ? playback.completedDays : 0
  const horizon = state?.horizon ?? 0
  const atEnd = playback.completedDays >= playback.horizon
  const agentLabel = mode === 'watch' && agent ? AGENT_LABELS[agent] : null

  return (
    <div className="app">
      <GameHeader day={day} horizon={horizon} agentLabel={agentLabel} />

      {error && <div className="app__error">{error}</div>}

      {state ? (
        <>
          <StoreStrip stores={state.stores} />
          <div className="app__stage">
            <div className="app__map-wrap">
              <MapView state={state} routes={routes} progress={progress} />
            </div>
            <ControlPanel
              seed={seed}
              onSeedChange={setSeed}
              onNewGame={handleNewGame}
              busy={busy}
              mode={mode}
              onModeChange={setMode}
              stores={state.stores}
              game={game}
              onRunAgent={handleRunAgent}
              hasEpisode={episode != null}
              playing={playback.playing}
              atEnd={atEnd}
              speed={playback.speed}
              onPlay={playback.play}
              onPause={playback.pause}
              onStep={playback.step}
              onReset={playback.reset}
              onSpeed={playback.setSpeed}
              cost={playback.runningCost}
            />
          </div>
        </>
      ) : (
        <div className="app__loading">Starting a game…</div>
      )}
    </div>
  )
}

export default App
