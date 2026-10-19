import { Outlet } from 'react-router'
import { useRouteFocus } from '../lib/useRouteFocus'
import { Footer } from './Footer'
import { Header } from './Header'
import { PhaseBanner } from './PhaseBanner'
import { SkipLink } from './SkipLink'

export function Layout() {
  useRouteFocus()
  return (
    <>
      <SkipLink />
      <Header />
      <PhaseBanner />
      <main id="main" tabIndex={-1}>
        <Outlet />
      </main>
      <Footer />
    </>
  )
}
