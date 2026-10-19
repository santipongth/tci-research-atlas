import { DataBanner } from '../components/DataBanner'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { useI18n } from '../lib/i18n'

/** The printable brief lives outside the app shell, so it shows the data banner itself when the release cannot load. */
export default function BriefPage() {
  const { t } = useI18n()
  return (
    <main id="main">
      <DataBanner />
      <RequireRelease title={t('nav.brief')}>
        {() => (
          <div className="container">
            <PageHeader title={t('nav.brief')} />
          </div>
        )}
      </RequireRelease>
    </main>
  )
}
