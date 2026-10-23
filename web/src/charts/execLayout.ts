/*
 * Pure layout helpers for the executive pages' infographics (web refresh, batch 5): the collaboration arc diagram,
 * the column chart's axis, 100 % mix bars, the opportunity quadrant and its labels, status transitions and the goal
 * tile grid. Nothing here touches the DOM, so every rule is unit-tested (execLayout.test.ts).
 */
import { STATUSES, type StatusId } from '../lib/status'
import { niceTicks } from './scale'

/* ---------- text boxes ---------- */

const cp = (n: number) => String.fromCodePoint(n)
/** Combining marks: Latin diacritics, Thai above/below vowels and tone marks. */
const COMBINING = new RegExp(`[${cp(0x300)}-${cp(0x36f)}${cp(0xe31)}${cp(0xe34)}-${cp(0xe3a)}${cp(0xe47)}-${cp(0xe4e)}]`)

/** Approximate rendered width of `text` at `px` (Sarabun): combining Thai marks take no width. */
export function textWidth(text: string, px: number): number {
  let w = 0
  for (const ch of text) {
    if (COMBINING.test(ch)) continue
    w += ch === ' ' ? 0.27 : /[A-Z]/.test(ch) ? 0.62 : /[0-9.,×−+%]/.test(ch) ? 0.55 : 0.53
  }
  return w * px
}

export interface Box {
  x: number
  y: number
  w: number
  h: number
}

export const overlaps = (a: Box, b: Box, pad = 2): boolean =>
  a.x < b.x + b.w + pad && b.x < a.x + a.w + pad && a.y < b.y + b.h + pad && b.y < a.y + a.h + pad

/* ---------- collaboration arc diagram ---------- */

export interface ArcInput {
  nodes: readonly { id: string; weight: number }[]
  links: readonly { a: string; b: string; value: number }[]
}

export interface ArcLink {
  a: string
  b: string
  value: number
  /** row centres of the two ends (top end first) */
  y1: number
  y2: number
  /** how far the arc bulges right of the node axis */
  bulge: number
  /** stroke width, linear in `value` */
  width: number
  /** the joint-article count at the apex, or null when it would collide */
  label: { x: number; y: number } | null
}

export interface ArcLayout {
  nodes: { id: string; y: number }[]
  links: ArcLink[]
  height: number
  /** links not drawn because an end is outside the top `maxNodes` */
  hidden: number
}

/**
 * Institutions as rows (largest first — only those with a partnership), each pair as a half-ellipse to the right of the
 * node axis: the farther apart the rows, the wider the arc; stroke width is linear in joint articles. Apex labels are
 * placed strongest pair first and dropped when they would overlap one already placed.
 */
export function arcLayout({ nodes, links }: ArcInput, opts: { row: number; width: number; maxNodes?: number; minStroke?: number; maxStroke?: number; labelPx?: number }): ArcLayout {
  const { row, width, maxNodes = 10, minStroke = 2, maxStroke = 12, labelPx = 14 } = opts
  const linked = new Set(links.flatMap((l) => [l.a, l.b]))
  const shown = [...nodes].filter((n) => linked.has(n.id)).sort((p, q) => q.weight - p.weight || (p.id < q.id ? -1 : 1)).slice(0, maxNodes)
  const index = new Map(shown.map((n, i) => [n.id, i]))
  const kept = links.filter((l) => index.has(l.a) && index.has(l.b) && l.a !== l.b)
  const maxV = Math.max(1, ...kept.map((l) => l.value))
  const maxSpan = Math.max(1, ...kept.map((l) => Math.abs((index.get(l.a) as number) - (index.get(l.b) as number))))
  const room = Math.max(16, width - maxStroke - textWidth('0000', labelPx) - 12)
  const cy = (i: number) => i * row + row / 2
  const drawn = kept
    .map((l) => {
      const i = index.get(l.a) as number
      const j = index.get(l.b) as number
      const span = Math.abs(i - j)
      return {
        a: l.a,
        b: l.b,
        value: l.value,
        y1: cy(Math.min(i, j)),
        y2: cy(Math.max(i, j)),
        bulge: Math.max(12, (span / maxSpan) * room),
        width: minStroke + (l.value / maxV) * (maxStroke - minStroke),
        label: null as ArcLink['label'],
      }
    })
    .sort((p, q) => q.value - p.value)
  const placed: Box[] = []
  for (const l of drawn) {
    const text = String(l.value)
    const w = textWidth(text, labelPx) + 6
    const h = labelPx * 1.3
    const x = 6 + l.bulge + l.width / 2 + 4
    const y = (l.y1 + l.y2) / 2
    const box = { x, y: y - h / 2, w, h }
    if (x + w <= width + 1 && !placed.some((b) => overlaps(b, box))) {
      placed.push(box)
      l.label = { x, y }
    }
  }
  return {
    nodes: shown.map((n, i) => ({ id: n.id, y: cy(i) })),
    links: drawn,
    height: shown.length * row,
    hidden: links.length - kept.length,
  }
}

