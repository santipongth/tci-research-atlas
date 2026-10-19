import { Link, useParams } from 'react-router'
import { MultiLineChart } from '../charts/MultiLineChart'
import { DataTable, type Column } from '../components/DataTable'
import { Figure } from '../components/Figure'
import { JournalLink } from '../components/JournalLink'
import { ModuleFile } from '../components/ModuleFile'
import { OnThisPage } from '../components/OnThisPage'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { ShareBar } from '../components/ShareBar'
import { TopicLink } from '../components/TopicLink'
import { useReleaseFile } from '../data/atlasContext'
import { hasModule, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { CompletenessItem, DriftPoint, JournalDetail, JournalSummary, JournalsFile, MethodShare, MethodsFile, Topic, TopicShare } from '../data/types'
import { DASH, fmtInt, fmtNum, fmtPct } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { inhouseFlag, inhouseGap, journalName, otherJournalName } from '../lib/journals'
import { journalCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import type { StrKey } from '../strings'

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
  const { t, lang } = useI18n()
  const detailFile = useReleaseFile<JournalDetail>(`journals/${journal.id}.json`)
  const detail = detailFile.status === 'ready' ? detailFile.data : null
  const [state, update] = useUrlState(journalCodec)
  const methodsFile = useReleaseFile<MethodsFile>(hasModule(release, 'methods') ? MODULE_FILES.methods : null)
  const methodInfo = new Map((methodsFile.status === 'ready' ? methodsFile.data.methods : []).map((m) => [m.key, m]))
  const w = file.window
  const shown = journalName(journal, lang)
  const other = otherJournalName(journal, lang)
  const source = t('source.line', { release: release.overview.release, v: release.definitionVersion })
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
  const owner = journal.owner || ''
  /** an empty value: too few articles ("low data") or unknown — never shown as zero */
  const gap = journal.low_data ? t('jr.lowData') : t('jr.unknown')
  const inhouseSub = journal.inhouse_share == null && inhouseGap(journal) === 'owner_not_found'
    ? t('jr.ownerNotFound')
    : owner ? t(journal.owner_source === 'inferred' ? 'jr.inhouseSubInferred' : 'jr.inhouseSub', { o: owner }) : t('jr.noOwner')
  const toc = [
    { id: 'numbers', label: t('jr.numbers.h') },
    ...(topics.length ? [{ id: 'topics', label: t('jr.topics.h') }] : []),
    ...(drift.some((d) => d.distance != null) ? [{ id: 'drift', label: t('jr.drift.h') }] : []),
    ...(comp.length ? [{ id: 'completeness', label: t('jr.comp.h') }] : []),
    ...(peers.length ? [{ id: 'peers', label: t('jr.peers.h') }] : []),
    ...(methods.length ? [{ id: 'methods', label: t('jr.methods.h') }] : []),
    ...(opps.length ? [{ id: 'opportunities', label: t('jr.opp.h') }] : []),
  ]
  const share = (s: TopicShare) => s.share
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
  const gapOf = (j: JournalSummary) => (j.low_data ? t('jr.lowData') : t('jr.unknown'))
  type PeerRow = { journal: JournalSummary; similarity: number | null }
  const peerRows: PeerRow[] = [{ journal, similarity: null }, ...peers.map((p) => ({ journal: byId.get(p.id) as JournalSummary, similarity: p.similarity }))]
  const peerColumns: Column<PeerRow>[] = [
    { key: 'name', csvHeader: 'journal_id', header: t('col.journal'), rowHeader: true, cell: (r) => (r.similarity === null ? <strong>{t('jr.this')}</strong> : <JournalLink journal={r.journal} />), csv: (r) => r.journal.id },
    { key: 'sim', csvHeader: 'similarity', header: t('col.similarity'), numeric: true, cell: (r) => (r.similarity === null ? DASH : fmtNum(r.similarity, 2)), csv: (r) => r.similarity },
    { key: 'articles', csvHeader: 'articles_window', header: t('col.articlesW'), numeric: true, cell: (r) => fmtInt(r.journal.articles_window), csv: (r) => r.journal.articles_window },
    { key: 'completeness', csvHeader: 'completeness', header: t('col.completeness'), numeric: true, cell: (r) => (r.journal.completeness == null ? gapOf(r.journal) : fmtNum(r.journal.completeness, 1)), csv: (r) => r.journal.completeness ?? null },
    { key: 'inhouse', csvHeader: 'inhouse_share', header: t('col.inhouse'), numeric: true, cell: (r) => (r.journal.inhouse_share == null ? gapOf(r.journal) : fmtPct(r.journal.inhouse_share, 0)), csv: (r) => r.journal.inhouse_share ?? null },
    { key: 'orgs', csvHeader: 'effective_orgs', header: t('col.effOrgs'), numeric: true, cell: (r) => (r.journal.effective_orgs == null ? gapOf(r.journal) : fmtNum(r.journal.effective_orgs, 1)), csv: (r) => r.journal.effective_orgs ?? null },
    { key: 'foreign', csvHeader: 'foreign_share', header: t('col.foreign'), numeric: true, cell: (r) => (r.journal.foreign_share == null ? gapOf(r.journal) : fmtPct(r.journal.foreign_share, 0)), csv: (r) => r.journal.foreign_share ?? null },
  ]
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
            <dl className="summary">
              <div>
                <dt>{t('col.articlesW')}</dt>
                <dd>{fmtInt(journal.articles_window)}<small>{t('jr.articlesSub', { a: w.start, b: w.end, all: fmtInt(journal.articles) })}</small></dd>
              </div>
              <div>
                <dt>{t('col.completeness')}</dt>
                <dd>{journal.completeness == null ? gap : fmtNum(journal.completeness, 1)}<small>{t('jr.completenessSub')}</small></dd>
              </div>
              <div>
                <dt>{t('col.inhouse')}</dt>
                <dd>
                  {journal.inhouse_share == null ? gap : fmtPct(journal.inhouse_share, 0)}
                  {journal.owner_source === 'inferred' && journal.inhouse_share != null ? <span className="flag">{t('jr.inferred')}</span> : null}
                  {inhouseFlag(journal, file.inhouse_flag_share) ? <span className="flag">{t('jr.flag')}</span> : null}
                  <small>{inhouseSub}</small>
                </dd>
              </div>
              <div>
                <dt>{t('col.effOrgs')}</dt>
                <dd>{journal.effective_orgs == null ? gap : fmtNum(journal.effective_orgs, 1)}<small>{journal.effective_orgs == null ? t('jr.orgsSubN', { n: fmtInt(journal.n_orgs ?? 0) }) : t('jr.orgsSub', { n: fmtInt(journal.n_orgs ?? 0), e: fmtNum(journal.effective_orgs, 1) })}</small></dd>
              </div>
              <div>
                <dt>{t('col.foreign')}</dt>
                <dd>{journal.foreign_share == null ? gap : fmtPct(journal.foreign_share, 0)}<small>{t('jr.foreignSub')}{journal.affiliation_coverage == null ? '' : ` · ${t('jr.coverageSub', { p: fmtPct(journal.affiliation_coverage, 0) })}`}</small></dd>
              </div>
            </dl>
          </Section>

          {topics.length ? (
            <Section id="topics" title={t('jr.topics.h')} intro={t('jr.topics.intro', { a: w.start, b: w.end })}>
              <DataTable caption={t('table.n', { n: 1, title: t('jr.topics.table') })} rows={topics} columns={topicColumns} rowKey={(s) => s.topic} defaultSort={{ key: 'count', dir: 'desc' }} csvFilename={`atlas-${rel}-${journal.id}-topics.csv`} />
              {gained.length ? <Shifts title={t('jr.gained', { r: `${file.recent.start}–${file.recent.end}`, b: `${file.baseline.start}–${file.baseline.end}` })} rows={gained} release={release} /> : null}
              {lost.length ? <Shifts title={t('jr.lost', { r: `${file.recent.start}–${file.recent.end}`, b: `${file.baseline.start}–${file.baseline.end}` })} rows={lost} release={release} /> : null}
            </Section>
          ) : null}

          {drift.some((d) => d.distance != null) ? (
            <Section id="drift" title={t('jr.drift.h')} intro={t('jr.drift.intro', { n: fmtInt(file.drift_reference_years ?? 0) })}>
              <Figure
                id="fig-drift"
                number={1}
                title={t('jr.drift.fig')}
                source={source}
                view={state.drift}
                onView={(v) => update({ drift: v })}
                chart={<MultiLineChart years={drift.map((d) => d.year)} series={[{ id: 'drift', label: t('jr.drift.series'), values: drift.map((d) => d.distance ?? null) }]} format={(v) => fmtNum(v, 2)} axisFormat={(v) => fmtNum(v, 1)} label={t('jr.drift.fig')} />}
                table={<DataTable caption={t('table.n', { n: 2, title: t('jr.drift.table') })} rows={drift} columns={driftColumns} rowKey={(d) => String(d.year)} stack={false} csvFilename={`atlas-${rel}-${journal.id}-drift.csv`} />}
              />
            </Section>
          ) : null}

          {comp.length ? (
            <Section id="completeness" title={t('jr.comp.h')} intro={t('jr.comp.intro')}>
              <DataTable caption={t('table.n', { n: 3, title: t('jr.comp.table') })} rows={comp} columns={compColumns} rowKey={(c) => c.key} stack={false} csvFilename={`atlas-${rel}-${journal.id}-completeness.csv`} />
            </Section>
          ) : null}

          {peers.length ? (
            <Section id="peers" title={t('jr.peers.h')} intro={t('jr.peers.intro')}>
              <DataTable caption={t('table.n', { n: 4, title: t('jr.peers.table') })} rows={peerRows} columns={peerColumns} rowKey={(r) => r.journal.id} csvFilename={`atlas-${rel}-${journal.id}-peers.csv`} />
            </Section>
          ) : null}

          {methods.length ? (
            <Section id="methods" title={t('jr.methods.h')} intro={t('jr.methods.intro', { p: fmtPct(journal.methods_coverage ?? null, 0) })}>
              <DataTable caption={t('table.n', { n: 5, title: t('jr.methods.table') })} rows={methods} columns={methodColumns} rowKey={(m) => m.method} stack={false} csvFilename={`atlas-${rel}-${journal.id}-methods.csv`} />
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

function Shifts({ title, rows, release }: { title: string; rows: readonly { topic: string; share_before: number; share_after: number }[]; release: AtlasRelease }) {
  const { t } = useI18n()
  return (
    <>
      <h3 className="mt-6">{title}</h3>
      <ul className="shift-list">
        {rows.map((s) => (
          <li key={s.topic}>
            <TopicLink topic={release.topicById.get(s.topic) as Topic} />{' '}
            <span className="topic-sub">{t('jr.shift', { from: fmtPct(s.share_before, 0), to: fmtPct(s.share_after, 0) })}</span>
          </li>
        ))}
      </ul>
    </>
  )
}
