import { z } from 'zod'
import type { Bundle, Latest } from './types'

export type DataErrorKind = 'missing' | 'network' | 'parse' | 'schema'

/** Why data could not be shown; the banner explains each kind in words. */
export class DataError extends Error {
  readonly kind: DataErrorKind
  readonly detail: string
  constructor(kind: DataErrorKind, detail: string) {
    super(`${kind}: ${detail}`)
    this.name = 'DataError'
    this.kind = kind
    this.detail = detail
  }
}

export function toDataError(e: unknown): DataError {
  return e instanceof DataError ? e : new DataError('network', e instanceof Error ? e.message : String(e))
}

export interface DataSource {
  readonly kind: 'http' | 'embedded'
  latest(): Promise<Latest>
  /** A file of a release (path relative to data/<release>/); null when that release has no such file. */
  file<T>(release: string, path: string): Promise<T | null>
}

const LatestShape = z.object({ release: z.string().min(1), path: z.string().min(1), schema_version: z.string().optional(), generated_at: z.string() })

function checkLatest(raw: unknown, where: string): Latest {
  const parsed = LatestShape.safeParse(raw)
  if (!parsed.success) throw new DataError('parse', `${where}: ${parsed.error.issues[0]?.message ?? 'invalid'}`)
  return raw as Latest
}

/** `${BASE_URL}data/<path>` — relative, so the site works from any sub-path and never asks for /data/ at the host root. */
export function dataUrl(base: string, path: string): string {
  return `${base.endsWith('/') ? base : `${base}/`}data/${path}`
}

/** GitHub Pages / any static host: fetch data/latest.json, then data/<release>/… */
export class HttpSource implements DataSource {
  readonly kind = 'http' as const
  private readonly base: string
  private readonly fetchImpl: typeof fetch

  constructor(base: string, fetchImpl: typeof fetch = (input, init) => fetch(input, init)) {
    this.base = base
    this.fetchImpl = fetchImpl
  }

  private async get(path: string, optional: boolean): Promise<unknown> {
    const url = dataUrl(this.base, path)
    let res: Response
    try {
      res = await this.fetchImpl(url, { cache: 'no-cache' })
    } catch (e) {
      throw new DataError('network', `${url}: ${e instanceof Error ? e.message : String(e)}`)
    }
    if (res.status === 404) {
      if (optional) return null
      throw new DataError('missing', url)
    }
    if (!res.ok) throw new DataError('network', `${url}: HTTP ${res.status}`)
    const text = await res.text()
    try {
      return JSON.parse(text) as unknown
    } catch {
      throw new DataError('parse', url)
    }
  }

  async latest(): Promise<Latest> {
    return checkLatest(await this.get('latest.json', false), 'data/latest.json')
  }

  async file<T>(release: string, path: string): Promise<T | null> {
    return (await this.get(`${release}/${path}`, true)) as T | null
  }
}

/** The single-file offline edition: the release travels inside the HTML. */
export class EmbeddedSource implements DataSource {
  readonly kind = 'embedded' as const
  private readonly bundle: Bundle

  constructor(bundle: Bundle) {
    this.bundle = bundle
  }

  async latest(): Promise<Latest> {
    return checkLatest(this.bundle.latest, 'embedded atlas-data')
  }

  async file<T>(release: string, path: string): Promise<T | null> {
    if (release !== this.bundle.latest?.release) return null
    const value = this.bundle.files[path]
    return value === undefined ? null : (value as T)
  }
}

class BrokenSource implements DataSource {
  readonly kind = 'embedded' as const
  private readonly error: DataError

  constructor(error: DataError) {
    this.error = error
  }

  latest(): Promise<Latest> {
    return Promise.reject(this.error)
  }

  file<T>(): Promise<T | null> {
    return Promise.reject(this.error)
  }
}

/** Pick the source from the <script id="atlas-data"> slot. Never throws: a damaged slot becomes a parse error on read. */
export function sourceFromEmbeddedText(text: string | null | undefined, base: string, fetchImpl?: typeof fetch): DataSource {
  const raw = (text ?? '').trim()
  if (raw === '' || raw === 'null') return new HttpSource(base, fetchImpl)
  let bundle: unknown
  try {
    bundle = JSON.parse(raw)
  } catch {
    return new BrokenSource(new DataError('parse', 'embedded atlas-data is not JSON'))
  }
  if (!bundle || typeof bundle !== 'object' || !('latest' in bundle) || !('files' in bundle)) {
    return new BrokenSource(new DataError('parse', 'embedded atlas-data has no {latest, files}'))
  }
  return new EmbeddedSource(bundle as Bundle)
}
