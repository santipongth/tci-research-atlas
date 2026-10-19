import { useMemo, useState, type KeyboardEvent } from 'react'
import { useRelease } from '../data/atlasContext'
import type { Topic } from '../data/types'
import { useI18n } from '../lib/i18n'
import { buildSearchIndex, searchTopics } from '../lib/search'
import { StatusGlyph } from './StatusGlyph'

/** ARIA 1.2 combobox over every topic name and keyword (Thai and English, tone-mark tolerant). */
export function TopicSearch({ id, label, onPick, hideLabel = false, exclude, placeholder }: {
  id: string
  label: string
  onPick: (topicId: string) => void
  hideLabel?: boolean
  exclude?: readonly string[]
  placeholder?: string
}) {
  const release = useRelease()
  const { t, name, other, otherLang } = useI18n()
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const index = useMemo(
    () => (release ? buildSearchIndex(release.topics.map((tp) => ({ id: tp.id, th: tp.th, en: tp.en, keywords: tp.keywords ?? [], size: tp.size }))) : null),
    [release],
  )
  const results = useMemo(() => {
    if (!index || !release) return []
    const skip = new Set(exclude ?? [])
    return searchTopics(index, query, 8 + skip.size)
      .filter((h) => !skip.has(h.id))
      .slice(0, 8)
      .map((h) => release.topicById.get(h.id))
      .filter((tp): tp is Topic => tp !== undefined)
  }, [index, release, query, exclude])
  const hasQuery = query.trim() !== ''
  const showList = open && hasQuery && results.length > 0
  const pick = (topicId: string) => {
    setQuery('')
    setOpen(false)
    setActive(0)
    onPick(topicId)
  }
  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setOpen(true)
      setActive((a) => Math.min(a + 1, Math.max(results.length - 1, 0)))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((a) => Math.max(a - 1, 0))
    } else if (e.key === 'Enter') {
      const hit = results[active]
      if (hasQuery && hit) {
        e.preventDefault()
        pick(hit.id)
      }
    } else if (e.key === 'Escape') {
      if (open) {
        e.preventDefault()
        setOpen(false)
      } else setQuery('')
    }
  }
  return (
    <div className="search">
      <label htmlFor={id} className={hideLabel ? 'sr-only' : 'search-label'}>{label}</label>
      <input
        id={id}
        type="search"
        role="combobox"
        aria-expanded={showList}
        aria-controls={`${id}-list`}
        aria-autocomplete="list"
        aria-activedescendant={showList ? `${id}-opt-${active}` : undefined}
        autoComplete="off"
        spellCheck={false}
        placeholder={placeholder ?? t('search.placeholder')}
        value={query}
        disabled={!release}
        onChange={(e) => {
          setQuery(e.target.value)
          setOpen(true)
          setActive(0)
        }}
        onKeyDown={onKeyDown}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
      />
      <ul id={`${id}-list`} role="listbox" aria-label={label} className="search-list" hidden={!showList}>
        {results.map((tp, i) => (
          <li key={tp.id} id={`${id}-opt-${i}`} role="option" aria-selected={i === active} className={i === active ? 'is-active' : undefined} onMouseDown={(e) => e.preventDefault()} onClick={() => pick(tp.id)}>
            <StatusGlyph status={tp.status} size={12} />
            <span className="search-name">{name(tp)}</span>
            <span className="search-alt" lang={otherLang}>{other(tp)}</span>
          </li>
        ))}
      </ul>
      <div className="sr-only" role="status" aria-live="polite">
        {hasQuery ? (results.length ? t('search.count', { n: results.length }) : t('search.none', { q: query })) : ''}
      </div>
      {open && hasQuery && results.length === 0 ? <p className="search-none">{t('search.none', { q: query })}</p> : null}
    </div>
  )
}