/** SVG path of an arc from (x, y1) to (x, y2) bulging `bulge` to the right. */
export function arcPath(x: number, y1: number, y2: number, bulge: number): string {
  const ry = (y2 - y1) / 2
  return `M${x},${y1.toFixed(1)}A${bulge.toFixed(1)},${ry.toFixed(1)} 0 0 1 ${x},${y2.toFixed(1)}`
}

/* ---------- column chart axis ---------- */

/** A zero-based axis whose top tick is at or above the largest value. */
export function columnAxis(values: readonly number[], count = 4): { max: number; ticks: number[] } {
  const hi = Math.max(0, ...values.filter(Number.isFinite))
  if (!(hi > 0)) return { max: 1, ticks: [0, 1] }
  const ticks = niceTicks(0, hi, count)
  const step = ticks.length > 1 ? ticks[1] - ticks[0] : hi
  while (ticks[ticks.length - 1] < hi - 1e-9) ticks.push(Math.round((ticks[ticks.length - 1] + step) * 1e9) / 1e9)
  return { max: ticks[ticks.length - 1], ticks }
}

/* ---------- 100 % mix bar ---------- */

export interface MixSegment {
  key: string
  id?: string | null
  value: number
  /** fraction of the whole bar (0–1) */
  frac: number
  /** where the segment starts (0–1) */
  start: number
  /** the folded remainder ("อื่น ๆ") */
  other: boolean
}

/**
 * The `top` largest parts as segments of one 100 % bar, the rest folded into one "other" segment. `total` is the whole
 * (1 for shares); parts that do not add up to it leave the gap to "other" too.
 */
export function mixSegments(items: readonly { key: string; id?: string | null; value: number }[], opts: { top?: number; total?: number; otherKey: string }): MixSegment[] {
  const { top = 4, otherKey } = opts
  const clean = items.filter((i) => Number.isFinite(i.value) && i.value > 0)
  const sum = clean.reduce((s, i) => s + i.value, 0)
  const total = Math.max(opts.total ?? sum, sum)
  if (!(total > 0)) return []
  const sorted = [...clean].sort((p, q) => q.value - p.value)
  const head = sorted.slice(0, top)
  const rest = total - head.reduce((s, i) => s + i.value, 0)
  const parts = [...head.map((i) => ({ ...i, other: false })), ...(rest > total * 1e-6 ? [{ key: otherKey, id: null, value: rest, other: true }] : [])]
  let start = 0
  return parts.map((p) => {
    const frac = p.value / total
    const seg = { key: p.key, id: p.id ?? null, value: p.value, frac, start, other: p.other }
    start += frac
    return seg
  })
}

/* ---------- opportunity quadrant ---------- */

export interface QuadPoint {
  id: string
  label: string
  /** Thai level vs the world (activity index; 1 = same) */
  x: number
  /** world growth ratio (recent ÷ baseline share) */
  y: number
  /** inside the opportunity zone (from the data, not recomputed) */
  hot: boolean
}

export interface QuadLayout {
  x: (v: number) => number
  y: (v: number) => number
  xTicks: number[]
  yTicks: number[]
  /** the shaded zone (x ≤ xMax, y ≥ yMin), or null when the thresholds are unknown */
  zone: Box | null
  plot: Box
}

const axisOf = (lo: number, hi: number): { d: [number, number]; ticks: number[] } => {
  const ticks = niceTicks(lo, hi, 5)
  const step = ticks.length > 1 ? ticks[1] - ticks[0] : 0.5
  const d0 = Math.floor(lo / step + 1e-9) * step
  const d1 = Math.ceil(hi / step - 1e-9) * step
  const out: number[] = []
  for (let v = d0; v <= d1 + step * 1e-9; v += step) out.push(Math.round(v * 1e9) / 1e9)
  return { d: [d0, d1 > d0 ? d1 : d0 + step], ticks: out }
}

/**
 * Linear axes (no log): x from 0 to past the largest level, always showing 1 ("same as the world"); y around the
 * growth ratios, always showing 1 ("no change") and the threshold. The zone is the top-left corner the data file names.
 */
