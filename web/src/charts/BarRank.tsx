import { Link } from 'react-router'
import type { RankRow } from './infographic'

/**
 * Mini bar ranking: name | an ink bar scaled to the largest item | the number, always printed (the bar never carries the
 * value alone). Names link when `href` gives a path. Under 640 px the bar and number sit under the name.
 */
export function BarRank({ rows, href, value, label }: {
  rows: readonly RankRow[]
  href?: (r: RankRow) => string | null
  value: (r: RankRow) => string
  /** what the list ranks, for screen readers */
  label: string
}) {
  return (
    <ol className="br" aria-label={label}>
      {rows.map((r) => {
        const to = href?.(r) ?? null
        return (
          <li className="br-row" key={r.key}>
            <span className="br-name">{to ? <Link to={to}>{r.key}</Link> : r.key}</span>
            <span className="br-bar" aria-hidden="true">
              <i style={{ width: `${Math.max(1.5, r.frac * 100)}%` }} />
            </span>
            <span className="br-val">{value(r)}</span>
          </li>
        )
      })}
    </ol>
  )
}
