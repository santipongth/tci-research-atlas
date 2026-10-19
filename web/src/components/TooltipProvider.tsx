import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { TooltipContext, type TooltipApi } from '../lib/tooltip'

const WIDTH = 300
const HEIGHT_GUESS = 170

export function TooltipProvider({ children }: { children: ReactNode }) {
  const [tip, setTip] = useState<{ content: ReactNode; left: number; top: number } | null>(null)
  const api = useMemo<TooltipApi>(() => {
    const place = (content: ReactNode, x: number, y: number) => {
      const left = x + 14 + WIDTH > window.innerWidth - 8 ? Math.max(8, x - 14 - WIDTH) : x + 14
      const top = y + 14 + HEIGHT_GUESS > window.innerHeight - 8 ? Math.max(8, y - 14 - HEIGHT_GUESS) : y + 14
      setTip({ content, left, top })
    }
    return {
      show: place,
      showAt: (content, el) => {
        const r = el.getBoundingClientRect()
        place(content, r.left + r.width / 2, r.top + r.height / 2)
      },
      hide: () => setTip(null),
    }
  }, [])
  useEffect(() => {
    if (!tip) return
    const hide = () => setTip(null)
    window.addEventListener('scroll', hide, { passive: true })
    return () => window.removeEventListener('scroll', hide)
  }, [tip])
  return (
    <TooltipContext.Provider value={api}>
      {children}
      {tip ? (
        <div className="tip" role="tooltip" style={{ left: tip.left, top: tip.top }}>
          {tip.content}
        </div>
      ) : null}
    </TooltipContext.Provider>
  )
}
