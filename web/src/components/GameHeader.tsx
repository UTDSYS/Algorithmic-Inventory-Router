interface Props {
  day: number
  horizon: number
  agentLabel: string | null
}

export function GameHeader({ day, horizon, agentLabel }: Props) {
  return (
    <header className="app-header">
      <div className="app-header__title">
        <span className="eyebrow">Inventory Routing Problem</span>
        <h1>Inventory Router</h1>
      </div>
      <div className="app-header__status">
        {agentLabel && <span className="app-header__agent">{agentLabel}</span>}
        <span className="app-header__day mono">
          Day <strong>{day}</strong> / {horizon}
        </span>
      </div>
    </header>
  )
}
