import type { CostView } from '../api/types'
import { formatCost } from '../game/format'
import { CostBreakdown } from './CostBreakdown'

interface Props {
  day: number
  horizon: number
  done: boolean
  lastCost: CostView | null
  total: CostView
}

export function ScorePanel({ day, horizon, done, lastCost, total }: Props) {
  return (
    <section className="panel__block panel__block--cost">
      <span className="eyebrow">Your season</span>
      <div className="cost__row">
        <span className="cost__label">Day</span>
        <span className="cost__value mono">
          {day} / {horizon}
        </span>
      </div>
      {lastCost && (
        <div className="cost__row">
          <span className="cost__label">Last day</span>
          <span className="cost__value mono">{formatCost(lastCost.total)}</span>
        </div>
      )}
      <CostBreakdown cost={total} heading="Total so far" />
      {done && (
        <div className="score__banner">Season complete — total {formatCost(total.total)}</div>
      )}
    </section>
  )
}
