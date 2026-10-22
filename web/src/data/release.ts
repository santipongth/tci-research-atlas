import { z } from 'zod'
import { DataError, isReleaseName, type DataSource } from './source'
import type {
  EdgesFile, EmergingKeyword, GroupInfo, KeywordsFile, Latest, Manifest, Overview, SearchDocShard, SearchIndexShard, SearchVocab, SeriesFile, TaxonomyFile, Topic,
  TopicDetail, TopicsFile,
} from './types'

export const SUPPORTED_SCHEMA_MAJOR = 2
/** Embedding providers that never produce a real release (fixtures, the CPU fallback). */
const SAMPLE_PROVIDERS = new Set(['fixture', 'lite'])

export interface AtlasRelease {
  source: DataSource['kind']
  latest: Latest
  manifest: Manifest
  overview: Overview
  taxonomy: TaxonomyFile
  topics: Topic[]
  series: SeriesFile
  edges: EdgesFile['edges']
  keywords: EmergingKeyword[] | null
  previousOverview: Overview | null
  /** previous_release is set but its folder is not on this site (or not in the offline file): Δ is hidden and the pages say why */
  previousMissing: string | null
  topicById: ReadonlyMap<string, Topic>
  groupById: ReadonlyMap<string, GroupInfo>
  ciLevel: number
  definitionVersion: number
  sample: boolean
}

export function schemaMajor(version: string | null | undefined): number | null {
  const m = /^(\d+)\./.exec(version ?? '')
  return m ? Number(m[1]) : null
}

const ManifestShape = z.looseObject({
  release: z.string(),
  schema_version: z.string().regex(/^\d+\./),
  modules: z.array(z.string()).optional(),
  previous_release: z.string().nullable().optional(),
})

async function required<T>(source: DataSource, release: string, path: string): Promise<T> {
  const value = await source.file<T>(release, path)
  if (value === null) throw new DataError('missing', `${release}/${path}`)
  return value
}

function expectArray(value: unknown, where: string): void {
  if (!Array.isArray(value)) throw new DataError('parse', where)
}

/** latest → manifest (schema 2.x) → core files in parallel → previous overview (for Δ, optional). */
export async function loadRelease(source: DataSource): Promise<AtlasRelease> {
  const latest = await source.latest()
  const release = latest.release
  const manifest = await required<Manifest>(source, release, 'manifest.json')
  if (!ManifestShape.safeParse(manifest).success) throw new DataError('parse', `${release}/manifest.json`)
  const version = manifest.schema_version ?? ''
  if (schemaMajor(version) !== SUPPORTED_SCHEMA_MAJOR) throw new DataError('schema', version)
  const modules = new Set(manifest.modules ?? [])
  const [overview, taxonomy, topicsFile, series, edgesFile, keywordsFile] = await Promise.all([
    required<Overview>(source, release, 'overview.json'),
    required<TaxonomyFile>(source, release, 'taxonomy.json'),
    required<TopicsFile>(source, release, 'topics.json'),
    required<SeriesFile>(source, release, 'series.json'),
    source.file<EdgesFile>(release, 'edges.json'),
    modules.has('keywords') ? source.file<KeywordsFile>(release, 'keywords.json') : Promise.resolve(null),
  ])
  expectArray(topicsFile.topics, `${release}/topics.json`)
  expectArray(taxonomy.groups, `${release}/taxonomy.json`)
  expectArray(series.years, `${release}/series.json`)
  expectArray(overview.corpus_by_year, `${release}/overview.json`)
  const previous = manifest.previous_release ?? overview.previous_release ?? null
  const previousOverview = previous && isReleaseName(previous) ? await source.file<Overview>(previous, 'overview.json').catch(() => null) : null
  const topics = topicsFile.topics
  return {
    source: source.kind,
    latest,
    manifest,
    overview,
    taxonomy,
    topics,
    series,
    edges: edgesFile?.edges ?? [],
    keywords: keywordsFile?.keywords ?? null,
    previousOverview,
    previousMissing: previous && isReleaseName(previous) && !previousOverview ? previous : null,
    topicById: new Map(topics.map((t) => [t.id, t])),
    groupById: new Map(taxonomy.groups.map((g) => [g.id, g])),
    ciLevel: manifest.ci_level ?? 0.9,
    definitionVersion: manifest.definition_version ?? overview.definition_version ?? 0,
    sample: SAMPLE_PROVIDERS.has(manifest.embedding_provider ?? ''),
  }
}

