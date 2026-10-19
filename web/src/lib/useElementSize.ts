import { useEffect, useState } from 'react'

/** Measure an element with ResizeObserver (callback ref). Charts draw nothing until the width is known. Also returns the element. */
export function useElementSize<T extends Element>(): [(el: T | null) => void, { width: number; height: number }, T | null] {
  const [el, setEl] = useState<T | null>(null)
  const [size, setSize] = useState({ width: 0, height: 0 })
  useEffect(() => {
    if (!el) return
    const ro = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect
      setSize((s) => (s.width === Math.round(width) && s.height === Math.round(height) ? s : { width: Math.round(width), height: Math.round(height) }))
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [el])
  return [setEl, size, el]
}
