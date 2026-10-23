import type { ReactNode } from 'react'
import type { CheckState } from './editorLayout'

export interface CheckRow {
  key: string
  name: ReactNode
  rate: number | null
  state: CheckState
  /** the share as printed ("85%"), or "ไม่ทราบ" */
  value: string
}

function CheckIcon({ state }: { state: CheckState }) {
  return (
    <svg className={`ck-ic is-${state}`} viewBox="0 0 20 20" width="20" height="20" aria-hidden="true" focusable="false">
      {state === 'full' ? (
        <>
          <rect x="1" y="1" width="18" height="18" className="ck-box is-fill" />
          <path d="M5 10.5l3.2 3.2L15 6.8" className="ck-mark" />
        </>
      ) : state === 'partial' ? (
        <>
          <rect x="1.5" y="1.5" width="17" height="17" className="ck-box" />
          <path d="M1.5 18.5 18.5 1.5V18.5Z" className="ck-half" />
        </>
      ) : state === 'none' ? (
        <>
          <rect x="1.5" y="1.5" width="17" height="17" className="ck-box" />
          <path d="M6 6l8 8M14 6l-8 8" className="ck-x" />
        </>
      ) : (
        <rect x="1.5" y="1.5" width="17" height="17" className="ck-box is-dashed" />
      )}
    </svg>
  )
}

/**
 * A record checklist: one row per item — a drawn ✓ / partial / missing box and its word (never the box alone), the item,
 * a bar of the share of articles that have it, and the share. The table view has the counts behind each share.
 */
export function ChecklistBars({ rows, words, label }: { rows: readonly CheckRow[]; words: Record<CheckState, string>; label: string }) {
  return (
    <ul className="ck" aria-label={label}>
      {rows.map((r) => (
        <li key={r.key} className={`ck-row is-${r.state}`}>
          <span className="ck-state">
            <CheckIcon state={r.state} />
            <span>{words[r.state]}</span>
          </span>
          <span className="ck-name">{r.name}</span>
          <span className="ck-bar" aria-hidden="true">
            {r.rate !== null ? <i style={{ width: `${Math.max(0, Math.min(1, r.rate)) * 100}%` }} /> : null}
          </span>
          <span className="ck-val">{r.value}</span>
        </li>
      ))}
    </ul>
  )
}
