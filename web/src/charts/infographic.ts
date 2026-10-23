/*
 * Pure layout helpers for the quiet infographic forms (status waffle, dot plot, mini bar ranking). The components that
 * draw them position marks with percentages, so they print and reflow without measuring the page.
 */
import type { Topic } from '../data/types'
import { sortBy } from '../lib/sort'
import { SIGNAL_STATUSES, STATUSES, type StatusId } from '../lib/status'
import { niceTicks } from './scale'

export interface WaffleGroup {
  status: StatusId
  /** the topics of this status, strongest signal first (score, then size) — one square each */
  topics: Topic[]
}

/** One group per status, in display order (EMERGING … LOW_DATA); empty statuses keep their row with a 0. */
export function waffleGroups(topics: readonly Topic[]): WaffleGroup[] {
  return STATUSES.map((status) => ({
    status,
    topics: sortBy(sortBy(topics.filter((tp) => tp.status === status), (tp) => tp.metrics.share_recent, 'desc'), (tp) => tp.score, 'desc'),
  }))
}

/** Percent of `total`, rounded to a whole number for labels (never NaN). */
export function percentOf(n: number, total: number): number {
  return total > 0 ? Math.round((n / total) * 100) : 0
}

/** A rounded axis covering every value and the `include` marks (zero): [lo, hi] on whole tick steps, plus the ticks. */
export function dotDomain(values: readonly number[], include: readonly number[] = [0], count = 4): { domain: [number, number]; ticks: number[] } {
  const v = [...values.filter(Number.isFinite), ...include]
  if (v.length === 0) return { domain: [0, 1], ticks: [0, 1] }
  const lo = Math.min(...v)
  const hi = Math.max(...v)
  if (!(hi > lo)) return { domain: [lo - 1, hi + 1], ticks: [lo] }
  const raw = niceTicks(lo, hi, count)
  const step = raw.length > 1 ? raw[1] - raw[0] : hi - lo
  const d0 = Math.floor(lo / step + 1e-9) * step
  const d1 = Math.ceil(hi / step - 1e-9) * step
  const ticks: number[] = []
  for (let x = d0; x <= d1 + step * 1e-9; x += step) ticks.push(Math.round(x * 1e9) / 1e9)
  return { domain: [d0, d1], ticks }
}

/** Position of `v` on the domain, in percent (0–100), clamped to the ends. */
export function pctAt(v: number, domain: readonly [number, number]): number {
  const [d0, d1] = domain
  if (!(d1 > d0)) return 50
  return Math.max(0, Math.min(100, ((v - d0) / (d1 - d0)) * 100))
}

const growthOf = (tp: Topic): number | null => (typeof tp.metrics.share_growth === 'number' && Number.isFinite(tp.metrics.share_growth) ? tp.metrics.share_growth : null)

/**
 * The release's top movers among signal topics: the `up` fastest-rising and the `down` fastest-shrinking shares,
 * listed from the biggest rise to the biggest fall.
 */
export function topMovers(topics: readonly Topic[], up = 5, down = 3): Topic[] {
  const signal = topics.filter((tp) => (SIGNAL_STATUSES as readonly string[]).includes(tp.status) && growthOf(tp) !== null)
  const risers = sortBy(signal.filter((tp) => (growthOf(tp) ?? 0) > 0), growthOf, 'desc').slice(0, up)
  const fallers = sortBy(signal.filter((tp) => (growthOf(tp) ?? 0) < 0), growthOf, 'asc').slice(0, down)
  return sortBy([...risers, ...fallers], growthOf, 'desc')
}

export interface RankItem {
  key: string
  id?: string | null
  count: number
}

export interface RankRow extends RankItem {
  /** bar length as a fraction of the largest count shown (0–1) */
  frac: number
}

/** The `n` largest items, largest first, with bar lengths relative to the first; `rest` = how many are not shown. */
export function rankBars(items: readonly RankItem[], n = 5): { rows: RankRow[]; rest: number } {
  const top = sortBy(items.filter((i) => Number.isFinite(i.count) && i.count >= 0), (i) => i.count, 'desc').slice(0, n)
  const max = top.length ? top[0].count : 0
  return { rows: top.map((i) => ({ ...i, frac: max > 0 ? i.count / max : 0 })), rest: Math.max(0, items.length - top.length) }
}
