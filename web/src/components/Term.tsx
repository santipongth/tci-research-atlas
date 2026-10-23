import { lazy, Suspense, useEffect, useId, useRef, useState, type CSSProperties, type KeyboardEvent, type ReactNode } from 'react'
import { termKey, type GlossaryTerm } from '../lib/glossary'
import { useI18n } from '../lib/i18n'

// definitions are a few kilobytes of text: their own chunk, fetched with the first term on a page
const TermDef = lazy(() => import('./TermDef'))

/** Popover width: 22rem, never wider than the screen minus the page gutters. */
const POP_MAX = 352
const GUTTER = 16

/**
 * An inline disclosure: a button (aria-expanded + aria-controls) that opens a small popover right below it.
 * Click or Enter/Space toggles, Escape closes and returns focus, a tap or click elsewhere closes. Never hover-only.
 * Phrasing content only, so it can sit inside a sentence, a table cell or a source line.
 */
export function InfoPop({ label, title, children, className }: { label: ReactNode; title?: ReactNode; children: ReactNode; className?: string }) {
  const id = useId()
  const [pos, setPos] = useState<CSSProperties | null>(null)
  const wrap = useRef<HTMLSpanElement>(null)
  const btn = useRef<HTMLButtonElement>(null)
  const open = pos !== null
  useEffect(() => {
    if (!open) return
    const onDown = (e: PointerEvent) => {
      if (!wrap.current?.contains(e.target as Node)) setPos(null)
    }
    document.addEventListener('pointerdown', onDown)
    return () => document.removeEventListener('pointerdown', onDown)
  }, [open])
  const toggle = () => {
    if (open) {
      setPos(null)
      return
    }
    // placed from the button's own position when it opens: kept inside the screen, never clipped on a phone
    const r = btn.current?.getBoundingClientRect()
    const vw = typeof window === 'undefined' ? 1024 : window.innerWidth
    const width = Math.min(POP_MAX, vw - 2 * GUTTER)
    const left = r ? Math.max(GUTTER - r.left, Math.min(0, vw - GUTTER - (r.left + width))) : 0
    setPos({ left, width })
  }
  const onKeyDown = (e: KeyboardEvent<HTMLSpanElement>) => {
    if (e.key === 'Escape' && open) {
      e.preventDefault()
      e.stopPropagation()
      setPos(null)
      btn.current?.focus()
    }
  }
  return (
    <span ref={wrap} className={`pop${className ? ` ${className}` : ''}`} onKeyDown={onKeyDown}>
      <button ref={btn} type="button" className="pop-btn" aria-expanded={open} aria-controls={id} onClick={toggle}>
        {label}
      </button>
      <span id={id} className="pop-panel" hidden={!open} style={pos ?? undefined}>
        {title ? <span className="pop-title">{title}</span> : null}
        <span className="pop-body">{children}</span>
      </span>
    </span>
  )
}

/** A glossary term in running text (layer 2 of the copy ruling): the word, and its plain definition in a popover. */
export function Term({ term, children }: { term: GlossaryTerm; children?: ReactNode }) {
  const { t } = useI18n()
  const word = t(termKey(term))
  return (
    <InfoPop className="term" label={children ?? word} title={word}>
      <Suspense fallback={t('loading')}>
        <TermDef term={term} />
      </Suspense>
    </InfoPop>
  )
}
