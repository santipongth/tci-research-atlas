import { useTooltip } from '../lib/tooltip'
import { useElementSize } from '../lib/useElementSize'
import { useFontsVersion } from '../lib/useFontsVersion'
import { textWidth as measureText } from '../lib/measure'
import { LABEL_PX } from '../lib/labelSizes'
import { placeLabels, quadrantLayout, type Box, type QuadPoint } from './execLayout'
import { tickDecimals } from './scale'

const graphemes = typeof Intl !== 'undefined' && 'Segmenter' in Intl ? new Intl.Segmenter('en', { granularity: 'grapheme' }) : null
const clip = (s: string, max: number) => {
  const parts = graphemes ? [...graphemes.segment(s)].map((g) => g.segment) : [...s]
  return parts.length > max ? `${parts.slice(0, max - 1).join('').trimEnd()}…` : s
}

/**
 * Opportunity quadrant: one dot per subfield — x = how much Thailand works on it relative to the world (activity index,
 * 1 = same), y = how fast the world grew (recent ÷ baseline share). Linear axes; dashed reference lines at 1 on both.
 * The shaded top-left zone is the data file's own thresholds (`xMax`, `yMin`); dots inside the criteria are filled
 * blue, the rest hollow ink. Labels go to the opportunities first, never overlapping marks or each other.
 */
