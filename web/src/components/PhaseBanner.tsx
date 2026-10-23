import { useRelease } from '../data/atlasContext'
import { useI18n } from '../lib/i18n'

/** One compact notice line under the navigation: the beta tag, the sample-data tag (test releases) and a short
 * sentence; the full beta and sample-data texts open under "รายละเอียด". The sample tag stays visible on every page. */
export function PhaseBanner() {
  const { t } = useI18n()
  const sample = useRelease()?.sample === true
  const short = t(sample ? 'notice.shortSample' : 'notice.short')
  return (
    <div className="phase">
      <details className="container notice">
        <summary>
          {sample ? <strong className="phase-tag is-sample">{t('sample.tag')}</strong> : <strong className="phase-tag">{t('phase.tag')}</strong>}
          <span className="notice-short">{short}</span>
          <span className="notice-more">
            {t('notice.more')}
            <svg viewBox="0 0 10 6" aria-hidden="true" focusable="false">
              <path d="M1 1l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.6" />
            </svg>
          </span>
        </summary>
        <div className="notice-body">
          {/* phones hide the summary's sentence (one-line strip): it opens here instead */}
          <p className="notice-short-body">{short}</p>
          <p>{t('phase.text')}</p>
          {sample ? <p>{t('sample.text')}</p> : null}
        </div>
      </details>
    </div>
  )
}
