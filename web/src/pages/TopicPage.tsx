import { lazy, Suspense } from 'react'
import { Link, useParams } from 'react-router'
import { BarRank } from '../charts/BarRank'
import { rankBars } from '../charts/infographic'
import { TrendChart } from '../charts/TrendChart'
import { FeedLink } from '../embed/EmbedTools'
import { Card, DashGrid, DashStack, SeeAll } from '../components/dashboard/Card'
import { Icon } from '../components/dashboard/Icon'
import { KpiCard, KpiRow } from '../components/dashboard/KpiCard'
import { PageBar } from '../components/dashboard/PageBar'
import { RankRows } from '../components/dashboard/RankRows'
import { EmptyState } from '../components/EmptyState'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { StatusChip, StatusGlyph } from '../components/StatusGlyph'
import { InfoPop } from '../components/Term'
import { TopicName } from '../components/TopicName'
import { useTopicDetail } from '../data/atlasContext'
import { groupName, neighborsOf, seriesOf, type AtlasRelease } from '../data/release'
import type { Topic } from '../data/types'
import { fmtWindow, ruleVars, windows } from '../lib/definition'
import { breadthText } from '../lib/breadth'
import { forecastView } from '../lib/forecast'
import { ciPct, DASH, fmtInt, fmtPct, fmtShare, fmtSignedPct } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { ciText, growthText, lowDataText, ratioText, statusMeaning, statusName } from '../lib/topicText'

// The SDG chips read goal names from sdg.json: they load on demand.
const TopicSdg = lazy(() => import('./topic/TopicExtras').then((m) => ({ default: m.TopicSdg })))

export default function TopicPage() {
  const { id } = useParams()
  const { t } = useI18n()
  return <RequireRelease title={t('tp.loadingTitle')}>{(release) => <TopicView release={release} id={id ?? ''} />}</RequireRelease>
}

function TopicView({ release, id }: { release: AtlasRelease; id: string }) {
  const topic = release.topicById.get(id)
  return topic ? <TopicContent key={topic.id} release={release} topic={topic} /> : <TopicMissing id={id} />
}

function TopicMissing({ id }: { id: string }) {
  const { t } = useI18n()
  return (
    <div className="container">
      <PageHeader title={t('tp.notFound', { id: id || DASH })} lede={t('tp.notFound.body')} />
      <p className="dash-back">
        <SeeAll to="/topics" label={t('tp.backTopics')} />
      </p>
    </div>
  )
}

