import { describe, expect, it } from 'vitest'
import { buildSearchIndex, foldText, searchTopics, segmentWords, topicsForWords } from './search'

const index = buildSearchIndex([
  { id: 'T1', th: 'ความต้องการของผู้สูงอายุ', en: 'Needs of older adults', keywords: ['ผู้สูงอายุ', 'ageing'], size: 10 },
  { id: 'T2', th: 'การจัดการเรียนรู้เชิงรุก', en: 'Active learning', keywords: ['active learning', 'ทักษะศตวรรษที่ 21'], size: 50 },
  { id: 'T3', th: 'AI เพื่อการศึกษา', en: 'AI in education', keywords: ['generative AI'], size: 30 },
  { id: 'T4', th: 'การจัดการน้ำ', en: 'Water management', keywords: ['อุทกภัย'], size: 20 },
])
const ids = (q: string) => searchTopics(index, q).map((h) => h.id)

describe('foldText', () => {
  it('folds tone marks, the decomposed sara am, invisible characters, case and Latin accents', () => {
    expect(foldText('ความต้องการ')).toBe(foldText('ความตองการ'))
    expect(foldText('น้ํา')).toBe(foldText('น้ำ'))
    expect(foldText('AI​  Café')).toBe('ai cafe')
  })
})

describe('segmentWords', () => {
  it('splits Thai into words with Intl.Segmenter and keeps English words', () => {
    expect(segmentWords('การจัดการน้ำ').length).toBeGreaterThan(1)
    expect(segmentWords('active learning')).toEqual(['active', 'learning'])
  })
})

describe('searchTopics', () => {
  it('finds Thai names even when the query lost its tone marks', () => {
    expect(ids('ความตองการ')[0]).toBe('T1')
    expect(ids('จัดการน้ำ')).toContain('T4')
  })

  it('ranks exact and prefix name matches above keyword matches', () => {
    expect(ids('ACTIVE')[0]).toBe('T2')
    expect(ids('education ai')).toEqual(['T3'])
    expect(ids('generative')).toEqual(['T3'])
    expect(ids('ทักษะ')).toEqual(['T2'])
  })

  it('returns nothing for blank queries and respects the limit', () => {
    expect(ids('   ')).toEqual([])
    expect(searchTopics(index, 'การ', 2)).toHaveLength(2)
  })
})

describe('topicsForWords', () => {
  it('falls back to the known words when the whole query matches nothing, best match first, capped', () => {
    expect(searchTopics(index, 'ผู้สูงอายุควอนตัม')).toEqual([])
    expect(topicsForWords(index, 'ผู้สูงอายุควอนตัม', ['ผู้สูงอายุ']).map((h) => h.id)).toEqual(['T1'])
    expect(topicsForWords(index, 'learning water', ['learning', 'water'], 1).map((h) => h.id)).toHaveLength(1)
    expect(topicsForWords(index, '', [])).toEqual([])
  })
})
