import { useTooltip } from '../lib/tooltip'
import { useElementSize } from '../lib/useElementSize'
import { LABEL_PX } from '../lib/labelSizes'
import { labelOrder, scatterLayout, type ScatterPoint } from './editorLayout'
import { placeLabels, textWidth, type Box } from './execLayout'
import { tickDecimals } from './scale'

const graphemes = typeof Intl !== 'undefined' && 'Segmenter' in Intl ? new Intl.Segmenter('th', { granularity: 'grapheme' }) : null
const clip = (s: string, max: number) => {
  const parts = graphemes ? [...graphemes.segment(s)].map((g) => g.segment) : [...s]
  return parts.length > max ? `${parts.slice(0, max - 1).join('').trimEnd()}…` : s
}

/**
 * Journals scatter: one dot per journal — x = complete records (0–100), y = share of articles with an author from the
 * journal's owner. The band above the release's in-house bar is shaded and named; journals whose owner was inferred
 * are hollow. The largest journals (and those above the bar) are named, never over a mark or each other; every journal
 * is in the tooltip and the table view.
 */
export function JournalScatter({ points, yRef, text, label, describe, pct }: {
  points: readonly ScatterPoint[]
  yRef?: number | null
  text: { x: string; y: string; zone: string; owner: string; inferred: string }
  label: string
  describe: (p: ScatterPoint) => string
  /** a share as printed on the axis ("40%"), with the decimals the tick step needs */
  pct: (v: number, decimals: number) => string
}) {
  const [ref, { width: W }] = useElementSize<HTMLDivElement>()
  const tip = useTooltip()
  if (W === 0 || points.length === 0) return <div ref={ref} className="js-host" />
  const narrow = W < 560
  const H = Math.round(Math.max(300, Math.min(440, W * 0.58)))
  const M = { t: 12, r: 16, b: 30, l: 48 }
  const L = scatterLayout(points, { width: W, height: H, margin: M, yRef })
  const yd = tickDecimals(L.yStep, 100)
  const avoid: Box[] = []
  const zone = L.zone
  const zoneLabel = zone && zone.h > LABEL_PX.strong * 1.8 ? { x: zone.x + 8, y: zone.y + 8 + LABEL_PX.strong * 0.8 } : null
  if (zone && zoneLabel) avoid.push({ x: zone.x, y: zone.y, w: textWidth(text.zone, LABEL_PX.strong) + 18, h: LABEL_PX.strong * 1.6 + 8 })
  const order = labelOrder(points, yRef)
  const labels = placeLabels(
    order.map((p) => ({ id: p.id, text: clip(p.label, narrow ? 16 : 28), cx: L.x(p.x), cy: L.y(p.y) })),
    { px: LABEL_PX.label, r: 7, bounds: { x: 0, y: 0, w: W, h: H - M.b + 4 }, avoid, max: narrow ? 4 : 8 },
  )
  const hasInferred = points.some((p) => p.inferred)
  return (
    <div ref={ref} className="js-host">
      <p className="oq-ytitle" aria-hidden="true">{text.y}</p>
      <svg className="js" width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label}>
        {zone ? <rect x={zone.x} y={zone.y} width={zone.w} height={zone.h} className="oq-zone" /> : null}
        {L.yTicks.map((v) => (
          <g key={`y${v}`}>
            <line x1={L.plot.x} x2={L.plot.x + L.plot.w} y1={L.y(v)} y2={L.y(v)} className="tr-gl" />
            <text x={L.plot.x - 6} y={L.y(v)} dy="0.35em" textAnchor="end" className="tr-tick">{pct(v, yd)}</text>
          </g>
        ))}
        {L.xTicks.map((v) => (
          <text key={`x${v}`} x={L.x(v)} y={H - M.b + 18} textAnchor={v === 0 ? 'start' : v === 100 ? 'end' : 'middle'} className="tr-tick">{v}</text>
        ))}
        <line x1={L.plot.x} x2={L.plot.x + L.plot.w} y1={L.plot.y + L.plot.h} y2={L.plot.y + L.plot.h} className="tr-base" />
        {zone && typeof yRef === 'number' ? <line x1={L.plot.x} x2={L.plot.x + L.plot.w} y1={L.y(yRef)} y2={L.y(yRef)} className="oq-ref" /> : null}
        {zoneLabel ? <text x={zoneLabel.x} y={zoneLabel.y} className="oq-zonelabel">{text.zone}</text> : null}
        {order
          .slice()
          .reverse()
          .map((p) => (
            <g
              key={p.id}
              className={p.inferred ? 'js-pt is-inferred' : 'js-pt'}
              onPointerEnter={(e) => tip.showAt(<div>{describe(p)}</div>, e.currentTarget)}
              onPointerLeave={() => tip.hide()}
            >
              <circle cx={L.x(p.x)} cy={L.y(p.y)} r={14} className="oq-hit" />
              <circle cx={L.x(p.x)} cy={L.y(p.y)} r={6} className="js-dot" />
            </g>
          ))}
        {labels.map((l) => (
          <text key={l.id} x={l.x} y={l.y} dy="0.35em" textAnchor={l.anchor} className="oq-label">{l.text}</text>
        ))}
      </svg>
      <p className="oq-xtitle js-xtitle" aria-hidden="true">{text.x}</p>
      <ul className="oq-key">
        <li><svg width="14" height="14" aria-hidden="true" focusable="false"><circle cx="7" cy="7" r="5.5" className="js-dot" /></svg>{text.owner}</li>
        {hasInferred ? <li><svg width="14" height="14" aria-hidden="true" focusable="false"><circle cx="7" cy="7" r="5" className="js-dot is-hollow" /></svg>{text.inferred}</li> : null}
        {zone ? <li><span className="oq-zonesw" aria-hidden="true" />{text.zone}</li> : null}
      </ul>
    </div>
  )
}
