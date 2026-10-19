import { useNavigate } from 'react-router'
import { TopicTip } from '../components/TopicTip'
import type { Topic } from '../data/types'
import type { Quadrant } from '../lib/definition'
import { fmtPct, fmtSignedPct } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { placeLabels, type Box } from '../lib/labels'
import { textWidth } from '../lib/measure'
import { glyphPath, isSignal } from '../lib/status'
import { useTooltip } from '../lib/tooltip'
import { growthText, statusName } from '../lib/topicText'
import { useElementSize } from '../lib/useElementSize'
import { useFontsVersion } from '../lib/useFontsVersion'
import { clamp, dataDomain, linear, logScale, niceTicks } from './scale'

export interface PortfolioLabels {
  name: string
  x: string
  y: string
  split: string
  quadrants: Record<Quadrant, string>
}

/** Growth-axis limits: the axis follows the data inside these; a topic beyond is drawn on the edge with its value. */
const Y_CAP: readonly [number, number] = [-1, 3]
/** Half-size of a marker as an obstacle for labels (glyph + stroke). */
const MARK_R = { signal: 8, other: 5.5 }

function logTicks(lo: number, hi: number, narrow: boolean): number[] {
  const out: number[] = []
  for (let e = Math.floor(Math.log10(lo)); e <= Math.ceil(Math.log10(hi)); e++) {
    for (const m of narrow ? [1] : [1, 2, 5]) {
      const v = m * 10 ** e
      if (v >= lo && v <= hi) out.push(v)
    }
  }
  return out
}

const pctTick = (v: number) => fmtPct(v, v < 0.001 ? 2 : v < 0.01 ? 1 : 0)

/**
 * Size × growth (E2). Log share across, share growth up (axis from the data), the "large" threshold dashed, zero solid.
 * Signal topics are focusable links; STABLE topics are small and pointer-only (the table view lists all).
 * Direct labels never sit on a marker or a quadrant name; a label with no clear spot is left out (the table has every name).
 */
