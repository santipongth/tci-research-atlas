import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router'

/** After a page change (not on first load, not on ?query changes): scroll to top and focus <main>. */
export function useRouteFocus(): void {
  const { pathname } = useLocation()
  const first = useRef(true)
  useEffect(() => {
    if (first.current) {
      first.current = false
      return
    }
    window.scrollTo(0, 0)
    document.getElementById('main')?.focus({ preventScroll: true })
  }, [pathname])
}
