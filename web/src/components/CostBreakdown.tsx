import type { CostView } from '../api/types'
import { formatCost } from '../game/format'

function CostRow({ label, value, strong }: { label: string; value: number; strong?: boolean }) {
  return (
    <div className={strong ? 'cost__row cost__row--total' : 'cost__row'}>
      <span className="cost__label">{label}</span>
      <span className="cost__value mono">{formatCost(value)}</span>
    </div>
  )
}

interface Props {
  cost: CostView
  heading?: string
}

/** Travel / Holding / Stockout / Total rows, shared by the watch and play panels. */
export function CostBreakdown({ cost, heading }: Props) {
  return (
    <>
      {heading && <span className="eyebrow">{heading}</span>}
      <CostRow label="Travel" value={cost.travel} />
      <CostRow label="Holding" value={cost.holding} />
      <CostRow label="Stockout" value={cost.stockout} />
      <CostRow label="Total" value={cost.total} strong />
    </>
  )
}
