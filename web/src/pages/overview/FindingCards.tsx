import { Link } from 'react-router'
import { Sparkline } from '../../components/StatTile'
import { StatusChip } from '../../components/StatusGlyph'
import { seriesOf, type AtlasRelease } from '../../data/release'
import { fmtWindow, windows } from '../../lib/definition'
import type { Finding } from '../../lib/findings'
import { fmtInt, fmtPct, fmtSignedPct } from '../../lib/format'
import { useI18n } from '../../lib/i18n'
import { ciText, statusName } from '../../lib/topicText'

/**
 * "3 เรื่องสำคัญรอบนี้": one finding per column — what it is, one big number (its likely range under it), the example
 * topic (a link), one plain sentence, and the topic's articles a year as an ink sparkline with its first and last year.
 * Every number comes from the release. Renders nothing without findings.
 */
export function FindingCards({ release, findings, links = true }: { release: AtlasRelease; findings: readonly Finding[]; links?: boolean }) {
  const { t, name } = useI18n()
  if (findings.length === 0) return null
  const years = release.series.years
  const w = fmtWindow(windows(release.overview.last_complete_year).R)
  return (
    <ol className="finds">
      {findings.map(({ kind, topic }) => {
        const m = topic.metrics
        const g = m.share_growth ?? 0
        const counts = seriesOf(release, topic.id) ?? []
        const spark = counts.length > 2 && counts.length === years.length
        const big = kind === 'large' ? fmtPct(m.share_recent, 1) : fmtSignedPct(g, 0)
        const unit = kind === 'large' ? t('ov.fc.unit.share', { w }) : t('ov.fc.unit.growth')
        const ci = kind === 'large' ? null : ciText(t, m, release.ciLevel)
        const sentence =
          kind === 'emerging'
            ? t('ov.fc.emerging.s', { g: fmtSignedPct(g, 0) })
            : kind === 'large'
              ? t('ov.fc.large.s', { k: fmtInt(Math.max(1, Math.round(m.share_recent * 100))), g: fmtSignedPct(g, 0) })
              : t('ov.fc.decline.s', { g: fmtPct(Math.abs(g), 0) })
        return (
          <li className="find" key={topic.id}>
            <p className="find-k">{t(`ov.fc.${kind}.k` as const)}</p>
            <p className="find-v">
              <span className="find-num">{big}</span>
              <span className="find-unit">{unit}</span>
            </p>
            {ci ? <p className="find-ci">{ci}</p> : null}
            <h3 className="find-topic">
              {links ? <Link to={`/topics/${topic.id}`}>{name(topic)}</Link> : name(topic)}
            </h3>
            <p className="find-s">
              <StatusChip status={topic.status} label={statusName(t, topic.status)} small /> {sentence}
            </p>
            {spark ? (
              <div className="find-trend">
                <span className="find-tl">{t('ov.fc.trend')}</span>
                <Sparkline values={counts} width={168} height={36} />
                <span className="find-yr" aria-hidden="true">
                  <span>{years[0]}</span>
                  <span>{years[years.length - 1]}</span>
                </span>
                <span className="sr-only">{t('stat.trend', { a: years[0], b: years[years.length - 1], values: counts.map((v) => fmtInt(v)).join(', ') })}</span>
              </div>
            ) : null}
          </li>
        )
      })}
    </ol>
  )
}
