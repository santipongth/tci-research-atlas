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
  const { pathname } = useLocation()
  return (
    <>
      <SkipLink />
      <Header />
      <PhaseBanner />
      <DataBanner />
      <main id="main" tabIndex={-1}>
        <ErrorBoundary resetKey={pathname}>
          <Outlet />
        </ErrorBoundary>
      </main>
      <Footer />
    </>
  )
}
