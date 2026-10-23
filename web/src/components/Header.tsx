import { useLayoutEffect, useRef, useState, type FocusEvent, type KeyboardEvent } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router'
import { Wordmark } from '../brand/Wordmark'
import { useRelease } from '../data/atlasContext'
import { hasModule } from '../data/release'
import { useI18n } from '../lib/i18n'
import { COMPACT_CHROME, useMediaQuery } from '../lib/useMediaQuery'
import type { StrKey } from '../strings'
import { LangSwitch } from './LangSwitch'
import { TopicSearch } from './TopicSearch'

interface Item {
  to: string
  key: StrKey
  /** one plain line under the page name in the desktop menu: the question the page answers */
  hint?: StrKey
}

const START: readonly Item[] = [
  { to: '/overview', key: 'nav.overview' },
  { to: '/brief', key: 'nav.brief' },
]
/** Pages grouped by the question a reader brings, not by who they are — every page stays two clicks away. */
const GROUPS: readonly { id: string; key: StrKey; items: readonly Item[] }[] = [
  {
    id: 'nav-coming',
    key: 'nav.q.coming',
    items: [
      { to: '/emerging', key: 'nav.emerging', hint: 'nav.hint.emerging' },
      { to: '/keywords', key: 'nav.keywords', hint: 'nav.hint.keywords' },
      { to: '/changes', key: 'nav.changes', hint: 'nav.hint.changes' },
      { to: '/gaps', key: 'nav.gaps', hint: 'nav.hint.gaps' },
    ],
  },
  {
    id: 'nav-who',
    key: 'nav.q.who',
    items: [
      { to: '/institutions', key: 'nav.institutions', hint: 'nav.hint.institutions' },
      { to: '/journals', key: 'nav.journals', hint: 'nav.hint.journals' },
      { to: '/methods', key: 'nav.methods', hint: 'nav.hint.methods' },
      { to: '/references', key: 'nav.references', hint: 'nav.hint.references' },
    ],
  },
  {
    id: 'nav-where',
    key: 'nav.q.where',
    items: [
      { to: '/regions', key: 'nav.regions', hint: 'nav.hint.regions' },
      { to: '/global', key: 'nav.global', hint: 'nav.hint.global' },
      { to: '/sdg', key: 'nav.sdg', hint: 'nav.hint.sdg' },
    ],
  },
  {
    id: 'nav-find',
    key: 'nav.q.find',
    items: [
      { to: '/search', key: 'nav.search', hint: 'nav.hint.search' },
      { to: '/atlas', key: 'nav.atlas', hint: 'nav.hint.atlas' },
      { to: '/galaxy', key: 'nav.galaxy', hint: 'nav.hint.galaxy' },
      { to: '/compare', key: 'nav.compare', hint: 'nav.hint.compare' },
      { to: '/match', key: 'nav.match', hint: 'nav.hint.match' },
    ],
  },
]
const END: readonly Item[] = [
  { to: '/data', key: 'nav.data' },
  { to: '/about', key: 'nav.about' },
]

