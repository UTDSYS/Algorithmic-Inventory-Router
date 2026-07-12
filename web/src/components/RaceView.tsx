import type { CostView } from '../api/types'
import { formatCost } from '../game/format'
import { rankContenders, type Contender } from '../game/race'
import type { Race } from '../game/useRace'
import { MapView } from './MapView'

/** Stacked travel/holding/stockout bar, normalised to the busiest contender. */
function CostBar({ cost, max }: { cost: CostView; max: number }) {
  const pct = (v: number) => `${max > 0 ? (v / max) * 100 : 0}%`
  return (
    <div className="costbar" role="img" aria-label={`total ${formatCost(cost.total)}`}>
      <span className="costbar__seg costbar__seg--travel" style={{ width: pct(cost.travel) }} />
      <span className="costbar__seg costbar__seg--holding" style={{ width: pct(cost.holding) }} />
      <span className="costbar__seg costbar__seg--stockout" style={{ width: pct(cost.stockout) }} />
    </div>
  )
}

function ContenderTile({ c, max, rank, finished, progress }: {
  c: Contender; max: number; rank: number | null; finished: boolean; progress: number
}) {
  const leader = finished && rank === 0
  return (
    <div className={leader ? 'race__tile race__tile--leader' : 'race__tile'}>
      <div className="race__head">
        <span className="race__name">{c.label}</span>
        {finished && rank != null && <span className="race__rank mono">#{rank + 1}</span>}
      </div>
      <div className="race__map">
        {c.displayState && (
          <MapView state={c.displayState} routes={c.activeRoutes} progress={progress} compact />
        )}
      </div>
      <CostBar cost={c.runningCost} max={max} />
      <span className="race__total mono">{formatCost(c.runningCost.total)}</span>
    </div>
  )
}

export function RaceView({ race }: { race: Race }) {
  if (race.contenders.length === 0) {
    return <div className="race race--empty">Run the race to compare every strategy on this seed.</div>
  }
  const max = Math.max(...race.contenders.map((c) => c.runningCost.total), 1)
  const finished = race.completedDays >= race.horizon
  const order = rankContenders(race.contenders)
  const rankOf = (c: Contender) => order.indexOf(c)
  return (
    <div className="race">
      <div className="race__grid">
        {race.contenders.map((c) => (
          <ContenderTile
            key={c.label}
            c={c}
            max={max}
            rank={finished ? rankOf(c) : null}
            finished={finished}
            progress={race.progress}
          />
        ))}
      </div>
    </div>
  )
}
