import { useId } from 'react'
import type { StatusId } from '../lib/status'
import { StatusGlyph } from '../components/StatusGlyph'
import { fmtInt } from '../lib/format'
import { donutArcs } from './donut'

export interface DonutRow {
  status: StatusId
  n: number
}

/**
 * Every topic by status as a ring + its list: each status keeps its glyph, colour and name, the count and the share are
 * printed in the list (the ring never carries a number alone). "ข้อมูลน้อย" is hatched, as in every chart.
 */
export function StatusDonut({ rows, total, totalUnit, label, name, pct }: {
  rows: readonly DonutRow[]
  total: string
  totalUnit: string
  label: string
  name: (s: StatusId) => string
  pct: (n: number) => string
}) {
  const hatch = `dnh${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`
  const S = 150
  const arcs = donutArcs(rows.map((r) => ({ key: r.status, value: r.n })), S / 2, S / 2, 50, 72)
  return (
    <div className="dn">
      <svg className="dn-ring" viewBox={`0 0 ${S} ${S}`} width={S} height={S} role="img" aria-label={label}>
        <defs>
          <pattern id={hatch} width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="5" height="5" className="dn-hatch-bg" />
            <line x1="0" y1="0" x2="0" y2="5" className="dn-hatch-line" />
          </pattern>
        </defs>
        {arcs.map((a) =>
          a.d ? (
            <path key={a.key} d={a.d} className={`dn-seg mk-${a.key}`} style={a.key === 'LOW_DATA' ? { fill: `url(#${hatch})` } : undefined} />
          ) : null,
        )}
        <text x={S / 2} y={S / 2 - 2} className="dn-total" textAnchor="middle">{total}</text>
        <text x={S / 2} y={S / 2 + 18} className="dn-unit" textAnchor="middle">{totalUnit}</text>
      </svg>
      <ul className="dn-list">
        {rows.map((r) => (
          <li key={r.status}>
            <StatusGlyph status={r.status} size={12} />
            <span className="dn-name">{name(r.status)}</span>
            <span className="dn-n">{fmtInt(r.n)}</span>
            <span className="dn-pct">{pct(r.n)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
