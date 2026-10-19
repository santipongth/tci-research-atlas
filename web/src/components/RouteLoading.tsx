import { useI18n } from '../lib/i18n'

/** Shown while a lazily loaded page's code arrives (Suspense fallback). */
export function RouteLoading() {
  const { t } = useI18n()
  return (
    <div className="container">
      <p className="loading" role="status">{t('loading')}</p>
    </div>
  )
}
