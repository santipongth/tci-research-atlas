import { PageHeader } from '../components/PageHeader'
import { useI18n } from '../lib/i18n'

export default function AtlasPage() {
  const { t } = useI18n()
  return (
    <div className="container">
      <PageHeader title={t('nav.atlas')} />
    </div>
  )
}
