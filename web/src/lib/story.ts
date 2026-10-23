import type { Topic } from '../data/types'
import { sortBy } from './sort'

/** Statuses that count as "on the rise" for the front door's story: only the confirmed ones — never WATCH (unconfirmed, often one journal), low data, stable or declining. */
const RISING: readonly Topic['status'][] = ['EMERGING', 'HOT']

const finite = (v: number | null | undefined): v is number => typeof v === 'number' && Number.isFinite(v)

/**
 * The topics the front door's story is about: the first n best-supported risers among the confirmed rising statuses. A topic with
 * no baseline (nothing in the base years) is left out — its growth ratio is arbitrary. Ranking is by the lower bound of
 * the growth interval (the growth the data supports even on a cautious reading), then by signal score for a topic without
 * an interval, then by id. The first one is the answer to "which topic is on the rise?".
 */
export function pickRisers(topics: readonly Topic[], n = 5): Topic[] {
  const rising = topics.filter((tp) => RISING.includes(tp.status) && !tp.metrics.no_baseline && finite(tp.metrics.share_growth) && tp.metrics.share_growth > 0)
  const withCi = sortBy(sortBy(rising.filter((tp) => finite(tp.metrics.share_growth_lo)), (tp) => tp.id, 'asc'), (tp) => tp.metrics.share_growth_lo, 'desc')
  const without = sortBy(sortBy(rising.filter((tp) => !finite(tp.metrics.share_growth_lo)), (tp) => tp.id, 'asc'), (tp) => tp.score, 'desc')
  return [...withCi, ...without].slice(0, n)
}

/**
 * Direct labels at the end of lines: keep each label at its line's height where it can, but at least `gap` apart and
 * inside [lo, hi]. Returns the label positions in the input order. Labels are pushed down from the top, then the
 * stack is pulled back up if it ran past `hi`.
 */
export function spreadLabels(ys: readonly number[], gap: number, lo: number, hi: number, pin = -1): number[] {
  if (pin >= 0 && pin < ys.length) return pinnedLabels(ys, gap, lo, hi, pin)
  const order = ys.map((y, i) => ({ y, i })).sort((a, b) => a.y - b.y || a.i - b.i)
  const out = new Array<number>(ys.length)
  let prev = -Infinity
  for (const o of order) {
    const y = Math.max(o.y, lo, prev + gap)
    out[o.i] = y
    prev = y
  }
  const over = prev - hi
  if (over > 0) {
    let next = Infinity
    for (let k = order.length - 1; k >= 0; k--) {
      const i = order[k].i
      const y = Math.min(out[i] - over, next - gap)
      out[i] = Math.max(lo, y)
      next = out[i]
    }
  }
  return out
}

/** As `spreadLabels`, but label `pin` stays exactly at its line: the others above it stack upwards, the rest downwards. */
function pinnedLabels(ys: readonly number[], gap: number, lo: number, hi: number, pin: number): number[] {
  const out = [...ys]
  const at = Math.min(hi, Math.max(lo, ys[pin]))
  out[pin] = at
  const others = ys.map((y, i) => ({ y, i })).filter((o) => o.i !== pin)
  const above = others.filter((o) => o.y < at || (o.y === at && o.i < pin)).sort((a, b) => b.y - a.y || b.i - a.i)
  const below = others.filter((o) => !above.includes(o)).sort((a, b) => a.y - b.y || a.i - b.i)
  let prev = at
  const spill: typeof above = []
  for (const o of above) {
    const y = Math.min(o.y, prev - gap)
    // no room left above the pinned label: this one (and the rest) goes under it instead
    if (y < lo) {
      spill.push(o)
      continue
    }
    out[o.i] = y
    prev = y
  }
  below.unshift(...spill.reverse())
  prev = at
  for (const o of below) {
    out[o.i] = Math.min(hi, Math.max(o.y, prev + gap))
    prev = out[o.i]
  }
  return out
}
