import { useI18n } from '../lib/i18n'
import { useDocumentTitle } from '../lib/useDocumentTitle'

export default function BriefPage() {
  const { t } = useI18n()
  useDocumentTitle(t('nav.brief'))
  return (
    <main id="main" className="container">
      <h1>{t('nav.brief')}</h1>
    </main>
  )
}
