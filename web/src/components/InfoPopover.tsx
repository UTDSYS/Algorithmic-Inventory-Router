import { useEffect, useId, useRef, useState, type ReactNode } from 'react'

interface Props {
  /** Heading shown at the top of the popover panel. */
  title: string
  /** Accessible label for the trigger button. Defaults to `title`. */
  label?: string
  children: ReactNode
}

/** A small "?" trigger that reveals a short explanation on demand. */
export function InfoPopover({ title, label, children }: Props) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const panelId = useId()

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    const onPointer = (e: PointerEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('keydown', onKey)
    document.addEventListener('pointerdown', onPointer)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.removeEventListener('pointerdown', onPointer)
    }
  }, [open])

  return (
    <div className="info" ref={rootRef}>
      <button
        type="button"
        className="info__trigger"
        aria-label={label ?? title}
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        onClick={() => setOpen((v) => !v)}
      >
        ?
      </button>
      {open && (
        <div className="info__panel" id={panelId} role="tooltip">
          <span className="info__title">{title}</span>
          <div className="info__body">{children}</div>
        </div>
      )}
    </div>
  )
}
