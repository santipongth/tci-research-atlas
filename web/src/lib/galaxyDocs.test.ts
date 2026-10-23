import { describe, expect, it } from 'vitest'
import { docShardOf, rowToDoc } from './galaxyDocs'

describe('galaxy docs', () => {
  it('finds the shard of an ordinal', () => {
    expect(docShardOf(0, 2000)).toBe(0)
    expect(docShardOf(1999, 2000)).toBe(0)
    expect(docShardOf(2000, 2000)).toBe(1)
  })

  it('reads a shard row with the journal from the shard list', () => {
    const doc = rowToDoc(['a1', 'ชื่อ', 'Title', 2023, 1, 't9', null, 'https://x', 2], 7, ['J0', 'J1'])
    expect(doc).toEqual({ ordinal: 7, id: 'a1', titleTh: 'ชื่อ', titleEn: 'Title', year: 2023, journal: 'J1', topic: 't9', doi: null, url: 'https://x', cited: 2 })
    expect(rowToDoc(['a2', '', '', 2020, 5, null, null, null, 0], 0, []).journal).toBe('')
  })
})
