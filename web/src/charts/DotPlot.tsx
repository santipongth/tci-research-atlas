import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { StatusGlyph } from '../components/StatusGlyph'
import type { StatusId } from '../lib/status'
import { dotDomain, pctAt } from './infographic'

export interface DotRow {
  id: string
  label: ReactNode
  sub?: string
  status: StatusId
  value: number
  /** the value as printed ("+113%") */
  text: string
  /** its likely range in words, printed under the value */
  ci?: string | null
  href?: string
}

/**
 * Dot plot: one row per item — name | the estimate as its status glyph on a shared axis, joined to zero by a hairline |
 * the value with its range in text. Marks are placed in percent of the track, so the chart reflows and prints without
 * measuring. A dashed line marks `refValue` (the emerging bar) and a solid line zero.
 */
export function DotPlot({ rows, axisLabel, tick, refValue, refLabel }: {
  rows: readonly DotRow[]
  axisLabel: string
  tick: (v: number) => string
  refValue?: number
  refLabel?: string
}) {
  const { domain, ticks } = dotDomain(rows.map((r) => r.value), refValue === undefined ? [0] : [0, refValue])
  const zero = pctAt(0, domain)
  const ref = refValue === undefined ? null : pctAt(refValue, domain)
  return (
    <div className="dp">
      <div className="dp-head" aria-hidden="true">
        <span className="dp-axl">{axisLabel}</span>
        <span className="dp-scale">
          {ticks.map((v) => (
            <span key={v} className="dp-tick" style={{ left: `${pctAt(v, domain)}%` }}>{tick(v)}</span>
          ))}
          {ref !== null && refLabel ? <span className="dp-reflabel" style={{ left: `${ref}%` }}>{refLabel}</span> : null}
        </span>
        <span />
      </div>
      <ul className="dp-list">
        {rows.map((r) => {
          const x = pctAt(r.value, domain)
          return (
            <li className="dp-row" key={r.id}>
              <span className="dp-name">
                {r.href ? <Link to={r.href} title={typeof r.label === 'string' ? r.label : undefined}>{r.label}</Link> : <b>{r.label}</b>}
                {r.sub ? <small>{r.sub}</small> : null}
              </span>
              <span className="dp-track" aria-hidden="true">
                <i className="dp-zero" style={{ left: `${zero}%` }} />
                {ref !== null ? <i className="dp-ref" style={{ left: `${ref}%` }} /> : null}
                <i className="dp-stem" style={{ left: `${Math.min(x, zero)}%`, width: `${Math.abs(x - zero)}%` }} />
                <span className="dp-dot" style={{ left: `${x}%` }}>
                  <StatusGlyph status={r.status} size={16} />
                </span>
              </span>
              <span className="dp-val">
                <b>{r.text}</b>
                {r.ci ? <small>{r.ci}</small> : null}
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
