import { useState } from 'react'
import type { TopicForecast, TopicNowcast } from '../data/types'
import { forecastView } from '../lib/forecast'
import { fmtCompact, fmtInt } from '../lib/format'
import { glyphPath, type StatusId } from '../lib/status'
import { useTooltip } from '../lib/tooltip'
import { useElementSize } from '../lib/useElementSize'
import { linear, niceTicks } from './scale'

export interface TrendLabels {
  name: string
  forecast: string
  articles: string
  range80: (lo: string, hi: string) => string
}

/** Articles a year (line + area), and — only when the release shows a forecast (never for LOW_DATA) — 80 % and 95 % bands with a dashed mean. */
export function TrendChart({ status, years, counts, forecast, nowcast, labels }: {
  status: StatusId
  years: readonly number[]
  counts: readonly number[]
  forecast: TopicForecast | null
  nowcast: TopicNowcast | null
  labels: TrendLabels
}) {
  const [ref, { width: W }] = useElementSize<HTMLDivElement>()
  const tip = useTooltip()
  const [hover, setHover] = useState<number | null>(null)
  if (W === 0 || years.length === 0) return <div ref={ref} className="tr-host" />
  const fc = forecast && forecastView(status, forecast) === 'show' ? forecast : null
  const last = years[years.length - 1]
  const extra = [...(fc ? fc.years : []), ...(nowcast && !years.includes(nowcast.year) && !(fc?.years ?? []).includes(nowcast.year) ? [nowcast.year] : [])]
  const all = [...years, ...extra].sort((a, b) => a - b)
  const first = all[0]
  const end = all[all.length - 1]
  const H = Math.round(Math.max(220, Math.min(320, W * 0.5)))
  const M = { t: 22, r: 18, b: 32, l: 48 }
  const maxV = Math.max(1, ...counts, ...(fc ? fc.hi95 : []), ...(nowcast ? [nowcast.mean] : []))
  const ticks = niceTicks(0, maxV * 1.05, 4)
  const yMax = Math.max(ticks[ticks.length - 1] ?? maxV, maxV * 1.08)
  const x = linear(first, end === first ? first + 1 : end, M.l, W - M.r)
  const y = linear(0, yMax, H - M.b, M.t)
  const lastV = counts[counts.length - 1] ?? 0
  const line = years.map((yr, i) => `${i ? 'L' : 'M'}${x(yr).toFixed(1)},${y(counts[i] ?? 0).toFixed(1)}`).join('')
  const area = `${line}L${x(last).toFixed(1)},${y(0).toFixed(1)}L${x(years[0]).toFixed(1)},${y(0).toFixed(1)}Z`
  const band = (lo: readonly number[], hi: readonly number[]) =>
    fc
      ? `M${x(last)},${y(lastV)}${fc.years.map((yr, i) => `L${x(yr)},${y(hi[i])}`).join('')}${[...fc.years.keys()].reverse().map((i) => `L${x(fc.years[i])},${y(lo[i])}`).join('')}Z`
      : ''
  const meanLine = fc ? `M${x(last)},${y(lastV)}${fc.years.map((yr, i) => `L${x(yr)},${y(fc.mean[i])}`).join('')}` : ''
  const step = W < 420 ? 3 : 2
  const yearTicks = all.filter((yr, i) => i === all.length - 1 || (yr - first) % step === 0)
  const content = (yr: number) => {
    const i = years.indexOf(yr)
    if (i >= 0) return (<><div className="tip-title">{yr}</div><div className="tip-row"><strong>{fmtInt(counts[i])}</strong> {labels.articles}</div></>)
    const j = fc ? fc.years.indexOf(yr) : -1
    if (fc && j >= 0) {
      return (
        <>
          <div className="tip-title">{yr} · {labels.forecast}</div>
          <div className="tip-row"><strong>{fmtInt(fc.mean[j])}</strong> {labels.articles}</div>
          <div className="tip-row tip-muted">{labels.range80(fmtInt(fc.lo80[j]), fmtInt(fc.hi80[j]))}</div>
        </>
      )
    }
    if (nowcast && nowcast.year === yr) return (<><div className="tip-title">{yr}</div><div className="tip-row"><strong>{fmtInt(nowcast.mean)}</strong> {labels.articles}</div></>)
    return null
  }
  return (
    <div ref={ref} className="tr-host">
      <svg className="tr" width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={labels.name}>
        {ticks.map((v) => (
          <g key={v}>
            <line x1={M.l} x2={W - M.r} y1={y(v)} y2={y(v)} className={v === 0 ? 'tr-base' : 'tr-gl'} />
            <text x={M.l - 8} y={y(v) + 4} textAnchor="end" className="tr-tick">{fmtCompact(v)}</text>
          </g>
        ))}
        {yearTicks.map((yr) => (
          <text key={yr} x={x(yr)} y={H - M.b + 18} textAnchor="middle" className="tr-tick">{yr}</text>
        ))}
        {fc ? (
          <>
            <rect x={x(last + 0.5)} y={M.t} width={Math.max(0, W - M.r - x(last + 0.5))} height={H - M.b - M.t} className="tr-fzone" />
            <text x={x(last + 0.5) + 6} y={M.t + 12} className="tr-flabel">{labels.forecast}</text>
            <path d={band(fc.lo95, fc.hi95)} className="tr-band95" />
            <path d={band(fc.lo80, fc.hi80)} className="tr-band" />
          </>
        ) : null}
        <path d={area} className="tr-area" />
        <path d={line} className="tr-line" />
        {fc ? <path d={meanLine} className="tr-fline" /> : null}
        <circle cx={x(last)} cy={y(lastV)} r={4} className="tr-end" />
        <text x={x(last) - 8} y={y(lastV) - 10} textAnchor="end" className="tr-endlabel">{fmtInt(lastV)}</text>
        {nowcast ? <path transform={`translate(${x(nowcast.year)},${y(nowcast.mean)})`} d={glyphPath('WATCH', 4.4)} className="tr-now" /> : null}
        {hover !== null ? <line x1={x(hover)} x2={x(hover)} y1={M.t} y2={H - M.b} className="tr-cross" /> : null}
        <rect
          x={M.l}
          y={M.t}
          width={W - M.l - M.r}
          height={H - M.t - M.b}
          className="tr-hit"
          onPointerMove={(e) => {
            const r = e.currentTarget.ownerSVGElement?.getBoundingClientRect()
            if (!r) return
            const yr = Math.max(first, Math.min(end, Math.round(x.invert(((e.clientX - r.left) * W) / r.width))))
            setHover(yr)
            const c = content(yr)
            if (c) tip.show(c, e.clientX, e.clientY, e.currentTarget)
          }}
          onPointerLeave={() => {
            setHover(null)
            tip.hide()
          }}
        />
      </svg>
    </div>
  )
}
