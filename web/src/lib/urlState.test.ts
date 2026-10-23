import { describe, expect, it } from 'vitest'
import { atlasCodec, galaxyCodec, mergeParams, overviewCodec, topicsCodec, type AtlasUrlState } from './urlState'

describe('URL state codecs', () => {
  it('topics: round-trips and writes nothing for the defaults; an old /emerging status still parses', () => {
    const s = { status: 'WATCH', by: 'size' } as const
    expect(topicsCodec.parse(topicsCodec.write(s))).toEqual(s)
    expect(topicsCodec.write(topicsCodec.defaults).toString()).toBe('')
    expect(topicsCodec.parse(new URLSearchParams('status=HOT&sort=journals&view=table')).status).toBe('HOT')
  })

  it('invalid or tampered values fall back to the defaults', () => {
    expect(topicsCodec.parse(new URLSearchParams('status=BOGUS&by=x'))).toEqual(topicsCodec.defaults)
    expect(overviewCodec.parse(new URLSearchParams('mv=sideways&pt=1'))).toEqual(overviewCodec.defaults)
  })

  it('atlas: selection, hidden statuses in canonical order, an empty layer set', () => {
    const s: AtlasUrlState = { sel: 'T000201', hide: ['LOW_DATA', 'STABLE'], layers: [], by: 'size' }
    expect(atlasCodec.parse(new URLSearchParams(atlasCodec.write(s).toString()))).toEqual({ ...s, hide: ['STABLE', 'LOW_DATA'] })
    expect(atlasCodec.parse(new URLSearchParams('sel=T12&hide=HOT,NOPE'))).toMatchObject({ sel: null, hide: ['HOT'], layers: ['contours', 'tints', 'names'] })
  })

  it('overview and galaxy', () => {
    expect(overviewCodec.parse(overviewCodec.write({ mv: 'down', pt: 'policy' }))).toEqual({ mv: 'down', pt: 'policy' })
    expect(galaxyCodec.parse(new URLSearchParams('from=2020&to=20x&g=F17'))).toEqual({ from: 2020, to: null, g: 'F17' })
  })
})

describe('mergeParams', () => {
  it('keeps query params the codec does not know and drops defaults of its own', () => {
    const prev = new URLSearchParams('status=WATCH&lang=en&ids=T000201&x=1')
    const next = mergeParams(topicsCodec, prev, { status: 'EMERGING' })
    expect(next.get('lang')).toBe('en')
    expect(next.get('ids')).toBe('T000201')
    expect(next.get('x')).toBe('1')
    expect(next.has('status')).toBe(false)
  })
})
