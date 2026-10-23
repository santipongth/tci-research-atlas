import { TopicName } from '../components/TopicName'
import { lazy, Suspense } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { FitCiWhisker } from '../components/CiWhisker'
import { DataTable, type Column } from '../components/DataTable'
import { EmptyState } from '../components/EmptyState'
import { Figure } from '../components/Figure'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { StatGrid, StatTile } from '../components/StatTile'
import { StatusChip, StatusGlyph } from '../components/StatusGlyph'
import { Term } from '../components/Term'
import { TopicLink } from '../components/TopicLink'
import { TopicSearch } from '../components/TopicSearch'
import { TrendChart } from '../charts/TrendChart'
import { useTopicDetail } from '../data/atlasContext'
import { groupName, hasModule, neighborsOf, seriesOf, type AtlasRelease } from '../data/release'
import type { Topic } from '../data/types'
import { DEFINITION, fmtWindow, ruleVars, windows } from '../lib/definition'
import { breadthText } from '../lib/breadth'
import { forecastView } from '../lib/forecast'
import { ciPct, DASH, fmtInt, fmtNum, fmtPct, fmtSignedPct } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { ciText, growthText, lowDataText, ratioText, statusMeaning, statusName } from '../lib/topicText'
import { figureCsv } from '../lib/tableCsv'
import { topicCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import { FOREST_DOMAIN } from './topicColumns'

// SDG chips (they read sdg.json) and the RIS/BibTeX export load on demand: this page is in the entry chunk.
const TopicSdg = lazy(() => import('./topic/TopicExtras').then((m) => ({ default: m.TopicSdg })))
const ArticleCite = lazy(() => import('./topic/TopicExtras').then((m) => ({ default: m.ArticleCite })))
const TopicRanking = lazy(() => import('./topic/TopicExtras').then((m) => ({ default: m.TopicRanking })))
// The embed code and the topic's Atom feed link, also on demand.
const EmbedSnippet = lazy(() => import('../embed/EmbedTools').then((m) => ({ default: m.EmbedSnippet })))
const FeedLink = lazy(() => import('../embed/EmbedTools').then((m) => ({ default: m.FeedLink })))

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
  const navigate = useNavigate()
  return (
    <div className="container">
      <PageHeader title={t('tp.notFound', { id: id || DASH })} lede={t('tp.notFound.body')} />
      <div className="mt-6 max-w-xl">
        <TopicSearch id="missing-search" label={t('search.label')} onPick={(tid) => navigate(`/topics/${tid}`)} />
      </div>
    </div>
  )
}

interface TrendRow {
  year: number
  kind: 'actual' | 'forecast' | 'nowcast'
  articles: number | null
  share: number | null
  mean: number | null
  lo80: number | null
  hi80: number | null
  lo95: number | null
  hi95: number | null
}

