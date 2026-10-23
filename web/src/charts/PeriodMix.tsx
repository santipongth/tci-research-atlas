import type { ReactNode } from 'react'
import type { PeriodRow } from './editorLayout'

/**
 * Then vs now: two 100 % bars (the earlier years over the recent years) split into the same topics in the same order
 * and shade — so a part that grows or shrinks between the bars is the journal's change of course itself. The key repeats
 * every topic with both shares and the change, so nothing is read from colour or length alone.
 */
export function PeriodMix({ rows, other, periods, name, fmt, change, otherName, label }: {
  rows: readonly PeriodRow[]
  other: { before: number; after: number }
  /** the two bars' labels ("2017–2021", "2022–2024") */
  periods: readonly [string, string]
  name: (topic: string) => ReactNode
  fmt: (v: number) => string
  /** the change between the bars as printed ("+9 จุด") */
  change: (before: number, after: number) => string
  otherName: string
  /** the whole figure in words, for screen readers */
  label: string
}) {
  const bar = (k: 'before' | 'after') => (
    <span className="pm-bar">
      {rows.map((r, i) => (r[k] > 0 ? <span key={r.topic} className={`mx-seg mx-${Math.min(i, 3)}`} style={{ width: `${r[k] * 100}%` }} /> : null))}
      {other[k] > 0 ? <span className="mx-seg mx-other" style={{ width: `${other[k] * 100}%` }} /> : null}
    </span>
  )
  return (
    <div className="pm">
      <div className="pm-bars" role="img" aria-label={label}>
        <div className="pm-row">
          <span className="pm-period">{periods[0]}</span>
          {bar('before')}
        </div>
        <div className="pm-row">
          <span className="pm-period">{periods[1]}</span>
          {bar('after')}
        </div>
      </div>
      <ol className="pm-key">
        {rows.map((r, i) => (
          <li key={r.topic}>
            <span className={`mx-sw mx-${Math.min(i, 3)}`} aria-hidden="true" />
            <span className="pm-name">{name(r.topic)}</span>
            <span className="pm-vals">
              <span>{fmt(r.before)}</span>
              <svg viewBox="0 0 16 10" width="16" height="10" aria-hidden="true" focusable="false"><path d="M1 5h12M9 1.5 13 5 9 8.5" fill="none" stroke="currentColor" strokeWidth="1.6" /></svg>
              <b>{fmt(r.after)}</b>
              <span className={r.after > r.before ? 'pm-d is-up' : 'pm-d'}>{change(r.before, r.after)}</span>
            </span>
          </li>
        ))}
        <li className="is-other">
          <span className="mx-sw mx-other" aria-hidden="true" />
          <span className="pm-name">{otherName}</span>
          <span className="pm-vals">
            <span>{fmt(other.before)}</span>
            <svg viewBox="0 0 16 10" width="16" height="10" aria-hidden="true" focusable="false"><path d="M1 5h12M9 1.5 13 5 9 8.5" fill="none" stroke="currentColor" strokeWidth="1.6" /></svg>
            <b>{fmt(other.after)}</b>
          </span>
        </li>
      </ol>
    </div>
  )
}
