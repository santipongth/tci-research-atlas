import { STATUSES, type StatusId } from './status'

/** One URL query key with a default (defaults are never written, so shared links stay short). */
export interface Field<V> {
  key: string
  def: V
  parse(raw: string | null): V
  write(value: V): string | null
}

export interface Codec<T> {
  defaults: T
  parse(params: URLSearchParams): T
  write(state: T): URLSearchParams
  /** query keys this codec owns */
  keys: readonly string[]
}

/** New query string for a state patch: the codec's own keys are rewritten, every other param is kept. */
export function mergeParams<T>(codec: Codec<T>, prev: URLSearchParams, patch: Partial<T>): URLSearchParams {
  const next = codec.write({ ...codec.parse(prev), ...patch })
  for (const [k, v] of prev) if (!codec.keys.includes(k) && !next.has(k)) next.set(k, v)
  return next
}

export function makeCodec<T extends object>(fields: { [K in keyof T]: Field<T[K]> }): Codec<T> {
  const entries = Object.entries(fields) as [keyof T & string, Field<unknown>][]
  const defaults = Object.fromEntries(entries.map(([k, f]) => [k, f.def])) as T
  return {
    defaults,
    keys: entries.map(([, f]) => f.key),
    parse(params) {
      return Object.fromEntries(entries.map(([k, f]) => [k, f.parse(params.get(f.key))])) as T
    },
    write(state) {
      const out = new URLSearchParams()
      for (const [k, f] of entries) {
        const v = f.write(state[k])
        if (v !== null) out.set(f.key, v)
      }
      return out
    },
  }
}

export function oneOf<V extends string>(key: string, values: readonly V[], def: V): Field<V> {
  return {
    key,
    def,
    parse: (raw) => (raw !== null && (values as readonly string[]).includes(raw) ? (raw as V) : def),
    write: (v) => (v === def ? null : v),
  }
}

/** A set written in canonical order; "" in the URL means "none" (different from the default). */
export function setOf<V extends string>(key: string, values: readonly V[], def: readonly V[]): Field<V[]> {
  const norm = (xs: readonly string[]): V[] => values.filter((v) => xs.includes(v))
  const defN = norm(def)
  const same = (a: readonly V[]) => a.length === defN.length && a.every((v, i) => v === defN[i])
  return {
    key,
    def: defN,
    parse: (raw) => (raw === null ? defN : raw === '' ? [] : norm(raw.split(','))),
    write: (v) => {
      const n = norm(v)
      return same(n) ? null : n.join(',')
    },
  }
}

const TOPIC_ID = /^T\d{6}$/

/** Ordered topic ids, deduplicated, invalid ids dropped, at most `max`. */
export function topicList(key: string, max: number): Field<string[]> {
  return {
    key,
    def: [],
    parse: (raw) => [...new Set((raw ?? '').split(',').map((s) => s.trim()).filter((s) => TOPIC_ID.test(s)))].slice(0, max),
    write: (v) => (v.length ? v.join(',') : null),
  }
}

export function optionalTopic(key: string): Field<string | null> {
  return { key, def: null, parse: (raw) => (raw && TOPIC_ID.test(raw) ? raw : null), write: (v) => v }
}

/** A 4-digit year, or null. */
export function optionalYear(key: string): Field<number | null> {
  return { key, def: null, parse: (raw) => (raw && /^\d{4}$/.test(raw) ? Number(raw) : null), write: (v) => (v === null ? null : String(v)) }
}

export function text(key: string, maxLength: number): Field<string> {
  return { key, def: '', parse: (raw) => (raw ?? '').slice(0, maxLength), write: (v) => (v ? v.slice(0, maxLength) : null) }
}

export const VIEWS = ['chart', 'table'] as const
export type View = (typeof VIEWS)[number]
export const EMERGING_SORTS = ['growth', 'lo', 'share', 'ratio', 'journals', 'orgs', 'score', 'articles', 'name'] as const
export type EmergingSort = (typeof EMERGING_SORTS)[number]
export const LAYERS = ['contours', 'tints', 'names'] as const
export type Layer = (typeof LAYERS)[number]

export interface EmergingUrlState {
  status: StatusId
  sort: EmergingSort
  dir: 'asc' | 'desc'
  view: View
}
export const emergingCodec = makeCodec<EmergingUrlState>({
  status: oneOf('status', STATUSES, 'EMERGING'),
  sort: oneOf('sort', EMERGING_SORTS, 'growth'),
  dir: oneOf('dir', ['asc', 'desc'] as const, 'desc'),
  view: oneOf('view', VIEWS, 'table'),
})

export interface AtlasUrlState {
  sel: string | null
  hide: StatusId[]
  layers: Layer[]
  q: string
}
export const atlasCodec = makeCodec<AtlasUrlState>({
  sel: optionalTopic('sel'),
  hide: setOf('hide', STATUSES, []),
  layers: setOf('layers', LAYERS, LAYERS),
  q: text('q', 80),
})