/** A disclosure menu (not an ARIA menu): Enter/Space toggles, Escape closes and returns focus, leaving it closes. */
function NavGroup({ id, label, items, pathname }: { id: string; label: string; items: readonly Item[]; pathname: string }) {
  const { t } = useI18n()
  const [open, setOpen] = useState(false)
  const menu = useRef<HTMLUListElement>(null)
  // a group near the right edge opens its menu leftwards, so it never pushes the page sideways (the row wraps differently at every width)
  useLayoutEffect(() => {
    const el = menu.current
    if (!open || !el) return
    el.classList.remove('is-flipped')
    if (el.getBoundingClientRect().right > document.documentElement.clientWidth - 16) el.classList.add('is-flipped')
  }, [open])
  const active = items.some((i) => pathname === i.to || pathname.startsWith(`${i.to}/`))
  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Escape' && open) {
      setOpen(false)
      e.currentTarget.querySelector('button')?.focus()
    }
  }
  const onBlur = (e: FocusEvent<HTMLDivElement>) => {
    if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setOpen(false)
  }
  return (
    <div className="nav-group" onKeyDown={onKeyDown} onBlur={onBlur}>
      <button type="button" className={`nav-link nav-btn${active ? ' is-active' : ''}`} aria-expanded={open} aria-controls={`${id}-menu`} onClick={() => setOpen((o) => !o)}>
        <span>{label}</span>
        <svg viewBox="0 0 10 6" width="10" height="6" aria-hidden="true" focusable="false">
          <path d="M1 1l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.6" />
        </svg>
      </button>
      <ul ref={menu} id={`${id}-menu`} className="nav-menu" hidden={!open}>
        {items.map((i) => (
          <li key={i.to}>
            <NavLink to={i.to} className="nav-menu-link" onClick={() => setOpen(false)} aria-describedby={i.hint ? `${id}-${i.to.slice(1)}-hint` : undefined}>
              <span className="nav-menu-name">{t(i.key)}</span>
              {i.hint ? (
                <span className="nav-menu-hint" id={`${id}-${i.to.slice(1)}-hint`} aria-hidden="true">
                  {t(i.hint)}
                </span>
              ) : null}
            </NavLink>
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Inside the phone menu a group is a plain labelled list: every page one tap away, no nested disclosures. */
function NavGroupList({ id, label, items }: { id: string; label: string; items: readonly Item[] }) {
  const { t } = useI18n()
  return (
    <>
      <p className="nav-group-h" id={`${id}-h`}>{label}</p>
      <ul className="nav-sub" aria-labelledby={`${id}-h`}>
        {items.map((i) => (
          <li key={i.to}>
            <NavLink to={i.to} className="nav-link">
              {t(i.key)}
            </NavLink>
          </li>
        ))}
      </ul>
    </>
  )
}

function MenuIcon({ open }: { open: boolean }) {
  return (
    <svg viewBox="0 0 18 18" aria-hidden="true" focusable="false">
      {open ? (
        <path d="M3.5 3.5l11 11M14.5 3.5l-11 11" fill="none" stroke="currentColor" strokeWidth="2" />
      ) : (
        <path d="M2 4.5h14M2 9h14M2 13.5h14" fill="none" stroke="currentColor" strokeWidth="2" />
      )}
    </svg>
  )
}

function SiteSearch() {
  const navigate = useNavigate()
  const { t } = useI18n()
  const release = useRelease()
  return <TopicSearch id="site-search" label={t('search.label')} hideLabel onPick={(id) => navigate(`/topics/${id}`)} articleSearch={release ? hasModule(release, 'search') : false} />
}

export function Header() {
  const { t, lang } = useI18n()
  const { pathname } = useLocation()
  const compact = useMediaQuery(COMPACT_CHROME)
  // the menu remembers the page it was opened on, so choosing a page closes it without an effect
  const [openOn, setOpenOn] = useState<string | null>(null)
  const open = compact && openOn === pathname
  const menuBtn = useRef<HTMLButtonElement>(null)
  const close = (refocus: boolean) => {
    setOpenOn(null)
    if (refocus) menuBtn.current?.focus()
  }
  const onKeyDown = (e: KeyboardEvent<HTMLElement>) => {
    if (e.key === 'Escape' && open && !e.defaultPrevented) close(true)
  }
  const link = (item: Item) => (
    <li key={item.to}>
      <NavLink to={item.to} className="nav-link">
        {t(item.key)}
      </NavLink>
    </li>
  )
  const search = (
    <div className="nav-search">
      <SiteSearch />
    </div>
  )
  return (
    <>
      <header className="hdr" onKeyDown={onKeyDown}>
        <div className="container hdr-row">
          <Link to="/overview" className="hdr-wm">
            <Wordmark sub={t('brandSub')} lang={lang} />
          </Link>
          {compact ? null : (
            <div className="hdr-tools">
              <div className="hdr-search">
                <SiteSearch />
              </div>
              <LangSwitch />
            </div>
          )}
          {compact ? (
            <button ref={menuBtn} type="button" className="menubtn" aria-expanded={open} aria-controls="site-nav" onClick={() => (open ? close(false) : setOpenOn(pathname))}>
              <MenuIcon open={open} />
              <span>{t('menu.button')}</span>
            </button>
          ) : null}
        </div>
      </header>
      <nav id="site-nav" className={`nav${open ? ' is-open' : ''}`} aria-label={t('nav.label')} onKeyDown={onKeyDown}>
        <div className="container nav-row">
          {compact ? search : null}
          <ul className="nav-list">
            {START.map(link)}
            {GROUPS.map((g) => (
              <li key={g.id}>
                {compact ? (
                  <NavGroupList id={g.id} label={t(g.key)} items={g.items} />
                ) : (
                  /* a new route remounts the group, so an open menu closes after navigation */
                  <NavGroup key={`${g.id}:${pathname}`} id={g.id} label={t(g.key)} items={g.items} pathname={pathname} />
                )}
              </li>
            ))}
            {END.map(link)}
          </ul>
          {compact ? (
            <div className="nav-tools">
              <LangSwitch />
            </div>
          ) : null}
        </div>
      </nav>
    </>
  )
}
