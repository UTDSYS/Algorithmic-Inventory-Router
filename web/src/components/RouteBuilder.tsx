import { useState } from 'react'
import type { ActionView, StoreView } from '../api/types'
import { truckLoad, validateAction } from '../game/action'
import { storeName } from '../game/store'

interface Props {
  stores: StoreView[]
  action: ActionView
  capacity: number
  disabled: boolean
  error: string | null
  onAddStop: (truckId: number, storeId: number, quantity: number) => void
  onRemoveStop: (truckId: number, index: number) => void
  onMoveStop: (truckId: number, index: number, dir: -1 | 1) => void
  onSetQty: (truckId: number, index: number, quantity: number) => void
  onClear: () => void
  onDispatch: () => void
}

export function RouteBuilder(props: Props) {
  const { stores, action, capacity, disabled, error } = props
  const errors = validateAction(action, capacity)
  const canDispatch = !disabled && errors.length === 0

  return (
    <section className="panel__block builder">
      <span className="eyebrow">Build the day</span>

      {action.routes.map((route) => (
        <div key={route.truck_id} className="builder__truck">
          <div className="builder__truck-head">
            <span className="builder__truck-name">Truck {route.truck_id}</span>
            <span className="builder__cap mono">{capacity - truckLoad(route)} left</span>
          </div>

          <ul className="builder__stops">
            {route.stops.map((stop, i) => (
              <li key={i} className="builder__stop">
                <span className="builder__stop-name">{storeName(stop.store_id)}</span>
                <input
                  className="field__input builder__qty mono"
                  type="number"
                  min={1}
                  value={stop.quantity}
                  disabled={disabled}
                  onChange={(e) =>
                    props.onSetQty(route.truck_id, i, Number.parseInt(e.target.value, 10) || 0)
                  }
                />
                <button
                  className="btn btn--icon"
                  disabled={disabled || i === 0}
                  onClick={() => props.onMoveStop(route.truck_id, i, -1)}
                  aria-label="Move up"
                >
                  ↑
                </button>
                <button
                  className="btn btn--icon"
                  disabled={disabled || i === route.stops.length - 1}
                  onClick={() => props.onMoveStop(route.truck_id, i, 1)}
                  aria-label="Move down"
                >
                  ↓
                </button>
                <button
                  className="btn btn--icon"
                  disabled={disabled}
                  onClick={() => props.onRemoveStop(route.truck_id, i)}
                  aria-label="Remove stop"
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>

          <AddStopRow
            stores={stores}
            disabled={disabled}
            onAdd={(storeId, qty) => props.onAddStop(route.truck_id, storeId, qty)}
          />
        </div>
      ))}

      {errors.length > 0 && (
        <ul className="builder__errors">
          {errors.map((msg, i) => (
            <li key={i}>{msg}</li>
          ))}
        </ul>
      )}
      {error && <div className="builder__errors builder__errors--api">{error}</div>}

      <div className="panel__row">
        <button className="btn btn--ghost" onClick={props.onClear} disabled={disabled}>
          Clear day
        </button>
        <button className="btn btn--primary" onClick={props.onDispatch} disabled={!canDispatch}>
          Dispatch day
        </button>
      </div>
    </section>
  )
}

function AddStopRow({
  stores,
  disabled,
  onAdd,
}: {
  stores: StoreView[]
  disabled: boolean
  onAdd: (storeId: number, quantity: number) => void
}) {
  const [storeId, setStoreId] = useState(stores[0]?.store_id ?? 0)
  const [qty, setQty] = useState(1)
  return (
    <div className="builder__add">
      <select
        className="field__input"
        value={storeId}
        disabled={disabled}
        onChange={(e) => setStoreId(Number.parseInt(e.target.value, 10))}
      >
        {stores.map((s) => (
          <option key={s.store_id} value={s.store_id}>
            {storeName(s.store_id)}
          </option>
        ))}
      </select>
      <input
        className="field__input builder__qty mono"
        type="number"
        min={1}
        value={qty}
        disabled={disabled}
        onChange={(e) => setQty(Number.parseInt(e.target.value, 10) || 0)}
      />
      <button className="btn btn--ghost" disabled={disabled} onClick={() => onAdd(storeId, qty)}>
        Add
      </button>
    </div>
  )
}
