import { useSyncExternalStore } from 'react'

/** Below this width the navigation folds into the header's menu button and "ในหน้านี้" into a disclosure (layout.css). */
export const COMPACT_CHROME = '(max-width: 899px)'

const media = (query: string) => (typeof window !== 'undefined' && typeof window.matchMedia === 'function' ? window.matchMedia(query) : null)

/** True while the media query matches; re-renders when it changes (no state set in an effect). */
export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const m = media(query)
      m?.addEventListener('change', onChange)
      return () => m?.removeEventListener('change', onChange)
    },
    () => media(query)?.matches ?? false,
    () => false,
  )
}
