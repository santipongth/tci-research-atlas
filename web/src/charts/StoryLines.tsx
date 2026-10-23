import { useState } from 'react'
import { LABEL_PX } from '../lib/labelSizes'
import { fitText, textWidth } from '../lib/measure'
import { spreadLabels } from '../lib/story'
import { useElementSize } from '../lib/useElementSize'
import { useFontsVersion } from '../lib/useFontsVersion'
import { niceTicks } from './scale'

export interface StorySeries {
  id: string
  label: string
  values: readonly (number | null)[]
}

/**
 * The front door's story chart: every series as a quiet grey line, the one in focus in TCI blue with an orange end
 * mark, and a direct label at the end of each line (no legend). Pointing at a line or label, or tabbing to a label,
 * moves the focus; each end label (a button) carries its series' name and last value for keyboard and screen-reader users. The lines
 * draw once on arrival (already drawn under reduced motion).
 */
export function StoryLines({ years, series, initial, format, label, note, height }: {
  years: readonly number[]
  series: readonly StorySeries[]
  /** the series in focus before the reader points anywhere (the answer) */
  initial: string
  format: (v: number) => string
  label: string
  /** one short line written on the chart beside the focused series' end */
  note?: (s: StorySeries, last: number) => string
  /** the chart's height in px (default 420, 300 when narrow) */
  height?: number
}) {
  const [ref, { width }] = useElementSize<HTMLDivElement>()
  const [focus, setFocus] = useState(initial)
  useFontsVersion() // end labels are measured in Sarabun: measure again once it has loaded
  const narrow = width > 0 && width < 560
  const W = width
  const H = height ?? (narrow ? 300 : 420)
  const M = { t: 24, r: narrow ? 12 : 250, b: 34, l: 44 }
  const values = series.flatMap((s) => s.values.filter((v): v is number => v !== null))
  const max = Math.max(1, ...values)
  const ticks = niceTicks(0, max, 4)
  const step = ticks.length > 1 ? ticks[1] - ticks[0] : 0
  if (step > 0 && ticks[ticks.length - 1] < max) ticks.push(Math.round((ticks[ticks.length - 1] + step) * 1e9) / 1e9)
  const top = Math.max(max, ticks[ticks.length - 1] ?? max)
  const x = (i: number) => M.l + (years.length > 1 ? (i / (years.length - 1)) * (W - M.l - M.r) : 0)
  const y = (v: number) => M.t + (H - M.t - M.b) * (1 - v / top)
  const lastOf = (s: StorySeries) => {
    const i = s.values.reduce<number>((a, v, k) => (v !== null ? k : a), -1)
    return i < 0 ? null : { i, v: s.values[i] as number }
  }
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
  const ends = series.map(lastOf)
  const on = series.find((s) => s.id === focus) ?? series[0]
  const onEnd = on ? lastOf(on) : null
  // the focused label sits exactly at its end mark; the others make room around it
  const labelY = spreadLabels(ends.map((e) => (e ? y(e.v) : M.t)), 26, M.t + 6, H - M.b, series.indexOf(on))
  // the note points at the rise: anchored one year before the end, written above-left with a dashed leader
  const noteAt = onEnd && on && onEnd.i > 0 && on.values[onEnd.i - 1] !== null ? { i: onEnd.i - 1, v: on.values[onEnd.i - 1] as number } : null
  // the focused line is drawn last so it sits on top
  const order = [...series].sort((a, b) => Number(a.id === on?.id) - Number(b.id === on?.id))
  return (
    // a labelled group, not role="img": the end labels inside are buttons
    <div ref={ref} className="sl-host" role="group" aria-label={label}>
      {W > 0 ? (
        <svg className="sl" width={W} height={H} viewBox={`0 0 ${W} ${H}`} onMouseLeave={() => setFocus(initial)}>
          {ticks.map((v) => (
            <g key={v}>
              <line x1={M.l} x2={W - M.r} y1={y(v)} y2={y(v)} className={v === 0 ? 'sl-base' : 'sl-grid'} />
              <text x={M.l - 10} y={y(v)} dy="0.35em" textAnchor="end" className="sl-tick">{format(v)}</text>
            </g>
          ))}
          <text x={M.l} y={H - 8} className="sl-tick">{years[0]}</text>
          <text x={W - M.r} y={H - 8} textAnchor="end" className="sl-tick">{years[years.length - 1]}</text>
          {order.map((s) => (
            <g key={s.id} className={s.id === on?.id ? 'sl-series is-on' : 'sl-series'} onMouseEnter={() => setFocus(s.id)}>
              <path d={path(s.values)} className="sl-hit" />
              <path d={path(s.values)} className="sl-line" pathLength={1} />
            </g>
          ))}
          {onEnd && on ? <circle cx={x(onEnd.i)} cy={y(onEnd.v)} r={6.5} className="sl-end" /> : null}
          {onEnd && on && note && noteAt && !narrow ? (
            <g aria-hidden="true">
              <line x1={x(noteAt.i) - 30} y1={Math.max(M.t + 10, y(noteAt.v) - 56) + 6} x2={x(noteAt.i) - 5} y2={y(noteAt.v) - 6} className="sl-note-lead" />
              <text x={x(noteAt.i) - 36} y={Math.max(M.t + 10, y(noteAt.v) - 56)} textAnchor="end" className="sl-note">{note(on, onEnd.v)}</text>
            </g>
          ) : null}
          {narrow
            ? null
            : series.map((s, k) => {
                const e = ends[k]
                if (!e) return null
                // a long name (60–90 Thai characters) is cut with "…" inside the plot's right gutter; the value always shows
                // and the full name is in the label's <title>
                const value = ` ${format(e.v)}`
                const room = W - (x(e.i) + 24) - 4 - textWidth(value, LABEL_PX.strong, 700)
                const name = fitText(s.label, room, LABEL_PX.strong, 700)
                return (
                  <g
                    key={s.id}
                    className={s.id === on?.id ? 'sl-lab is-on' : 'sl-lab'}
                    tabIndex={0}
                    role="button"
                    aria-pressed={s.id === on?.id}
                    onMouseEnter={() => setFocus(s.id)}
                    onFocus={() => setFocus(s.id)}
                    onClick={() => setFocus(s.id)}
                  >
                    {/* the full name reaches readers through <title>, not aria-label: an aria-label that does not
                        start with the visible (cut) text breaks WCAG 2.5.3 "label in name" */}
                    {name !== s.label ? <title>{`${s.label}${value}`}</title> : null}
                    <line x1={x(e.i) + 9} x2={x(e.i) + 18} y1={y(e.v)} y2={labelY[k]} className="sl-leader" />
                    <text x={x(e.i) + 24} y={labelY[k]} dy="0.35em">
                      <tspan className="sl-name">{name}</tspan>
                      <tspan className="sl-val">{value}</tspan>
                    </text>
                  </g>
                )
              })}
        </svg>
      ) : null}
      {narrow ? (
        <ul className="sl-keys">
          {series.map((s, k) => {
            const e = ends[k]
            return (
              <li key={s.id}>
                <button type="button" className={s.id === on?.id ? 'sl-key is-on' : 'sl-key'} aria-pressed={s.id === on?.id} onClick={() => setFocus(s.id)}>
                  <span className="sl-sw" aria-hidden="true" />
                  <span className="sl-name">{s.label}</span>
                  {e ? <span className="sl-val">{format(e.v)}</span> : null}
                </button>
              </li>
            )
          })}
        </ul>
      ) : null}
    </div>
  )
}
