import type { AgentName, CostView } from '../api/types'
import { formatCost } from '../game/format'

interface Props {
  seed: string
  onSeedChange: (value: string) => void
  onNewGame: () => void
  onRunAgent: (agent: AgentName) => void
  busy: boolean
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

function CostRow({ label, value, strong }: { label: string; value: number; strong?: boolean }) {
  return (
    <div className={strong ? 'cost__row cost__row--total' : 'cost__row'}>
      <span className="cost__label">{label}</span>
      <span className="cost__value mono">{formatCost(value)}</span>
    </div>
  )
}

export function ControlPanel(props: Props) {
  const { cost } = props
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
        <CostRow label="Travel" value={cost.travel} />
        <CostRow label="Holding" value={cost.holding} />
        <CostRow label="Stockout" value={cost.stockout} />
        <CostRow label="Total" value={cost.total} strong />
      </section>
    </aside>
  )
}
