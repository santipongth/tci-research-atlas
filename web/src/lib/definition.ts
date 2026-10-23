import type { Topic } from '../data/types'
import { fmtNum, fmtPct, fmtSignedPct, yearSpan } from './format'

/**
 * Emerging-definition constants shown in the UI. They mirror pipeline/config.example.yaml defaults
 * (docs/EMERGING_SPEC.md) because contract v2 publishes only definition_version, ci_level and last_complete_year.
 * When the manifest gains a `definition` block, read it first and keep these as fallbacks.
 */
export const DEFINITION = {
  emergingMinGrowthLo: 0.1,
  emergingMinShareRatio: 1.8,
  decliningMaxShareRatio: 0.8,
  largeQuantile: 0.75,
  minArticlesRecent: 30,
  minJournals: 3,
  minOrgs: 3,
  /** breadth test: share of recent articles from journals new in R must stay below this */
  maxNewJournalShare: 0.5,
  recentYears: 3,
  baselineYears: 5,
  trendYears: 5,
  /** keywords.min_active_years: an emerging keyword appears in at least this many years of the W window */
  keywordMinActiveYears: 3,
} as const

export interface Windows {
  R: [number, number]
  B: [number, number]
  W: [number, number]
}

export function windows(lastCompleteYear: number): Windows {
  const L = lastCompleteYear
  const { recentYears, baselineYears, trendYears } = DEFINITION
  return { R: [L - recentYears + 1, L], B: [L - recentYears - baselineYears + 1, L - recentYears], W: [L - trendYears + 1, L] }
}

export const fmtWindow = (w: readonly [number, number]): string => yearSpan(w[0], w[1])

/** Linear interpolation between closest ranks (pandas' default) on an ascending array. */
export function quantile(sorted: readonly number[], q: number): number {
  if (sorted.length === 0) return Number.NaN
  const pos = (sorted.length - 1) * q
  const lo = Math.floor(pos)
  const hi = Math.ceil(pos)
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo)
}

/** "Large" = share_recent at or above the 0.75 quantile of classified (non-LOW_DATA) topics. */
export function largeShareThreshold(topics: readonly Topic[]): number | null {
  const shares = topics.filter((t) => t.status !== 'LOW_DATA').map((t) => t.metrics.share_recent).filter((s) => Number.isFinite(s))
  if (shares.length === 0) return null
  return quantile([...shares].sort((a, b) => a - b), DEFINITION.largeQuantile)
}

export type Quadrant = 'stars' | 'rising' | 'mature' | 'declining'
export const QUADRANTS: readonly Quadrant[] = ['stars', 'rising', 'mature', 'declining']

export function quadrantOf(t: Topic, threshold: number): Quadrant | null {
  const g = t.metrics.share_growth
  if (t.status === 'LOW_DATA' || g === null || g === undefined) return null
  const large = t.metrics.share_recent >= threshold
  if (g > 0) return large ? 'stars' : 'rising'
  return large ? 'mature' : 'declining'
}

/** Every placeholder used by the `rule.*` strings, from DEFINITION — the one place that fills them (/emerging, /about). */
export function ruleVars(level: number): Record<string, string | number> {
  return {
    level,
    bar: fmtSignedPct(DEFINITION.emergingMinGrowthLo, 0),
    ratio: fmtNum(DEFINITION.emergingMinShareRatio, 1),
    dratio: fmtNum(DEFINITION.decliningMaxShareRatio, 1),
    j: DEFINITION.minJournals,
    o: DEFINITION.minOrgs,
    ns: fmtPct(DEFINITION.maxNewJournalShare, 0),
    n: DEFINITION.minArticlesRecent,
    ry: DEFINITION.recentYears, // the recent window, in years
    by: DEFINITION.baselineYears, // the baseline window before it, in years
    ky: DEFINITION.keywordMinActiveYears, // em.kw.intro: years a keyword must stay active
    top: fmtPct(1 - DEFINITION.largeQuantile, 0),
  }
}
