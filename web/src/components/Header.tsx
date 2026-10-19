import { Link, NavLink, useNavigate } from 'react-router'
import { Wordmark } from '../brand/Wordmark'
import { useI18n } from '../lib/i18n'
import type { StrKey } from '../strings'
import { LangSwitch } from './LangSwitch'
import { ThemeToggle } from './ThemeToggle'
import { TopicSearch } from './TopicSearch'

const NAV: readonly { to: string; key: StrKey }[] = [
  { to: '/overview', key: 'nav.overview' },
  { to: '/atlas', key: 'nav.atlas' },
  { to: '/emerging', key: 'nav.emerging' },
  { to: '/journals', key: 'nav.journals' },
  { to: '/compare', key: 'nav.compare' },
  { to: '/data', key: 'nav.data' },
  { to: '/about', key: 'nav.about' },
]

function SiteSearch() {
  const navigate = useNavigate()
  const { t } = useI18n()
  return <TopicSearch id="site-search" label={t('search.label')} hideLabel onPick={(id) => navigate(`/topics/${id}`)} />
}

export function Header() {
  const { t, lang } = useI18n()
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
            {NAV.map((item) => (
              <li key={item.to}>
                <NavLink to={item.to} className="nav-link">
                  {t(item.key)}
                </NavLink>
              </li>
            ))}
          </ul>
          <div className="nav-search">
            <SiteSearch />
          </div>
        </div>
      </nav>
    </>
  )
}
