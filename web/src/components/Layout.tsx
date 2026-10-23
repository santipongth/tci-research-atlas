import { useRef, useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router'
import { Wordmark } from '../brand/Wordmark'
import { useI18n } from '../lib/i18n'
import { useTooltip } from '../lib/tooltip'
import { useMediaQuery, WIDE_SHELL } from '../lib/useMediaQuery'
import { useRouteFocus } from '../lib/useRouteFocus'
import { DataBanner } from './DataBanner'
import { Drawer } from './dashboard/Drawer'
import { Icon } from './dashboard/Icon'
import { SideNav } from './dashboard/SideNav'
import { ErrorBoundary } from './ErrorBoundary'
import { Footer } from './Footer'
import { LangSwitch } from './LangSwitch'
import { SkipLink } from './SkipLink'

/** The app shell: the white sidebar (or the phone top bar + menu drawer) and the canvas the page's cards sit on. */
export function Layout() {
  useRouteFocus()
  const { t, lang } = useI18n()
  const { pathname, search, key } = useLocation()
  const wide = useMediaQuery(WIDE_SHELL)
  const tip = useTooltip()
  // the menu remembers the navigation it was opened on (location.key), so choosing any link — the current page too —
  // closes it without an effect
  const [openOn, setOpenOn] = useState<string | null>(null)
  const open = !wide && openOn === key
  const menuBtn = useRef<HTMLButtonElement>(null)
  return (
    <div className="app">
      <SkipLink />
      {wide ? (
        <aside className="side">
          <SideNav />
        </aside>
      ) : (
        <header className="mbar">
          <button
            ref={menuBtn}
            type="button"
            className="icon-btn mbar-menu"
            aria-label={t('menu.button')}
            aria-expanded={open}
            onClick={() => {
              // a chart tooltip left open (a tap on a phone) would float over the menu
              tip.hide()
              setOpenOn(key)
            }}
          >
            <Icon name="menu" size={22} />
          </button>
          <Link to="/overview" className="mbar-wm">
            <Wordmark sub={t('brandSub')} lang={lang} />
          </Link>
          <LangSwitch />
        </header>
      )}
      <div className="app-col">
        <DataBanner />
        <main id="main" tabIndex={-1}>
          {/* the query too: a failure caused by a URL parameter is retried when the parameter changes */}
          <ErrorBoundary resetKey={pathname + search}>
            <Outlet />
          </ErrorBoundary>
        </main>
        <Footer />
      </div>
      {wide ? null : (
        <Drawer open={open} onClose={() => setOpenOn(null)} side="left" title={t('nav.label')}>
          <SideNav withLogo={false} />
        </Drawer>
      )}
    </div>
  )
}
