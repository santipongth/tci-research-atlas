import { useI18n } from '../lib/i18n'

export function PhaseBanner() {
  const { t } = useI18n()
  return (
    <div className="phase">
      <div className="container phase-row">
        <strong className="phase-tag">{t('phase.tag')}</strong>
        <span>{t('phase.text')}</span>
      </div>
    </div>
  )
}
