import { useNavigate } from 'react-router'
import { TopicTip } from '../components/TopicTip'
import type { Topic } from '../data/types'
import type { Quadrant } from '../lib/definition'
import { fmtPct, fmtSignedPct } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { glyphPath, isSignal } from '../lib/status'
import { useTooltip } from '../lib/tooltip'
import { growthText, statusName } from '../lib/topicText'
import { useElementSize } from '../lib/useElementSize'
import { clamp, linear, logScale } from './scale'

export interface PortfolioLabels {
  name: string
  x: string
  y: string
  split: string
  quadrants: Record<Quadrant, string>
}

const Y: readonly [number, number] = [-0.4, 1.0]
const Y_TICKS = [-0.2, 0, 0.2, 0.4, 0.6, 0.8]

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
 * Size × growth (E2). Log share across, share growth up, the "large" threshold dashed, zero solid.
 * Signal topics are focusable links; STABLE topics are small and pointer-only (the table view lists all).
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
  if (W === 0 || topics.length === 0) return <div ref={ref} className="pf-host" />
  const narrow = W < 560
  const H = Math.round(Math.max(340, Math.min(560, W * (narrow ? 1.1 : 0.62))))
  const M = { t: 20, r: narrow ? 12 : 24, b: narrow ? 72 : 54, l: narrow ? 52 : 64 }
  const shares = topics.map((tp) => tp.metrics.share_recent)
  const x0 = Math.min(...shares, threshold) * 0.8
  const x1 = Math.max(...shares, threshold) * 1.25
  const x = logScale(x0, x1, M.l, W - M.r)
  const y = linear(Y[0], Y[1], H - M.b, M.t)
  const py = (g: number | null | undefined) => y(clamp(g ?? 0, Y[0], Y[1]))
  const xs = x(threshold)
  const splitAnchor = xs + 220 > W - M.r ? 'end' : 'start'
  const order = [...topics].sort((a, b) => Number(isSignal(a.status)) - Number(isSignal(b.status)))
  const boxes: { x: number; y: number; w: number; h: number }[] = []
  const directLabels = [...topics]
    .filter((tp) => tp.status === 'EMERGING')
    .sort((a, b) => (b.metrics.share_growth ?? 0) - (a.metrics.share_growth ?? 0))
    .slice(0, narrow ? 1 : 3)
    .flatMap((tp) => {
      const text = name(tp)
      const w = Math.min(240, text.length * 7.4)
      const cx = x(tp.metrics.share_recent)
      const cy = py(tp.metrics.share_growth)
      for (const [dx, anchor] of [[10, 'start'], [-10, 'end']] as const) {
        const box = { x: anchor === 'start' ? cx + dx : cx + dx - w, y: cy - 18, w, h: 18 }
        const inside = box.x >= M.l && box.x + box.w <= W - M.r && box.y >= M.t
        const free = boxes.every((b) => box.x + box.w < b.x || b.x + b.w < box.x || box.y + box.h < b.y || b.y + b.h < box.y)
        if (inside && free) {
          boxes.push(box)
          return [{ id: tp.id, text, x: cx + dx, y: cy - 6, anchor }]
        }
      }
      return []
    })
  const quadrant = (q: Quadrant, qx: number, qy: number, anchor: 'start' | 'end') => (
    <text key={q} x={qx} y={qy} textAnchor={anchor} className="pf-qname">
      {labels.quadrants[q]}
      <tspan x={qx} dy="1.3em" className="pf-qcount">{t('topicsN', { n: counts[q] })}</tspan>
    </text>
  )
  return (
    <div ref={ref} className="pf-host">
      <svg className="pf" width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="group" aria-label={labels.name}>
        <g aria-hidden="true">
          {Y_TICKS.map((v) => (
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
          {quadrant('stars', W - M.r - 8, M.t + 34, 'end')}
          {quadrant('rising', M.l + 8, M.t + 18, 'start')}
          {quadrant('mature', W - M.r - 8, H - M.b - 44, 'end')}
          {quadrant('declining', M.l + 8, H - M.b - 44, 'start')}
          {directLabels.map((d) => (
            <text key={d.id} x={d.x} y={d.y} textAnchor={d.anchor} className="pf-ltext">{d.text}</text>
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
                onPointerEnter={(e) => tip.show(content, e.clientX, e.clientY)}
                onPointerMove={(e) => tip.show(content, e.clientX, e.clientY)}
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
