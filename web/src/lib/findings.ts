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
 * "About k in every N articles" for a topic's share, with N chosen so k has two significant digits or more: per 100
 * from 10 %, per 1,000 from 0.15 %, per 10,000 below (0.04 % reads "4 in every 10,000", not "1 in every 1,000";
 * rounding a small share to a coarse base overstates it). A real share never prints 0 (k ≥ 1); a share that is not a
 * number or is negative has no sentence (null).
 */
export function articlesPer(share: number | null | undefined): { k: number; per: 100 | 1000 | 10000 } | null {
  if (share === null || share === undefined || !Number.isFinite(share) || share < 0) return null
  const per = share < 0.0015 ? 10000 : share < 0.1 ? 1000 : 100
  const k = Math.round(share * per)
  return { k: share > 0 ? Math.max(1, k) : 0, per }
}

/** {k} and {per} for the sentences, printed with thousands separators; null = leave the sentence out. */
export function perVars(share: number | null | undefined): { k: string; per: string } | null {
  const r = articlesPer(share)
  return r && { k: fmtInt(r.k), per: fmtInt(r.per) }
}
