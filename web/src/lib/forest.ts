import type { Topic } from '../data/types'
import { sortBy } from './sort'
import type { SignalStatus } from './status'

export function hasCi(tp: Topic): boolean {
  const m = tp.metrics
  return m.share_growth_lo !== null && m.share_growth_lo !== undefined && m.share_growth_hi !== null && m.share_growth_hi !== undefined
}

export interface ForestSelection {
  /** the rows to draw, strongest signal first (DECLINING: steepest fall first); rows without a CI stay, as text rows */
  rows: Topic[]
  /** every topic with this status */
  total: number
  /** topics with this status that have no confidence interval (shown or not) */
  noCi: number
}

/** Rows of one status group in the CI forest plot. Topics without an interval never vanish: they are listed and counted. */
export function forestSelection(topics: readonly Topic[], status: SignalStatus, limit = Infinity): ForestSelection {
  const all = topics.filter((tp) => tp.status === status)
  const rows = sortBy(all, (tp) => tp.metrics.share_growth, status === 'DECLINING' ? 'asc' : 'desc').slice(0, limit)
  return { rows, total: all.length, noCi: all.filter((tp) => !hasCi(tp)).length }
}
