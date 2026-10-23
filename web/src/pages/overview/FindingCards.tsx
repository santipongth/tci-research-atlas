import { Link } from 'react-router'
import { StatusChip } from '../../components/StatusGlyph'
import type { AtlasRelease } from '../../data/release'
import { fmtWindow, windows } from '../../lib/definition'
import { perVars, type Finding } from '../../lib/findings'
import { fmtPct, fmtSignedPct } from '../../lib/format'
import { useI18n } from '../../lib/i18n'
import { ciText, statusName } from '../../lib/topicText'

/**
 * "3 เรื่องสำคัญรอบนี้": one finding per column, led by its topic (a link) — what kind of finding it is with the status
 * chip, the number with its unit, its likely range, and one plain sentence. Every number comes from the release.
 * Renders nothing without findings.
 */
export function FindingCards({ release, findings, links = true }: { release: AtlasRelease; findings: readonly Finding[]; links?: boolean }) {
  const { t, name } = useI18n()
  if (findings.length === 0) return null
  const w = fmtWindow(windows(release.overview.last_complete_year).R)
  return (
    <ol className="finds">
      {findings.map(({ kind, topic }) => {
        const m = topic.metrics
        const g = m.share_growth ?? 0
        const big = kind === 'large' ? fmtPct(m.share_recent, 1) : fmtSignedPct(g, 0)
        const unit = kind === 'large' ? t('ov.fc.unit.share', { w }) : t('ov.fc.unit.growth')
        const ci = kind === 'large' ? null : ciText(t, m, release.ciLevel)
        const sentence =
          kind === 'emerging'
            ? t('ov.fc.emerging.s', { g: fmtSignedPct(g, 0) })
            : kind === 'large'
              ? t('ov.fc.large.s', { ...perVars(m.share_recent), g: fmtSignedPct(g, 0) })
              : t('ov.fc.decline.s', { g: fmtPct(Math.abs(g), 0) })
        return (
          <li className="find" key={topic.id}>
            <h3 className="find-topic">
              {links ? <Link to={`/topics/${topic.id}`}>{name(topic)}</Link> : name(topic)}
            </h3>
            <p className="find-k">
              <StatusChip status={topic.status} label={statusName(t, topic.status)} small /> {t(`ov.fc.${kind}.k` as const)}
            </p>
            <p className="find-v">
              <span className="find-num">{big}</span>
              <span className="find-unit">{unit}</span>
            </p>
            <p className="find-ci">{ci ?? ""}</p>
            <p className="find-s">{sentence}</p>
          </li>
        )
      })}
    </ol>
  )
}
