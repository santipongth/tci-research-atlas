/**
 * Whole-corpus article search (R2) over the sharded static index of contract 2.3:
 * query → known/unknown words (searchTokens, greedy on the vocabulary) → the index shards of the known words →
 * AND of their postings → the doc shards of the matches → rank → rows.
 *
 * Ranking (Ruling 4): number of known words found in the title (Thai or English, normalised) desc, then year desc, then
 * ordinal. Postings do not record where a word occurs, so title hits are counted here once the rows are fetched.
 *
 * Fetch bound: rows live in doc shards of `docs_per_shard` articles in article_id order, so a broad query can touch
 * every doc shard. At most `maxDocShards` doc shards are fetched per query — the ones holding the most matches (ties:
 * the lower shard) — and the outcome says how many matches were examined (`examined` < `total`, `complete` false). The
 * page then tells the reader the list is drawn from part of the matches and suggests adding a word.
 */
import type { SearchDocRow, SearchDocShard, SearchIndexShard, SearchMeta, SearchVocab } from '../data/types'
import { docShardOf, indexShardOf, normalise, queryTokens } from './searchTokens'

/** Doc shards fetched per query at most (6 × 2,000 rows by default ≈ 0.5 MB gzip). */
export const MAX_DOC_SHARDS = 6

export interface SearchSource {
  meta: SearchMeta
  vocab: ReadonlySet<string>
  stopwords: ReadonlySet<string>
  index: (shard: number) => Promise<SearchIndexShard | null>
  docs: (shard: number) => Promise<SearchDocShard | null>
}

export interface SearchDoc {
  ordinal: number
  id: string
  titleTh: string
  titleEn: string
  year: number
  journal: string
  topic: string | null
  doi: string | null
  url: string | null
  cited: number
}

export interface SearchHit extends SearchDoc {
  /** known query words found in the title */
  titleHits: number
}

export interface SearchOutcome {
  known: string[]
  unknown: string[]
  /** articles that contain every known word */
  total: number
  /** of those, the ones whose rows were fetched and ranked */
  examined: number
  complete: boolean
  /** ranked; every examined match (filters and the max_results cap are applied by the caller) */
  hits: SearchHit[]
}

export interface SearchFilters {
  from: number | null
  to: number | null
  topic: string | null
  journal: string
}

export class SearchDataError extends Error {}

export function makeSource(meta: SearchMeta, vocab: SearchVocab, files: Pick<SearchSource, 'index' | 'docs'>): SearchSource {
  return { meta, vocab: new Set(vocab.tokens), stopwords: new Set(meta.stopwords), index: files.index, docs: files.docs }
}

/** Delta-encoded postings (first value absolute, then gaps) → ascending ordinals. */
export function decodePostings(deltas: readonly number[]): number[] {
  const out = new Array<number>(deltas.length)
  let acc = 0
  for (let i = 0; i < deltas.length; i++) {
    acc = i === 0 ? deltas[0] : acc + deltas[i]
    out[i] = acc
  }
  return out
}

/** Intersection of ascending lists, ascending. */
export function intersect(lists: readonly (readonly number[])[]): number[] {
  if (lists.length === 0) return []
  const sorted = [...lists].sort((a, b) => a.length - b.length)
  let acc = [...sorted[0]]
  for (const list of sorted.slice(1)) {
    const next: number[] = []
    let j = 0
    for (const v of acc) {
      while (j < list.length && list[j] < v) j++
      if (j < list.length && list[j] === v) next.push(v)
    }
    acc = next
    if (acc.length === 0) break
  }
  return acc
}

export function rowToDoc(row: SearchDocRow, ordinal: number, journals: readonly string[]): SearchDoc {
  const [id, titleTh, titleEn, year, j, topic, doi, url, cited] = row
  return { ordinal, id, titleTh, titleEn, year, journal: journals[j] ?? '', topic, doi, url, cited }
}

/** Known words that occur in the (normalised) Thai or English title. */
export function titleHits(doc: SearchDoc, known: readonly string[]): number {
  const title = `${normalise(doc.titleTh)}\n${normalise(doc.titleEn)}`
  return known.filter((w) => title.includes(w)).length
}

