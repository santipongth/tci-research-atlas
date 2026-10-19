import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative, sep } from 'node:path'
import { fileURLToPath } from 'node:url'
import type { Bundle } from '../src/data/types'

export const FIXTURES = fileURLToPath(new URL('../fixtures', import.meta.url))

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name)
    return statSync(p).isDirectory() ? walk(p) : [p]
  })
}

/** What `atlas publish` injects into the offline HTML: {latest, files} of the newest release. */
export function bundleOf(set: 'example' | 'empty'): Bundle {
  const data = join(FIXTURES, set, 'data')
  const latest = JSON.parse(readFileSync(join(data, 'latest.json'), 'utf8')) as Bundle['latest']
  const root = join(data, latest.release)
  const files: Record<string, unknown> = {}
  for (const p of walk(root)) files[relative(root, p).split(sep).join('/')] = JSON.parse(readFileSync(p, 'utf8'))
  return { latest, files }
}

/** A fetch that serves <base>data/** from a fixture set, recording every URL it was asked for. */
export function fixtureFetch(set: 'example' | 'empty', base: string, asked: string[] = []): typeof fetch {
  const data = join(FIXTURES, set, 'data')
  return (async (input: RequestInfo | URL) => {
    const url = String(input)
    asked.push(url)
    const prefix = `${base.endsWith('/') ? base : `${base}/`}data/`
    if (!url.startsWith(prefix)) return new Response('wrong base', { status: 400 })
    try {
      return new Response(readFileSync(join(data, url.slice(prefix.length))), { status: 200, headers: { 'content-type': 'application/json' } })
    } catch {
      return new Response('not found', { status: 404 })
    }
  }) as typeof fetch
}
