import { useMemo, useState, type KeyboardEvent } from 'react'
import { Link } from 'react-router'
import { useRelease } from '../data/atlasContext'
import type { Topic } from '../data/types'
import { useI18n } from '../lib/i18n'
import { comboKey } from '../lib/comboKeys'
import { buildSearchIndex, searchTopics } from '../lib/search'
import { StatusGlyph } from './StatusGlyph'

/** ARIA 1.2 combobox over every topic name and keyword (Thai and English, tone-mark tolerant). */
export function TopicSearch({ id, label, onPick, hideLabel = false, exclude, placeholder, disabled = false, articleSearch = false }: {
  id: string
  label: string
  onPick: (topicId: string) => void
  hideLabel?: boolean
  exclude?: readonly string[]
  placeholder?: string
  disabled?: boolean
  /** no topic matches → offer the whole-corpus article search (/search) for the same words */
  articleSearch?: boolean
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
    const a = comboKey(e.key, { open, showList, active, count: results.length, hasQuery })
    if (a.prevent) e.preventDefault()
    if (a.open !== undefined) setOpen(a.open)
    if (a.active !== undefined) setActive(a.active)
    if (a.clear) setQuery('')
    const hit = results[active]
    if (a.pick && hit) pick(hit.id)
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
        disabled={!release || disabled}
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
      {open && hasQuery && results.length === 0 ? (
        <p className="search-none">
          {t('search.none', { q: query })}
          {articleSearch ? (
            <>
              {' · '}
              <Link to={`/search?q=${encodeURIComponent(query.trim())}`} onMouseDown={(e) => e.preventDefault()} onClick={() => { setQuery(''); setOpen(false) }}>
                {t('search.articles')}
              </Link>
            </>
          ) : null}
        </p>
      ) : null}
    </div>
  )
}
