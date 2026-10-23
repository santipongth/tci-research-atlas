import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router'
import { scrollToId } from './scroll'

/** After a page change (not on first load, not on ?query changes): scroll to top and focus <main>.
 * A link may carry route state `{ section: id }` (e.g. the footer's "cite" link): then that section is scrolled to instead. */
export function useRouteFocus(): void {
  const { pathname, state, key } = useLocation()
  const section = state && typeof state === 'object' && typeof (state as { section?: unknown }).section === 'string' ? (state as { section: string }).section : null
  const first = useRef(true)
  useEffect(() => {
    if (first.current) {
      first.current = false
      return
    }
    window.scrollTo(0, 0)
    document.getElementById('main')?.focus({ preventScroll: true })
  }, [pathname])
  useEffect(() => {
    if (!section) return
    scrollToId(section)
    // charts above the section size themselves after the first paint: once the page has settled, land on it again
    const settle = window.setTimeout(() => {
      const top = document.getElementById(section)?.getBoundingClientRect().top
      if (top !== undefined && (top < -4 || top > 120)) document.getElementById(section)?.scrollIntoView({ block: 'start' })
    }, 900)
    return () => window.clearTimeout(settle)
  }, [key, section])
}
