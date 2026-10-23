import type { ReactNode } from 'react'
import { Link, useLocation } from 'react-router'
import { ErrorBoundary } from '../components/ErrorBoundary'
import { useI18n } from '../lib/i18n'

/** A widget that failed to render: one short line and the attribution link, sized for an iframe (never a white frame). */
function EmbedFailure({ chunk }: { chunk: boolean }) {
  const { pick, t } = useI18n()
  return (
    <div className="embed">
      <main id="main" className="embed-main">
        <p className="embed-h" role="alert">
          {chunk ? pick('เว็บมีรุ่นใหม่แล้ว โหลดกรอบนี้ใหม่', 'The site has been updated. Reload this frame.') : pick('แสดงกราฟนี้ไม่สำเร็จ', 'This chart could not be shown.')}
        </p>
      </main>
      <p className="embed-attr">
        <Link to="/overview" target="_blank" rel="noopener noreferrer" className="embed-brand">
          TCI Research Atlas
          <span className="sr-only"> {t('newTab')}</span>
        </Link>
      </p>
    </div>
  )
}

/** The error boundary of the embeddable widgets (/embed/*): they render outside the site's layout and its boundary. */
export function EmbedBoundary({ children }: { children: ReactNode }) {
  const { pathname, search } = useLocation()
  return (
    <ErrorBoundary resetKey={pathname + search} fallback={(chunk) => <EmbedFailure chunk={chunk} />}>
      {children}
    </ErrorBoundary>
  )
}