function TopicContent({ release, topic }: { release: AtlasRelease; topic: Topic }) {
  const { t, name, other, lang } = useI18n()
  const detail = useTopicDetail(topic.id)
  const m = topic.metrics
  const level = ciPct(release.ciLevel)
  const w = windows(release.overview.last_complete_year)
  const group = groupName(release, topic.group, lang)
  const years = release.series.years
  const counts = seriesOf(release, topic.id) ?? []
  const fc = topic.forecast ?? null
  // LOW_DATA never gets a band, even if the data carries one; the reason shown depends on why there is none
  const fcView = forecastView(topic.status, fc)
  const showFc = fcView === 'show'
  const nowcast = topic.nowcast ?? null
  const ready = detail.status === 'ready' ? detail.detail : null
  const relatedIds = ready?.neighbors?.length ? ready.neighbors : neighborsOf(release, topic.id)
  const related = relatedIds.map((rid) => release.topicById.get(rid)).filter((r): r is Topic => r !== undefined).slice(0, 6)
  const keywords = ready?.keywords?.length ? ready.keywords : (topic.keywords ?? [])
  const narrative = ready?.narrative ?? null
  const journals = ready?.journals ?? []
  const institutions = ready?.institutions ?? []
  // null / absent = the module is not in this release (hidden); [] = none found (hidden too)
  const glossary = [...(ready?.glossary ?? [])].sort((a, b) => b.n - a.n).slice(0, 6)
  const cited = ready?.cited_in_tci ?? null
  const sdgGoals = topic.sdg ?? []
  const ci = ciText(t, m, release.ciLevel)
  const lineage = topic.lineage ?? {}
  const event = lineage.event ?? 'new'
  const total = counts.reduce((n, c) => n + (c ?? 0), 0)
  const altName = other(topic)
  const lineageText = (
    <>
      {t(`tp.lineage.${event}` as const, { born: lineage.born ?? DASH })}
      {(lineage.parents ?? []).map((p, i) => {
        const parent = release.topicById.get(p)
        return (
          <span key={p}>
            {i ? ', ' : ' '}
            {parent ? <Link to={`/topics/${p}`}><TopicName topic={parent} /></Link> : p}
          </span>
        )
      })}
    </>
  )
  return (
    <>
      <PageBar
        title={name(topic)}
        titleLang={lang === 'en' && !topic.en ? 'th' : undefined}
        sub={[altName !== name(topic) ? altName : '', t('tp.field', { f: group }), topic.subfield_en ?? ''].filter(Boolean).join(' · ')}
        info={
          <>
            {topic.description ? <>{topic.description} </> : null}
            {lineageText}
          </>
        }
        actions={
          <>
            <FeedLink release={release} kind="topic" topicId={topic.id} />
            <StatusChip status={topic.status} label={statusName(t, topic.status)} />
          </>
        }
      />
      <div className="dash">
        <KpiRow>
          <KpiCard icon="topics" label={t('tp.growth')} value={growthText(t, m)} sub={statusMeaning(t, topic.status)} />
          <KpiCard icon="layers" label={t('tp.share')} value={fmtShare(m.share_recent, 2)} sub={t('dash.years', { w: fmtWindow(w.R) })} />
          <KpiCard icon="articles" label={t('tp.articlesR', { w: fmtWindow(w.R) })} value={fmtInt(m.count_recent)} sub={counts.length ? t('tp.articlesSub', { n: fmtInt(total), a: years[0] }) : undefined} />
          <KpiCard icon="building" label={t('tp.orgsR', { w: fmtWindow(w.R) })} value={fmtInt(m.n_orgs_R)} sub={t('tp.kpiJournals', { n: fmtInt(m.n_journals_R) })} />
        </KpiRow>
        <DashGrid>
          <Card
            span={8}
            title={t('tp.trend.title', { a: years[0], b: years[years.length - 1] })}
            info={
              <>
                {ci ? <>{t('tp.growth')} {growthText(t, m)} · {ci}. </> : null}
                {showFc && fc ? t('tp.fc.skill', { skill: fmtPct(fc.skill_vs_naive, 0) }) : t(fcView === 'lowData' ? 'fc.lowData' : fcView === 'noSkill' ? 'fc.noSkill' : 'fc.none')}
                {nowcast ? <> {t('tp.nowcast', { year: nowcast.year, month: nowcast.as_of_month, ytd: fmtInt(nowcast.ytd), mean: fmtInt(nowcast.mean) })}</> : null}
              </>
            }
          >
            {counts.length ? (
              <TrendChart
                status={topic.status}
                years={years}
                counts={counts}
                forecast={showFc ? fc : null}
                nowcast={nowcast}
                labels={{ name: `${t('tp.trend.title', { a: years[0], b: years[years.length - 1] })} · ${name(topic)}`, forecast: t('forecast'), articles: t('col.articles'), range80: (lo, hi) => t('tp.range80', { lo, hi }), actual: t('actual'), band: t('tp.legend.band'), nowcast: t('tp.nowcastLabel') }}
              />
            ) : (
              <EmptyState title={t('tp.noSeries')} />
            )}
          </Card>
          <DashStack span={4}>
            {narrative ? (
              <Card span={12} title={t('tp.narrative.h')} info={t(narrative.source === 'llm' ? 'autoSummary.llm' : 'autoSummary.template')}>
                <p className="tp-narr">{lang === 'en' ? narrative.en : narrative.th}</p>
              </Card>
            ) : null}
            <Card span={12} title={t('tp.numbers.h')}>
              {topic.status === 'WATCH' ? (
                <p className="card-alert">
                  <StatusGlyph status="WATCH" size={13} /> {t('journalDriven')} — {breadthText(t, topic)}
                  <InfoPop className="card-info" label={<><Icon name="info" size={14} /><span className="sr-only">{t('journalDriven')}</span></>}>{t('journalDrivenBody', ruleVars(level))}</InfoPop>
                </p>
              ) : null}
              <dl className="facts">
                <div><dt>{t('col.ratio', { base: fmtWindow(w.B) })}</dt><dd><b>{ratioText(t, m, fmtWindow(w.B))}</b></dd></div>
                <div><dt>{t('col.journals')}</dt><dd><b>{fmtInt(m.n_journals_R)}</b></dd></div>
                {cited !== null ? <div><dt>{t('tp.cited')}</dt><dd><b>{t('tp.cited.v', { n: fmtInt(cited) })}</b></dd></div> : null}
                {topic.status === 'LOW_DATA' ? <div><dt>{t('col.reason')}</dt><dd><b>{lowDataText(t, m) ?? DASH}</b></dd></div> : null}
              </dl>
              {sdgGoals.length ? (
                <Suspense fallback={null}>
                  <TopicSdg release={release} goals={sdgGoals} />
                </Suspense>
              ) : null}
            </Card>
          </DashStack>
        </DashGrid>
        {journals.length || institutions.length || keywords.length ? (
          <DashGrid>
            {journals.length ? (
              <Card span={4} title={t('tp.journals.h')}>
                <BarRank rows={rankBars(journals, 5).rows} href={(r) => (r.id ? `/journals/${r.id}` : null)} value={(r) => fmtInt(r.count)} label={t('tp.journals.h')} />
              </Card>
            ) : null}
            {institutions.length ? (
              <Card span={4} title={t('tp.orgs.h')}>
                <BarRank rows={rankBars(institutions, 5).rows} href={(r) => (r.id ? `/institutions/${r.id}` : null)} value={(r) => fmtInt(r.count)} label={t('tp.orgs.h')} />
              </Card>
            ) : null}
            {keywords.length ? (
              <Card span={4} title={t('tp.keywords.h')}>
                <ul className="kw-list">
                  {keywords.map((k) => <li key={k}>{k}</li>)}
                </ul>
                {glossary.length ? (
                  <>
                    <p className="card-h3">{t('tp.glossary.h')}</p>
                    <ul className="gloss">
                      {glossary.map((g) => (
                        <li key={`${g.th}|${g.en}`}>
                          <span lang="th">{g.th}</span>
                          <span aria-hidden="true">↔</span>
                          <span lang="en">{g.en}</span>
                        </li>
                      ))}
                    </ul>
                  </>
                ) : null}
              </Card>
            ) : null}
          </DashGrid>
        ) : null}
        <DashGrid>
          <Card span={related.length ? 8 : 12} title={t('tp.articles.h')} info={t('tp.articles.intro')}>
            {detail.status === 'loading' ? (
              <p className="loading" role="status">{t('loading')}</p>
            ) : ready && ready.articles.length ? (
              <ol className="articles">
                {ready.articles.map((a) => (
                  <li key={a.article_id}>
                    {a.url ? (
                      <a href={a.url} target="_blank" rel="noopener noreferrer">{a.title}<span className="sr-only"> {t('newTab')}</span></a>
                    ) : (
                      <span>{a.title}</span>
                    )}
                    <span className="art-meta">
                      {[a.journal, a.year ? String(a.year) : ''].filter(Boolean).join(' · ')}
                      {a.doi ? (
                        <>
                          {' · '}
                          <a href={`https://doi.org/${a.doi}`} target="_blank" rel="noopener noreferrer">DOI<span className="sr-only"> {a.doi} {t('newTab')}</span></a>
                        </>
                      ) : null}
                    </span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="card-empty">{t('tp.articles.none')}</p>
            )}
          </Card>
          {related.length ? (
            <Card span={4} title={t('tp.related.h')}>
              <RankRows
                numbered={false}
                label={t('tp.related.h')}
                rows={related.map((r) => ({
                  key: r.id,
                  to: `/topics/${r.id}`,
                  name: name(r),
                  meta: <StatusChip status={r.status} label={statusName(t, r.status)} small />,
                  value: r.metrics.share_growth != null ? <b className={r.metrics.share_growth < 0 ? 'rise-g is-down' : 'rise-g'}>{fmtSignedPct(r.metrics.share_growth, 0)} {t('perYear')}</b> : undefined,
                }))}
              />
            </Card>
          ) : null}
        </DashGrid>
      </div>
    </>
  )
}
