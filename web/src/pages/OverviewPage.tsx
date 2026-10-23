import { lazy, Suspense } from 'react'
import { Link } from 'react-router'
import { EmptyState } from '../components/EmptyState'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { hasModule, type AtlasRelease } from '../data/release'
import { largeShareThreshold, quadrantOf } from '../lib/definition'
import { fmtSignedPct } from '../lib/format'
import { sortBy } from '../lib/sort'
import { statusName } from '../lib/topicText'
import { useI18n } from '../lib/i18n'
import { pickFindings } from '../lib/findings'
import { FindingCards } from './overview/FindingCards'
import { Findings } from './overview/Findings'
import { KpiGrid } from './overview/KpiGrid'
import { StoryHero } from './overview/StoryHero'

// The sections below the key figures load on demand (this page is in the entry chunk): the status waffle and forest
// plot, and the size × growth matrix at the end of the page.
const StatusOverview = lazy(() => import('./overview/StatusOverview').then((m) => ({ default: m.StatusOverview })))
const Portfolio = lazy(() => import('./overview/Portfolio').then((m) => ({ default: m.Portfolio })))

export default function OverviewPage() {
  const { t } = useI18n()
  return <RequireRelease title={t('nav.overview')}>{(release) => <Overview release={release} />}</RequireRelease>
}

function Overview({ release }: { release: AtlasRelease }) {
  const { t, lang, name } = useI18n()
  const ov = release.overview
  const brief = ov.brief
  const bullets = brief ? ((lang === 'en' ? brief.bullets_en : brief.bullets_th) ?? []) : []
  const exec = ov.executive ? ((lang === 'en' ? ov.executive.bullets_en : ov.executive.bullets_th) ?? []) : []
  const hasTopics = release.topics.length > 0
  const threshold = largeShareThreshold(release.topics)
  const plotted = threshold === null ? [] : release.topics.filter((tp) => tp.metrics.share_recent > 0 && quadrantOf(tp, threshold) !== null)
  const trimmed = release.manifest.trimmed_years ?? []
  // layer 1 leads with an example from the data: the strongest emerging topic (else the fastest hot one)
  const example =
    sortBy(release.topics.filter((tp) => tp.status === 'EMERGING'), (tp) => tp.score, 'desc')[0] ??
    sortBy(release.topics.filter((tp) => tp.status === 'HOT' && tp.metrics.share_growth != null), (tp) => tp.metrics.share_growth, 'desc')[0]
  const statusIntro = example
    ? t('ov.status.intro', { topic: name(example), g: fmtSignedPct(example.metrics.share_growth, 0), status: statusName(t, example.status) })
    : t('ov.status.introPlain')
  const star = threshold === null ? undefined : sortBy(plotted.filter((tp) => quadrantOf(tp, threshold) === 'stars'), (tp) => tp.metrics.share_recent, 'desc')[0]
  const pfIntro = star ? t('ov.pf.intro', { topic: name(star) }) : t('ov.pf.introPlain')
  const findings = pickFindings(release.topics)
  const findingsTitle = findings.length === 3 ? t('ov.fc.h3') : t('ov.findings.h')
  const kpiIntro = release.previousOverview
    ? t('ov.kpi.intro', { prev: release.previousOverview.release })
    : release.previousMissing
      ? t('prev.missing', { prev: release.previousMissing })
      : ov.previous_release
        ? undefined
        : t('firstRelease')
  return (
    <div className="container">
      <StoryHero release={release}>
        {trimmed.length ? <p className="note">{t('ov.trimmed', { years: trimmed.join(', ') })}</p> : null}
        <p className="page-acts">
          <Link className="btn-secondary" to="/brief">
            <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">
              <path d="M3.5 1.5h6l3 3v10h-9z M9.5 1.5v3h3 M5.5 8h5 M5.5 10.5h5 M5.5 13h3" fill="none" stroke="currentColor" strokeWidth="1.4" />
            </svg>
            {t('ov.brief.btn')}
          </Link>
          <Link className="btn-secondary" to="/story">{t('nav.story')}</Link>
        </p>
      </StoryHero>
      <div className="layout">
        <div className="main-col">
          {findings.length ? (
            <Section id="findings" title={findingsTitle} intro={t('ov.fc.intro')}>
              <FindingCards release={release} findings={findings} />
              {bullets.length ? (
                <details className="more-points">
                  <summary>{t('ov.fc.points', { n: bullets.length })}</summary>
                  <Findings release={release} bullets={bullets} />
                </details>
              ) : null}
            </Section>
          ) : bullets.length ? (
            <Section id="findings" title={findingsTitle}>
              <Findings release={release} bullets={bullets} />
            </Section>
          ) : null}
          <Section id="kpi" title={t('ov.kpi.h')} intro={kpiIntro}>
            <KpiGrid release={release} />
            {hasModule(release, 'diff') && ov.previous_release ? (
              <p className="mt-2"><Link className="go-link" to="/changes">{t('ov.changes', { prev: ov.previous_release })}</Link></p>
            ) : null}
          </Section>
          {hasTopics ? (
            <Section id="status" title={t('ov.status.h')} intro={statusIntro}>
              <Suspense fallback={<p className="loading" role="status">{t('loading')}</p>}>
                <StatusOverview release={release} />
              </Suspense>
            </Section>
          ) : (
            <EmptyState title={t('empty.topics')} />
          )}
          {exec.length ? (
            <Section id="policy" title={t('ov.exec.h')}>
              <ol className="policy-list">
                {exec.map((b, i) => (
                  <li key={i}>{b}</li>
                ))}
              </ol>
              <p className="policy-note">{t('brief.execNote')}</p>
            </Section>
          ) : null}
          {plotted.length && threshold !== null ? (
            <Section id="portfolio" title={t('ov.pf.h')} intro={pfIntro}>
              <Suspense fallback={<p className="loading" role="status">{t('loading')}</p>}>
                <Portfolio release={release} topics={plotted} threshold={threshold} />
              </Suspense>
            </Section>
          ) : null}
        </div>
      </div>
    </div>
  )
}