export function quadrantLayout(points: readonly QuadPoint[], opts: { width: number; height: number; margin: { t: number; r: number; b: number; l: number }; xMax?: number | null; yMin?: number | null }): QuadLayout {
  const { width, height, margin: m } = opts
  const xs = points.map((p) => p.x).filter(Number.isFinite)
  const ys = points.map((p) => p.y).filter(Number.isFinite)
  const xa = axisOf(0, Math.max(1.2, ...xs, opts.xMax ?? 0) * 1.05)
  const yLo = Math.min(1, ...ys, opts.yMin ?? 1)
  const yHi = Math.max(1, ...ys, opts.yMin ?? 1)
  const pad = (yHi - yLo) * 0.08 || 0.1
  const ya = axisOf(Math.max(0, yLo - pad), yHi + pad)
  const plot = { x: m.l, y: m.t, w: Math.max(10, width - m.l - m.r), h: Math.max(10, height - m.t - m.b) }
  const x = (v: number) => plot.x + ((v - xa.d[0]) / (xa.d[1] - xa.d[0])) * plot.w
  const y = (v: number) => plot.y + plot.h - ((v - ya.d[0]) / (ya.d[1] - ya.d[0])) * plot.h
  const zone =
    typeof opts.xMax === 'number' && typeof opts.yMin === 'number'
      ? { x: plot.x, y: plot.y, w: Math.max(0, x(opts.xMax) - plot.x), h: Math.max(0, y(opts.yMin) - plot.y) }
      : null
  return { x, y, xTicks: xa.ticks, yTicks: ya.ticks, zone, plot }
}

export interface PlacedLabel {
  id: string
  text: string
  x: number
  y: number
  anchor: 'start' | 'end' | 'middle'
  box: Box
}

/**
 * Greedy, collision-aware point labels: candidates right, left, above, below each mark (in that order), kept inside
 * `bounds`, clear of every mark (radius `r`), of `avoid` boxes and of labels already placed. Points are tried in the
 * given order (most important first) and at most `max` get a label. `tries` caps how many points are examined at all
 * (a chart of thousands of marks only ever names its first few dozen, so the tests stay cheap and deterministic).
 * `measure` replaces the character estimate with a real measurement (lib/measure.ts, Sarabun on a canvas) in the browser.
 */
export function placeLabels(points: readonly { id: string; text: string; cx: number; cy: number }[], opts: { px: number; r: number; bounds: Box; avoid?: readonly Box[]; max?: number; tries?: number; measure?: (text: string, px: number) => number }): PlacedLabel[] {
  const { px, r, bounds, avoid = [], max = 8, tries = Infinity, measure = textWidth } = opts
  const h = px * 1.35
  const marks = points.map((p) => ({ x: p.cx - r, y: p.cy - r, w: 2 * r, h: 2 * r }))
  const placed: PlacedLabel[] = []
  let examined = 0
  for (const p of points) {
    if (placed.length >= max || examined >= tries) break
    examined += 1
    const w = measure(p.text, px) + 4
    const gap = r + 4
    const cands: { box: Box; x: number; y: number; anchor: PlacedLabel['anchor'] }[] = [
      { box: { x: p.cx + gap, y: p.cy - h / 2, w, h }, x: p.cx + gap, y: p.cy, anchor: 'start' },
      { box: { x: p.cx - gap - w, y: p.cy - h / 2, w, h }, x: p.cx - gap, y: p.cy, anchor: 'end' },
      { box: { x: p.cx - w / 2, y: p.cy - gap - h, w, h }, x: p.cx, y: p.cy - gap - h / 2, anchor: 'middle' },
      { box: { x: p.cx - w / 2, y: p.cy + gap, w, h }, x: p.cx, y: p.cy + gap + h / 2, anchor: 'middle' },
    ]
    const inside = (b: Box) => b.x >= bounds.x && b.y >= bounds.y && b.x + b.w <= bounds.x + bounds.w && b.y + b.h <= bounds.y + bounds.h
    const ok = cands.find((c) => inside(c.box) && !marks.some((mk) => overlaps(mk, c.box, 1)) && !avoid.some((a) => overlaps(a, c.box)) && !placed.some((q) => overlaps(q.box, c.box)))
    if (ok) placed.push({ id: p.id, text: p.text, x: ok.x, y: ok.y, anchor: ok.anchor, box: ok.box })
  }
  return placed
}

/* ---------- status transitions ---------- */

export interface FlowNode {
  status: StatusId
  count: number
  y: number
  h: number
}

export interface FlowLink {
  from: StatusId
  to: StatusId
  count: number
  /** band top and bottom on the left (previous) and right (current) side */
  y0: number
  y0b: number
  y1: number
  y1b: number
  topics: string[]
}

