import { describe, expect, it } from 'vitest'
import { fixtureFetch } from '../../test/fixtureData'
import { createFileLoader, createSearchFiles, MODULE_FILES } from '../data/release'
import { HttpSource } from '../data/source'
import type { SearchMeta, SearchVocab } from '../data/types'
import { decodePostings, filterHits, intersect, makeSource, pickDocShards, runSearch, type SearchSource } from './searchClient'

async function exampleSource(asked: string[] = []): Promise<SearchSource> {
  const file = createFileLoader(new HttpSource('./', fixtureFetch('example', './', asked)), '2026Q4')
  const files = createSearchFiles(file)
  const meta = (await file(MODULE_FILES.search)) as SearchMeta
  return makeSource(meta, (await files.vocab()) as SearchVocab, files)
}

describe('search helpers', () => {
  it('decodes delta postings and intersects ascending lists', () => {
    expect(decodePostings([3, 2, 10])).toEqual([3, 5, 15])
    expect(intersect([[1, 3, 5, 7], [3, 4, 5], [0, 3, 5, 9]])).toEqual([3, 5])
    expect(intersect([])).toEqual([])
  })

  it('fetches the doc shards holding the most matches first', () => {
    expect(pickDocShards([1, 2, 450, 451, 452, 900], 200, 2)).toEqual([2, 0])
  })
})

describe('runSearch on the example release', () => {
  it('ANDs the known words, ranks title hits first, then newer years', async () => {
    const asked: string[] = []
    const src = await exampleSource(asked)
    const out = await runSearch(src, 'ผู้สูงอายุ ageing')
    expect(out.known).toEqual(['ผู้สูงอายุ', 'ageing'])
    expect(out.unknown).toEqual([])
    expect(out.total).toBeGreaterThan(0)
    expect(out.complete).toBe(true)
    for (const h of out.hits) expect(`${h.titleTh} ${h.titleEn}`).toMatch(/ผู้สูงอายุ|ageing/)
    for (let i = 1; i < out.hits.length; i++) {
      const [a, b] = [out.hits[i - 1], out.hits[i]]
      expect(a.titleHits > b.titleHits || (a.titleHits === b.titleHits && (a.year > b.year || (a.year === b.year && a.ordinal < b.ordinal)))).toBe(true)
    }
    expect(asked.some((u) => /search\/idx-\d{3}\.json$/.test(u))).toBe(true)
    const years = filterHits(out.hits, { from: 2022, to: 2024, topic: null, journal: '' })
    expect(years.every((h) => h.year >= 2022 && h.year <= 2024)).toBe(true)
  })

  it('names words that are not in the corpus and finds nothing for them alone', async () => {
    const out = await runSearch(await exampleSource(), 'ควอนตัม')
    expect(out).toMatchObject({ known: [], unknown: ['ควอนตัม'], total: 0, hits: [] })
  })

  it('examines only part of a broad match when the doc shard cap is reached', async () => {
    const src = await exampleSource()
    const full = await runSearch(src, 'study')
    const part = await runSearch(src, 'study', 1)
    expect(full.complete).toBe(true)
    expect(part.complete).toBe(false)
    expect(part.total).toBe(full.total)
    expect(part.examined).toBeLessThan(full.total)
  })
})
