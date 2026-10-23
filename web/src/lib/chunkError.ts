/** A lazy page's file is gone (the site was redeployed while this tab stayed open) or could not be fetched. */
export function isChunkLoadError(error: unknown): boolean {
  const text = error instanceof Error ? `${error.name} ${error.message}` : String(error)
  return /dynamically imported module|importing a module script failed|loading (css )?chunk .* failed|ChunkLoadError/i.test(text)
}

export const RELOAD_GUARD_KEY = 'atlas-chunk-reload'
const GUARD_MS = 60_000

/** Reloading once fetches the new build; the guard (a time stamp in sessionStorage) stops a reload loop when the
 *  failure is not a redeploy. Without storage there is no guard, so no automatic reload. */
export function shouldReloadOnce(storage: Pick<Storage, 'getItem' | 'setItem'> | null, now: number): boolean {
  if (!storage) return false
  try {
    const last = Number(storage.getItem(RELOAD_GUARD_KEY))
    if (Number.isFinite(last) && last > 0 && now - last < GUARD_MS) return false
    storage.setItem(RELOAD_GUARD_KEY, String(now))
    return true
  } catch {
    return false
  }
}