export interface FlowLayout {
  left: FlowNode[]
  right: FlowNode[]
  links: FlowLink[]
  height: number
}

/** Pixels per topic in the status-flow diagram: `maxUnit` for a handful of changes, shrinking so the bands stay within `budget` px however many topics changed. */
export function flowUnit(total: number, maxUnit = 26, budget = 520): number {
  return total > 0 ? Math.min(maxUnit, budget / total) : maxUnit
}

/**
 * Previous status (left) → current status (right), one band per transition whose thickness is its topic count.
 * Nodes are in status order, `unit` px per topic (at least `minH`, so a glyph and a two-line name fit), `gap` apart.
 */
export function statusFlow(changes: readonly { topic: string; previous: string; current: string }[], opts: { unit: number; minH: number; gap: number }): FlowLayout {
  const { unit, minH, gap } = opts
  const ok = changes.filter((c): c is { topic: string; previous: StatusId; current: StatusId } => (STATUSES as readonly string[]).includes(c.previous) && (STATUSES as readonly string[]).includes(c.current))
  const order = (s: StatusId) => STATUSES.indexOf(s)
  const pairs = new Map<string, FlowLink>()
  for (const c of ok) {
    const k = `${c.previous}>${c.current}`
    const l = pairs.get(k) ?? { from: c.previous, to: c.current, count: 0, y0: 0, y0b: 0, y1: 0, y1b: 0, topics: [] }
    l.count += 1
    l.topics.push(c.topic)
    pairs.set(k, l)
  }
  const links = [...pairs.values()].sort((p, q) => order(p.from) - order(q.from) || order(p.to) - order(q.to))
  const column = (side: 'from' | 'to'): FlowNode[] => {
    const counts = new Map<StatusId, number>()
    for (const l of links) counts.set(l[side], (counts.get(l[side]) ?? 0) + l.count)
    let y = 0
    return STATUSES.filter((s) => counts.has(s)).map((s) => {
      const count = counts.get(s) as number
      const node = { status: s, count, y, h: Math.max(minH, count * unit) }
      y += node.h + gap
      return node
    })
  }
  const left = column('from')
  const right = column('to')
  const fill = (nodes: FlowNode[], side: 'from' | 'to', other: 'from' | 'to', top: 'y0' | 'y1', bottom: 'y0b' | 'y1b') => {
    for (const n of nodes) {
      let y = n.y
      for (const l of links.filter((x) => x[side] === n.status).sort((p, q) => order(p[other]) - order(q[other]))) {
        const h = (l.count / n.count) * n.h
        l[top] = y
        l[bottom] = y + h
        y += h
      }
    }
  }
  fill(left, 'from', 'to', 'y0', 'y0b')
  fill(right, 'to', 'from', 'y1', 'y1b')
  const end = (nodes: FlowNode[]) => (nodes.length ? nodes[nodes.length - 1].y + nodes[nodes.length - 1].h : 0)
  return { left, right, links, height: Math.max(end(left), end(right)) }
}

/** SVG path of a band from the left edge (x0) to the right edge (x1). */
export function bandPath(l: FlowLink, x0: number, x1: number): string {
  const m = (x0 + x1) / 2
  const f = (v: number) => v.toFixed(1)
  return `M${x0},${f(l.y0)}C${m},${f(l.y0)} ${m},${f(l.y1)} ${x1},${f(l.y1)}L${x1},${f(l.y1b)}C${m},${f(l.y1b)} ${m},${f(l.y0b)} ${x0},${f(l.y0b)}Z`
}

/* ---------- goal tiles ---------- */

export interface GoalTile {
  id: string
  number: number
  count: number
  share: number
  /** share bar length relative to the largest goal (0–1) */
  frac: number
  topics: string[]
}

/** The goals of one framework in goal order, each with its topic count and a share bar scaled to the largest goal. */
export function goalTiles(goals: readonly { id: string; framework: string; number: number; topics?: readonly string[] | null; share_recent?: number | null }[], framework: string, known: (id: string) => boolean = () => true): GoalTile[] {
  const mine = goals.filter((g) => g.framework === framework).sort((p, q) => p.number - q.number)
  const max = Math.max(0, ...mine.map((g) => g.share_recent ?? 0))
  return mine.map((g) => {
    const topics = (g.topics ?? []).filter(known)
    const share = g.share_recent ?? 0
    return { id: g.id, number: g.number, count: topics.length, share, frac: max > 0 ? share / max : 0, topics }
  })
}
