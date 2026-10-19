import { describe, expect, it } from 'vitest'
import { createDetailLoader, groupName, loadRelease, schemaMajor, seriesOf } from './release'
import { EmbeddedSource, HttpSource } from './source'
import { bundleOf, fixtureFetch } from '../../test/fixtureData'

describe('loadRelease', () => {
  it('loads the example release from the offline bundle with indexes and flags', async () => {
    const r = await loadRelease(new EmbeddedSource(bundleOf('example')))
    expect(r.source).toBe('embedded')
    expect(r.topics).toHaveLength(48)
    expect(r.topicById.get('T000201')?.status).toBe('EMERGING')
    expect(r.groupById.size).toBe(8)
    expect(r.keywords?.length).toBeGreaterThan(0)
    expect(r.previousOverview).toBeNull() // the offline file carries one release
    expect(r.sample).toBe(true)
    expect(r.ciLevel).toBe(0.9)
    expect(r.definitionVersion).toBe(3)
    expect(seriesOf(r, 'T000201')).toHaveLength(10)
    expect(groupName(r, 'F33', 'en')).toBe('Social Sciences')
    expect(groupName(r, 'F99', 'th')).toBe('F99')
  })

  it('reads the previous release overview over HTTP for KPI deltas', async () => {
    const r = await loadRelease(new HttpSource('./', fixtureFetch('example', './')))
    expect(r.previousOverview?.release).toBe('2026Q3')
  })

  it('loads an empty release and skips modules the manifest does not list', async () => {
    const asked: string[] = []
    const r = await loadRelease(new HttpSource('./', fixtureFetch('empty', './', asked)))
    expect(r.topics).toEqual([])
    expect(r.keywords).toBeNull()
    expect(r.overview.brief ?? null).toBeNull()
    expect(asked.some((u) => u.endsWith('keywords.json'))).toBe(false)
  })

  it('refuses another schema major and missing required files with typed errors', async () => {
    const wrong = bundleOf('example')
    wrong.files['manifest.json'] = { ...(wrong.files['manifest.json'] as object), schema_version: '3.0.0' }
    await expect(loadRelease(new EmbeddedSource(wrong))).rejects.toMatchObject({ kind: 'schema', detail: '3.0.0' })
    const missing = bundleOf('example')
    delete missing.files['topics.json']
    await expect(loadRelease(new EmbeddedSource(missing))).rejects.toMatchObject({ kind: 'missing' })
    const damaged = bundleOf('example')
    damaged.files['topics.json'] = {}
    await expect(loadRelease(new EmbeddedSource(damaged))).rejects.toMatchObject({ kind: 'parse' })
  })

  it('parses schema majors', () => {
    expect(schemaMajor('2.0.0')).toBe(2)
    expect(schemaMajor('2.13.1')).toBe(2)
    expect(schemaMajor('v2')).toBeNull()
    expect(schemaMajor(undefined)).toBeNull()
  })
})

describe('createDetailLoader', () => {
  it('loads a topic detail once and answers null for unknown topics', async () => {
    const asked: string[] = []
    const load = createDetailLoader(new HttpSource('./', fixtureFetch('example', './', asked)), '2026Q4')
    const [a, b] = await Promise.all([load('T000201'), load('T000201')])
    expect(a?.id).toBe('T000201')
    expect(b).toBe(a)
    expect(asked.filter((u) => u.endsWith('T000201.json'))).toHaveLength(1)
    expect(await load('T999999')).toBeNull()
  })
})
