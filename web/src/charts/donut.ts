/** Donut layout: one ring segment per value, clockwise from 12 o'clock, in the input order. Pure (tested). */

export interface DonutInput {
  key: string
  value: number
}

export interface DonutArc {
  key: string
  value: number
  /** share of the total, 0…1 */
  frac: number
  /** angles in radians, 0 = 12 o'clock, clockwise */
  start: number
  end: number
  /** SVG path of the ring segment ('' for an empty value) */
  d: string
}

const TAU = Math.PI * 2
const pt = (cx: number, cy: number, r: number, a: number) => `${(cx + r * Math.sin(a)).toFixed(2)},${(cy - r * Math.cos(a)).toFixed(2)}`

/** One ring segment between angles a0 < a1 (a1 − a0 < 2π), outer radius r1, inner radius r0. */
function segment(cx: number, cy: number, r0: number, r1: number, a0: number, a1: number): string {
  const large = a1 - a0 > Math.PI ? 1 : 0
  return `M${pt(cx, cy, r1, a0)}A${r1},${r1} 0 ${large} 1 ${pt(cx, cy, r1, a1)}L${pt(cx, cy, r0, a1)}A${r0},${r0} 0 ${large} 0 ${pt(cx, cy, r0, a0)}Z`
}

/**
 * The ring segments of `values` around (cx, cy). Values that are not finite or ≤ 0 keep their place with an empty path
 * (so a legend can still list them). A single segment that fills the ring is drawn as two halves (an SVG arc cannot
 * start and end on the same point).
 */
export function donutArcs(values: readonly DonutInput[], cx: number, cy: number, r0: number, r1: number): DonutArc[] {
  const clean = values.map((v) => ({ key: v.key, value: Number.isFinite(v.value) && v.value > 0 ? v.value : 0 }))
  const total = clean.reduce((s, v) => s + v.value, 0)
  let at = 0
  return clean.map((v) => {
    const frac = total > 0 ? v.value / total : 0
    const start = at
    const end = at + frac * TAU
    at = end
    let d = ''
    if (frac >= 1 - 1e-9) d = segment(cx, cy, r0, r1, 0, Math.PI) + segment(cx, cy, r0, r1, Math.PI, TAU)
    else if (frac > 0) d = segment(cx, cy, r0, r1, start, end)
    return { key: v.key, value: v.value, frac, start, end, d }
  })
}
