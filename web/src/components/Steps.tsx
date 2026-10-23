import type { ReactNode } from 'react'

export interface StepItem {
  title: ReactNode
  body?: ReactNode
  /** a small drawing for the step (decorative) */
  art?: ReactNode
  /** under the body: e.g. the statuses the step decides */
  foot?: ReactNode
}

/**
 * A short numbered sequence (3–4 steps) whose order carries meaning: a horizontal row joined by a rule on wide
 * screens, a vertical list on phones. `current` marks one step (aria-current="step").
 */
export function Steps({ label, items, current }: { label: string; items: readonly StepItem[]; current?: number }) {
  return (
    <ol className={`steps steps-${items.length}`} aria-label={label}>
      {items.map((it, i) => (
        <li key={i} className={i === current ? 'step is-current' : 'step'} aria-current={i === current ? 'step' : undefined}>
          <span className="step-n" aria-hidden="true">{i + 1}</span>
          <div className="step-c">
            {it.art ? <div className="step-art" aria-hidden="true">{it.art}</div> : null}
            <p className="step-t">{it.title}</p>
            {it.body ? <p className="step-b">{it.body}</p> : null}
            {it.foot ? <div className="step-f">{it.foot}</div> : null}
          </div>
        </li>
      ))}
    </ol>
  )
}
