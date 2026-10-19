import { useEffect, useState } from 'react'

/**
 * A number that changes whenever web fonts finish loading. Components that measure text with canvas (label collision
 * boxes) call it so they re-measure in Sarabun once it has arrived — the @font-face rules use font-display: swap.
 */
export function useFontsVersion(): number {
  const [version, setVersion] = useState(0)
  useEffect(() => {
    const fonts = typeof document !== 'undefined' ? document.fonts : undefined
    if (!fonts) return
    let live = true
    const bump = () => {
      if (live) setVersion((v) => v + 1)
    }
    fonts.addEventListener('loadingdone', bump)
    void fonts.ready.then(bump)
    return () => {
      live = false
      fonts.removeEventListener('loadingdone', bump)
    }
  }, [])
  return version
}
