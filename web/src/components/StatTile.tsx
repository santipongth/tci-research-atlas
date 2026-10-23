import type { ReactNode } from 'react'
import { useI18n } from '../lib/i18n'

export interface StatDelta {
  /** the change as printed ("+1,204", "+0.4 จุด") */
  text: string
  /** direction of the change as printed: 1 up, −1 down, 0 none (no arrow) */
  dir: number
  /** what it is compared with ("จาก 2026Q3") */
  ref: string
}

/** A grid of stat tiles (a description list). `cols` is the desktop column count; phones show two. */
export function StatGrid({ cols = 3, children, className }: { cols?: 2 | 3 | 4; children: ReactNode; className?: string }) {
  return <dl className={`stats stats-${cols}${className ? ` ${className}` : ''}`}>{children}</dl>
}

/**
 * Ink-only sparkline: a 2 px line and the latest point, scaled to its own range. Decorative (aria-hidden):
 * the tile gives the same numbers in text (`trendText`).
 */
export function Sparkline({ values }: { values: readonly (number | null)[] }) {
  const pts = values.map((v, i) => (v === null || !Number.isFinite(v) ? null : { i, v }))
  const ok = pts.filter((p): p is { i: number; v: number } => p !== null)
  if (ok.length < 2) return null
  const W = 120
  const H = 28
  const lo = Math.min(...ok.map((p) => p.v))
  const hi = Math.max(...ok.map((p) => p.v))
  const x = (i: number) => 2 + (i / Math.max(1, values.length - 1)) * (W - 4)
  const y = (v: number) => (hi === lo ? H / 2 : H - 3 - ((v - lo) / (hi - lo)) * (H - 6))
  let d = ''
  let pen = false
  for (const p of pts) {
    if (!p) {
      pen = false
      continue
    }
    d += `${pen ? 'L' : 'M'}${x(p.i).toFixed(1)},${y(p.v).toFixed(1)}`
    pen = true
  }
  const last = ok[ok.length - 1]
  return (
    <svg className="spark" viewBox={`0 0 ${W} ${H}`} width={W} height={H} aria-hidden="true" focusable="false">
      <path d={d} className="spark-line" />
      <circle cx={x(last.i)} cy={y(last.v)} r={3} className="spark-end" />
    </svg>
  )
}

/**
 * One key figure: a plain label, the big number (`--fs-tile`), an optional change vs the previous release, an optional
 * ink-only sparkline, a short line of context and an optional "เช่น …" example. Must sit inside a `StatGrid`.
 * A long text value (e.g. "ใหม่ — ไม่มีในช่วงฐาน") is set at the lead size instead of the tile size.
 */
export function StatTile({ label, value, sub, delta, trend, trendText, example, wide = false, children }: {
  label: ReactNode
  value: ReactNode
  sub?: ReactNode
  delta?: StatDelta | null
  trend?: readonly (number | null)[]
  /** the sparkline's numbers in words, for screen readers */
  trendText?: string
  example?: ReactNode
  /** spans two columns (e.g. a tile with an interval whisker; the whole row on phones); 'phone' = the whole row on phones only */
  wide?: boolean | 'phone'
  children?: ReactNode
}) {
  const { t } = useI18n()
  const isText = typeof value === 'string' && value.length > 12
  return (
    <div className={`stat${wide === 'phone' ? ' is-wide-phone' : wide ? ' is-wide' : ''}`}>
      <dt className="stat-label">{label}</dt>
      <dd className="stat-body">
        <span className={`stat-v${isText ? ' is-text' : ''}`}>{value}</span>
        {delta ? (
          <span className={delta.dir < 0 ? 'stat-d is-down' : 'stat-d'}>
            {delta.dir !== 0 ? (
              <svg viewBox="0 0 10 10" aria-hidden="true" focusable="false">
                <path d={delta.dir > 0 ? 'M5 1.5L9 7.5H1z' : 'M5 8.5L9 2.5H1z'} fill="currentColor" />
              </svg>
            ) : null}
            <span>{delta.text}</span>
            <span className="stat-dref">{delta.ref}</span>
          </span>
        ) : null}
        {trend ? <Sparkline values={trend} /> : null}
        {trend && trendText ? <span className="sr-only">{trendText}</span> : null}
        {sub ? <span className="stat-sub">{sub}</span> : null}
        {children}
        {example ? (
          <span className="stat-eg">
            <b>{t('stat.example')}</b> {example}
          </span>
        ) : null}
      </dd>
    </div>
  )
}
