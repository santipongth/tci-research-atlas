import { useState } from 'react'
import { useTooltip } from '../lib/tooltip'
import { useElementSize } from '../lib/useElementSize'
import { linear, niceTicks } from './scale'
import { SERIES_DASHES } from './series'

export interface LineSeries {
  id: string
  label: string
  values: readonly (number | null)[]
  /** colour/dash slot 0–3 (default: the series' position) — keeps a topic's colour when another one is removed */
  slot?: number
}

const graphemes = typeof Intl !== 'undefined' && 'Segmenter' in Intl ? new Intl.Segmenter('th', { granularity: 'grapheme' }) : null

/** Shorten a label to `max` characters without splitting a Thai consonant from its vowel or tone marks. */
function clip(text: string, max: number): string {
  const parts = graphemes ? [...graphemes.segment(text)].map((g) => g.segment) : [...text]
  return parts.length > max ? `${parts.slice(0, max - 1).join('')}…` : text
}

/** 2–4 series overlaid on one axis (R10); end labels on wide screens, the legend always; crosshair + tooltip. */
export function MultiLineChart({ years, series, format, axisFormat, label }: {
  years: readonly number[]
  series: readonly LineSeries[]
  format: (v: number) => string
  axisFormat: (v: number) => string
  label: string
}) {
  const [ref, { width: W }] = useElementSize<HTMLDivElement>()
  const tip = useTooltip()
  const [hover, setHover] = useState<number | null>(null)
  if (W === 0 || years.length === 0 || series.length === 0) return <div ref={ref} className="ml-host" />
  const slotOf = (k: number) => series[k].slot ?? k
  const narrow = W < 520
  const H = Math.round(Math.max(260, Math.min(380, W * 0.55)))
  const M = { t: 18, r: narrow ? 12 : 170, b: 32, l: 56 }
  const values = series.flatMap((s) => s.values.filter((v): v is number => v !== null))
  const maxV = Math.max(0, ...values)
  const ticks = niceTicks(0, maxV * 1.05 || 1, 4)
  // the top gridline sits above the highest value, so the peak can be read off the axis
  const tickStep = ticks.length > 1 ? ticks[1] - ticks[0] : 0
  if (tickStep > 0 && ticks[ticks.length - 1] < maxV) ticks.push(Math.round((ticks[ticks.length - 1] + tickStep) * 1e9) / 1e9)
  const yMax = Math.max(ticks[ticks.length - 1] ?? 1, maxV * 1.08) || 1
  const first = years[0]
  const last = years[years.length - 1]
  const x = linear(first, last === first ? first + 1 : last, M.l, W - M.r)
  const y = linear(0, yMax, H - M.b, M.t)
  const path = (vals: readonly (number | null)[]) => {
    let d = ''
    let pen = false
    vals.forEach((v, i) => {
      if (v === null) {
        pen = false
        return
      }
      d += `${pen ? 'L' : 'M'}${x(years[i]).toFixed(1)},${y(v).toFixed(1)}`
      pen = true
    })
    return d
  }
  const ends = series
    .map((s, i) => {
      let j = s.values.length - 1
      while (j >= 0 && s.values[j] === null) j--
      return j < 0 ? null : { i, x: x(years[j]), y: y(s.values[j] as number), text: s.label }
    })
    .filter((e): e is { i: number; x: number; y: number; text: string } => e !== null)
    .sort((a, b) => a.y - b.y)
  const labels = ends.reduce<{ i: number; x: number; y: number; ly: number; text: string }[]>((acc, e) => {
    const prev = acc[acc.length - 1]
    return [...acc, { ...e, ly: prev ? Math.max(e.y, prev.ly + 16) : e.y }]
  }, [])
  const step = narrow ? 3 : 2
  const yearTicks = years.filter((yr, i) => i === years.length - 1 || (yr - first) % step === 0)
  const content = (yr: number) => {
    const i = years.indexOf(yr)
    return (
      <>
        <div className="tip-title">{yr}</div>
        {series.map((s, k) => (
          <div className="tip-row" key={s.id}>
            <svg className="tip-swatch" width="22" height="8" aria-hidden="true" focusable="false">
              <line x1="0" x2="22" y1="4" y2="4" style={{ stroke: `var(--series-${slotOf(k) + 1})` }} strokeWidth="3" strokeDasharray={SERIES_DASHES[slotOf(k)]} />
            </svg>{' '}
            <strong>{s.values[i] === null || s.values[i] === undefined ? '–' : format(s.values[i] as number)}</strong> {s.label}
          </div>
        ))}
      </>
    )
  }
  return (
    <div ref={ref} className="ml-host">
      <svg className="ml" width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label}>
        {ticks.map((v) => (
          <g key={v}>
            <line x1={M.l} x2={W - M.r} y1={y(v)} y2={y(v)} className={v === 0 ? 'tr-base' : 'tr-gl'} />
            <text x={M.l - 8} y={y(v) + 4} textAnchor="end" className="tr-tick">{axisFormat(v)}</text>
          </g>
        ))}
        {yearTicks.map((yr) => (
          <text key={yr} x={x(yr)} y={H - M.b + 18} textAnchor="middle" className="tr-tick">{yr}</text>
        ))}
        {series.map((s, k) => (
          <path key={s.id} d={path(s.values)} className="ml-line" style={{ stroke: `var(--series-${slotOf(k) + 1})` }} strokeDasharray={SERIES_DASHES[slotOf(k)]} />
        ))}
        {ends.map((e) => (
          <circle key={e.i} cx={e.x} cy={e.y} r={3.5} className="ml-end" style={{ fill: `var(--series-${slotOf(e.i) + 1})` }} />
        ))}
        {narrow
          ? null
          : labels.map((l) => (
              <text key={l.i} x={l.x + 8} y={l.ly + 4} className="ml-label">{clip(l.text, 24)}</text>
            ))}
        {hover !== null ? <line x1={x(hover)} x2={x(hover)} y1={M.t} y2={H - M.b} className="tr-cross" /> : null}
        <rect
          x={M.l}
          y={M.t}
          width={Math.max(0, W - M.l - M.r)}
          height={H - M.t - M.b}
          className="tr-hit"
          onPointerMove={(e) => {
            const r = e.currentTarget.ownerSVGElement?.getBoundingClientRect()
            if (!r) return
            const yr = Math.max(first, Math.min(last, Math.round(x.invert(((e.clientX - r.left) * W) / r.width))))
            setHover(yr)
            tip.show(content(yr), e.clientX, e.clientY)
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
