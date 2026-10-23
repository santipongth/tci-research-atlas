import { useStrings } from '../lib/i18n'
import { useElementSize } from '../lib/useElementSize'
import { editorViz } from '../strings/editorViz'
import type { LineSeries } from './MultiLineChart'
import { niceTicks } from './scale'
import { SERIES_DASHES } from './series'

/**
 * One small chart per topic, every panel on the same vertical scale (so heights compare across panels): the topic's own
 * line in its series colour and dash, the others as faint grey context, the first and last year, and the latest value
 * printed at the end. Loaded on demand from /compare (the page is in the entry chunk).
 */
export default function SmallMultiples({ years, series, format, axisFormat, mono = false }: {
  years: readonly number[]
  series: readonly LineSeries[]
  format: (v: number) => string
  axisFormat: (v: number, step: number) => string
  /** every panel's own line in the brand blue (solid), the others grey — series colours belong to the compare pages */
  mono?: boolean
}) {
  const s = useStrings(editorViz)
  const [ref, { width: W }] = useElementSize<HTMLDivElement>()
  const values = series.flatMap((x) => x.values.filter((v): v is number => v !== null))
  const maxV = Math.max(0, ...values)
  const ticks = niceTicks(0, maxV * 1.05 || 1, 3)
  const step = ticks.length > 1 ? ticks[1] - ticks[0] : 0
  if (step > 0 && ticks[ticks.length - 1] < maxV) ticks.push(Math.round((ticks[ticks.length - 1] + step) * 1e9) / 1e9)
  const yMax = Math.max(ticks[ticks.length - 1] ?? 1, maxV) || 1
  const cols = W >= 640 ? 2 : 1
  const pw = W > 0 ? Math.floor((W - (cols - 1) * 24) / cols) : 0
  const ph = 150
  const M = { t: 10, r: 64, b: 24, l: 44 }
  const x = (i: number) => M.l + (years.length > 1 ? (i / (years.length - 1)) * (pw - M.l - M.r) : 0)
  const y = (v: number) => M.t + (ph - M.t - M.b) * (1 - v / yMax)
  const path = (vals: readonly (number | null)[]) => {
    let d = ''
    let pen = false
    vals.forEach((v, i) => {
      if (v === null) {
        pen = false
        return
      }
      d += `${pen ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`
      pen = true
    })
    return d
  }
  return (
    <div ref={ref} className="smx-host">
      {pw > 0 ? (
        <ul className={`smx smx-${cols}`}>
          {series.map((x0, k) => {
            const slot = x0.slot ?? k
            const stroke = mono ? 'var(--brand)' : `var(--series-${slot + 1})`
            const dash = mono ? undefined : SERIES_DASHES[slot]
            const lastI = x0.values.reduce<number>((a, v, i) => (v !== null ? i : a), -1)
            const last = lastI >= 0 ? (x0.values[lastI] as number) : null
            return (
              <li key={x0.id} className="smx-panel">
                <p className="smx-title">
                  <svg width="28" height="10" aria-hidden="true" focusable="false">
                    <line x1="0" x2="28" y1="5" y2="5" style={{ stroke }} strokeWidth="3" strokeDasharray={dash} />
                  </svg>
                  <span>{x0.label}</span>
                </p>
                <svg width={pw} height={ph} viewBox={`0 0 ${pw} ${ph}`} role="img" aria-label={s('sm.label', { t: x0.label, values: x0.values.map((v, i) => `${years[i]} ${v === null ? '–' : format(v)}`).join(', ') })}>
                  {ticks.map((v) => (
                    <g key={v}>
                      <line x1={M.l} x2={pw - M.r} y1={y(v)} y2={y(v)} className={v === 0 ? 'tr-base' : 'tr-gl'} />
                      <text x={M.l - 6} y={y(v)} dy="0.35em" textAnchor="end" className="tr-tick">{axisFormat(v, step)}</text>
                    </g>
                  ))}
                  <text x={M.l} y={ph - 6} className="tr-tick">{years[0]}</text>
                  <text x={pw - M.r} y={ph - 6} textAnchor="end" className="tr-tick">{years[years.length - 1]}</text>
                  {series.map((o, j) => (j === k ? null : <path key={o.id} d={path(o.values)} className="smx-ctx" />))}
                  <path d={path(x0.values)} className="ml-line" style={{ stroke }} strokeDasharray={dash} />
                  {last !== null ? (
                    <>
                      <circle cx={x(lastI)} cy={y(last)} r={4} className="ml-end" style={{ fill: stroke }} />
                      <text x={x(lastI) + 8} y={y(last)} dy="0.35em" className="ml-label">{format(last)}</text>
                    </>
                  ) : null}
                </svg>
              </li>
            )
          })}
        </ul>
      ) : null}
      <p className="note">{s('sm.same')}</p>
    </div>
  )
}