/** Optional modules (contract 2.1–2.3) and the file each page reads first. */
export const MODULE_FILES = {
  journals: 'journals.json', methods: 'methods.json', diff: 'diff.json', match: 'match.json',
  institutions: 'institutions.json', regions: 'regions.json', sdg: 'sdg.json', global: 'global.json', gaps: 'gaps.json',
  references: 'references.json', search: 'search/meta.json', galaxy: 'galaxy.json', kwtrends: 'kwtrends.json',
} as const
export type ModuleName = keyof typeof MODULE_FILES

export function hasModule(release: AtlasRelease, module: ModuleName | 'journal_detail' | 'institution_detail'): boolean {
  return (release.manifest.modules ?? []).includes(module)
}

/** Any other file of the release (journals.json, journals/<id>.json, methods.json, diff.json, match.json), fetched on
 *  demand and cached; a failed request may be retried later. null = this release (or this offline file) has no such file. */
export function createFileLoader(source: DataSource, release: string): (path: string) => Promise<unknown> {
  const cache = new Map<string, Promise<unknown>>()
  return (path) => {
    let pending = cache.get(path)
    if (!pending) {
      pending = source.file<unknown>(release, path)
      pending.catch(() => cache.delete(path))
      cache.set(path, pending)
    }
    return pending
  }
}

const pad3 = (n: number) => String(n).padStart(3, '0')
export const SEARCH_VOCAB = 'search/vocab.json'
/** search/idx-<NNN>.json: the postings of the tokens whose fnv1a32 % meta.index_shards is NNN. */
export const searchIndexPath = (shard: number) => `search/idx-${pad3(shard)}.json`
/** search/docs-<NNN>.json: the article rows of ordinals NNN · docs_per_shard … (NNN + 1) · docs_per_shard − 1. */
export const searchDocsPath = (shard: number) => `search/docs-${pad3(shard)}.json`

export interface SearchFiles {
  vocab(): Promise<SearchVocab | null>
  index(shard: number): Promise<SearchIndexShard | null>
  docs(shard: number): Promise<SearchDocShard | null>
}

/** The sharded search files (contract 2.3) on demand. Each path is fetched once and kept in memory for the release
 *  (the release file loader caches every request; a failed one may be retried). */
export function createSearchFiles(file: (path: string) => Promise<unknown>): SearchFiles {
  return {
    vocab: () => file(SEARCH_VOCAB) as Promise<SearchVocab | null>,
    index: (shard) => file(searchIndexPath(shard)) as Promise<SearchIndexShard | null>,
    docs: (shard) => file(searchDocsPath(shard)) as Promise<SearchDocShard | null>,
  }
}

/** topics/<id>.json on demand, one request per topic; a failed request may be retried later. */
export function createDetailLoader(source: DataSource, release: string): (id: string) => Promise<TopicDetail | null> {
  const cache = new Map<string, Promise<TopicDetail | null>>()
  return (id) => {
    let pending = cache.get(id)
    if (!pending) {
      pending = source.file<TopicDetail>(release, `topics/${id}.json`)
      pending.catch(() => cache.delete(id))
      cache.set(id, pending)
    }
    return pending
  }
}

export function seriesOf(release: AtlasRelease, id: string): number[] | null {
  return release.series.topics[id] ?? null
}

export function groupName(release: AtlasRelease, groupId: string, lang: 'th' | 'en'): string {
  const g = release.groupById.get(groupId)
  if (!g) return groupId
  return lang === 'en' ? g.en || g.th : g.th || g.en
}

/** Topics linked to `id` in edges.json, strongest first (used when topics/<id>.json has no neighbours). */
export function neighborsOf(release: AtlasRelease, id: string, limit = 8): string[] {
  return release.edges
    .filter((e) => e.s === id || e.t === id)
    .sort((a, b) => b.w - a.w)
    .map((e) => (e.s === id ? e.t : e.s))
    .slice(0, limit)
}
