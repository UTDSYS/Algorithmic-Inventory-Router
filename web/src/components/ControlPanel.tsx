import type { AgentName, CostView, StoreView } from '../api/types'
import type { PlayGame } from '../game/usePlayGame'
import { CostBreakdown } from './CostBreakdown'
import { RouteBuilder } from './RouteBuilder'
import { ScorePanel } from './ScorePanel'

type Mode = 'play' | 'watch'

interface Props {
  // shell
  seed: string
  onSeedChange: (value: string) => void
  onNewGame: () => void
  busy: boolean
  mode: Mode
  onModeChange: (mode: Mode) => void
  // play
  stores: StoreView[]
  game: PlayGame
  // watch
  onRunAgent: (agent: AgentName) => void
  hasEpisode: boolean
  playing: boolean
  atEnd: boolean
  speed: number
  onPlay: () => void
  onPause: () => void
  onStep: () => void
  onReset: () => void
  onSpeed: (s: number) => void
  cost: CostView
}

const SPEEDS = [0.5, 1, 2, 4]

export function ControlPanel(props: Props) {
  const { game, mode } = props
  return (
    <aside className="panel">
      <section className="panel__block">
        <span className="eyebrow">New game</span>
        <div className="panel__row">
          <label className="field">
            <span className="field__label">Seed</span>
            <input
              className="field__input mono"
              value={props.seed}
              inputMode="numeric"
              onChange={(e) => props.onSeedChange(e.target.value)}
            />
          </label>
          <button className="btn btn--ghost" onClick={props.onNewGame} disabled={props.busy}>
            Start
          </button>
        </div>
      </section>

      <section className="panel__block">
        <div className="mode-toggle" role="group" aria-label="Mode">
          <button
            className={mode === 'play' ? 'mode-toggle__btn mode-toggle__btn--active' : 'mode-toggle__btn'}
            onClick={() => props.onModeChange('play')}
          >
            Play
          </button>
          <button
            className={mode === 'watch' ? 'mode-toggle__btn mode-toggle__btn--active' : 'mode-toggle__btn'}
            onClick={() => props.onModeChange('watch')}
          >
            Watch
          </button>
        </div>
      </section>

      {mode === 'play' ? (
        <>
          <RouteBuilder
            stores={props.stores}
            action={game.action}
            capacity={game.capacity}
            disabled={game.phase === 'animating' || game.done}
            error={game.error}
            onAddStop={game.addStop}
            onRemoveStop={game.removeStop}
            onMoveStop={game.moveStop}
            onSetQty={game.setQty}
            onClear={game.clearDay}
            onDispatch={game.dispatch}
          />
          <ScorePanel
            day={game.day}
            horizon={game.horizon}
            done={game.done}
            lastCost={game.lastCost}
            total={game.total}
          />
        </>
      ) : (
        <>
          <section className="panel__block">
            <span className="eyebrow">Watch a baseline</span>
            <div className="panel__row">
              <button
                className="btn btn--primary"
                onClick={() => props.onRunAgent('greedy')}
                disabled={props.busy}
              >
                Run Greedy
              </button>
              <button
                className="btn btn--primary"
                onClick={() => props.onRunAgent('nearest_neighbour')}
                disabled={props.busy}
              >
                Run Nearest
              </button>
            </div>
          </section>

          <section className="panel__block">
            <span className="eyebrow">Playback</span>
            <div className="panel__row panel__row--controls">
              {props.playing ? (
                <button className="btn btn--icon" onClick={props.onPause} disabled={!props.hasEpisode} aria-label="Pause">
                  ⏸
                </button>
              ) : (
                <button className="btn btn--icon" onClick={props.onPlay} disabled={!props.hasEpisode} aria-label="Play">
                  ⏵
                </button>
              )}
              <button className="btn btn--icon" onClick={props.onStep} disabled={!props.hasEpisode || props.atEnd} aria-label="Step one day">
                ⏭
              </button>
              <button className="btn btn--icon" onClick={props.onReset} disabled={!props.hasEpisode} aria-label="Reset">
                ↺
              </button>
              <div className="speed" role="group" aria-label="Speed">
                {SPEEDS.map((s) => (
                  <button
                    key={s}
                    className={s === props.speed ? 'speed__btn speed__btn--active mono' : 'speed__btn mono'}
                    onClick={() => props.onSpeed(s)}
                  >
                    {s}×
                  </button>
                ))}
              </div>
            </div>
          </section>

          <section className="panel__block panel__block--cost">
            <span className="eyebrow">Cost</span>
            <CostBreakdown cost={props.cost} />
          </section>
        </>
      )}
    </aside>
  )
}
