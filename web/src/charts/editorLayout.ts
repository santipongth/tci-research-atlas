/*
 * Pure layout helpers for the editors' and researchers' infographics (web refresh, batch 6): the journals scatter,
 * the then-vs-now topic mix of one journal, the record checklist, the keyword risers, the galaxy's example picks and
 * the references' average marker. Nothing here touches the DOM, so every rule is unit-tested (editorLayout.test.ts).
 */
import type { Box } from './execLayout'
import { niceTicks } from './scale'

/* ---------- journals scatter: complete records (0–100) × authors from the owner (0–1) ---------- */

export interface ScatterPoint {
  id: string
  label: string
  /** complete-records score, 0–100 */
  x: number
  /** share of articles with an author from the owner institution, 0–1 */
  y: number
  /** articles in the window — label priority only (bigger journals are named first) */
  weight: number
  /** the owner was inferred from the articles, not the registry: drawn hollow */
  inferred: boolean
}

export interface ScatterLayout {
  x: (v: number) => number
  y: (v: number) => number
  xTicks: number[]
  yTicks: number[]
  /** spacing of the y ticks (for the tick decimals) */
  yStep: number
  plot: Box
  /** the band above the in-house bar (y > yRef), or null when the release has no bar */
  zone: Box | null
}

/**
 * x is fixed 0–100 (the score is out of 100); y runs from 0 to a round tick past the highest share and the bar, so the
 * bar always sits inside the plot and the zone above it is labelled.
 */
export function scatterLayout(points: readonly ScatterPoint[], opts: { width: number; height: number; margin: { t: number; r: number; b: number; l: number }; yRef?: number | null }): ScatterLayout {
  const { width, height, margin: m } = opts
  const ys = points.map((p) => p.y).filter(Number.isFinite)
  const ref = typeof opts.yRef === 'number' && Number.isFinite(opts.yRef) ? opts.yRef : null
  const hi = Math.max(0.1, ref ?? 0, ...ys)
  const raw = niceTicks(0, hi * 1.06, 4)
  const step = raw.length > 1 ? raw[1] - raw[0] : hi
  const top = Math.ceil(hi * 1.06 / step - 1e-9) * step
  const yTicks: number[] = []
  for (let v = 0; v <= top + step * 1e-9; v += step) yTicks.push(Math.round(v * 1e9) / 1e9)
  const d1 = yTicks[yTicks.length - 1] || 1
  const plot = { x: m.l, y: m.t, w: Math.max(10, width - m.l - m.r), h: Math.max(10, height - m.t - m.b) }
  const x = (v: number) => plot.x + (Math.max(0, Math.min(100, v)) / 100) * plot.w
  const y = (v: number) => plot.y + plot.h - (Math.max(0, Math.min(d1, v)) / d1) * plot.h
  const zone = ref !== null && ref < d1 ? { x: plot.x, y: plot.y, w: plot.w, h: Math.max(0, y(ref) - plot.y) } : null
  return { x, y, xTicks: [0, 20, 40, 60, 80, 100], yTicks, yStep: step, plot, zone }
}

/** Which journals get a name on the chart, most important first: above the bar first, then the largest. */
export function labelOrder(points: readonly ScatterPoint[], yRef: number | null | undefined): ScatterPoint[] {
  const above = (p: ScatterPoint) => (typeof yRef === 'number' && p.y > yRef ? 1 : 0)
  return [...points].sort((a, b) => above(b) - above(a) || b.weight - a.weight || a.id.localeCompare(b.id))
}

/* ---------- one journal's topic mix, then vs now ---------- */

export interface PeriodRow {
  topic: string
  before: number
  after: number
}

/**
 * The topics whose share moved most (the journal's gained + lost lists, `top` largest by their bigger share), and the
 * rest of each period as "other" — so both bars add up to 100 % and the same topic keeps its place and shade in both.
 */
