import { Outlet, useLocation } from 'react-router'
import { useRouteFocus } from '../lib/useRouteFocus'
import { DataBanner } from './DataBanner'
import { ErrorBoundary } from './ErrorBoundary'
import { Footer } from './Footer'
import { Header } from './Header'
import { PhaseBanner } from './PhaseBanner'
import { SkipLink } from './SkipLink'

export function Layout() {
  useRouteFocus()
  const { pathname, search } = useLocation()
  return (
    <>
      <SkipLink />
      <Header />
      <PhaseBanner />
      <DataBanner />
      <main id="main" tabIndex={-1}>
        {/* the query too: a failure caused by a URL parameter is retried when the parameter changes */}
        <ErrorBoundary resetKey={pathname + search}>
          <Outlet />
        </ErrorBoundary>
      </main>
      <Footer />
    </>
  )
}
