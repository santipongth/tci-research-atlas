import { useState, type FocusEvent, type KeyboardEvent } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router'
import { Wordmark } from '../brand/Wordmark'
import { useRelease } from '../data/atlasContext'
import { hasModule } from '../data/release'
import { useI18n } from '../lib/i18n'
import type { StrKey } from '../strings'
import { LangSwitch } from './LangSwitch'
import { ThemeToggle } from './ThemeToggle'
import { TopicSearch } from './TopicSearch'

interface Item {
  to: string
  key: StrKey
}

const START: readonly Item[] = [
  { to: '/overview', key: 'nav.overview' },
  { to: '/atlas', key: 'nav.atlas' },
  { to: '/emerging', key: 'nav.emerging' },
]
/** Pages grouped by who uses them most — every page stays two clicks away. */
const GROUPS: readonly { id: string; key: StrKey; items: readonly Item[] }[] = [
  {
    id: 'nav-exec',
    key: 'nav.group.exec',
    items: [
      { to: '/institutions', key: 'nav.institutions' },
      { to: '/regions', key: 'nav.regions' },
      { to: '/sdg', key: 'nav.sdg' },
      { to: '/global', key: 'nav.global' },
      { to: '/changes', key: 'nav.changes' },
      { to: '/brief', key: 'nav.brief' },
    ],
  },
  { id: 'nav-editors', key: 'nav.group.editors', items: [{ to: '/journals', key: 'nav.journals' }, { to: '/methods', key: 'nav.methods' }] },
  {
    id: 'nav-research',
    key: 'nav.group.research',
    items: [
      { to: '/search', key: 'nav.search' },
      { to: '/gaps', key: 'nav.gaps' },
      { to: '/match', key: 'nav.match' },
      { to: '/compare', key: 'nav.compare' },
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
      <ul id={`${id}-menu`} className="nav-menu" hidden={!open}>
        {items.map((i) => (
          <li key={i.to}>
            <NavLink to={i.to} className="nav-menu-link" onClick={() => setOpen(false)}>
              {t(i.key)}
            </NavLink>
          </li>
        ))}
      </ul>
    </div>
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
  const link = (item: Item) => (
    <li key={item.to}>
      <NavLink to={item.to} className="nav-link">
        {t(item.key)}
      </NavLink>
    </li>
  )
  return (
    <>
      <header className="hdr">
        <div className="container hdr-row">
          <Link to="/overview" className="hdr-wm">
            <Wordmark sub={t('brandSub')} lang={lang} />
          </Link>
          <div className="hdr-tools">
            <LangSwitch />
            <ThemeToggle />
          </div>
        </div>
      </header>
      <nav className="nav" aria-label={t('nav.label')}>
        <div className="container nav-row">
          <ul className="nav-list">
            {START.map(link)}
            {GROUPS.map((g) => (
              <li key={g.id}>
                {/* a new route remounts the group, so an open menu closes after navigation */}
                <NavGroup key={`${g.id}:${pathname}`} id={g.id} label={t(g.key)} items={g.items} pathname={pathname} />
              </li>
            ))}
            {END.map(link)}
          </ul>
          <div className="nav-search">
            <SiteSearch />
          </div>
        </div>
      </nav>
    </>
  )
}
