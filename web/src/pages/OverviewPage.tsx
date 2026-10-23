import { Link } from 'react-router'
import { EmptyState } from '../components/EmptyState'
import { OnThisPage } from '../components/OnThisPage'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { hasModule, type AtlasRelease } from '../data/release'
import { largeShareThreshold, quadrantOf } from '../lib/definition'
import { fmtDate, fmtInt, fmtSignedPct, releaseQuarter } from '../lib/format'
import { sortBy } from '../lib/sort'
import { statusName } from '../lib/topicText'
import { useI18n } from '../lib/i18n'
import { Findings } from './overview/Findings'
import { Headline } from './overview/Headline'
import { KpiGrid } from './overview/KpiGrid'
import { Portfolio } from './overview/Portfolio'
import { StatusOverview } from './overview/StatusOverview'

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
  const quarter = releaseQuarter(ov.release)
  // layer 1 leads with an example from the data: the strongest emerging topic (else the fastest hot one)
  const example =
    sortBy(release.topics.filter((tp) => tp.status === 'EMERGING'), (tp) => tp.score, 'desc')[0] ??
    sortBy(release.topics.filter((tp) => tp.status === 'HOT' && tp.metrics.share_growth != null), (tp) => tp.metrics.share_growth, 'desc')[0]
  const statusIntro = example
    ? t('ov.status.intro', { topic: name(example), g: fmtSignedPct(example.metrics.share_growth, 0), status: statusName(t, example.status) })
    : t('ov.status.introPlain')
  const star = threshold === null ? undefined : sortBy(plotted.filter((tp) => quadrantOf(tp, threshold) === 'stars'), (tp) => tp.metrics.share_recent, 'desc')[0]
  const pfIntro = star ? t('ov.pf.intro', { topic: name(star) }) : t('ov.pf.introPlain')
  const toc = [
    { id: 'kpi', label: t('ov.kpi.h') },
    ...(bullets.length ? [{ id: 'findings', label: t('ov.findings.h') }] : []),
    ...(exec.length ? [{ id: 'policy', label: t('ov.exec.h') }] : []),
    ...(hasTopics ? [{ id: 'status', label: t('ov.status.h') }] : []),
    ...(plotted.length ? [{ id: 'portfolio', label: t('ov.pf.h') }] : []),
  ]
  const kpiIntro = release.previousOverview
    ? t('ov.kpi.intro', { prev: release.previousOverview.release })
    : release.previousMissing
      ? t('prev.missing', { prev: release.previousMissing })
      : ov.previous_release
        ? undefined
        : t('firstRelease')
  return (
    <div className="container">
      <PageHeader
        title={t('ov.title', { release: ov.release })}
        lede={
          ov.kpis.assigned_articles != null
            ? t('ov.lede.assigned', { articles: fmtInt(ov.kpis.articles), assigned: fmtInt(ov.kpis.assigned_articles), topics: fmtInt(ov.kpis.topics), unassigned: fmtInt(Math.max(0, ov.kpis.articles - ov.kpis.assigned_articles)) })
            : t('ov.lede', { articles: fmtInt(ov.kpis.articles), topics: fmtInt(ov.kpis.topics) })
        }
        meta={[
          { label: t('ov.meta.through'), value: t('ov.meta.throughV', { year: ov.last_complete_year }) },
          { label: t('ov.meta.release'), value: quarter ? t('release.long', { release: ov.release, q: quarter.q, y: quarter.y }) : ov.release },
          { label: t('ov.meta.generated'), value: fmtDate(ov.generated_at, lang) },
          { label: t('ov.meta.definition'), value: t('ov.meta.definitionV', { v: release.definitionVersion }) },
        ]}
      >
        {trimmed.length ? <p className="note">{t('ov.trimmed', { years: trimmed.join(', ') })}</p> : null}
      </PageHeader>
      <Headline release={release} />
      <div className="layout">
        <div className="main-col">
          <Section id="kpi" title={t('ov.kpi.h')} intro={kpiIntro}>
            <KpiGrid release={release} />
            {hasModule(release, 'diff') && ov.previous_release ? (
              <p className="mt-2"><Link className="go-link" to="/changes">{t('ov.changes', { prev: ov.previous_release })}</Link></p>
            ) : null}
          </Section>
          {bullets.length ? (
            <Section id="findings" title={t('ov.findings.h')}>
              <Findings release={release} bullets={bullets} />
            </Section>
          ) : null}
          {exec.length ? (
            <Section id="policy" title={t('ov.exec.h')} intro={t('brief.execNote')}>
              <ul className="exec-points">
                {exec.map((b, i) => (
                  <li key={i}>{b}</li>
                ))}
              </ul>
            </Section>
          ) : null}
          {hasTopics ? (
            <Section id="status" title={t('ov.status.h')} intro={statusIntro}>
              <StatusOverview release={release} />
            </Section>
          ) : (
            <EmptyState title={t('empty.topics')} />
          )}
          {plotted.length && threshold !== null ? (
            <Section id="portfolio" title={t('ov.pf.h')} intro={pfIntro}>
              <Portfolio release={release} topics={plotted} threshold={threshold} />
            </Section>
          ) : null}
        </div>
        <aside className="rail" aria-label={t('onThisPage')}>
          <OnThisPage items={toc} />
        </aside>
      </div>
    </div>
  )
}