export function PortfolioMatrix({ topics, threshold, ciLevel, labels, counts }: {
  topics: readonly Topic[]
  threshold: number
  ciLevel: number
  labels: PortfolioLabels
  counts: Record<Quadrant, number>
}) {
  const [ref, { width: W }] = useElementSize<HTMLDivElement>()
  const navigate = useNavigate()
  const tip = useTooltip()
  const { t, name } = useI18n()
  useFontsVersion()
  if (W === 0 || topics.length === 0) return <div ref={ref} className="pf-host" />
  const narrow = W < 560
  const H = Math.round(Math.max(340, Math.min(560, W * (narrow ? 1.1 : 0.62))))
  const M = { t: 20, r: narrow ? 12 : 24, b: narrow ? 72 : 54, l: narrow ? 60 : 74 }
  const shares = topics.map((tp) => tp.metrics.share_recent)
  const x0 = Math.min(...shares, threshold) * 0.8
  const x1 = Math.max(...shares, threshold) * 1.25
  const x = logScale(x0, x1, M.l, W - M.r)
  const Y = dataDomain(topics.map((tp) => tp.metrics.share_growth), [-0.1, 0.1], Y_CAP, 0.12)
  const y = linear(Y[0], Y[1], H - M.b, M.t)
  const yTicks = niceTicks(Y[0], Y[1], narrow ? 5 : 7).filter((v) => v >= Y[0] && v <= Y[1])
  const py = (g: number | null | undefined) => y(clamp(g ?? 0, Y[0], Y[1]))
  const beyond = (g: number | null | undefined) => g !== null && g !== undefined && (g > Y[1] || g < Y[0])
  const xs = x(threshold)
  const splitAnchor = xs + 220 > W - M.r ? 'end' : 'start'
  const order = [...topics].sort((a, b) => Number(isSignal(a.status)) - Number(isSignal(b.status)))
  const quads: { q: Quadrant; x: number; y: number; anchor: 'start' | 'end' }[] = [
    { q: 'stars', x: W - M.r - 8, y: M.t + 34, anchor: 'end' },
    { q: 'rising', x: M.l + 8, y: M.t + 18, anchor: 'start' },
    { q: 'mature', x: W - M.r - 8, y: H - M.b - 44, anchor: 'end' },
    { q: 'declining', x: M.l + 8, y: H - M.b - 44, anchor: 'start' },
  ]
  const quadBoxes: Box[] = quads.map((qd) => {
    const w = Math.max(textWidth(labels.quadrants[qd.q], 15, 700), textWidth(t('topicsN', { n: counts[qd.q] }), 12.5, 400))
    return { x: qd.anchor === 'end' ? qd.x - w : qd.x, y: qd.y - 15, w, h: 15 + 19.5 + 4 }
  })
  const markBoxes = topics.map((tp) => {
    const r = isSignal(tp.status) ? MARK_R.signal : MARK_R.other
    return { id: tp.id, x: x(tp.metrics.share_recent) - r, y: py(tp.metrics.share_growth) - r, w: 2 * r, h: 2 * r }
  })
  const directLabels = placeLabels(
    [...topics]
      .filter((tp) => tp.status === 'EMERGING')
      .sort((a, b) => (b.metrics.share_growth ?? 0) - (a.metrics.share_growth ?? 0))
      .slice(0, narrow ? 1 : 3)
      .map((tp) => {
        const text = name(tp)
        return { id: tp.id, text, width: textWidth(text, 13, 700), height: 13, x: x(tp.metrics.share_recent), y: py(tp.metrics.share_growth), radius: MARK_R.signal }
      }),
    [...markBoxes, ...quadBoxes],
    { x: M.l, y: M.t, w: W - M.l - M.r, h: H - M.t - M.b },
  )
  const frame = { x: M.l, y: M.t, w: W - M.l - M.r, h: H - M.t - M.b }
  // topics beyond the growth axis sit on its edge; their "↑ +N%" value is placed like any label and skipped when no spot is clear
  const edgeLabels = placeLabels(
    topics
      .filter((tp) => beyond(tp.metrics.share_growth))
      .map((tp) => {
        const text = `${(tp.metrics.share_growth ?? 0) > Y[1] ? '↑' : '↓'} ${fmtSignedPct(tp.metrics.share_growth, 0)}`
        return { id: tp.id, text, width: textWidth(text, 12, 600), height: 12, x: x(tp.metrics.share_recent), y: py(tp.metrics.share_growth), radius: MARK_R.signal }
      }),
    [...markBoxes, ...quadBoxes, ...directLabels.map((d) => d.box)],
    frame,
  )
  return (
    <div ref={ref} className="pf-host">
      <svg className="pf" width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="group" aria-label={labels.name}>
        <g aria-hidden="true">
          {yTicks.map((v) => (
            <g key={v}>
              <line x1={M.l} x2={W - M.r} y1={y(v)} y2={y(v)} className={v === 0 ? 'pf-axis0' : 'pf-gl'} />
              <text x={M.l - 8} y={y(v) + 4} textAnchor="end" className="pf-tick">{v === 0 ? '0%' : fmtSignedPct(v, 0)}</text>
            </g>
          ))}
          {logTicks(x0, x1, narrow).map((v) => (
            <g key={v}>
              <line x1={x(v)} x2={x(v)} y1={M.t} y2={H - M.b} className="pf-gl" />
              <text x={x(v)} y={H - M.b + 18} textAnchor="middle" className="pf-tick">{pctTick(v)}</text>
            </g>
          ))}
          <line x1={xs} x2={xs} y1={M.t} y2={H - M.b} className="pf-split" />
          <text x={splitAnchor === 'start' ? xs + 6 : xs - 6} y={H - M.b - 8} textAnchor={splitAnchor} className="pf-split-label">{labels.split}</text>
          <text x={(M.l + W - M.r) / 2} y={H - (narrow ? 34 : 12)} textAnchor="middle" className="pf-axis-title">{labels.x}</text>
          <text x={14} y={(M.t + H - M.b) / 2} textAnchor="middle" transform={`rotate(-90 14 ${(M.t + H - M.b) / 2})`} className="pf-axis-title">{labels.y}</text>
          {quads.map((qd) => (
            <text key={qd.q} x={qd.x} y={qd.y} textAnchor={qd.anchor} className="pf-qname">
              {labels.quadrants[qd.q]}
              <tspan x={qd.x} dy="1.3em" className="pf-qcount">{t('topicsN', { n: counts[qd.q] })}</tspan>
            </text>
          ))}
          {directLabels.map((d) => (
            <text key={d.id} x={d.x} y={d.y} textAnchor={d.anchor} className="pf-ltext">{d.text}</text>
          ))}
          {edgeLabels.map((d) => (
            <text key={d.id} x={d.x} y={d.y} textAnchor={d.anchor} className="pf-edge">{d.text}</text>
          ))}
        </g>
        <g>
          {order.map((tp) => {
            const signal = isSignal(tp.status)
            const content = <TopicTip topic={tp} ciLevel={ciLevel} />
            const open = () => {
              tip.hide()
              navigate(`/topics/${tp.id}`)
            }
            return (
              <g
                key={tp.id}
                transform={`translate(${x(tp.metrics.share_recent).toFixed(1)},${py(tp.metrics.share_growth).toFixed(1)})`}
                className={`pf-node st-${tp.status}`}
                role={signal ? 'link' : undefined}
                tabIndex={signal ? 0 : undefined}
                aria-label={signal ? `${t('openTopic', { n: name(tp) })} · ${statusName(t, tp.status)} · ${growthText(t, tp.metrics)}` : undefined}
                onClick={open}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    open()
                  }
                }}
                onPointerEnter={(e) => tip.show(content, e.clientX, e.clientY, e.currentTarget)}
                onPointerMove={(e) => tip.show(content, e.clientX, e.clientY, e.currentTarget)}
                onPointerLeave={() => tip.hide()}
                onFocus={(e) => tip.showAt(content, e.currentTarget)}
                onBlur={() => tip.hide()}
              >
                <circle r={signal ? 12 : 7} className="hit" />
                <path className={`mk mk-${tp.status}`} d={glyphPath(tp.status, signal ? 5.4 : 3.4)} />
              </g>
            )
          })}
        </g>
      </svg>
    </div>
  )
}
