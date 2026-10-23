import { describe, expect, it } from 'vitest'
import { cachedLoader } from './cache'

function counter() {
  const asked: string[] = []
  return { asked, load: (k: string) => { asked.push(k); return Promise.resolve(k.toUpperCase()) } }
}

describe('cachedLoader', () => {
  it('asks once per key and shares the promise', async () => {
    const { asked, load } = counter()
    const get = cachedLoader(load)
    expect(await get('a')).toBe('A')
    expect(get('a')).toBe(get('a'))
    expect(asked).toEqual(['a'])
  })

  it('forgets a failed request so it can be retried', async () => {
    let n = 0
    const get = cachedLoader((k: string) => (++n === 1 ? Promise.reject(new Error('net')) : Promise.resolve(k)))
    await expect(get('a')).rejects.toThrow('net')
    await Promise.resolve()
    await expect(get('a')).resolves.toBe('a')
    expect(n).toBe(2)
  })

  it('keeps at most `max` evictable keys, dropping the least recently used, and never drops the others', async () => {
    const { asked, load } = counter()
    const get = cachedLoader(load, { max: 2, evictable: (k) => k.startsWith('docs-') })
    await get('keep')
    await get('docs-1')
    await get('docs-2')
    await get('docs-1') // docs-1 is now the most recent
    await get('docs-3') // evicts docs-2
    await get('keep')
    await get('docs-1')
    expect(asked).toEqual(['keep', 'docs-1', 'docs-2', 'docs-3'])
    await get('docs-2') // was evicted: asked again
    expect(asked.filter((k) => k === 'docs-2')).toHaveLength(2)
  })

  it('never drops a request still in flight: a, b, a with max 1 loads twice, then shrinks back once they settle', async () => {
    const asked: string[] = []
    const waiting: (() => void)[] = []
    const load = (k: string) => {
      asked.push(k)
      return new Promise<string>((done) => waiting.push(() => done(k)))
    }
    const get = cachedLoader(load, { max: 1 })
    const a1 = get('a')
    get('b')
    const a2 = get('a')
    expect(a2).toBe(a1)
    expect(asked).toEqual(['a', 'b'])
    waiting.forEach((w) => w())
    await a1
    await Promise.resolve()
    get('a') // the most recent settled key stays; the other was dropped
    get('b')
    expect(asked).toEqual(['a', 'b', 'b'])
  })
})