export function periodMix(shifts: readonly { topic: string; share_before: number; share_after: number }[], top = 4): { rows: PeriodRow[]; other: { before: number; after: number } } {
  const seen = new Set<string>()
  const clean: PeriodRow[] = []
  for (const s of shifts) {
    if (seen.has(s.topic) || !Number.isFinite(s.share_before) || !Number.isFinite(s.share_after)) continue
    seen.add(s.topic)
    clean.push({ topic: s.topic, before: Math.max(0, s.share_before), after: Math.max(0, s.share_after) })
  }
  const rows = clean.sort((a, b) => Math.max(b.before, b.after) - Math.max(a.before, a.after) || a.topic.localeCompare(b.topic)).slice(0, top)
  const sum = (k: 'before' | 'after') => rows.reduce((n, r) => n + r[k], 0)
  return { rows, other: { before: Math.max(0, 1 - sum('before')), after: Math.max(0, 1 - sum('after')) } }
}

/* ---------- record checklist ---------- */

export type CheckState = 'full' | 'partial' | 'none' | 'unknown'

/** Share of articles from which an item counts as "there" (✓): 95 %. */
export const CHECK_FULL = 0.95
/** At or under 5 % the item is "missing", not "partial". */
export const CHECK_NONE = 0.05

/** ✓ when nearly every article has the item, partial in between, missing when almost none has it; null = not checked. */
export function checkState(rate: number | null | undefined): CheckState {
  if (rate === null || rate === undefined || !Number.isFinite(rate)) return 'unknown'
  if (rate >= CHECK_FULL) return 'full'
  if (rate <= CHECK_NONE) return 'none'
  return 'partial'
}

/* ---------- keyword risers ---------- */

export interface Riser {
  /** mean share of the first two years and of the last two (0–1) */
  from: number
  to: number
  firstYear: number
  lastYear: number
}

/** The change a riser chip prints: the mean share of the first two years → of the last two (null when not computable). */
export function riserOf(years: readonly number[], shares: readonly (number | null)[]): Riser | null {
  const n = Math.min(years.length, shares.length)
  if (n < 4) return null
  const [a, b, c, d] = [shares[0], shares[1], shares[n - 2], shares[n - 1]]
  if (a === null || b === null || c === null || d === null) return null
  return { from: (a + b) / 2, to: (c + d) / 2, firstYear: years[0], lastYear: years[n - 1] }
}

/* ---------- galaxy: three example articles from different fields ---------- */

/**
 * One article per field, for the first `n` fields in `slots` order (largest first): the article nearest its field's
 * centre (the most typical place), skipping articles without a topic. Returns point indices.
 */
export function galaxyPicks(pts: { count: number; wx: ArrayLike<number>; wy: ArrayLike<number>; slot: ArrayLike<number>; topic: ArrayLike<number> }, slots: readonly number[], n = 3): number[] {
  const out: number[] = []
  for (const s of slots) {
    if (out.length >= n) break
    let sx = 0
    let sy = 0
    let k = 0
    for (let i = 0; i < pts.count; i++) {
      if (pts.slot[i] !== s || pts.topic[i] < 0) continue
      sx += pts.wx[i]
      sy += pts.wy[i]
      k++
    }
    if (k === 0) continue
    const cx = sx / k
    const cy = sy / k
    let best = -1
    let bd = Infinity
    for (let i = 0; i < pts.count; i++) {
      if (pts.slot[i] !== s || pts.topic[i] < 0) continue
      const d = (pts.wx[i] - cx) ** 2 + (pts.wy[i] - cy) ** 2
      if (d < bd) {
        bd = d
        best = i
      }
    }
    if (best >= 0) out.push(best)
  }
  return out
}

/* ---------- references: the all-journal average ---------- */

/** Mean of `value` weighted by `weight`, over items where both are finite (null when there are none). */
export function weightedMean<T>(items: readonly T[], value: (x: T) => number | null | undefined, weight: (x: T) => number): number | null {
  let s = 0
  let w = 0
  for (const it of items) {
    const v = value(it)
    const k = weight(it)
    if (v === null || v === undefined || !Number.isFinite(v) || !(k > 0)) continue
    s += v * k
    w += k
  }
  return w > 0 ? s / w : null
}
