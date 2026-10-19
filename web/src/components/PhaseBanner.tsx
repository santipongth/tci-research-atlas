import { useRelease } from '../data/atlasContext'
import { useI18n } from '../lib/i18n'

export function PhaseBanner() {
  const { t } = useI18n()
  const release = useRelease()
  return (
    <div className="phase">
      <div className="container phase-row">
        <strong className="phase-tag">{t('phase.tag')}</strong>
        <span>{t('phase.text')}</span>
        {release?.sample ? (
          <>
            <strong className="phase-tag is-sample">{t('sample.tag')}</strong>
            <span>{t('sample.text')}</span>
          </>
        ) : null}
      </div>
    </div>
  )
}
