import { useRef, type ReactNode } from 'react'

export interface TabItem {
  id: string
  label: string
  icon?: ReactNode
  count?: number
}

/** ARIA tabs (automatic activation): ←/→ move and select, Home/End jump; the panel holds the selected content. */
export function Tabs({ id, label, items, value, onChange, children }: { id: string; label: string; items: readonly TabItem[]; value: string; onChange: (id: string) => void; children: ReactNode }) {
  const buttons = useRef(new Map<string, HTMLButtonElement>())
  const select = (item: TabItem | undefined) => {
    if (!item) return
    onChange(item.id)
    buttons.current.get(item.id)?.focus()
  }
  const selected = items.find((it) => it.id === value) ?? items[0]
  return (
    <div className="tabs">
      <div className="tablist" role="tablist" aria-label={label}>
        {items.map((it, i) => {
          const isSel = it.id === selected?.id
          return (
            <button
              key={it.id}
              ref={(el) => {
                if (el) buttons.current.set(it.id, el)
                else buttons.current.delete(it.id)
              }}
              type="button"
              role="tab"
              id={`${id}-tab-${it.id}`}
              aria-selected={isSel}
              aria-controls={`${id}-panel`}
              tabIndex={isSel ? 0 : -1}
              onClick={() => onChange(it.id)}
              onKeyDown={(e) => {
                const n = items.length
                const target = e.key === 'ArrowRight' ? items[(i + 1) % n] : e.key === 'ArrowLeft' ? items[(i - 1 + n) % n] : e.key === 'Home' ? items[0] : e.key === 'End' ? items[n - 1] : undefined
                if (target) {
                  e.preventDefault()
                  select(target)
                }
              }}
            >
              {it.icon}
              <span>{it.label}</span>
              {it.count !== undefined ? <span className="tab-count">{it.count}</span> : null}
            </button>
          )
        })}
      </div>
      <div className="tabpanel" role="tabpanel" id={`${id}-panel`} aria-labelledby={selected ? `${id}-tab-${selected.id}` : undefined} tabIndex={0}>
        {children}
      </div>
    </div>
  )
}
