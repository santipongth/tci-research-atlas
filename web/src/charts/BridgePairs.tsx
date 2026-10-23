import type { ReactNode } from 'react'

export interface BridgeRow {
  key: string
  a: ReactNode
  b: ReactNode
  /** institutions working on both topics (or, for a directed pair, the citations) — 0 draws a dashed link */
  shared: number
  /** "3 สถาบันทำทั้งสองเรื่อง" / "ยังไม่มี…" */
  sharedText: string
  /** "เนื้อหาใกล้กัน 0.82 (เต็ม 1)"; empty = no line under the link */
  simText: string
}

/**
 * Two-node link diagrams, one per topic pair: topic — link — topic, the link labelled with the institutions working on
 * both (a dashed link when none does) and the content closeness under it. `directed` draws the link as an arrow from a
 * to b (e.g. citing topic → cited topic). Side by side on wide screens, stacked on phones.
 */
export function BridgePairs({ rows, label, directed = false }: { rows: readonly BridgeRow[]; label: string; directed?: boolean }) {
  return (
    <ul className={directed ? 'bp is-directed' : 'bp'} aria-label={label}>
      {rows.map((r) => (
        <li key={r.key} className={r.shared > 0 ? 'bp-row' : 'bp-row is-none'}>
          <span className="bp-node bp-a">{r.a}</span>
          <span className="bp-link">
            <span className="bp-shared">{r.sharedText}</span>
            <span className="bp-line" aria-hidden="true" />
            {r.simText ? <span className="bp-sim">{r.simText}</span> : null}
          </span>
          <span className="bp-node bp-b">{r.b}</span>
        </li>
      ))}
    </ul>
  )
}
