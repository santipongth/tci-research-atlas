import { lazy, Suspense } from 'react'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { useI18n } from '../lib/i18n'

// The downloads, the quality checklist and the dictionary load on demand: this page is in the entry chunk.
const OpenData = lazy(() => import('./data/OpenData'))

export default function DataPage() {
  const { t } = useI18n()
  return (
    <RequireRelease title={t('data.title')}>
      {(release) => (
        <div className="container">
          <PageHeader title={t('data.title')} lede={t('data.lede', { release: release.overview.release })} />
          <Suspense fallback={<p className="loading" role="status">{t('loading')}</p>}>
            <OpenData release={release} />
          </Suspense>
        </div>
      )}
    </RequireRelease>
  )
}
