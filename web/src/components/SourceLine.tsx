import { useRelease } from '../data/atlasContext'
import { useI18n } from '../lib/i18n'
import { InfoPop } from './Term'

/** "รายละเอียด" after the short source line: where the figures come from and the status definition version. */
export function SourceMore() {
  const { t } = useI18n()
  const release = useRelease()
  if (!release) return null
  return (
    <>
      <span className="source-sep" aria-hidden="true">{' · '}</span>
      <InfoPop className="source-more" label={t('notice.more')} title={t('source.more')}>
        {t('source.def', { v: release.definitionVersion })}
      </InfoPop>
    </>
  )
}

/** The figure source line "ที่มา: TCI Research Atlas · รอบ {release}", for tables and maps outside a `Figure`. */
export function SourceLine({ text, className }: { text?: string; className?: string }) {
  const { t } = useI18n()
  const release = useRelease()
  return (
    <p className={`source${className ? ` ${className}` : ''}`}>
      {text ?? t('source.line', { release: release?.overview.release ?? '' })}
      <SourceMore />
    </p>
  )
}
