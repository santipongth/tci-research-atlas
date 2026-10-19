export interface Linear {
  (v: number): number
  invert(px: number): number
}

export function linear(d0: number, d1: number, r0: number, r1: number): Linear {
  const span = d1 - d0 || 1
  const f = ((v: number) => r0 + ((v - d0) / span) * (r1 - r0)) as Linear
  f.invert = (px: number) => d0 + ((px - r0) / (r1 - r0 || 1)) * span
  return f
}

/** Log10 scale; values ≤ 0 are drawn at the lower end. */
export function logScale(d0: number, d1: number, r0: number, r1: number): (v: number) => number {
  const l0 = Math.log10(d0)
  const l1 = Math.log10(d1)
  return (v: number) => r0 + ((Math.log10(Math.max(v, d0)) - l0) / (l1 - l0 || 1)) * (r1 - r0)
}

/** Round tick values (1, 2, 5 × 10ⁿ) covering [lo, hi]. */
export function niceTicks(lo: number, hi: number, count: number): number[] {
  const span = hi - lo
  if (!(span > 0)) return [lo]
  let step = 10 ** Math.floor(Math.log10(span / count))
  const err = (count / span) * step
  if (err <= 0.15) step *= 10
  else if (err <= 0.35) step *= 5
  else if (err <= 0.75) step *= 2
  const out: number[] = []
  for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-9; v += step) out.push(Math.round(v * 1e9) / 1e9)
  return out
}

/** Ticks for a count axis from 0: whole numbers only, so a small series never shows "2, 2, 1, 1, 0". */
export function countTicks(hi: number, count: number): number[] {
  const whole = niceTicks(0, hi, count).filter(Number.isInteger)
  if (whole.length >= 2) return whole
  return Array.from({ length: Math.max(2, Math.ceil(hi) + 1) }, (_, i) => i)
}

/**
 * Axis domain from the data: every finite value plus the `include` marks (zero, a threshold), padded by `pad` × span,
 * and limited to `cap` — a value beyond the cap is drawn at the edge (with its number) instead of flattening the rest.
 */
export function dataDomain(values: readonly (number | null | undefined)[], include: readonly number[], cap: readonly [number, number], pad = 0.05): [number, number] {
  const v = [...values.filter((x): x is number => typeof x === 'number' && Number.isFinite(x)), ...include]
  if (v.length === 0) return [cap[0], cap[1]]
  const lo = Math.min(...v)
  const hi = Math.max(...v)
  const span = hi - lo || 0.1
  return [Math.max(cap[0], lo - span * pad), Math.min(cap[1], hi + span * pad)]
}

export function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v))
}
