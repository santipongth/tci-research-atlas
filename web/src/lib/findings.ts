import type { Topic } from '../data/types'
import { fmtInt } from './format'
import { sortBy } from './sort'

/** The three kinds of "what changed" finding the Overview and the brief lead with. */
export type FindingKind = 'emerging' | 'large' | 'decline'

export interface Finding {
  kind: FindingKind
  topic: Topic
}

const hasGrowth = (tp: Topic): boolean => typeof tp.metrics.share_growth === 'number' && Number.isFinite(tp.metrics.share_growth)

/**
 * Up to three examples from the release, each a different topic: the strongest emerging topic (by signal score), the
 * largest hot topic (large and still growing) and the fastest-shrinking declining topic. A kind with no topic is left
 * out, so a release without, say, declining topics gets two findings.
 */
export function pickFindings(topics: readonly Topic[]): Finding[] {
  const used = new Set<string>()
  const out: Finding[] = []
  const take = (kind: FindingKind, ranked: readonly Topic[]) => {
    const tp = ranked.find((c) => !used.has(c.id))
    if (!tp) return
    used.add(tp.id)
    out.push({ kind, topic: tp })
  }
  const of = (status: Topic['status']) => topics.filter((tp) => tp.status === status && hasGrowth(tp))
  take('emerging', sortBy(of('EMERGING'), (tp) => tp.score, 'desc'))
  take('large', sortBy(of('HOT'), (tp) => tp.metrics.share_recent, 'desc'))
  take('decline', sortBy(of('DECLINING'), (tp) => tp.metrics.share_growth, 'asc'))
  return out
}

/**
 * "About k in every N articles" for a topic's share: per 100 for a large share, per 1,000 below 1.5 % (so 0.4 % reads
 * "4 in every 1,000", not "1 in every 100" — rounding a small share to whole percents overstates it).
 */
export function articlesPer(share: number): { k: number; per: 100 | 1000 } {
  const per = share < 0.015 ? 1000 : 100
  return { k: Math.max(1, Math.round(share * per)), per }
}

/** {k} and {per} for the sentences, printed with thousands separators. */
export function perVars(share: number): { k: string; per: string } {
  const { k, per } = articlesPer(share)
  return { k: fmtInt(k), per: fmtInt(per) }
}
