import { describe, expect, it } from 'vitest'
import { DataError, EmbeddedSource, HttpSource, dataUrl, sourceFromEmbeddedText } from './source'
import { bundleOf, fixtureFetch } from '../../test/fixtureData'

const respond = (status: number, body: string): typeof fetch => (async () => new Response(body, { status })) as typeof fetch

describe('dataUrl', () => {
  it('joins the Vite base and data/ for root, sub-path and relative bases', () => {
    expect(dataUrl('./', 'latest.json')).toBe('./data/latest.json')
    expect(dataUrl('/tci-research-atlas/', '2026Q4/topics.json')).toBe('/tci-research-atlas/data/2026Q4/topics.json')
    expect(dataUrl('/sub', 'latest.json')).toBe('/sub/data/latest.json')
  })
})

describe('HttpSource', () => {
  it('reads latest.json and release files relative to the base, without the browser cache', async () => {
    const asked: string[] = []
    const calls: RequestInit[] = []
    const inner = fixtureFetch('example', '/sub/', asked)
    const src = new HttpSource('/sub/', ((input: RequestInfo | URL, init?: RequestInit) => {
      calls.push(init ?? {})
      return inner(input, init)
    }) as typeof fetch)
    const latest = await src.latest()
    expect(latest.release).toBe('2026Q4')
    const topics = await src.file<{ topics: unknown[] }>('2026Q4', 'topics.json')
    expect(topics?.topics).toHaveLength(48)
    expect(asked).toEqual(['/sub/data/latest.json', '/sub/data/2026Q4/topics.json'])
    expect(calls.every((c) => c.cache === 'no-cache')).toBe(true)
  })

  it('returns null for a missing release file but reports a missing latest.json as an error', async () => {
    const src = new HttpSource('./', fixtureFetch('example', './'))
    expect(await src.file('2026Q4', 'nope.json')).toBeNull()
    await expect(new HttpSource('./', respond(404, 'x')).latest()).rejects.toMatchObject({ kind: 'missing' })
  })

  it('classifies network failures, server errors and damaged JSON', async () => {
    const offline = (async () => {
      throw new TypeError('Failed to fetch')
    }) as typeof fetch
    await expect(new HttpSource('./', offline).latest()).rejects.toMatchObject({ kind: 'network' })
    await expect(new HttpSource('./', respond(500, 'boom')).file('2026Q4', 'topics.json')).rejects.toMatchObject({ kind: 'network' })
    await expect(new HttpSource('./', respond(200, '{"release":')).latest()).rejects.toMatchObject({ kind: 'parse' })
    await expect(new HttpSource('./', respond(200, '{"hello":1}')).latest()).rejects.toBeInstanceOf(DataError)
  })
})

describe('EmbeddedSource', () => {
  it('serves the bundled release and nothing else', async () => {
    const src = new EmbeddedSource(bundleOf('example'))
    expect((await src.latest()).release).toBe('2026Q4')
    expect(await src.file('2026Q4', 'topics/T000201.json')).toMatchObject({ id: 'T000201' })
    expect(await src.file('2026Q3', 'overview.json')).toBeNull()
    expect(await src.file('2026Q4', 'nope.json')).toBeNull()
  })
})

describe('sourceFromEmbeddedText', () => {
  it('uses HTTP when the slot is empty or null, the bundle when it holds one', () => {
    expect(sourceFromEmbeddedText(null, './').kind).toBe('http')
    expect(sourceFromEmbeddedText('  null ', './').kind).toBe('http')
    expect(sourceFromEmbeddedText('', './').kind).toBe('http')
    expect(sourceFromEmbeddedText(JSON.stringify(bundleOf('empty')), './').kind).toBe('embedded')
  })

  it('never throws on a damaged slot; the error surfaces when data is read', async () => {
    const src = sourceFromEmbeddedText('{not json', './')
    await expect(src.latest()).rejects.toMatchObject({ kind: 'parse' })
    await expect(sourceFromEmbeddedText('{"a":1}', './').latest()).rejects.toMatchObject({ kind: 'parse' })
  })
})
