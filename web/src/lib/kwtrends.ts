import type { KeywordTrend, KwTrendsFile } from '../data/types'
import { foldText } from './search'

/** "<lang>:<term>" — a keyword's id in the URL (the same written form can occur in both keyword lists). */
export const kwKey = (k: Pick<KeywordTrend, 'lang' | 'term'>) => `${k.lang}:${k.term}`

/** Articles per year that could carry a keyword of this language (the share's denominator, kwtrends.json). */
export function totalsFor(file: KwTrendsFile, lang: KeywordTrend['lang']): readonly number[] {
  return lang === 'th' ? file.totals_th : file.totals_en
}

/** Share per year = count / articles that year with ≥ 1 keyword in the same language; null when that total is 0. */
export function shareOf(file: KwTrendsFile, k: KeywordTrend): (number | null)[] {
  const totals = totalsFor(file, k.lang)
  return file.years.map((_, i) => (totals[i] ? (k.counts[i] ?? 0) / totals[i] : null))
}

export interface KwOption {
  keyword: KeywordTrend
  /** the glossary partner the query matched (the keyword itself did not) */
  via: string | null
}

/**
 * Combobox options for a query: keywords whose term matches (exact, then prefix, then word prefix, then anywhere —
 * folded like the topic search, so tone marks and case do not matter), then keywords reached through the TH↔EN
 * glossary (type a Thai word, get its English pair too). Most-used first within each rank.
 */
export function matchKeywords(file: KwTrendsFile, query: string, exclude: ReadonlySet<string>, limit = 8): KwOption[] {
  const q = foldText(query)
  if (!q) return []
  const byTerm = new Map<string, KeywordTrend>()
  for (const k of file.keywords) {
    const f = `${k.lang}:${foldText(k.term)}`
    if (!byTerm.has(f)) byTerm.set(f, k)
  }
  const rank = (term: string): number => {
    const f = foldText(term)
    if (f === q) return 0
    if (f.startsWith(q)) return 1
    if (f.split(/[\s\-/]+/).some((w) => w.startsWith(q))) return 2
    return f.includes(q) ? 3 : -1
  }
  const direct = file.keywords
    .map((k, i) => ({ k, i, r: exclude.has(kwKey(k)) ? -1 : rank(k.term) }))
    .filter((x) => x.r >= 0)
    .sort((a, b) => a.r - b.r || a.i - b.i)
    .map((x): KwOption => ({ keyword: x.k, via: null }))
  const seen = new Set(direct.map((o) => kwKey(o.keyword)))
  const via: KwOption[] = []
  for (const g of file.glossary) {
    if (direct.length + via.length >= limit * 2) break
    const pairs: [string, string, KeywordTrend['lang']][] = [[g.th, g.en, 'en'], [g.en, g.th, 'th']]
    for (const [hit, partner, lang] of pairs) {
      if (rank(hit) < 0) continue
      const k = byTerm.get(`${lang}:${foldText(partner)}`)
      if (!k || seen.has(kwKey(k)) || exclude.has(kwKey(k))) continue
      seen.add(kwKey(k))
      via.push({ keyword: k, via: hit })
    }
  }
  return [...direct, ...via].slice(0, limit)
}

/** Keywords whose share grew the most: mean share of the last two years ÷ the first two, among the `pool` most used
 *  keywords with a share in every one of those years. A suggestion list, not a statistic. */
export function risingKeywords(file: KwTrendsFile, n: number, pool = 200): KeywordTrend[] {
  const last = file.years.length - 1
  if (last < 3) return []
  const mean = (a: number | null, b: number | null) => (a === null || b === null ? null : (a + b) / 2)
  return file.keywords
    .slice(0, pool)
    .map((k) => {
      const s = shareOf(file, k)
      const early = mean(s[0], s[1])
      const late = mean(s[last - 1], s[last])
      return { k, ratio: early && late !== null ? late / early : null }
    })
    .filter((x): x is { k: KeywordTrend; ratio: number } => x.ratio !== null && x.ratio > 1)
    .sort((a, b) => b.ratio - a.ratio)
    .slice(0, n)
    .map((x) => x.k)
}

export interface KwInsight {
  dir: 'up' | 'down' | 'flat'
  a: number
  b: number
  p1: number
  p2: number
}

/** First and last year with a share; "flat" when they differ by less than a tenth. */
export function kwInsight(years: readonly number[], share: readonly (number | null)[]): KwInsight | null {
  const i0 = share.findIndex((v) => v !== null)
  let i1 = share.length - 1
  while (i1 >= 0 && share[i1] === null) i1--
  if (i0 < 0 || i1 <= i0) return null
  const p1 = share[i0] as number
  const p2 = share[i1] as number
  const dir = Math.abs(p2 - p1) < 0.1 * Math.max(p1, p2) ? 'flat' : p2 > p1 ? 'up' : 'down'
  return { dir, a: years[i0], b: years[i1], p1, p2 }
}
