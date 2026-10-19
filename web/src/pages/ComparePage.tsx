import { PageHeader } from '../components/PageHeader'
import { useI18n } from '../lib/i18n'

export default function ComparePage() {
  const { t } = useI18n()
  return (
    <div className="container">
      <PageHeader title={t('nav.compare')} />
    </div>
  )
}
