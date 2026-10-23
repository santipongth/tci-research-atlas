import type { ReactNode } from 'react'

export interface BridgeRow {
  key: string
  a: ReactNode
  b: ReactNode
  /** institutions working on both topics */
  shared: number
  /** "3 สถาบันทำทั้งสองเรื่อง" / "ยังไม่มี…" */
  sharedText: string
  /** "เนื้อหาใกล้กัน 0.82 (เต็ม 1)" */
  simText: string
}

/**
 * Two-node link diagrams, one per topic pair: topic — link — topic, the link labelled with the institutions working on
 * both (a dashed link when none does) and the content closeness under it. Side by side on wide screens, stacked on phones.
 */
export function BridgePairs({ rows, label }: { rows: readonly BridgeRow[]; label: string }) {
  return (
    <ul className="bp" aria-label={label}>
      {rows.map((r) => (
        <li key={r.key} className={r.shared > 0 ? 'bp-row' : 'bp-row is-none'}>
          <span className="bp-node bp-a">{r.a}</span>
          <span className="bp-link">
            <span className="bp-shared">{r.sharedText}</span>
            <span className="bp-line" aria-hidden="true" />
            <span className="bp-sim">{r.simText}</span>
          </span>
          <span className="bp-node bp-b">{r.b}</span>
        </li>
      ))}
    </ul>
  )
}
