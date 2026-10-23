import { Link, useParams } from 'react-router'
import { ChecklistBars, type CheckRow } from '../charts/ChecklistBars'
import { CHECK_FULL, CHECK_NONE, checkState, periodMix, type PeriodRow } from '../charts/editorLayout'
import { MultiLineChart } from '../charts/MultiLineChart'
import { PeriodMix } from '../charts/PeriodMix'
import SmallMultiples from '../charts/SmallMultiples'
import { tickDecimals } from '../charts/scale'
import { DataTable, type Column } from '../components/DataTable'
import { Figure } from '../components/Figure'
import { HowNote } from '../components/HowNote'
import { JournalLink } from '../components/JournalLink'
import { ModuleFile } from '../components/ModuleFile'
import { OnThisPage } from '../components/OnThisPage'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { StatGrid, StatTile } from '../components/StatTile'
import { Term } from '../components/Term'
import { ShareBar } from '../components/ShareBar'
import { TopicLink } from '../components/TopicLink'
import { useReleaseFile } from '../data/atlasContext'
import { hasModule, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { CompletenessItem, DriftPoint, JournalDetail, JournalSummary, JournalsFile, MethodShare, MethodsFile, Topic, TopicShare } from '../data/types'
import { DASH, fmtInt, fmtNum, fmtPct } from '../lib/format'
import { useI18n, useStrings } from '../lib/i18n'
import { withPrimary } from '../lib/columns'
import { figureCsv } from '../lib/tableCsv'
import { inhouseFlag, inhouseGap, journalName, otherJournalName } from '../lib/journals'
import { journalCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import type { StrKey } from '../strings'
import { editorViz } from '../strings/editorViz'

export default function JournalPage() {
  const { id } = useParams()
  const { t } = useI18n()
  return (
    <RequireRelease title={t('jr.title')}>
      {(release) => (
        <ModuleFile<JournalsFile> release={release} module="journals" path={MODULE_FILES.journals} title={t('jr.title')}>
          {(file) => <JournalView release={release} file={file} id={id ?? ''} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

function JournalView({ release, file, id }: { release: AtlasRelease; file: JournalsFile; id: string }) {
  const { t } = useI18n()
  const journal = file.journals.find((j) => j.id === id)
  if (!journal) {
    return (
      <div className="container">
        <PageHeader title={t('jr.notFound', { id: id || DASH })} lede={t('jr.notFound.body')} />
        <p className="mt-6"><Link to="/journals">{t('jr.back')}</Link></p>
      </div>
    )
  }
  return <JournalContent key={journal.id} release={release} file={file} journal={journal} />
}

function JournalContent({ release, file, journal }: { release: AtlasRelease; file: JournalsFile; journal: JournalSummary }) {
  const { t, lang, name } = useI18n()
  const s = useStrings(editorViz)
  const detailFile = useReleaseFile<JournalDetail>(`journals/${journal.id}.json`)
  const detail = detailFile.status === 'ready' ? detailFile.data : null
  const [state, update] = useUrlState(journalCodec)
  const methodsFile = useReleaseFile<MethodsFile>(hasModule(release, 'methods') ? MODULE_FILES.methods : null)
  const methodInfo = new Map((methodsFile.status === 'ready' ? methodsFile.data.methods : []).map((m) => [m.key, m]))
  const w = file.window
  const shown = journalName(journal, lang)
  const other = otherJournalName(journal, lang)
  const source = t('source.line', { release: release.overview.release })
  const topicOf = (tid: string): Topic | undefined => release.topicById.get(tid)
  const byId = new Map(file.journals.map((j) => [j.id, j]))
  const topics = (detail?.topics ?? []).filter((s) => topicOf(s.topic))
  const drift = detail?.drift ?? []
  const comp = detail?.completeness ?? []
  const methods = detail?.methods ?? []
  const peers = (detail?.peers ?? []).filter((p) => byId.has(p.id))
  const opps = (detail?.opportunities ?? []).filter((o) => topicOf(o.topic))
  const gained = (detail?.gained ?? []).filter((s) => topicOf(s.topic))
  const lost = (detail?.lost ?? []).filter((s) => topicOf(s.topic))
  const mix = periodMix([...gained, ...lost])
  const ty = detail?.topic_years ?? null
  const tyTopics = (ty?.topics ?? []).filter((x) => topicOf(x.topic))
  const hasTy = ty !== null && tyTopics.length > 0 && ty.years.length > 1
  const hasDrift = drift.some((d) => d.distance != null)
  const recentSpan = `${file.recent.start}–${file.recent.end}`
  const baseSpan = `${file.baseline.start}–${file.baseline.end}`
  const owner = journal.owner || ''
  /** an empty value: too few articles ("low data") or unknown — never shown as zero */
  const gap = journal.low_data ? t('jr.lowData') : t('jr.unknown')
  const inhouseSub = journal.inhouse_share == null && inhouseGap(journal) === 'owner_not_found'
    ? t('jr.ownerNotFound')
    : owner ? t(journal.owner_source === 'inferred' ? 'jr.inhouseSubInferred' : 'jr.inhouseSub', { o: owner }) : t('jr.noOwner')
  const toc = [
    { id: 'numbers', label: t('jr.numbers.h') },
    ...(topics.length ? [{ id: 'topics', label: t('jr.topics.h') }] : []),
    ...(hasDrift || mix.rows.length ? [{ id: 'drift', label: t('jr.drift.h') }] : []),
    ...(comp.length ? [{ id: 'completeness', label: t('jr.comp.h') }] : []),
    ...(peers.length ? [{ id: 'peers', label: t('jr.peers.h') }] : []),
    ...(methods.length ? [{ id: 'methods', label: t('jr.methods.h') }] : []),
    ...(opps.length ? [{ id: 'opportunities', label: t('jr.opp.h') }] : []),
  ]
  const share = (s: TopicShare) => s.share
  const topTopic = topics.length ? topicOf(topics.reduce((a, b) => (b.count > a.count ? b : a)).topic) : undefined
  const topicColumns: Column<TopicShare>[] = [
    { key: 'topic', csvHeader: 'topic_id', header: t('col.topic'), rowHeader: true, cell: (s) => <TopicLink topic={topicOf(s.topic) as Topic} showStatus />, sortValue: (s) => s.topic, csv: (s) => s.topic },
    { key: 'count', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (s) => fmtInt(s.count), sortValue: (s) => s.count },
    { key: 'share', csvHeader: 'share', header: t('col.share'), numeric: true, cell: (s) => <ShareBar value={s.share} max={Math.max(...topics.map(share), 0.0001)} />, sortValue: share },
  ]
  const driftColumns: Column<DriftPoint>[] = [
    { key: 'year', csvHeader: 'year', header: t('col.year'), rowHeader: true, cell: (d) => String(d.year), sortValue: (d) => d.year },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (d) => fmtInt(d.articles), sortValue: (d) => d.articles },
    { key: 'distance', csvHeader: 'distance', header: t('col.distance'), numeric: true, cell: (d) => fmtNum(d.distance ?? null, 2), sortValue: (d) => d.distance ?? null },
  ]
  const compColumns: Column<CompletenessItem>[] = [
    { key: 'key', csvHeader: 'element', header: t('col.element'), rowHeader: true, cell: (c) => t(`comp.${c.key}` as StrKey), csv: (c) => c.key },
    { key: 'rate', csvHeader: 'rate', header: t('col.rate'), numeric: true, cell: (c) => (c.rate == null ? <span className="sbar-na">{t('jr.unknown')}</span> : <ShareBar value={c.rate} />), sortValue: (c) => c.rate ?? null },
    { key: 'n', csvHeader: 'articles', header: t('col.n'), numeric: true, cell: (c) => fmtInt(c.n), sortValue: (c) => c.n },
  ]
  const mixName = (tid: string) => {
    const tp = topicOf(tid)
    return tp ? name(tp) : tid
  }
  const pts = (before: number, after: number) => {
    const d = Math.round((after - before) * 100)
    return s('pm.pts', { d: d > 0 ? `+${d}` : d < 0 ? `−${Math.abs(d)}` : '0' })
  }
  const mixColumns: Column<PeriodRow>[] = [
    { key: 'topic', csvHeader: 'topic_id', header: t('col.topic'), rowHeader: true, cell: (r) => (topicOf(r.topic) ? <TopicLink topic={topicOf(r.topic) as Topic} showStatus /> : r.topic), csv: (r) => r.topic },
    { key: 'before', csvHeader: 'share_before', header: s('pm.col.before', { b: baseSpan }), numeric: true, cell: (r) => fmtPct(r.before, 0), sortValue: (r) => r.before },
    { key: 'after', csvHeader: 'share_after', header: s('pm.col.after', { r: recentSpan }), numeric: true, cell: (r) => fmtPct(r.after, 0), sortValue: (r) => r.after },
    { key: 'change', csvHeader: 'change', header: s('pm.col.change'), unit: s('pm.ptsUnit'), numeric: true, cell: (r) => pts(r.before, r.after), sortValue: (r) => r.after - r.before, csv: (r) => Math.round((r.after - r.before) * 1e4) / 1e4 },
  ]
  type TyRow = { year: number; articles: number; shares: (number | null)[]; other: number | null }
  const tyRows: TyRow[] = ty ? ty.years.map((year, k) => ({ year, articles: ty.articles[k], shares: tyTopics.map((x) => x.shares[k] ?? null), other: ty.other[k] ?? null })) : []
  const tyColumns: Column<TyRow>[] = [
    { key: 'year', csvHeader: 'year', header: t('col.year'), rowHeader: true, cell: (r) => String(r.year), sortValue: (r) => r.year },
    { key: 'articles', csvHeader: 'articles', header: s('ty.col.articles'), numeric: true, cell: (r) => fmtInt(r.articles), sortValue: (r) => r.articles },
    ...tyTopics.map((x, i): Column<TyRow> => ({ key: x.topic, csvHeader: x.topic, header: mixName(x.topic), numeric: true, cell: (r) => fmtPct(r.shares[i], 0), sortValue: (r) => r.shares[i], csv: (r) => r.shares[i] })),
    { key: 'other', csvHeader: 'other', header: s('ty.col.other'), numeric: true, cell: (r) => fmtPct(r.other, 0), sortValue: (r) => r.other, csv: (r) => r.other },
  ]
  const thinYears = ty ? ty.years.filter((_, k) => ty.articles[k] < ty.min_articles) : []
  /** the example: the largest topic, from its first to its last year with a share */
  const tyLead = (() => {
    const first = tyTopics[0]
    if (!ty || !first) return null
    const known = first.shares.flatMap((v, k) => (v == null ? [] : [k]))
    if (known.length < 2) return null
    const [a, b] = [known[0], known[known.length - 1]]
    return s('ty.lead', { t: mixName(first.topic), a: fmtPct(first.shares[a] ?? null, 0), y1: ty.years[a], b: fmtPct(first.shares[b] ?? null, 0), y2: ty.years[b] })
  })()
  // figures and tables are numbered in reading order, counting only those on the page
  const numbered = (shown: [string, boolean][]): Record<string, number> => Object.fromEntries(shown.filter(([, on]) => on).map(([k], i) => [k, i + 1]))
  const figNo = numbered([['ty', hasTy], ['mix', mix.rows.length > 0], ['drift', hasDrift], ['comp', comp.length > 0]])
  const tabNo = numbered([['topics', topics.length > 0], ['ty', hasTy], ['mix', mix.rows.length > 0], ['drift', hasDrift], ['comp', comp.length > 0], ['peers', peers.length > 0], ['methods', methods.length > 0]])
  const moved = mix.rows.length ? mix.rows.reduce((a, b) => (Math.abs(b.after - b.before) > Math.abs(a.after - a.before) ? b : a)) : null
  const checks: CheckRow[] = comp.map((c) => ({
    key: c.key, name: t(`comp.${c.key}` as StrKey), rate: c.rate ?? null, state: checkState(c.rate), value: c.rate == null ? t('jr.unknown') : fmtPct(c.rate, 0),
  }))
  const nFull = checks.filter((c) => c.state === 'full').length
  const weakest = comp.filter((c) => c.rate != null).reduce<CompletenessItem | null>((a, b) => (a === null || (b.rate as number) < (a.rate as number) ? b : a), null)
  const gapOf = (j: JournalSummary) => (j.low_data ? t('jr.lowData') : t('jr.unknown'))
  type PeerRow = { journal: JournalSummary; similarity: number | null }
  const peerRows: PeerRow[] = [{ journal, similarity: null }, ...peers.map((p) => ({ journal: byId.get(p.id) as JournalSummary, similarity: p.similarity }))]
  const peerColumns: Column<PeerRow>[] = withPrimary<PeerRow>([
    { key: 'name', csvHeader: 'journal_id', header: t('col.journal'), rowHeader: true, cell: (r) => (r.similarity === null ? <strong>{t('jr.this')}</strong> : <JournalLink journal={r.journal} />), csv: (r) => r.journal.id },
    { key: 'sim', csvHeader: 'similarity', header: t('col.similarity'), numeric: true, cell: (r) => (r.similarity === null ? DASH : fmtNum(r.similarity, 2)), csv: (r) => r.similarity },
    { key: 'articles', csvHeader: 'articles_window', header: t('col.articlesW'), numeric: true, cell: (r) => fmtInt(r.journal.articles_window), csv: (r) => r.journal.articles_window },
    { key: 'completeness', csvHeader: 'completeness', header: t('col.completeness'), numeric: true, cell: (r) => (r.journal.completeness == null ? gapOf(r.journal) : fmtNum(r.journal.completeness, 1)), csv: (r) => r.journal.completeness ?? null },
    { key: 'inhouse', csvHeader: 'inhouse_share', header: t('col.inhouse'), numeric: true, cell: (r) => (r.journal.inhouse_share == null ? gapOf(r.journal) : fmtPct(r.journal.inhouse_share, 0)), csv: (r) => r.journal.inhouse_share ?? null },
    { key: 'orgs', csvHeader: 'effective_orgs', header: t('col.effOrgs'), numeric: true, cell: (r) => (r.journal.effective_orgs == null ? gapOf(r.journal) : fmtNum(r.journal.effective_orgs, 1)), csv: (r) => r.journal.effective_orgs ?? null },
    { key: 'foreign', csvHeader: 'foreign_share', header: t('col.foreign'), numeric: true, cell: (r) => (r.journal.foreign_share == null ? gapOf(r.journal) : fmtPct(r.journal.foreign_share, 0)), csv: (r) => r.journal.foreign_share ?? null },
  ], ['sim', 'articles', 'completeness'])
  const methodName = (key: string) => {
    const m = methodInfo.get(key)
    return m ? (lang === 'en' ? m.en : m.th) : key
  }
  const methodColumns: Column<MethodShare>[] = [
    { key: 'method', csvHeader: 'method', header: t('col.method'), rowHeader: true, cell: (m) => methodName(m.method), csv: (m) => m.method },
    { key: 'count', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (m) => fmtInt(m.count), sortValue: (m) => m.count },
    { key: 'share', csvHeader: 'share', header: t('col.share'), numeric: true, cell: (m) => <ShareBar value={m.share} />, sortValue: (m) => m.share },
  ]
  const rel = release.overview.release
  return (
    <div className="container">
      <PageHeader title={shown.text} titleLang={shown.lang ?? undefined}>
        {other ? <p className="tp-alt" lang={lang === 'en' ? 'th' : 'en'}>{other}</p> : null}
        <div className="j-tags">
          {journal.tci_tier ? <span className="tp-badge">{t('jr.tier.n', { n: journal.tci_tier })}</span> : null}
          <span className="tp-sub">{shown.isPath ? t('jr.noName') : t('jr.ojs', { path: journal.path })}</span>
          {journal.issn ? <span>ISSN {journal.issn}</span> : null}
          {journal.eissn ? <span>e-ISSN {journal.eissn}</span> : null}
          {journal.publisher ? <span>{t('jr.publisher', { p: journal.publisher })}</span> : null}
          {journal.first_year && journal.last_year ? <span>{t('jr.years', { a: journal.first_year, b: journal.last_year })}</span> : null}
          {journal.url ? <a href={journal.url} target="_blank" rel="noopener noreferrer">{t('jr.site')}<span className="sr-only"> {t('newTab')}</span></a> : null}
        </div>
      </PageHeader>
      <div className="layout">
        <div className="main-col">
          <Section id="numbers" title={t('jr.numbers.h')}>
            {journal.low_data ? <p className="note">{t('jr.lowDataBody', { a: w.start, b: w.end, n: fmtInt(file.min_articles) })}</p> : null}
            <StatGrid cols={3}>
              <StatTile
                wide
                label={t('col.articlesW')}
                value={fmtInt(journal.articles_window)}
                sub={t('jr.articlesSub', { a: w.start, b: w.end, all: fmtInt(journal.articles) })}
              />
              <StatTile label={t('col.completeness')} value={journal.completeness == null ? gap : fmtNum(journal.completeness, 1)} sub={t('jr.completenessSub')} />
              <StatTile label={t('col.inhouse')} value={journal.inhouse_share == null ? gap : fmtPct(journal.inhouse_share, 0)} sub={inhouseSub}>
                {journal.owner_source === 'inferred' && journal.inhouse_share != null ? <span className="flag">{t('jr.inferred')}</span> : null}
                {inhouseFlag(journal, file.inhouse_flag_share) ? <span className="flag">{t('jr.flag')}</span> : null}
              </StatTile>
              <StatTile
                label={t('col.effOrgs')}
                value={journal.effective_orgs == null ? gap : fmtNum(journal.effective_orgs, 1)}
                sub={journal.effective_orgs == null ? t('jr.orgsSubN', { n: fmtInt(journal.n_orgs ?? 0) }) : t('jr.orgsSub', { n: fmtInt(journal.n_orgs ?? 0), e: fmtNum(journal.effective_orgs, 1) })}
              />
              <StatTile
                label={t('col.foreign')}
                value={journal.foreign_share == null ? gap : fmtPct(journal.foreign_share, 0)}
                sub={`${t('jr.foreignSub')}${journal.affiliation_coverage == null ? '' : ` · ${t('jr.coverageSub', { p: fmtPct(journal.affiliation_coverage, 0) })}`}`}
              />
            </StatGrid>
          </Section>

          {topics.length ? (
            <Section id="topics" title={t('jr.topics.h')} intro={t('jr.topics.intro', { a: w.start, b: w.end, topic: topTopic ? name(topTopic) : DASH })}>
              <DataTable caption={t('table.n', { n: tabNo.topics, title: t('jr.topics.table') })} rows={topics} columns={topicColumns} rowKey={(x) => x.topic} defaultSort={{ key: 'count', dir: 'desc' }} csvFilename={`atlas-${rel}-${journal.id}-topics.csv`} />
              {hasTy && ty ? (
                <Figure
                  id="fig-topic-years"
                  number={figNo.ty}
                  title={s('ty.fig', { n: fmtInt(tyTopics.length), a: ty.years[0], b: ty.years[ty.years.length - 1] })}
                  tableTitle={t('table.n', { n: tabNo.ty, title: s('ty.table') })}
                  csv={figureCsv(`atlas-${rel}-${journal.id}-topics-by-year.csv`, tyRows, tyColumns)}
                  how={<p>{s('ty.how')}</p>}
                  note={
                    tyLead || thinYears.length ? (
                      <>
                        {tyLead ? <p className="note">{tyLead}</p> : null}
                        {/* a blank year must never read as zero: say so beside the chart, not only under "how to read" */}
                        {thinYears.length ? <p className="note">{s('ty.thin', { m: fmtInt(ty.min_articles), years: thinYears.join(', ') })}</p> : null}
                      </>
                    ) : undefined
                  }
                  source={source}
                  view={state.ty}
                  onView={(v) => update({ ty: v })}
                  chart={
                    <SmallMultiples
                      years={ty.years}
                      series={tyTopics.map((x) => ({ id: x.topic, label: mixName(x.topic), values: x.shares.map((v) => v ?? null) }))}
                      format={(v) => fmtPct(v, 0)}
                      axisFormat={(v) => fmtPct(v, 0)}
                    />
                  }
                  table={<DataTable caption={t('table.n', { n: tabNo.ty, title: s('ty.table') })} rows={tyRows} columns={tyColumns} rowKey={(r) => String(r.year)} stack={false} />}
                />
              ) : null}
            </Section>
          ) : null}

          {hasDrift || mix.rows.length ? (
            <Section
              id="drift"
              title={t('jr.drift.h')}
              intro={moved ? s('pm.lead', { t: mixName(moved.topic), a: fmtPct(moved.before, 0), b: fmtPct(moved.after, 0) }) : t('jr.drift.intro', { n: fmtInt(file.drift_reference_years ?? 0) })}
            >
              {mix.rows.length ? (
                <Figure
                  id="fig-mix"
                  number={figNo.mix}
                  title={s('pm.fig', { b: baseSpan, r: recentSpan })}
                  tableTitle={t('table.n', { n: tabNo.mix, title: s('pm.table') })}
                  csv={figureCsv(`atlas-${rel}-${journal.id}-topic-shift.csv`, mix.rows, mixColumns)}
                  how={<p>{s('pm.how', { b: baseSpan, r: recentSpan })}</p>}
                  source={source}
                  view={state.mix}
                  onView={(v) => update({ mix: v })}
                  chart={
                    <PeriodMix
                      rows={mix.rows}
                      other={mix.other}
                      periods={[baseSpan, recentSpan]}
                      name={(tid) => (topicOf(tid) ? <TopicLink topic={topicOf(tid) as Topic} /> : tid)}
                      fmt={(v) => fmtPct(v, 0)}
                      change={pts}
                      otherName={s('pm.other')}
                      label={s('pm.label', {
                        b: baseSpan,
                        r: recentSpan,
                        x: mix.rows.map((r) => `${mixName(r.topic)} ${fmtPct(r.before, 0)}`).join(', '),
                        y: mix.rows.map((r) => `${mixName(r.topic)} ${fmtPct(r.after, 0)}`).join(', '),
                      })}
                    />
                  }
                  table={<DataTable caption={t('table.n', { n: tabNo.mix, title: s('pm.table') })} rows={mix.rows} columns={mixColumns} rowKey={(r) => r.topic} defaultSort={{ key: 'change', dir: 'desc' }} />}
                />
              ) : null}
              {hasDrift ? (
                <Figure
                  id="fig-drift"
                  number={figNo.drift}
                  title={t('jr.drift.fig')}
                  tableTitle={t('table.n', { n: tabNo.drift, title: t('jr.drift.fig') })}
                  csv={figureCsv(`atlas-${rel}-${journal.id}-drift.csv`, drift, driftColumns)}
                  how={
                    <>
                      <p>{t('jr.drift.intro', { n: fmtInt(file.drift_reference_years ?? 0) })}</p>
                      <p>{t('jr.drift.how', { n: fmtInt(file.drift_reference_years ?? 0) })}</p>
                      <p className="how-terms">
                        <span>{t('glossary.terms')}:</span>
                        <Term term="jsd" />
                      </p>
                    </>
                  }
                  source={source}
                  view={state.drift}
                  onView={(v) => update({ drift: v })}
                  chart={<MultiLineChart years={drift.map((d) => d.year)} series={[{ id: 'drift', label: t('jr.drift.series'), values: drift.map((d) => d.distance ?? null) }]} format={(v) => fmtNum(v, 2)} axisFormat={(v, step) => fmtNum(v, tickDecimals(step))} label={t('jr.drift.fig')} />}
                  table={<DataTable caption={t('table.n', { n: tabNo.drift, title: t('jr.drift.fig') })} rows={drift} columns={driftColumns} rowKey={(d) => String(d.year)} stack={false} />}
                />
              ) : null}
            </Section>
          ) : null}

          {comp.length ? (
            <Section
              id="completeness"
              title={t('jr.comp.h')}
              intro={weakest && nFull < checks.length
                ? s('ck.lead', { k: fmtInt(nFull), n: fmtInt(checks.length), item: t(`comp.${weakest.key}` as StrKey), p: fmtPct(weakest.rate ?? null, 0) })
                : s('ck.leadAll', { n: fmtInt(checks.length) })}
            >
              <Figure
                id="fig-comp"
                number={figNo.comp}
                title={s('ck.fig')}
                tableTitle={t('table.n', { n: tabNo.comp, title: t('jr.comp.table') })}
                csv={figureCsv(`atlas-${rel}-${journal.id}-completeness.csv`, comp, compColumns)}
                how={
                  <>
                    <p>{t('jr.comp.intro')}</p>
                    <p>{s('ck.how', { full: fmtPct(CHECK_FULL, 0), none: fmtPct(CHECK_NONE, 0) })}</p>
                  </>
                }
                source={source}
                view={state.comp}
                onView={(v) => update({ comp: v })}
                chart={<ChecklistBars rows={checks} words={{ full: s('ck.full'), partial: s('ck.partial'), none: s('ck.none'), unknown: s('ck.unknown') }} label={s('ck.label', { n: fmtInt(checks.length) })} />}
                table={<DataTable caption={t('table.n', { n: tabNo.comp, title: t('jr.comp.table') })} rows={comp} columns={compColumns} rowKey={(c) => c.key} stack={false} />}
              />
            </Section>
          ) : null}

          {peers.length ? (
            <Section id="peers" title={t('jr.peers.h')} intro={t('jr.peers.intro')}>
              <DataTable caption={t('table.n', { n: tabNo.peers, title: t('jr.peers.table') })} rows={peerRows} columns={peerColumns} rowKey={(r) => r.journal.id} csvFilename={`atlas-${rel}-${journal.id}-peers.csv`} />
              <HowNote>
                <p className="how-terms">
                  <span>{t('glossary.terms')}:</span>
                  <Term term="cosine" />
                </p>
              </HowNote>
            </Section>
          ) : null}

          {methods.length ? (
            <Section id="methods" title={t('jr.methods.h')} intro={t('jr.methods.intro', { p: fmtPct(journal.methods_coverage ?? null, 0) })}>
              <DataTable caption={t('table.n', { n: tabNo.methods, title: t('jr.methods.table') })} rows={methods} columns={methodColumns} rowKey={(m) => m.method} stack={false} csvFilename={`atlas-${rel}-${journal.id}-methods.csv`} />
            </Section>
          ) : null}

          {opps.length ? (
            <Section id="opportunities" title={t('jr.opp.h')} intro={t('jr.opp.intro')}>
              <ul className="opp-list">
                {opps.map((o) => (
                  <li key={o.topic}>
                    <TopicLink topic={topicOf(o.topic) as Topic} showStatus />
                    <span className="topic-sub">{t(o.reason === 'in_scope' ? 'jr.opp.in_scope' : 'jr.opp.adjacent', { n: fmtInt(o.journal_articles), h: fmtInt(o.hosts) })}</span>
                  </li>
                ))}
              </ul>
            </Section>
          ) : null}
          {detailFile.status === 'loading' ? <p className="loading" role="status">{t('loading')}</p> : null}
        </div>
        <aside className="rail" aria-label={t('onThisPage')}>
          <OnThisPage items={toc} />
          <p className="mt-6"><Link to="/journals">{t('jr.back')}</Link></p>
        </aside>
      </div>
    </div>
  )
}
