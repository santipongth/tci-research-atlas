import { useRef, type ReactNode } from 'react'

export interface TabItem {
  id: string
  label: string
  icon?: ReactNode
  count?: number
}

/**
 * The ARIA tablist alone (automatic activation): ←/→ move and select, Home/End jump. The panel is `${id}-panel`.
 * `strip`: on phones the tabs stay on one line and scroll sideways (with a fade at the edge) instead of wrapping.
 */
export function TabList({ id, label, items, value, onChange, strip = false }: { id: string; label: string; items: readonly TabItem[]; value: string; onChange: (id: string) => void; strip?: boolean }) {
  const buttons = useRef(new Map<string, HTMLButtonElement>())
  const select = (item: TabItem | undefined) => {
    if (!item) return
    onChange(item.id)
    buttons.current.get(item.id)?.focus()
  }
  const selected = items.find((it) => it.id === value) ?? items[0]
  const list = (
    <div className={`tablist${strip ? ' is-strip' : ''}`} role="tablist" aria-label={label}>
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
  )
  return strip ? <div className="tabstrip">{list}</div> : list
}

/** ARIA tabs: the tablist and the panel that holds the selected content. */
export function Tabs({ id, label, items, value, onChange, children, strip = false }: { id: string; label: string; items: readonly TabItem[]; value: string; onChange: (id: string) => void; children: ReactNode; strip?: boolean }) {
  const selected = items.find((it) => it.id === value) ?? items[0]
  return (
    <div className="tabs">
      <TabList id={id} label={label} items={items} value={value} onChange={onChange} strip={strip} />
      <div className="tabpanel" role="tabpanel" id={`${id}-panel`} aria-labelledby={selected ? `${id}-tab-${selected.id}` : undefined} tabIndex={0}>
        {children}
      </div>
    </div>
  )
}
