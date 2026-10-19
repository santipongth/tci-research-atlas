import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { TooltipContext, type TooltipApi } from '../lib/tooltip'

const WIDTH = 300
const HEIGHT_GUESS = 170
const TIP_ID = 'atlas-tooltip'

export function TooltipProvider({ children }: { children: ReactNode }) {
  const [tip, setTip] = useState<{ content: ReactNode; left: number; top: number; source: Element | null } | null>(null)
  const api = useMemo<TooltipApi>(() => {
    const place = (content: ReactNode, x: number, y: number, source: Element | null = null) => {
      const left = x + 14 + WIDTH > window.innerWidth - 8 ? Math.max(8, x - 14 - WIDTH) : x + 14
      const top = y + 14 + HEIGHT_GUESS > window.innerHeight - 8 ? Math.max(8, y - 14 - HEIGHT_GUESS) : y + 14
      setTip({ content, left, top, source })
    }
    return {
      show: (content, x, y, source) => place(content, x, y, source ?? null),
      showAt: (content, el) => {
        const r = el.getBoundingClientRect()
        place(content, r.left + r.width / 2, r.top + r.height / 2, el)
      },
      hide: () => setTip(null),
    }
  }, [])
  useEffect(() => {
    if (!tip) return
    const hide = () => setTip(null)
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') hide()
    }
    // a focus that scrolls the marker into view fires its scroll event after this effect; skip that one
    const arm = window.setTimeout(() => window.addEventListener('scroll', hide, { passive: true }), 150)
    window.addEventListener('keydown', onKey)
    return () => {
      window.clearTimeout(arm)
      window.removeEventListener('scroll', hide)
      window.removeEventListener('keydown', onKey)
    }
  }, [tip])
  const source = tip?.source ?? null
  useEffect(() => {
    if (!source) return
    const before = source.getAttribute('aria-describedby')
    source.setAttribute('aria-describedby', before ? `${before} ${TIP_ID}` : TIP_ID)
    return () => {
      if (before) source.setAttribute('aria-describedby', before)
      else source.removeAttribute('aria-describedby')
    }
  }, [source])
  return (
    <TooltipContext.Provider value={api}>
      {children}
      {tip ? (
        <div id={TIP_ID} className="tip" role="tooltip" style={{ left: tip.left, top: tip.top }}>
          {tip.content}
        </div>
      ) : null}
    </TooltipContext.Provider>
  )
}
