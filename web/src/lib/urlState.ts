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
