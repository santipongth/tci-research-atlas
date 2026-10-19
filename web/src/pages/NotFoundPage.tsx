import { Link } from 'react-router'
import { PageHeader } from '../components/PageHeader'
import { useI18n } from '../lib/i18n'

export default function NotFoundPage() {
  const { t } = useI18n()
  return (
    <div className="container">
      <PageHeader title={t('notFound.title')} lede={t('notFound.body')} />
      <p className="mt-6">
        <Link to="/overview">{t('notFound.home')}</Link>
      </p>
    </div>
  )
}
