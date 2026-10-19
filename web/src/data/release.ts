import { z } from 'zod'
import { DataError, isReleaseName, type DataSource } from './source'
import type {
  EdgesFile, EmergingKeyword, GroupInfo, KeywordsFile, Latest, Manifest, Overview, SeriesFile, TaxonomyFile, Topic, TopicDetail, TopicsFile,
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
