import type { CostView } from '../api/types'
import { formatCost } from '../game/format'
import { InfoPopover } from './InfoPopover'

/** Explains that the score is a cost (lower is better) and what each part means. */
export function ScoringInfo() {
  return (
    <InfoPopover title="How your score works" label="How scoring works">
      <p>
        Your score is the <strong>total cost</strong> of running the season, so{' '}
        <strong>lower is better.</strong> It adds up three things:
      </p>
      <ul className="info__legend">
        <li>
          <strong>Travel</strong> — distance your trucks drove
        </li>
        <li>
          <strong>Holding</strong> — excess stock sitting idle in stores
        </li>
        <li>
          <strong>Stockout</strong> — penalty when a store runs empty
        </li>
      </ul>
      <p>Keep every store stocked while driving and overstocking as little as possible.</p>
    </InfoPopover>
  )
}

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
