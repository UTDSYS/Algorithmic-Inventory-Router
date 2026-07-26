import type { StoreView } from '../api/types'
import { inventoryHealth } from '../game/health'
import { storeName } from '../game/store'
import { InfoPopover } from './InfoPopover'

function StoreBar({ store }: { store: StoreView }) {
  const ratio = store.max_capacity > 0 ? store.inventory / store.max_capacity : 0
  const { color, level, label } = inventoryHealth(store.inventory, store.max_capacity)
  const nextDemand = store.forecast.length > 0 ? Math.round(store.forecast[0]) : null

  return (
    <div
      className="store"
      data-level={level}
      title={`${storeName(store.store_id)}: ${store.inventory} of ${store.max_capacity} units in stock (${label})`}
    >
      <div className="store__head">
        <span className="store__id">{storeName(store.store_id)}</span>
        <span className="store__status" style={{ color }}>
          {label}
        </span>
      </div>
      <div className="store__track">
        <div
          className="store__fill"
          style={{ width: `${Math.min(100, ratio * 100)}%`, background: color }}
        />
      </div>
      <div className="store__stock">
        <span className="mono">
          {store.inventory}
          <span className="store__cap"> / {store.max_capacity}</span>
        </span>
        <span className="store__stock-label">in stock</span>
      </div>
      {nextDemand != null && (
        <div className="store__due">
          ~<span className="mono">{nextDemand}</span> units due tomorrow
        </div>
      )}
    </div>
  )
}

export function StoreStrip({ stores }: { stores: StoreView[] }) {
  return (
    <section className="stores" aria-label="Store inventory">
      <div className="stores__intro">
        <span className="eyebrow">Stores</span>
        <InfoPopover title="Reading a store" label="What the store cards show">
          <p>
            Each card is one store. The bar shows how full it is — current stock
            against its capacity. Trucks refill stores before demand hits.
          </p>
          <p>The status color is its stockout risk:</p>
          <ul className="info__legend">
            <li>
              <span className="legend legend--critical">Critical</span> — almost
              empty, at risk of running out
            </li>
            <li>
              <span className="legend legend--low">Low</span> — running down,
              refill soon
            </li>
            <li>
              <span className="legend legend--ok">Stocked</span> — healthy for now
            </li>
          </ul>
        </InfoPopover>
      </div>
      <div className="stores__grid">
        {stores.map((store) => (
          <StoreBar key={store.store_id} store={store} />
        ))}
      </div>
    </section>
  )
}
