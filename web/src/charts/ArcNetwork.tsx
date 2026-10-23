import { useState, type ReactNode } from 'react'
import { useElementSize } from '../lib/useElementSize'
import { LABEL_PX } from '../lib/labelSizes'
import { arcLayout, arcPath } from './execLayout'

export interface ArcRow {
  id: string
  /** the name as shown (usually a link) */
  name: ReactNode
  /** the name as text, for arc titles */
  text: string
  /** rows are ordered by this (articles), largest first */
  weight: number
  /** one short line under the name ("1,840 บทความ"); hidden on narrow screens */
  sub?: string
}

const AXIS = 6

/**
 * Collaboration as an arc diagram: institutions as rows (names in HTML, so they wrap and link), each co-authoring pair
 * as an arc right of the node axis — stroke width and the number at the peak are the joint articles. Deterministic
 * (no force simulation); pointing at or focusing a row highlights its arcs. The figure's table view lists every pair.
 */
export function ArcNetwork({ rows, links, label, pairTitle, maxNodes = 10 }: {
  rows: readonly ArcRow[]
  links: readonly { a: string; b: string; value: number }[]
  /** what the arcs show, for screen readers */
  label: string
  pairTitle: (a: string, b: string, value: number) => string
  maxNodes?: number
}) {
  const [ref, { width: W }] = useElementSize<HTMLDivElement>()
  const [hot, setHot] = useState<string | null>(null)
  const compact = W > 0 && W < 560
  const row = compact ? 60 : 56
  const arcW = Math.round(Math.min(340, Math.max(118, W * 0.42)))
  const byId = new Map(rows.map((r) => [r.id, r]))
  const layout = arcLayout({ nodes: rows.map((r) => ({ id: r.id, weight: r.weight })), links }, { row, width: arcW, maxNodes, labelPx: LABEL_PX.label })
  if (W === 0) return <div ref={ref} className="an" />
  const touches = (l: { a: string; b: string }) => hot !== null && (l.a === hot || l.b === hot)
  return (
    <div ref={ref} className={`an${compact ? ' is-compact' : ''}${hot ? ' has-hot' : ''}`} style={{ gridTemplateColumns: `minmax(0, 1fr) ${arcW}px` }}>
      <ol className="an-rows">
        {layout.nodes.map((n) => {
          const r = byId.get(n.id) as ArcRow
          return (
            <li
              key={n.id}
              className={hot === n.id ? 'an-row is-hot' : 'an-row'}
              style={{ height: row }}
              onPointerEnter={() => setHot(n.id)}
              onPointerLeave={() => setHot(null)}
              onFocus={() => setHot(n.id)}
              onBlur={() => setHot(null)}
            >
              <span className="an-name">{r.name}</span>
              {r.sub && !compact ? <span className="an-sub">{r.sub}</span> : null}
            </li>
          )
        })}
      </ol>
      <svg className="an-svg" width={arcW} height={layout.height} viewBox={`0 0 ${arcW} ${layout.height}`} role="img" aria-label={label}>
        <line x1={AXIS} x2={AXIS} y1={layout.nodes[0]?.y ?? 0} y2={layout.nodes[layout.nodes.length - 1]?.y ?? 0} className="an-axis" />
        {layout.links.map((l) => (
          <path
            key={`${l.a}~${l.b}`}
            d={arcPath(AXIS, l.y1, l.y2, l.bulge)}
            className={touches(l) ? 'an-link is-hot' : 'an-link'}
            style={{ strokeWidth: l.width }}
          >
            <title>{pairTitle(byId.get(l.a)?.text ?? l.a, byId.get(l.b)?.text ?? l.b, l.value)}</title>
          </path>
        ))}
        {layout.nodes.map((n) => (
          <circle key={n.id} cx={AXIS} cy={n.y} r={4.5} className={hot === n.id ? 'an-node is-hot' : 'an-node'} />
        ))}
        {layout.links.map((l) =>
          l.label ? (
            <text key={`t-${l.a}~${l.b}`} x={l.label.x} y={l.label.y} dy="0.35em" className={touches(l) ? 'an-num is-hot' : 'an-num'} aria-hidden="true">
              {l.value.toLocaleString('en-US')}
            </text>
          ) : null,
        )}
      </svg>
    </div>
  )
}