export function rank(hits: readonly SearchHit[]): SearchHit[] {
  return [...hits].sort((a, b) => b.titleHits - a.titleHits || b.year - a.year || a.ordinal - b.ordinal)
}

/** The doc shards to fetch: those holding the most matches first (ties: the lower shard), at most `max`. */
export function pickDocShards(ordinals: readonly number[], docsPerShard: number, max: number): number[] {
  const per = new Map<number, number>()
  for (const o of ordinals) {
    const s = docShardOf(o, docsPerShard)
    per.set(s, (per.get(s) ?? 0) + 1)
  }
  return [...per].sort((a, b) => b[1] - a[1] || a[0] - b[0]).slice(0, max).map(([s]) => s)
}

async function required<T>(p: Promise<T | null>, what: string): Promise<T> {
  const v = await p
  if (v === null || v === undefined) throw new SearchDataError(what)
  return v
}

export async function runSearch(src: SearchSource, q: string, maxDocShards = MAX_DOC_SHARDS): Promise<SearchOutcome> {
  const { meta } = src
  const { known, unknown } = queryTokens(q, src.vocab, src.stopwords, meta.max_token_chars)
  if (known.length === 0) return { known, unknown, total: 0, examined: 0, complete: true, hits: [] }

  const shardOf = new Map(known.map((w) => [w, indexShardOf(w, meta.index_shards)]))
  const shards = [...new Set(shardOf.values())]
  const loaded = await Promise.all(shards.map((s) => required(src.index(s), `search index shard ${s}`)))
  const byShard = new Map(shards.map((s, i) => [s, loaded[i]]))
  const lists = known.map((w) => decodePostings(byShard.get(shardOf.get(w) as number)?.postings[w] ?? []))
  const matches = intersect(lists)
  if (matches.length === 0) return { known, unknown, total: 0, examined: 0, complete: true, hits: [] }

  const per = meta.docs_per_shard
  const docShards = pickDocShards(matches, per, maxDocShards)
  const wanted = new Set(docShards)
  const examinedOrdinals = matches.filter((o) => wanted.has(docShardOf(o, per)))
  const docFiles = await Promise.all(docShards.map((s) => required(src.docs(s), `search doc shard ${s}`)))
  const fileOf = new Map(docShards.map((s, i) => [s, docFiles[i]]))
  const hits: SearchHit[] = []
  for (const o of examinedOrdinals) {
    const file = fileOf.get(docShardOf(o, per)) as SearchDocShard
    const row = file.docs[o - file.start]
    if (!row) continue
    const doc = rowToDoc(row, o, meta.journals)
    hits.push({ ...doc, titleHits: titleHits(doc, known) })
  }
  return { known, unknown, total: matches.length, examined: hits.length, complete: hits.length === matches.length, hits: rank(hits) }
}

export function filterHits(hits: readonly SearchHit[], f: SearchFilters): SearchHit[] {
  return hits.filter(
    (h) => (f.from === null || h.year >= f.from) && (f.to === null || h.year <= f.to) && (f.topic === null || h.topic === f.topic) && (!f.journal || h.journal === f.journal),
  )
}

/** Values present among the hits with their counts, most frequent first (ties: by value). */
export function facet<K extends string>(hits: readonly SearchHit[], key: (h: SearchHit) => K | null): [K, number][] {
  const n = new Map<K, number>()
  for (const h of hits) {
    const k = key(h)
    if (k) n.set(k, (n.get(k) ?? 0) + 1)
  }
  return [...n].sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))
}

/** The most frequent words of the vocabulary (no numbers), as query suggestions for an empty search. */
export function popularWords(vocab: SearchVocab, n: number): string[] {
  return vocab.tokens
    .map((t, i) => [t, vocab.df[i] ?? 0] as const)
    .filter(([t]) => !/^\d+$/.test(t))
    .sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1))
    .slice(0, n)
    .map(([t]) => t)
}