function TopicContent({ release, topic }: { release: AtlasRelease; topic: Topic }) {
  const { t, name, other, otherLang, lang } = useI18n()
  const detail = useTopicDetail(topic.id)
  const [state, update] = useUrlState(topicCodec)
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
  const related = relatedIds.map((rid) => release.topicById.get(rid)).filter((r): r is Topic => r !== undefined).slice(0, 8)
  const keywords = ready?.keywords?.length ? ready.keywords : (topic.keywords ?? [])
  const narrative = ready?.narrative ?? null
  const journals = ready?.journals ?? []
  const institutions = ready?.institutions ?? []
  // null / absent = the module is not in this release (hidden); [] = none found (hidden too)
  const glossary = ready?.glossary ?? []
  const glossaryTop = [...glossary].sort((a, b) => b.n - a.n)[0] ?? { th: '', en: '', n: 0 }
  const cited = ready?.cited_in_tci ?? null
  const sdgGoals = topic.sdg ?? []
  // tables are numbered in page order; sections without data are not rendered and take no number
  const tableNo = { glossary: 2, journals: glossary.length ? 3 : 2 }
  const orgsNo = tableNo.journals + (journals.length ? 1 : 0)
  const ci = ciText(t, m, release.ciLevel)
  const lineage = topic.lineage ?? {}
  const event = lineage.event ?? 'new'
  const source = t('source.line', { release: release.overview.release })

  const trendRows: TrendRow[] = [
    ...years.map((yr, i) => ({
      year: yr, kind: 'actual' as const, articles: counts[i] ?? 0,
      share: release.series.corpus_total[i] ? (counts[i] ?? 0) / release.series.corpus_total[i] : null,
      mean: null, lo80: null, hi80: null, lo95: null, hi95: null,
    })),
    ...(showFc && fc
      ? fc.years.map((yr, i) => ({ year: yr, kind: 'forecast' as const, articles: null, share: null, mean: fc.mean[i], lo80: fc.lo80[i], hi80: fc.hi80[i], lo95: fc.lo95[i], hi95: fc.hi95[i] }))
      : []),
  ]
  const trendColumns: Column<TrendRow>[] = [
    { key: 'year', csvHeader: 'year', header: t('col.year'), rowHeader: true, cell: (r) => (r.kind === 'forecast' ? t('tp.forecastYear', { year: r.year }) : String(r.year)), csv: (r) => r.year },
    { key: 'kind', csvHeader: 'kind', header: 'kind', cell: () => null, csv: (r) => r.kind, csvOnly: true },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (r) => (r.articles === null ? '' : fmtInt(r.articles)), csv: (r) => r.articles },
    { key: 'share', csvHeader: 'share_of_year', header: t('tp.col.shareOfYear'), numeric: true, cell: (r) => (r.share === null ? '' : fmtPct(r.share, 2)), csv: (r) => r.share },
    { key: 'mean', csvHeader: 'forecast_mean', header: t('forecast'), numeric: true, cell: (r) => (r.mean === null ? '' : fmtInt(r.mean)), csv: (r) => r.mean },
    { key: 'r80', csvHeader: 'range_80', header: t('tp.col.range80'), numeric: true, cell: (r) => (r.lo80 === null ? '' : `${fmtInt(r.lo80)}–${fmtInt(r.hi80)}`), csv: (r) => (r.lo80 === null ? null : `${r.lo80}-${r.hi80}`) },
    { key: 'r95', csvHeader: 'range_95', header: t('tp.col.range95'), numeric: true, cell: (r) => (r.lo95 === null ? '' : `${fmtInt(r.lo95)}–${fmtInt(r.hi95)}`), csv: (r) => (r.lo95 === null ? null : `${r.lo95}-${r.hi95}`) },
  ]
  const g = m.share_growth
  const heroText =
    g === null || g === undefined
      ? t('tp.hero.none')
      : Math.abs(g) < 0.005
        ? t('tp.hero.flat')
        : t(g > 0 ? 'tp.hero.up' : 'tp.hero.down', { g: g > 0 ? fmtSignedPct(g, 0) : fmtPct(Math.abs(g), 0) })
  const eg = ready?.articles[0] ?? null
  const total = counts.reduce((n, c) => n + (c ?? 0), 0)
  // tiles after the hero: never a row that ends with one tile beside an empty cell
  const nTiles = 3 + (cited !== null ? 1 : 0)
  const asideExtra = (
    <>
      <p className="mt-6">
        <Link className="btn-secondary" to={`/compare?ids=${topic.id}`}>{t('addToCompare')}</Link>
      </p>
      <p className="mt-2 hint">{t('tp.id', { id: topic.id })}</p>
      {release.latest.feeds === true ? (
        <Suspense fallback={null}>
          <FeedLink release={release} kind="topic" topicId={topic.id} />
        </Suspense>
      ) : null}
    </>
  )

  return (
    <div className="container">
      <PageHeader title={name(topic)} titleLang={lang === 'en' && !topic.en ? 'th' : undefined} lede={topic.description || undefined}>
        <p className="tp-alt" lang={otherLang}>{other(topic)}</p>
        <div className="tp-tags">
          <span className="tp-field">{t('tp.field', { f: group })}</span>
          {topic.subfield_en ? <span className="tp-sub" lang="en">{topic.subfield_en}</span> : null}
          {topic.cross_field ? <span className="tp-badge">{t('tp.crossField')}</span> : null}
        </div>
        {sdgGoals.length ? (
          <Suspense fallback={null}>
            <TopicSdg release={release} goals={sdgGoals} />
          </Suspense>
        ) : null}
        <p className="tp-lineage">
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
        </p>
      </PageHeader>
      <section className="tp-hero" aria-label={t('tp.hero.label')}>
        <div className="tp-hero-main">
          <p className="tp-hero-st">
            <StatusChip status={topic.status} label={statusName(t, topic.status)} />
            <span>{statusMeaning(t, topic.status)}</span>
          </p>
          <p className="tp-hero-g">{heroText}</p>
          {ci ? (
            <>
              <p className="tp-hero-ci"><Term term="shareGrowth">{t('tp.growth')}</Term> {growthText(t, m)} · {ci}</p>
              <FitCiWhisker status={topic.status} value={m.share_growth} lo={m.share_growth_lo} hi={m.share_growth_hi} domain={FOREST_DOMAIN} refValue={DEFINITION.emergingMinGrowthLo} maxWidth={360} height={22} />
            </>
          ) : g === null || g === undefined ? (
            <p className="tp-hero-ci">{lowDataText(t, m) ?? DASH}</p>
          ) : null}
        </div>
        <StatGrid cols={2} className="tp-hero-tiles">
          <StatTile
            label={t('tp.share')}
            value={fmtPct(m.share_recent, 2)}
            sub={t('tp.inWindow', { w: fmtWindow(w.R) })}
          />
          <StatTile
            label={t('tp.articlesR', { w: fmtWindow(w.R) })}
            value={fmtInt(m.count_recent)}
            sub={counts.length ? t('tp.articlesSub', { n: fmtInt(total), a: years[0] }) : undefined}
          />
        </StatGrid>
      </section>
      {eg ? (
        <p className="tp-eg">
          <b>{t('tp.eg')}</b>{' '}
          {eg.url ? (
            <a href={eg.url} target="_blank" rel="noopener noreferrer">{eg.title}<span className="sr-only"> {t('newTab')}</span></a>
          ) : (
            <span>{eg.title}</span>
          )}
          <span className="art-meta">{[eg.journal, eg.year ? String(eg.year) : ''].filter(Boolean).join(' · ')}</span>
        </p>
      ) : null}
      <div className="layout">
        <div className="main-col">
          <Section id="trend" title={t('tp.trend.h')}>
            {counts.length ? (
              <Figure
                id="fig-trend"
                number={1}
                title={t('tp.trend.title', { a: years[0], b: years[years.length - 1] })}
                tableTitle={t('table.n', { n: 1, title: t('tp.trend.table') })}
                csv={figureCsv(`atlas-${release.overview.release}-${topic.id}-trend.csv`, trendRows, trendColumns)}
                source={source}
                how={showFc && fc ? <p>{t('tp.fc.how', { m: fc.model, mase: fmtNum(fc.mase, 2) })}</p> : undefined}
                view={state.trend}
                onView={(trend) => update({ trend })}
                chart={
                  <TrendChart
                    status={topic.status}
                    years={years}
                    counts={counts}
                    forecast={showFc ? fc : null}
                    nowcast={nowcast}
                    labels={{ name: `${t('tp.trend.title', { a: years[0], b: years[years.length - 1] })} · ${name(topic)}`, forecast: t('forecast'), articles: t('col.articles'), range80: (lo, hi) => t('tp.range80', { lo, hi }), actual: t('actual'), band: t('tp.legend.band'), nowcast: t('tp.nowcastLabel') }}
                  />
                }
                table={
                  <DataTable
                    caption={t('table.n', { n: 1, title: t('tp.trend.table') })}
                    rows={trendRows}
                    rowKey={(r) => `${r.kind}-${r.year}`}
                    stack={false}
                    columns={trendColumns}
                  />
                }
                note={
                  <>
                    {showFc && fc ? (
                      <p className="note">{t('tp.fc.skill', { skill: fmtPct(fc.skill_vs_naive, 0) })}</p>
                    ) : (
                      <div className="uncertain">
                        <b>{t('fc.uncertain')}</b>
                        <p>{t(fcView === 'lowData' ? 'fc.lowData' : fcView === 'noSkill' ? 'fc.noSkill' : 'fc.none')}</p>
                      </div>
                    )}
                    {nowcast ? <p className="note">{t('tp.nowcast', { year: nowcast.year, month: nowcast.as_of_month, ytd: fmtInt(nowcast.ytd), mean: fmtInt(nowcast.mean) })}</p> : null}
                  </>
                }
              />
            ) : (
              <EmptyState title={t('tp.noSeries')} />
            )}
            {counts.length ? (
              <Suspense fallback={null}>
                <EmbedSnippet kind="topic" path={`topic/${topic.id}`} title={`${name(topic)} — TCI Research Atlas`} height={720} />
              </Suspense>
            ) : null}
          </Section>

          {narrative ? (
            <Section id="narrative" title={t('tp.narrative.h')}>
              <p className="tp-narr">{lang === 'en' ? narrative.en : narrative.th}</p>
              <p className="headline-src">{t(narrative.source === 'llm' ? 'autoSummary.llm' : 'autoSummary.template')}</p>
            </Section>
          ) : null}

          <Section id="numbers" title={t('tp.numbers.h')}>
            {m.journal_driven || topic.status === 'WATCH' ? (
              <div className="inset">
                <b><StatusGlyph status="WATCH" size={14} />{t('journalDriven')}</b>
                <p>{t('journalDrivenBody', ruleVars(level))}</p>
                <p><strong>{breadthText(t, topic)}</strong></p>
              </div>
            ) : null}
            <StatGrid cols={nTiles === 4 ? 4 : 3}>
              <StatTile label={t('col.ratio', { base: fmtWindow(w.B) })} value={ratioText(t, m, fmtWindow(w.B))} sub={t('tp.ratioSub', { r: fmtWindow(w.R), b: fmtWindow(w.B) })} />
              <StatTile label={t('col.journals')} value={fmtInt(m.n_journals_R)} sub={t('tp.inWindow', { w: fmtWindow(w.R) })} />
              <StatTile wide={nTiles === 3 ? 'phone' : false} label={t('col.orgs')} value={fmtInt(m.n_orgs_R)} sub={m.orgs_unverified ? t('orgsUnverified') : t('tp.inWindow', { w: fmtWindow(w.R) })} />
              {cited !== null ? (
                <StatTile
                  label={t('tp.cited')}
                  value={t('tp.cited.v', { n: fmtInt(cited) })}
                  sub={
                    <>
                      {t('tp.cited.sub')}
                      {hasModule(release, 'references') ? <> · <Link to="/references">{t('tp.cited.link')}</Link></> : null}
                    </>
                  }
                />
              ) : null}
              {topic.status === 'LOW_DATA' ? <StatTile wide label={t('col.reason')} value={lowDataText(t, m) ?? DASH} /> : null}
            </StatGrid>
          </Section>

          {keywords.length ? (
            <Section id="keywords" title={t('tp.keywords.h')}>
              <ul className="kw-list">
                {keywords.map((k) => <li key={k}>{k}</li>)}
              </ul>
            </Section>
          ) : null}

          {glossary.length ? (
            <Section id="glossary" title={t('tp.glossary.h')} intro={t('tp.glossary.intro', { th: glossaryTop.th, en: glossaryTop.en })}>
              <DataTable
                caption={t('table.n', { n: tableNo.glossary, title: t('tp.glossary.table') })}
                rows={glossary}
                rowKey={(g) => `${g.th}|${g.en}`}
                stack={false}
                csvFilename={`atlas-${release.overview.release}-${topic.id}-glossary.csv`}
                defaultSort={{ key: 'n', dir: 'desc' }}
                columns={[
                  { key: 'th', csvHeader: 'th', header: t('tp.glossary.th'), rowHeader: true, cell: (g) => <span lang="th">{g.th}</span>, sortValue: (g) => g.th },
                  { key: 'en', csvHeader: 'en', header: t('tp.glossary.en'), cell: (g) => <span lang="en">{g.en}</span>, sortValue: (g) => g.en.toLowerCase(), csv: (g) => g.en },
                  { key: 'n', csvHeader: 'n', header: t('col.articles'), numeric: true, cell: (g) => fmtInt(g.n), sortValue: (g) => g.n },
                ]}
              />
            </Section>
          ) : null}

          <Section id="articles" title={t('tp.articles.h')} intro={t('tp.articles.intro')}>
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
                    {a.title_en && a.title_en !== a.title ? <span className="art-alt" lang="en">{a.title_en}</span> : null}
                    <span className="art-meta">
                      {[a.journal, a.year ? String(a.year) : ''].filter(Boolean).join(' · ')}
                      {a.doi ? (
                        <>
                          {' · '}
                          <a href={`https://doi.org/${a.doi}`} target="_blank" rel="noopener noreferrer">DOI {a.doi}<span className="sr-only"> {t('newTab')}</span></a>
                        </>
                      ) : null}
                    </span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="note">{t('tp.articles.none')}</p>
            )}
            {ready && ready.articles.length ? (
              <Suspense fallback={null}>
                <ArticleCite release={release} topicId={topic.id} articles={ready.articles} />
              </Suspense>
            ) : null}
          </Section>

          {related.length ? (
            <Section id="related" title={t('tp.related.h')}>
              <ul className="related">
                {related.map((r) => (
                  <li key={r.id}>
                    <TopicLink topic={r} showStatus />
                    <span className="topic-sub">{statusName(t, r.status)} · {growthText(t, r.metrics)}</span>
                  </li>
                ))}
              </ul>
            </Section>
          ) : null}

          {journals.length ? (
            <Section id="journals" title={t('tp.journals.h')}>
              <Suspense fallback={null}>
                <TopicRanking release={release} topicId={topic.id} kind="journals" rows={journals} number={2} tableNo={tableNo.journals} view={state.jr} onView={(jr) => update({ jr })} />
              </Suspense>
            </Section>
          ) : null}
          {institutions.length ? (
            <Section id="orgs" title={t('tp.orgs.h')}>
              <Suspense fallback={null}>
                <TopicRanking release={release} topicId={topic.id} kind="institutions" rows={institutions} number={journals.length ? 3 : 2} tableNo={orgsNo} view={state.org} onView={(org) => update({ org })} />
              </Suspense>
            </Section>
          ) : null}
        </div>
        {/* the compare button, the topic id and the feed link close the page */}
        <div className="tp-after">{asideExtra}</div>
      </div>
    </div>
  )
}
