import { SegmentText } from '../../components/SegmentText'
import type { AtlasRelease } from '../../data/release'
import { segmentHeadline } from '../../lib/highlight'
import { useI18n } from '../../lib/i18n'

/** Editorial headline: the brief's sentence with figures highlighted and topic names linked. Hidden without a brief. */
export function Headline({ release }: { release: AtlasRelease }) {
  const { t, lang } = useI18n()
  const brief = release.overview.brief
  const text = brief ? (lang === 'en' ? brief.headline_en : brief.headline_th) : ''
  if (!brief || !text) return null
  return (
    <section className="headline-block" aria-labelledby="headline-h">
      <h2 id="headline-h" className="sr-only">{t('ov.headline.h')}</h2>
      <p className="headline">
        <SegmentText segments={segmentHeadline(text, release.topics)} />
      </p>
      <p className="headline-src">{t(brief.source === 'llm' ? 'autoSummary.llm' : 'autoSummary.template')}</p>
    </section>
  )
}
