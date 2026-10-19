import Ajv, { type ValidateFunction } from 'ajv'
import { createHash } from 'node:crypto'
import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const WEB = fileURLToPath(new URL('../..', import.meta.url))
const schema = JSON.parse(readFileSync(join(WEB, 'src', 'data', 'contract.schema.json'), 'utf8')) as { definitions: Record<string, unknown> }
const ajv = new Ajv({ allErrors: true, strict: false })
const compiled = new Map<string, ValidateFunction>()
const MODEL: Record<string, string> = {
  'latest.json': 'Latest', 'manifest.json': 'Manifest', 'overview.json': 'Overview', 'taxonomy.json': 'TaxonomyFile', 'topics.json': 'TopicsFile',
  'series.json': 'SeriesFile', 'edges.json': 'EdgesFile', 'keywords.json': 'KeywordsFile',
  'journals.json': 'JournalsFile', 'methods.json': 'MethodsFile', 'diff.json': 'DiffFile', 'match.json': 'MatchIndex',
}

function validate(path: string, value: unknown): string[] {
  const name = path.startsWith('topics/') ? 'TopicDetail' : path.startsWith('journals/') ? 'JournalDetail' : MODEL[path]
  if (!name) return [`no contract model for ${path}`]
  let fn = compiled.get(name)
  if (!fn) {
    fn = ajv.compile({ $ref: `#/definitions/${name}`, definitions: schema.definitions })
    compiled.set(name, fn)
  }
  return fn(value) ? [] : (fn.errors ?? []).map((e) => `${path}${e.instancePath} ${e.message ?? ''}`)
}

interface ManifestLike {
  previous_release?: string | null
  files: { path: string; bytes: number; sha256: string }[]
}

function checkRelease(dataDir: string, release: string): string[] {
  const problems: string[] = []
  const manifest = JSON.parse(readFileSync(join(dataDir, release, 'manifest.json'), 'utf8')) as ManifestLike
  problems.push(...validate('manifest.json', manifest))
  for (const f of manifest.files) {
    const bytes = readFileSync(join(dataDir, release, f.path))
    if (bytes.length !== f.bytes) problems.push(`${release}/${f.path}: ${bytes.length} bytes, manifest says ${f.bytes}`)
    if (createHash('sha256').update(bytes).digest('hex') !== f.sha256) problems.push(`${release}/${f.path}: sha256 differs`)
    problems.push(...validate(f.path, JSON.parse(bytes.toString('utf8'))))
  }
  return problems
}

for (const set of ['example', 'empty'] as const) {
  describe(`fixtures/${set}`, () => {
    const dataDir = join(WEB, 'fixtures', set, 'data')

    it('latest.json and every listed file match the contract, size and sha256', () => {
      const latest = JSON.parse(readFileSync(join(dataDir, 'latest.json'), 'utf8')) as { release: string; path: string }
      expect(validate('latest.json', latest)).toEqual([])
      expect(latest.path).toBe(`${latest.release}/manifest.json`)
      expect(checkRelease(dataDir, latest.release)).toEqual([])
      const manifest = JSON.parse(readFileSync(join(dataDir, latest.path), 'utf8')) as ManifestLike
      const prev = manifest.previous_release
      if (prev && existsSync(join(dataDir, prev, 'manifest.json'))) expect(checkRelease(dataDir, prev)).toEqual([])
    })
  })
}
