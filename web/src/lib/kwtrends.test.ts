import { describe, expect, it } from 'vitest'
import type { KwTrendsFile } from '../data/types'
import { kwInsight, kwKey, matchKeywords, shareOf } from './kwtrends'

const file = {
  schema_version: '2.3.0',
  years: [2022, 2023, 2024],
  totals: [100, 100, 100],
  totals_th: [50, 0, 80],
  totals_en: [40, 50, 60],
  min_count: 5,
  max_keywords: 3000,
  glossary_min_pairs: 2,
  keywords: [
    { term: 'digital marketing', lang: 'en', n: 30, counts: [8, 10, 12] },
    { term: 'การตลาดดิจิทัล', lang: 'th', n: 20, counts: [5, 0, 15] },
    { term: 'marketing mix', lang: 'en', n: 9, counts: [3, 3, 3] },
  ],
  glossary: [{ th: 'การตลาดออนไลน์', en: 'digital marketing', n: 7 }],
} as KwTrendsFile

describe('keyword trends', () => {
  it('divides by the articles with keywords in the same language; a year without any is a gap', () => {
    expect(shareOf(file, file.keywords[0])).toEqual([0.2, 0.2, 0.2])
    expect(shareOf(file, file.keywords[1])).toEqual([0.1, null, 0.1875])
  })

  it('matches prefix before substring, and reaches a keyword through its glossary partner', () => {
    expect(matchKeywords(file, 'MARK', new Set()).map((o) => o.keyword.term)).toEqual(['marketing mix', 'digital marketing'])
    const via = matchKeywords(file, 'การตลาดออนไลน์', new Set())
    expect(via.map((o) => [kwKey(o.keyword), o.via])).toEqual([['en:digital marketing', 'การตลาดออนไลน์']])
    expect(matchKeywords(file, 'การตลาดออนไลน์', new Set(['en:digital marketing']))).toEqual([])
  })

  it('reads the first and last year with a share', () => {
    expect(kwInsight(file.years, [0.1, null, 0.1875])).toEqual({ dir: 'up', a: 2022, b: 2024, p1: 0.1, p2: 0.1875 })
    expect(kwInsight(file.years, [0.2, 0.2, 0.21])?.dir).toBe('flat')
    expect(kwInsight(file.years, [null, 0.2, null])).toBeNull()
  })
})