export function OpportunityQuadrant({ points, xMax, yMin, text, label, describe, labelLang }: {
  points: readonly QuadPoint[]
  xMax?: number | null
  yMin?: number | null
  text: { x: string; y: string; zone: string; same: string; flat: string; opp: string; other: string }
  label: string
  describe: (p: QuadPoint) => string
  /** language of the point names (OpenAlex subfields are English) */
  labelLang?: string
}) {
  const [ref, { width: W }] = useElementSize<HTMLDivElement>()
  const tip = useTooltip()
  useFontsVersion() // label boxes are measured in Sarabun: measure again once it has loaded
  if (W === 0 || points.length === 0) return <div ref={ref} className="oq-host" />
  const narrow = W < 560
  const H = Math.round(Math.max(300, Math.min(460, W * 0.62)))
  const M = { t: 12, r: 14, b: 30, l: 44 }
  const L = quadrantLayout(points, { width: W, height: H, margin: M, xMax, yMin })
  const fmtTick = (ticks: number[]) => {
    const step = ticks.length > 1 ? ticks[1] - ticks[0] : 1
    const d = Math.min(2, tickDecimals(step))
    return (v: number) => v.toFixed(d)
  }
  const fx = fmtTick(L.xTicks)
  const fy = fmtTick(L.yTicks)
  const x1 = L.x(1)
  const y1 = L.y(1)
  const inX = x1 >= L.plot.x && x1 <= L.plot.x + L.plot.w
  const inY = y1 >= L.plot.y && y1 <= L.plot.y + L.plot.h
  const avoid: Box[] = []
  const zone = L.zone
  const zoneLabel = zone && zone.w > 40 && zone.h > 24 ? { x: zone.x + 8, y: zone.y + 8 + LABEL_PX.strong * 0.8 } : null
  if (zone && zoneLabel) avoid.push({ x: zone.x, y: zone.y, w: measureText(text.zone, LABEL_PX.strong, 700) + 18, h: LABEL_PX.strong * 1.6 + 8 })
  if (inX) avoid.push({ x: x1 + 2, y: L.plot.y, w: measureText(text.same, LABEL_PX.label, 400) + 8, h: LABEL_PX.label * 1.4 })
  if (inY) avoid.push({ x: L.plot.x + L.plot.w - measureText(text.flat, LABEL_PX.label, 400) - 8, y: y1 - LABEL_PX.label * 1.5, w: measureText(text.flat, LABEL_PX.label, 400) + 8, h: LABEL_PX.label * 1.4 })
  const order = [...points].sort((p, q) => Number(q.hot) - Number(p.hot) || q.y - p.y)
  // on phones only the opportunities are named; the rest are context (named in the tooltip and the table)
  const labels = placeLabels(
    order.filter((p) => !narrow || p.hot).map((p) => ({ id: p.id, text: clip(p.label, narrow ? 18 : 30), cx: L.x(p.x), cy: L.y(p.y) })),
    { px: LABEL_PX.label, r: 7, bounds: { x: 0, y: 0, w: W, h: H - M.b + 4 }, avoid, max: narrow ? 4 : 9, measure: (txt, px) => measureText(txt, px, 600) },
  )
  return (
    <div ref={ref} className="oq-host">
      <p className="oq-ytitle" aria-hidden="true">{text.y}</p>
      <svg className="oq" width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label}>
        {L.zone ? <rect x={L.zone.x} y={L.zone.y} width={L.zone.w} height={L.zone.h} className="oq-zone" /> : null}
        {L.yTicks.map((v) => (
          <g key={`y${v}`}>
            <line x1={L.plot.x} x2={L.plot.x + L.plot.w} y1={L.y(v)} y2={L.y(v)} className="tr-gl" />
            <text x={L.plot.x - 6} y={L.y(v)} dy="0.35em" textAnchor="end" className="tr-tick">{fy(v)}</text>
          </g>
        ))}
        {L.xTicks.map((v) => (
          <text key={`x${v}`} x={L.x(v)} y={H - M.b + 18} textAnchor="middle" className="tr-tick">{fx(v)}</text>
        ))}
        <line x1={L.plot.x} x2={L.plot.x + L.plot.w} y1={L.plot.y + L.plot.h} y2={L.plot.y + L.plot.h} className="tr-base" />
        {inX ? (
          <g>
            <line x1={x1} x2={x1} y1={L.plot.y} y2={L.plot.y + L.plot.h} className="oq-ref" />
            <text x={x1 + 5} y={L.plot.y + LABEL_PX.label} className="oq-reflabel">{text.same}</text>
          </g>
        ) : null}
        {inY ? (
          <g>
            <line x1={L.plot.x} x2={L.plot.x + L.plot.w} y1={y1} y2={y1} className="oq-ref" />
            <text x={L.plot.x + L.plot.w - 4} y={y1 - 6} textAnchor="end" className="oq-reflabel">{text.flat}</text>
          </g>
        ) : null}
        {zoneLabel ? <text x={zoneLabel.x} y={zoneLabel.y} className="oq-zonelabel">{text.zone}</text> : null}
        {order
          .slice()
          .reverse()
          .map((p) => (
            <g
              key={p.id}
              className={p.hot ? 'oq-pt is-hot' : 'oq-pt'}
              onPointerEnter={(e) => tip.showAt(<div>{describe(p)}</div>, e.currentTarget)}
              onPointerLeave={() => tip.hide()}
            >
              <circle cx={L.x(p.x)} cy={L.y(p.y)} r={14} className="oq-hit" />
              <circle cx={L.x(p.x)} cy={L.y(p.y)} r={p.hot ? 6 : 5} className="oq-dot" />
            </g>
          ))}
        {labels.map((l) => (
          <text key={l.id} x={l.x} y={l.y} dy="0.35em" textAnchor={l.anchor} className="oq-label" lang={labelLang}>{l.text}</text>
        ))}
      </svg>
      <p className="oq-xtitle" aria-hidden="true">{text.x}</p>
      <ul className="oq-key">
        <li><svg width="14" height="14" aria-hidden="true" focusable="false"><circle cx="7" cy="7" r="5.5" className="oq-dot is-hot" /></svg>{text.opp}</li>
        <li><svg width="14" height="14" aria-hidden="true" focusable="false"><circle cx="7" cy="7" r="4.5" className="oq-dot" /></svg>{text.other}</li>
        {L.zone ? <li><span className="oq-zonesw" aria-hidden="true" />{text.zone}</li> : null}
      </ul>
    </div>
  )
}
