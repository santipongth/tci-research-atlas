import { fmtPct } from '../lib/format'

/** A share 0–1 as a thin bar plus its number (the number carries the meaning; the bar is decoration). */
export function ShareBar({ value, digits = 0, max = 1 }: { value: number | null | undefined; digits?: number; max?: number }) {
  if (value === null || value === undefined || !Number.isFinite(value)) return <span className="sbar-na">–</span>
  const pct = Math.max(0, Math.min(100, (value / (max || 1)) * 100))
  return (
    <span className="sbar-cell">
      <span className="sbar" aria-hidden="true">
        <span className="sbar-fill" style={{ width: `${pct}%` }} />
      </span>
      <span className="sbar-num">{fmtPct(value, digits)}</span>
    </span>
  )
}
