import { describe, expect, it } from 'vitest'
import { createDetailLoader, createFileLoader, groupName, hasModule, loadRelease, MODULE_FILES, neighborsOf, schemaMajor, seriesOf, type ModuleName } from './release'
import type { JournalsFile } from './types'
import { EmbeddedSource, HttpSource } from './source'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { bundleOf, fixtureFetch, FIXTURES } from '../../test/fixtureData'

describe('loadRelease', () => {
  it('loads the example release from the offline bundle with indexes and flags', async () => {
    const r = await loadRelease(new EmbeddedSource(bundleOf('example')))
    expect(r.source).toBe('embedded')
    expect(r.topics).toHaveLength(48)
    expect(r.topicById.get('T000201')?.status).toBe('EMERGING')
    expect(r.groupById.size).toBe(8)
    expect(r.keywords?.length).toBeGreaterThan(0)
    expect(r.previousOverview).toBeNull() // the offline file carries one release
    expect(r.previousMissing).toBe('2026Q3')
    expect(r.previousProblem).toBe('offline') // the one-release file says so, not "not on this site"
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
    expect(r.previousMissing).toBeNull()
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

  it('treats literal null / non-object files as parse errors and requires a schema_version', async () => {
    for (const file of ['topics.json', 'taxonomy.json', 'series.json', 'overview.json']) {
      const b = bundleOf('example')
      b.files[file] = null
      await expect(loadRelease(new EmbeddedSource(b)), file).rejects.toMatchObject({ kind: 'parse' })
    }
    const noVersion = bundleOf('example')
    const rest = { ...(noVersion.files['manifest.json'] as Record<string, unknown>) }
    delete rest.schema_version
    noVersion.files['manifest.json'] = rest
    await expect(loadRelease(new EmbeddedSource(noVersion))).rejects.toMatchObject({ kind: 'parse' })
  })

  it('never fetches a previous release whose name is not a plain folder name', async () => {
    const asked: string[] = []
    const base = fixtureFetch('example', './', asked)
    const evil = ((input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith('2026Q4/manifest.json')) {
        return Promise.resolve(new Response(JSON.stringify({ ...JSON.parse(readFileSync(join(FIXTURES, 'example', 'data', '2026Q4', 'manifest.json'), 'utf8')), previous_release: '../x' })))
      }
      return base(input, init)
    }) as typeof fetch
    const r = await loadRelease(new HttpSource('./', evil))
    expect(r.previousOverview).toBeNull()
    expect(r.previousMissing).toBeNull() // a hostile name is never echoed
    expect(asked.some((u) => u.includes('..'))).toBe(false)
  })

  it('reports a previous release that is not on the site, with one request for it', async () => {
    const asked: string[] = []
    const base = fixtureFetch('example', './', asked)
    const gone = ((input: RequestInfo | URL, init?: RequestInit) => (String(input).includes('2026Q3/') ? (asked.push(String(input)), Promise.resolve(new Response('', { status: 404 }))) : base(input, init))) as typeof fetch
    const r = await loadRelease(new HttpSource('./', gone))
    expect(r.previousOverview).toBeNull()
    expect(r.previousMissing).toBe('2026Q3')
    expect(r.previousProblem).toBe('missing')
    expect(asked.filter((u) => u.includes('2026Q3/'))).toHaveLength(1)
  })

  it('tells a failed request for the previous release from one that is not there', async () => {
    const base = fixtureFetch('example', './')
    const down = ((input: RequestInfo | URL, init?: RequestInit) => (String(input).includes('2026Q3/') ? Promise.reject(new TypeError('network down')) : base(input, init))) as typeof fetch
    const r = await loadRelease(new HttpSource('./', down))
    expect(r.previousOverview).toBeNull()
    expect(r.previousMissing).toBe('2026Q3')
    expect(r.previousProblem).toBe('failed')
  })

  it('treats a previous overview without its KPI block as damaged, not as a crash', async () => {
    const base = fixtureFetch('example', './')
    const odd = ((input: RequestInfo | URL, init?: RequestInit) => (String(input).endsWith('2026Q3/overview.json') ? Promise.resolve(new Response(JSON.stringify({ release: '2026Q3' }))) : base(input, init))) as typeof fetch
    const r = await loadRelease(new HttpSource('./', odd))
    expect(r.previousOverview).toBeNull()
    expect(r.previousProblem).toBe('damaged')
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

describe('neighborsOf', () => {
  it('lists linked topics strongest first', async () => {
    const r = await loadRelease(new EmbeddedSource(bundleOf('example')))
    const ids = neighborsOf(r, 'T000701')
    expect(ids).toContain('T000201')
    expect(ids).toContain('T000106')
    const weight = (id: string) => r.edges.find((e) => (e.s === id && e.t === 'T000701') || (e.t === id && e.s === 'T000701'))?.w ?? 0
    expect(ids.map(weight)).toEqual([...ids.map(weight)].sort((a, b) => b - a))
    expect(neighborsOf(r, 'T999999')).toEqual([])
  })
})

describe('editors modules (contract 2.1)', () => {
  it('lists the modules and fetches each module file once', async () => {
    const asked: string[] = []
    const source = new HttpSource('./', fixtureFetch('example', './', asked))
    const r = await loadRelease(source)
    expect(['journals', 'journal_detail', 'methods', 'diff', 'match'].every((m) => hasModule(r, m as ModuleName))).toBe(true)
    expect(asked.some((u) => u.endsWith('journals.json'))).toBe(false) // never loaded up front
    const file = createFileLoader(source, r.latest.release)
    const j = (await file(MODULE_FILES.journals)) as JournalsFile
    expect(j.journals).toHaveLength(6)
    await file(MODULE_FILES.journals)
    expect(asked.filter((u) => u.endsWith('/journals.json'))).toHaveLength(1)
    expect(await file('journals/so02.nowhere.json')).toBeNull()
  })

  it('the empty release has none, and the offline file may leave out the match index', async () => {
    const empty = await loadRelease(new HttpSource('./', fixtureFetch('empty', './')))
    expect(hasModule(empty, 'journals')).toBe(false)
    const bundle = bundleOf('example')
    delete bundle.files['match.json']
    const source = new EmbeddedSource(bundle)
    const r = await loadRelease(source)
    expect(hasModule(r, 'match')).toBe(true)
    expect(await createFileLoader(source, r.latest.release)('match.json')).toBeNull()
  })
})
