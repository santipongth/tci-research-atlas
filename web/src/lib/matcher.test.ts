import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { bundleOf } from '../../test/fixtureData'
import type { MatchIndex, TopicsFile } from '../data/types'
import { analyze, charGrams, prepareIndex, queryLength, rankJournals, rankTopics } from './matcher'
import { foldText } from './search'

const PARITY = fileURLToPath(new URL('../../../pipeline/tests/fixtures/match_parity.json', import.meta.url))
const files = bundleOf('example').files
const index = files['match.json'] as MatchIndex
const topics = (files['topics.json'] as TopicsFile).topics

describe('matcher', () => {
  it('folds and cuts trigrams exactly like the pipeline', () => {
    const cases = JSON.parse(readFileSync(PARITY, 'utf8')) as { text: string; fold: string; grams: string[] }[]
    expect(cases.length).toBeGreaterThan(5)
    for (const c of cases) {
      expect(foldText(c.text), c.text).toBe(c.fold)
      expect(analyze(c.text), c.text).toEqual(c.grams)
    }
    expect(charGrams('ab')).toEqual([' ab', 'ab '])
    expect(queryLength('  ผู้สูงอายุ  ')).toBe(Array.from('ผูสูงอายุ').length)
  })

  it('ranks the topic whose words were pasted first, and journals that publish it', () => {
    const p = prepareIndex(index)
    for (const id of ['T000201', 'T000406', 'T000502']) {
      const t = topics.find((x) => x.id === id)!
      const hits = rankTopics(p, `${t.th} ${(t.keywords ?? []).join(' ')}`)
      expect(hits[0].id, id).toBe(id)
      expect(hits.every((h, i) => i === 0 || hits[i - 1].score >= h.score)).toBe(true)
    }
    const hits = rankTopics(p, 'AI เพื่อการศึกษา ปัญญาประดิษฐ์ generative AI teaching')
    const journals = rankJournals(index, hits)
    expect(journals.length).toBeGreaterThan(0)
    expect(journals[0].topics.some((x) => x.id === 'T000201')).toBe(true)
    expect(journals.every((j, i) => i === 0 || journals[i - 1].fit >= j.fit)).toBe(true)
  })

  it('returns nothing for text the index does not know', () => {
    expect(rankTopics(prepareIndex(index), 'zzzz qqqq')).toEqual([])
    expect(rankJournals(index, [])).toEqual([])
  })
})
