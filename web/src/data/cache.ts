/** Which entries of a loader's cache may be dropped, and how many are kept. */
export interface CacheLimit {
  /** at most this many evictable entries stay in memory; the least recently used goes first */
  max: number
  /** keys that count toward `max` (default: every key); the others are kept for the life of the page */
  evictable?: (key: string) => boolean
}

/**
 * A loader that asks for each key once and shares the answer: a repeated key returns the same promise, a failed request
 * is forgotten so it may be retried. With `limit`, the evictable keys form a small least-recently-used set — a big file
 * a visitor looked at ten clicks ago does not stay in memory.
 */
export function cachedLoader<V>(load: (key: string) => Promise<V>, limit?: CacheLimit): (key: string) => Promise<V> {
  const cache = new Map<string, Promise<V>>()
  const recent: string[] = []
  const counts = (key: string) => limit !== undefined && (limit.evictable?.(key) ?? true)
  const forget = (key: string) => {
    cache.delete(key)
    const i = recent.indexOf(key)
    if (i >= 0) recent.splice(i, 1)
  }
  return (key) => {
    let pending = cache.get(key)
    if (pending === undefined) {
      const request = load(key)
      pending = request
      request.catch(() => {
        if (cache.get(key) === request) forget(key)
      })
      cache.set(key, request)
    }
    if (limit !== undefined && counts(key)) {
      const i = recent.indexOf(key)
      if (i >= 0) recent.splice(i, 1)
      recent.push(key)
      while (recent.length > limit.max) cache.delete(recent.shift() as string)
    }
    return pending
  }
}
