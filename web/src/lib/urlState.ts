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

/** The chart ⇄ table view some older components still accept (no page shows the switch since 2026-10-24). */
export type View = 'chart' | 'table'

/** /overview: the rising / falling list and the findings / policy switch. */
export const MOVES = ['up', 'down'] as const
export const POINTS = ['find', 'policy'] as const
export const overviewCodec = makeCodec<{ mv: (typeof MOVES)[number]; pt: (typeof POINTS)[number] }>({
  mv: oneOf('mv', MOVES, 'up'),
  pt: oneOf('pt', POINTS, 'find'),
})

/** /topics: the status shown and how its topics are ranked (an old /emerging?status=… link keeps its status). */
export const TOPIC_BY = ['growth', 'size'] as const
export const topicsCodec = makeCodec<{ status: StatusId; by: (typeof TOPIC_BY)[number] }>({
  status: oneOf('status', STATUSES, 'EMERGING'),
  by: oneOf('by', TOPIC_BY, 'growth'),
})

/** /places: what the province map measures (per 100,000 people only when the release has the population table). */
export const REGION_METRICS = ['articles', 'per100k'] as const
export const placesCodec = makeCodec<{ m: (typeof REGION_METRICS)[number] }>({ m: oneOf('m', REGION_METRICS, 'articles') })

/** /journals: how the journal list is ranked. */
export const JOURNAL_BY = ['articles', 'complete'] as const
export const journalsCodec = makeCodec<{ by: (typeof JOURNAL_BY)[number] }>({ by: oneOf('by', JOURNAL_BY, 'articles') })

/** /goals: the goal framework shown in the tiles. */
export const goalsCodec = makeCodec<{ fw: string }>({ fw: text('fw', 24) })

/** /atlas: the selected topic, hidden statuses and map layers. */
export const LAYERS = ['contours', 'tints', 'names'] as const
export type Layer = (typeof LAYERS)[number]
export interface AtlasUrlState {
  sel: string | null
  hide: StatusId[]
  layers: Layer[]
}
export const atlasCodec = makeCodec<AtlasUrlState>({
  sel: optionalTopic('sel'),
  hide: setOf('hide', STATUSES, []),
  layers: setOf('layers', LAYERS, LAYERS),
})

/** /galaxy: the year range and the field in focus. */
export interface GalaxyUrlState {
  from: number | null
  to: number | null
  /** taxonomy group id (F… OpenAlex field, G… fallback group); '' = every field */
  g: string
}
export const galaxyCodec = makeCodec<GalaxyUrlState>({
  from: optionalYear('from'),
  to: optionalYear('to'),
  g: text('g', 24),
})
