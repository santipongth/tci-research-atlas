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
 * a visitor looked at ten clicks ago does not stay in memory. Only settled entries are dropped: a request still in
 * flight is shared until it answers (the set may exceed `max` meanwhile and shrinks back once it settles).
 */
export function cachedLoader<V>(load: (key: string) => Promise<V>, limit?: CacheLimit): (key: string) => Promise<V> {
  const cache = new Map<string, Promise<V>>()
  const settled = new Set<Promise<V>>()
  const recent: string[] = []
  const counts = (key: string) => limit !== undefined && (limit.evictable?.(key) ?? true)
  const forget = (key: string) => {
    cache.delete(key)
    const i = recent.indexOf(key)
    if (i >= 0) recent.splice(i, 1)
  }
  const trim = () => {
    if (limit === undefined) return
    // least recently used first; an entry still in flight stops the trim (its turn comes when it settles)
    while (recent.length > limit.max) {
      const p = cache.get(recent[0])
      if (p !== undefined && !settled.has(p)) return
      cache.delete(recent.shift() as string)
      if (p !== undefined) settled.delete(p)
    }
  }
  return (key) => {
    let pending = cache.get(key)
    if (pending === undefined) {
      const request = load(key)
      pending = request
      request.then(
        () => {
          settled.add(request)
          trim()
        },
        () => {
          if (cache.get(key) === request) forget(key)
        },
      )
      cache.set(key, request)
    }
    if (limit !== undefined && counts(key)) {
      const i = recent.indexOf(key)
      if (i >= 0) recent.splice(i, 1)
      recent.push(key)
      trim()
    }
    return pending
  }
}
