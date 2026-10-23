import { describe, expect, it } from 'vitest'
import { isChunkLoadError, RELOAD_GUARD_KEY, shouldReloadOnce } from './chunkError'

function memory(initial: Record<string, string> = {}) {
  const data = { ...initial }
  return { getItem: (k: string) => data[k] ?? null, setItem: (k: string, v: string) => void (data[k] = v), data }
}

describe('chunk load errors', () => {
  it('recognises the browsers\' messages for a missing lazy chunk', () => {
    expect(isChunkLoadError(new TypeError('Failed to fetch dynamically imported module: https://x/assets/Page-abc.js'))).toBe(true)
    expect(isChunkLoadError(new TypeError('error loading dynamically imported module'))).toBe(true)
    expect(isChunkLoadError(new TypeError('Importing a module script failed.'))).toBe(true)
    expect(isChunkLoadError(new Error('boom'))).toBe(false)
    expect(isChunkLoadError(undefined)).toBe(false)
  })

  it('reloads once, then not again within a minute', () => {
    const s = memory()
    expect(shouldReloadOnce(s, 1_000_000)).toBe(true)
    expect(s.data[RELOAD_GUARD_KEY]).toBe('1000000')
    expect(shouldReloadOnce(s, 1_030_000)).toBe(false)
    expect(shouldReloadOnce(s, 1_100_000)).toBe(true)
  })

  it('never reloads without storage or when storage throws', () => {
    expect(shouldReloadOnce(null, 5)).toBe(false)
    const broken = { getItem: () => { throw new Error('blocked') }, setItem: () => undefined }
    expect(shouldReloadOnce(broken, 5)).toBe(false)
  })
})
