import { describe, expect, it } from 'vitest'
import { mergeParams, atlasCodec, compareCodec, emergingCodec, keywordsCodec, overviewCodec, topicCodec, type AtlasUrlState, type EmergingUrlState } from './urlState'

describe('URL state codecs', () => {
  it('emerging: round-trips and writes nothing for the defaults', () => {
    const s: EmergingUrlState = { status: 'WATCH', sort: 'journals', dir: 'asc', view: 'chart' }
    expect(emergingCodec.parse(emergingCodec.write(s))).toEqual(s)
    expect(emergingCodec.write(emergingCodec.defaults).toString()).toBe('')
  })

  it('invalid or tampered values fall back to the defaults', () => {
    expect(emergingCodec.parse(new URLSearchParams('status=BOGUS&sort=x&dir=up&view=3d'))).toEqual(emergingCodec.defaults)
  })

  it('atlas: selection, hidden statuses in canonical order, an empty layer set, Thai search text', () => {
    const s: AtlasUrlState = { sel: 'T000201', hide: ['LOW_DATA', 'STABLE'], layers: [], q: 'ผู้สูงอายุ & AI' }
    expect(atlasCodec.parse(new URLSearchParams(atlasCodec.write(s).toString()))).toEqual({ ...s, hide: ['STABLE', 'LOW_DATA'] })
    expect(atlasCodec.parse(new URLSearchParams('sel=T12&hide=HOT,NOPE'))).toMatchObject({ sel: null, hide: ['HOT'], layers: ['contours', 'tints', 'names'] })
  })

  it('compare: keeps the order, drops duplicates and bad ids, caps at four', () => {
    const ids = compareCodec.parse(new URLSearchParams('ids=T000701,T000201,T000701,X,T000101,T000102,T000103')).ids
    expect(ids).toEqual(['T000701', 'T000201', 'T000101', 'T000102'])
    const s = { ids: ['T000201', 'T000701'], metric: 'count', view: 'table' } as const
    expect(compareCodec.parse(compareCodec.write({ ...s, ids: [...s.ids] }))).toEqual(s)
  })

  it('keywords: no k = the default pick, an empty k = none, items need a language prefix, capped at four', () => {
    expect(keywordsCodec.parse(new URLSearchParams('')).k).toBeNull()
    expect(keywordsCodec.parse(new URLSearchParams('k=')).k).toEqual([])
    expect(keywordsCodec.parse(new URLSearchParams('k=en:ai|bogus|th:ข้าว|en:ai|en:b|en:c|en:d')).k).toEqual(['en:ai', 'th:ข้าว', 'en:b', 'en:c'])
    const s = { k: ['th:ผู้สูงอายุ', 'en:digital marketing'], view: 'table', gq: 'care' } as const
    expect(keywordsCodec.parse(new URLSearchParams(keywordsCodec.write({ ...s, k: [...s.k] }).toString()))).toEqual(s)
    expect(keywordsCodec.write({ k: [], view: 'chart', gq: '' }).toString()).toBe('k=')
  })

  it('overview and topic views', () => {
    expect(overviewCodec.parse(overviewCodec.write({ wf: 'table', st: 'table', pf: 'chart' }))).toEqual({ wf: 'table', st: 'table', pf: 'chart' })
    expect(topicCodec.write({ trend: 'chart', jr: 'chart', org: 'chart' }).toString()).toBe('')
    expect(topicCodec.parse(new URLSearchParams('jr=table')).jr).toBe('table')
    // /emerging opens on the forest plot; the table is the other view
    expect(emergingCodec.defaults.view).toBe('chart')
  })
})

describe('mergeParams', () => {
  it('keeps query params the codec does not know and drops defaults of its own', () => {
    const prev = new URLSearchParams('status=WATCH&lang=en&ids=T000201&x=1')
    const next = mergeParams(emergingCodec, prev, { status: 'EMERGING' })
    expect(next.get('lang')).toBe('en')
    expect(next.get('ids')).toBe('T000201')
    expect(next.get('x')).toBe('1')
    expect(next.has('status')).toBe(false)
  })
})
