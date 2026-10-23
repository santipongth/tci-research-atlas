import { Link, NavLink } from 'react-router'
import { Wordmark } from '../../brand/Wordmark'
import { useI18n } from '../../lib/i18n'
import type { StrKey } from '../../strings'
import { Icon, type IconName } from './Icon'

interface Item {
  to: string
  key: StrKey
  icon: IconName
}

/** Five dashboards, then the two maps, then the reading guide; every page one click away. (The executive brief is the
 *  overview's printed form: its button sits on the overview.) */
const SECTIONS: readonly { key: StrKey; items: readonly Item[] }[] = [
  {
    key: 'nav.sec.dash',
    items: [
      { to: '/overview', key: 'nav.overview', icon: 'overview' },
      { to: '/topics', key: 'nav.topics', icon: 'topics' },
      { to: '/places', key: 'nav.places', icon: 'places' },
      { to: '/journals', key: 'nav.journals', icon: 'journals' },
      { to: '/goals', key: 'nav.goals', icon: 'goals' },
    ],
  },
  {
    key: 'nav.sec.maps',
    items: [
      { to: '/atlas', key: 'nav.atlas', icon: 'atlas' },
      { to: '/galaxy', key: 'nav.galaxy', icon: 'galaxy' },
    ],
  },
  {
    key: 'nav.sec.help',
    items: [{ to: '/about', key: 'nav.about', icon: 'about' }],
  },
]

/** The sidebar's content: the TCI logo and the page list (the language switch is in the page bar). */
export function SideNav({ withLogo = true }: { withLogo?: boolean }) {
  const { t, lang } = useI18n()
  return (
    <div className="side-in">
      {withLogo ? (
        <Link to="/overview" className="side-wm">
          <Wordmark sub={t('brandSub')} lang={lang} />
        </Link>
      ) : null}
      <nav className="side-nav" aria-label={t('nav.label')}>
        {SECTIONS.map((s) => (
          <div key={s.key} className="side-sec">
            <p className="side-h" id={`side-${s.key}`}>{t(s.key)}</p>
            <ul aria-labelledby={`side-${s.key}`}>
              {s.items.map((i) => (
                <li key={i.to}>
                  <NavLink to={i.to} className="side-link">
                    <Icon name={i.icon} />
                    <span>{t(i.key)}</span>
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>
    </div>
  )
}