export interface CompareUrlState {
  ids: string[]
  metric: 'share' | 'count'
  view: View
}
export const compareCodec = makeCodec<CompareUrlState>({
  ids: topicList('ids', 4),
  metric: oneOf('metric', ['share', 'count'] as const, 'share'),
  view: oneOf('view', VIEWS, 'chart'),
})

export const overviewCodec = makeCodec<{ st: View; pf: View }>({ st: oneOf('st', VIEWS, 'chart'), pf: oneOf('pf', VIEWS, 'chart') })
export const topicCodec = makeCodec<{ trend: View }>({ trend: oneOf('trend', VIEWS, 'chart') })
export const JOURNAL_SORTS = ['name', 'tier', 'articles', 'completeness', 'inhouse', 'orgs', 'foreign'] as const
export type JournalSort = (typeof JOURNAL_SORTS)[number]
export const TIERS = ['all', '1', '2', '3', 'none'] as const
export interface JournalsUrlState {
  q: string
  tier: (typeof TIERS)[number]
  sort: JournalSort
  dir: 'asc' | 'desc'
}
export const journalsCodec = makeCodec<JournalsUrlState>({
  q: text('q', 80),
  tier: oneOf('tier', TIERS, 'all'),
  sort: oneOf('sort', JOURNAL_SORTS, 'articles'),
  dir: oneOf('dir', ['asc', 'desc'] as const, 'desc'),
})
export const journalCodec = makeCodec<{ drift: View }>({ drift: oneOf('drift', VIEWS, 'chart') })
export const methodsCodec = makeCodec<{ trend: View; mono: 'all' | 'only' }>({ trend: oneOf('trend', VIEWS, 'chart'), mono: oneOf('mono', ['all', 'only'] as const, 'all') })
export const INST_SORTS = ['name', 'province', 'articles', 'recent', 'intl', 'partners'] as const
export type InstSort = (typeof INST_SORTS)[number]
export const INST_TYPE_FILTERS = ['all', 'university', 'rajabhat', 'rajamangala', 'hospital', 'government', 'research', 'company', 'other'] as const
export interface InstitutionsUrlState {
  q: string
  type: (typeof INST_TYPE_FILTERS)[number]
  sort: InstSort
  dir: 'asc' | 'desc'
}
export const institutionsCodec = makeCodec<InstitutionsUrlState>({
  q: text('q', 80),
  type: oneOf('type', INST_TYPE_FILTERS, 'all'),
  sort: oneOf('sort', INST_SORTS, 'articles'),
  dir: oneOf('dir', ['asc', 'desc'] as const, 'desc'),
})
export const REGION_METRICS = ['articles', 'per100k'] as const
export const regionsCodec = makeCodec<{ m: (typeof REGION_METRICS)[number]; view: View }>({
  m: oneOf('m', REGION_METRICS, 'articles'),
  view: oneOf('view', VIEWS, 'chart'),
})
export const sdgCodec = makeCodec<{ fw: string }>({ fw: text('fw', 24) })
export interface SearchUrlState {
  q: string
  from: number | null
  to: number | null
  topic: string | null
  journal: string
}
export const searchCodec = makeCodec<SearchUrlState>({
  q: text('q', 200),
  from: optionalYear('from'),
  to: optionalYear('to'),
  topic: optionalTopic('topic'),
  journal: text('journal', 300),
})
export const gapsCodec = makeCodec<{ all: 'no' | 'yes' }>({ all: oneOf('all', ['no', 'yes'] as const, 'no') })
export interface GalaxyUrlState {
  from: number | null
  to: number | null
  /** taxonomy group id (F… OpenAlex field, G… fallback group); '' = every field */
  g: string
  view: View
}
export const galaxyCodec = makeCodec<GalaxyUrlState>({
  from: optionalYear('from'),
  to: optionalYear('to'),
  g: text('g', 24),
  view: oneOf('view', VIEWS, 'chart'),
})
/** Keyword picks of /keywords: "<lang>:<term>" items joined by "|". null (no k in the URL) = the page's default pick;
 *  "" = the visitor removed every keyword. */
export function keywordList(key: string, max: number): Field<string[] | null> {
  return {
    key,
    def: null,
    parse: (raw) =>
      raw === null
        ? null
        : [...new Set(raw.split('|').map((s) => s.trim()).filter((s) => /^(th|en):\S/.test(s) && s.length <= 160))].slice(0, max),
    write: (v) => (v === null ? null : v.join('|')),
  }
}
export const KEYWORD_MAX = 4
export interface KeywordsUrlState {
  k: string[] | null
  view: View
  /** glossary filter */
  gq: string
}
export const keywordsCodec = makeCodec<KeywordsUrlState>({
  k: keywordList('k', KEYWORD_MAX),
  view: oneOf('view', VIEWS, 'chart'),
  gq: text('gq', 80),
})
