import { describe, expect, it } from 'vitest'
import { atlasCodec, compareCodec, emergingCodec, overviewCodec, topicCodec, type AtlasUrlState, type EmergingUrlState } from './urlState'

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

  it('overview and topic views', () => {
    expect(overviewCodec.parse(overviewCodec.write({ st: 'table', pf: 'chart' }))).toEqual({ st: 'table', pf: 'chart' })
    expect(topicCodec.write({ trend: 'chart' }).toString()).toBe('')
  })
})
