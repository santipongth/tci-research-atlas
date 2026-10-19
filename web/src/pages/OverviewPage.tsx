import { Link } from 'react-router'
import { EmptyState } from '../components/EmptyState'
import { OnThisPage } from '../components/OnThisPage'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { hasModule, type AtlasRelease } from '../data/release'
import { DEFINITION, largeShareThreshold, quadrantOf } from '../lib/definition'
import { ciPct, fmtDate, fmtInt, fmtSignedPct } from '../lib/format'
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
  const { t, lang } = useI18n()
  const ov = release.overview
  const brief = ov.brief
  const bullets = brief ? ((lang === 'en' ? brief.bullets_en : brief.bullets_th) ?? []) : []
  const hasTopics = release.topics.length > 0
  const threshold = largeShareThreshold(release.topics)
  const plotted = threshold === null ? [] : release.topics.filter((tp) => tp.metrics.share_recent > 0 && quadrantOf(tp, threshold) !== null)
  const trimmed = release.manifest.trimmed_years ?? []
  const toc = [
    { id: 'kpi', label: t('ov.kpi.h') },
    ...(bullets.length ? [{ id: 'findings', label: t('ov.findings.h') }] : []),
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
          { label: t('ov.meta.release'), value: ov.release },
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
              <p className="mt-2"><Link to="/changes">{t('ov.changes', { prev: ov.previous_release })}</Link></p>
            ) : null}
          </Section>
          {bullets.length ? (
            <Section id="findings" title={t('ov.findings.h')}>
              <Findings release={release} bullets={bullets} />
            </Section>
          ) : null}
          {hasTopics ? (
            <Section id="status" title={t('ov.status.h')} intro={t('ov.status.intro', { v: release.definitionVersion, level: ciPct(release.ciLevel), bar: fmtSignedPct(DEFINITION.emergingMinGrowthLo, 0) })}>
              <StatusOverview release={release} />
            </Section>
          ) : (
            <EmptyState title={t('empty.topics')} />
          )}
          {plotted.length && threshold !== null ? (
            <Section id="portfolio" title={t('ov.pf.h')} intro={t('ov.pf.intro')}>
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
