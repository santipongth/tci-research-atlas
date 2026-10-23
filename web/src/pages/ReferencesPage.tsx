import { Link } from 'react-router'
import { BridgePairs, type BridgeRow } from '../charts/BridgePairs'
import { weightedMean } from '../charts/editorLayout'
import { SplitBar } from '../charts/MixBar'
import { DataTable, type Column } from '../components/DataTable'
import { EmptyState } from '../components/EmptyState'
import { Figure } from '../components/Figure'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { SourceLine } from '../components/SourceLine'
import { ShareBar } from '../components/ShareBar'
import { StatGrid, StatTile } from '../components/StatTile'
import { TopicLink } from '../components/TopicLink'
import { hasModule, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { CitationFlow, CitedArticle, InternalCitations, JournalRefs, ReferencesFile, TopicCitations } from '../data/types'
import { toBibtex, toRis, type CiteRecord } from '../lib/citation'
import { downloadText, toCsv, type CsvColumn } from '../lib/csv'
import { DASH, fmtInt, fmtNum, fmtPct } from '../lib/format'
import { useI18n, useStrings } from '../lib/i18n'
import { sortBy } from '../lib/sort'
import { figureCsv } from '../lib/tableCsv'
import { referencesCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import { references as REF } from '../strings/references'

/** Topic pairs drawn as link diagrams; the rest are in the table view. */
const FLOW_PAIRS = 6
/** Rows of the per-topic table before "แสดงทั้งหมด". */
const TOPIC_ROWS = 10

export default function ReferencesPage() {
  const s = useStrings(REF)
  return (
    <RequireRelease title={s('title')}>
      {(release) => (
        <ModuleFile<ReferencesFile> release={release} module="references" path={MODULE_FILES.references} title={s('title')}>
          {(file) => <References release={release} file={file} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

/** Thai script (U+0E00–U+0E7F), built from code points: the codebase never writes a backslash-u escape. */
const THAI = new RegExp(`[${String.fromCodePoint(0x0e00)}-${String.fromCodePoint(0x0e7f)}]`)
const langOf = (text: string) => (THAI.test(text) ? 'th' : 'en')
const median = (v: number | null | undefined) => (v === null || v === undefined ? DASH : fmtNum(v, Number.isInteger(v) ? 0 : 1))

function References({ release, file }: { release: AtlasRelease; file: ReferencesFile }) {
  const s = useStrings(REF)
  const internal = file.internal ?? null
  const span = { a: file.window.start, b: file.window.end }
  return (
    <div className="container">
      <PageHeader title={s('title')} lede={s('lede', { p: fmtPct(file.coverage, 0), ...span, refs: fmtInt(file.refs_counted) })} />
      <div className="layout">
        <div className="main-col">
          <Coverage file={file} internal={internal} />
          <Journals release={release} file={file} />
          {internal ? (
            <>
              <Section id="ref-internal" title={s('in.h')}>
                <p className="ref-lead">
                  {s('in.intro', { n: fmtInt(internal.matches), citing: fmtInt(internal.citing_articles), cited: fmtInt(internal.cited_articles), doi: fmtPct(internal.share_doi, 0), title: fmtPct(internal.share_title, 0) })}
                </p>
              </Section>
              {internal.top_articles.length ? <TopArticles release={release} rows={internal.top_articles} /> : null}
              <Flows release={release} internal={internal} />
              <TopicTable release={release} rows={internal.topics} />
            </>
          ) : (
            <Section id="ref-internal" title={s('in.h')}>
              <EmptyState title={s('in.off.h')}>
                <p>{s('in.off.body')}</p>
                {file.internal_reason ? <p className="hint">{s('in.off.detail')} <span lang="en">{file.internal_reason}</span></p> : null}
              </EmptyState>
            </Section>
          )}
          <SourceLine className="ref-source" />
        </div>
      </div>
    </div>
  )
}

function Coverage({ file, internal }: { file: ReferencesFile; internal: InternalCitations | null }) {
  const s = useStrings(REF)
  const perArticle = file.articles_with_refs ? file.refs_counted / file.articles_with_refs : 0
  return (
    <Section id="ref-coverage" title={s('cov.h')}>
      <StatGrid cols={internal ? 3 : 2} className="ref-kpis">
        <StatTile label={s('cov.with')} value={fmtPct(file.coverage, 0)} sub={s('cov.withSub', { n: fmtInt(file.articles_with_refs), all: fmtInt(file.articles), a: file.window.start, b: file.window.end })} />
        <StatTile label={s('cov.refs')} value={fmtInt(file.refs_counted)} sub={s('cov.refsSub', { n: fmtInt(Math.round(perArticle)) })} />
        {internal ? <StatTile wide="phone" label={s('cov.internal')} value={fmtInt(internal.matches)} sub={s('cov.internalSub', { n: fmtInt(internal.citing_articles) })} /> : null}
      </StatGrid>
      <p className="note">{s('cov.note', { p: fmtPct(file.min_coverage, 0) })}</p>
    </Section>
  )
}

function JournalName({ j, linkable }: { j: JournalRefs; linkable: boolean }) {
  return j.id && linkable ? <Link to={`/journals/${j.id}`} lang={langOf(j.journal)}>{j.journal}</Link> : <span lang={langOf(j.journal)}>{j.journal}</span>
}

function Journals({ release, file }: { release: AtlasRelease; file: ReferencesFile }) {
  const s = useStrings(REF)
  const { t } = useI18n()
  const [state, update] = useUrlState(referencesCodec)
  const linkable = hasModule(release, 'journals')
  const withRecent = file.journals.filter((j) => j.share_recent !== null && j.share_recent !== undefined)
  const bars = sortBy(withRecent, (j) => j.share_recent, 'desc')
  const best = bars[0]
  const avg = weightedMean(file.journals, (j) => j.share_recent, (j) => j.articles_with_refs)
  const y = file.recent_years
  const columns: Column<JournalRefs>[] = [
    {
      key: 'journal', header: s('col.journal'), rowHeader: true,
      cell: (j) => <JournalName j={j} linkable={linkable} />,
      sortValue: (j) => j.journal,
      csvCols: [{ header: 'journal', value: (j) => j.journal }, { header: 'journal_id', value: (j) => j.id ?? '' }],
    },
    {
      key: 'read', header: s('col.withRefs'), numeric: true,
      cell: (j) => <>{fmtInt(j.articles_with_refs)} <span className="ref-of">{s('col.ofAll', { n: fmtInt(j.articles) })}</span></>,
      sortValue: (j) => j.articles_with_refs,
      csvCols: [{ header: 'articles', value: (j) => j.articles }, { header: 'articles_with_refs', value: (j) => j.articles_with_refs }],
    },
    { key: 'median', csvHeader: 'refs_median', header: s('col.median'), numeric: true, cell: (j) => median(j.refs_median), sortValue: (j) => j.refs_median },
    { key: 'age', csvHeader: 'age_median', header: s('col.age'), numeric: true, firstDir: 'asc', cell: (j) => median(j.age_median), sortValue: (j) => j.age_median },
    { key: 'recent', csvHeader: 'share_recent', header: s('col.recent'), firstDir: 'desc', cell: (j) => <ShareBar value={j.share_recent} />, sortValue: (j) => j.share_recent },
    { key: 'thai', csvHeader: 'share_thai', header: s('col.thai'), firstDir: 'desc', cell: (j) => <ShareBar value={j.share_thai} />, sortValue: (j) => j.share_thai },
    { key: 'doi', csvHeader: 'share_doi', header: s('col.doi'), firstDir: 'desc', cell: (j) => <ShareBar value={j.share_doi} />, sortValue: (j) => j.share_doi },
  ]
  const table = (
    <DataTable
      caption={t('table.n', { n: 1, title: s('jr.table') })}
      rows={file.journals}
      columns={columns}
      rowKey={(j) => j.id ?? j.journal}
      defaultSort={{ key: 'read', dir: 'desc' }}
      csvFilename={`atlas-${release.overview.release}-references-journals.csv`}
      wide
      empty={s('jr.none')}
    />
  )
  return (
    <Section id="ref-journals" title={s('jr.h')} intro={s('jr.intro', { n: fmtInt(file.min_journal_articles), y })}>
      {best ? <p className="ref-lead">{s('jr.insight', { j: best.journal, p: fmtPct(best.share_recent, 0), y })}</p> : null}
      {bars.length ? (
        <Figure
          id="fig-refs"
          number={1}
          title={s('rs.fig', { y })}
          tableTitle={t('table.n', { n: 1, title: s('jr.table') })}
          csv={figureCsv(`atlas-${release.overview.release}-references-journals.csv`, file.journals, columns)}
          how={<p>{s('rs.how', { y, p: fmtPct(avg, 0) })}</p>}
          source={t('source.line', { release: release.overview.release })}
          view={state.jr}
          onView={(v) => update({ jr: v })}
          legend={
            <ul className="sb-key">
              <li><span className="sb-sw is-top" aria-hidden="true" />{s('rs.recent', { y })}</li>
              <li><span className="sb-sw" aria-hidden="true" />{s('rs.older')}</li>
              {avg !== null ? <li><span className="sb-sw is-mark" aria-hidden="true" />{s('rs.avg', { p: fmtPct(avg, 0) })}</li> : null}
            </ul>
          }
          chart={
            <ul className="rk ref-split" aria-label={s('rs.list')}>
              {bars.map((j) => (
                <li key={j.id ?? j.journal} className="rk-row">
                  <span className="rk-unit"><JournalName j={j} linkable={linkable} /></span>
                  <span className="rk-bar">
                    <SplitBar frac={j.share_recent ?? 0} marker={avg ?? 0} text={fmtPct(j.share_recent, 0)} label={s('rs.label', { j: j.journal, p: fmtPct(j.share_recent, 0) })} />
                  </span>
                </li>
              ))}
            </ul>
          }
          table={table}
        />
      ) : (
        table
      )}
    </Section>
  )
}

const cite = (a: CitedArticle): CiteRecord => {
  const thaiMain = THAI.test(a.title) || !a.title_en
  return {
    id: a.article_id,
    titleTh: thaiMain ? a.title : (a.title_en ?? ''),
    titleEn: thaiMain ? (a.title_en ?? '') : a.title,
    journal: a.journal ?? '',
    year: a.year ?? null,
    doi: a.doi || null,
    url: a.url || null,
  }
}

function TopArticles({ release, rows }: { release: AtlasRelease; rows: readonly CitedArticle[] }) {
  const s = useStrings(REF)
  const { t, lang } = useI18n()
  const rel = release.overview.release
  const base = `atlas-${rel}-most-cited`
  const records = rows.map(cite)
  const csvColumns: CsvColumn<CitedArticle>[] = [
    { header: 'article_id', value: (a) => a.article_id },
    { header: 'title', value: (a) => a.title },
    { header: 'title_en', value: (a) => a.title_en },
    { header: 'journal', value: (a) => a.journal },
    { header: 'year', value: (a) => a.year ?? null },
    { header: 'topic', value: (a) => a.topic ?? '' },
    { header: 'doi', value: (a) => a.doi },
    { header: 'url', value: (a) => a.url },
    { header: 'cited_in_tci', value: (a) => a.count },
  ]
  const formats = [
    { key: 'x.ris' as const, run: () => downloadText(`${base}.ris`, toRis(records, rel), 'application/x-research-info-systems;charset=utf-8') },
    { key: 'x.bib' as const, run: () => downloadText(`${base}.bib`, toBibtex(records, rel), 'application/x-bibtex;charset=utf-8') },
    { key: 'x.csv' as const, run: () => downloadText(`${base}.csv`, toCsv(rows, csvColumns)) },
  ]
  return (
    <Section id="ref-top" title={s('top.h')} intro={s('top.intro')}>
      <div className="srch-x" role="group" aria-labelledby="ref-x-h">
        <p id="ref-x-h" className="srch-x-h">{s('x.h')}</p>
        <div className="srch-x-btns">
          {formats.map((f) => (
            <button key={f.key} type="button" className="btn-secondary" aria-label={s('x.label', { n: fmtInt(rows.length), format: s(f.key) })} onClick={f.run}>{s(f.key)}</button>
          ))}
        </div>
        <p className="hint">{s('x.note')}</p>
      </div>
      <ol className="rc-list">
        {rows.map((a) => {
          const th = THAI.test(a.title) ? a.title : ''
          const en = a.title_en || (th ? '' : a.title)
          const [main, sub] = lang === 'en' ? [en || th, en ? th : ''] : [th || en, th ? en : '']
          const topic = a.topic ? release.topicById.get(a.topic) : undefined
          return (
            <li key={a.article_id} className="rc-card">
              <p className="rc-n"><b>{fmtInt(a.count)}</b> <span>{s('rc.times')}</span></p>
              <div className="rc-body">
                <p className="srch-title" lang={langOf(main)}>
                  {a.url ? <a href={a.url} target="_blank" rel="noopener noreferrer">{main}<span className="sr-only"> {t('newTab')}</span></a> : main}
                </p>
                {sub ? <p className="srch-sub" lang={langOf(sub)}>{sub}</p> : null}
                <p className="srch-meta">
                  {a.journal ? <span lang={langOf(a.journal)}>{a.journal}</span> : null}
                  {a.year ? <span>{a.year}</span> : null}
                  {topic ? <span><TopicLink topic={topic} /></span> : <span>{s('top.noTopic')}</span>}
                  {a.doi ? (
                    <span>
                      <a href={`https://doi.org/${a.doi}`} target="_blank" rel="noopener noreferrer">DOI {a.doi}<span className="sr-only"> {t('newTab')}</span></a>
                    </span>
                  ) : null}
                </p>
              </div>
            </li>
          )
        })}
      </ol>
    </Section>
  )
}

function TopicCell({ release, id }: { release: AtlasRelease; id: string }) {
  const tp = release.topicById.get(id)
  return tp ? <TopicLink topic={tp} showStatus /> : <span>{id}</span>
}

function Flows({ release, internal }: { release: AtlasRelease; internal: InternalCitations }) {
  const s = useStrings(REF)
  const { t } = useI18n()
  const [state, update] = useUrlState(referencesCodec)
  const columns: Column<CitationFlow>[] = [
    { key: 'source', csvHeader: 'source', header: s('col.source'), rowHeader: true, cell: (f) => <TopicCell release={release} id={f.source} />, sortValue: (f) => f.source },
    {
      key: 'target', csvHeader: 'target', header: s('col.target'),
      cell: (f) => (f.source === f.target ? <span className="topic-sub">{s('flow.same')}</span> : <TopicCell release={release} id={f.target} />),
      sortValue: (f) => f.target,
    },
    { key: 'n', csvHeader: 'n', header: s('col.n'), numeric: true, cell: (f) => fmtInt(f.n), sortValue: (f) => f.n },
  ]
  const rel = release.overview.release
  const table = (
    <DataTable
      caption={t('table.n', { n: 2, title: s('flow.table') })}
      rows={internal.flows}
      columns={columns}
      rowKey={(f) => `${f.source}-${f.target}`}
      defaultSort={{ key: 'n', dir: 'desc' }}
      csvFilename={`atlas-${rel}-references-flows.csv`}
      empty={s('flow.none')}
    />
  )
  const top = sortBy(internal.flows, (f) => f.n, 'desc').slice(0, FLOW_PAIRS)
  const pairs: BridgeRow[] = top.map((f) => ({
    key: `${f.source}-${f.target}`,
    a: <TopicCell release={release} id={f.source} />,
    b: f.source === f.target ? <span className="topic-sub">{s('flow.same')}</span> : <TopicCell release={release} id={f.target} />,
    shared: f.n,
    sharedText: s('rf.n', { n: fmtInt(f.n) }),
    simText: '',
  }))
  return (
    <Section id="ref-flows" title={s('flow.h')} intro={s('flow.intro', { n: fmtInt(internal.min_flow) })}>
      {pairs.length ? (
        <Figure
          id="fig-flows"
          number={2}
          title={s('rf.fig')}
          tableTitle={t('table.n', { n: 2, title: s('flow.table') })}
          csv={figureCsv(`atlas-${rel}-references-flows.csv`, internal.flows, columns)}
          how={<p>{s('rf.how')}</p>}
          source={t('source.line', { release: rel })}
          view={state.flow}
          onView={(v) => update({ flow: v })}
          chart={<BridgePairs rows={pairs} label={s('rf.label', { n: fmtInt(pairs.length) })} directed />}
          table={table}
          note={internal.flows.length > pairs.length ? <p className="br-more">{s('rf.more', { n: fmtInt(internal.flows.length - pairs.length) })}</p> : null}
        />
      ) : (
        table
      )}
    </Section>
  )
}

function TopicTable({ release, rows }: { release: AtlasRelease; rows: readonly TopicCitations[] }) {
  const s = useStrings(REF)
  const { t } = useI18n()
  const columns: Column<TopicCitations>[] = [
    { key: 'topic', csvHeader: 'topic', header: s('col.topic'), rowHeader: true, cell: (r) => <TopicCell release={release} id={r.topic} />, sortValue: (r) => r.topic },
    { key: 'received', csvHeader: 'received', header: s('col.received'), numeric: true, cell: (r) => fmtInt(r.received), sortValue: (r) => r.received },
    { key: 'given', csvHeader: 'given', header: s('col.given'), numeric: true, cell: (r) => fmtInt(r.given), sortValue: (r) => r.given },
  ]
  return (
    <Section id="ref-topics" title={s('tp.h')} intro={s('tp.intro')}>
      <DataTable
        caption={t('table.n', { n: 3, title: s('tp.table') })}
        rows={rows}
        columns={columns}
        rowKey={(r) => r.topic}
        defaultSort={{ key: 'received', dir: 'desc' }}
        csvFilename={`atlas-${release.overview.release}-references-topics.csv`}
        limit={TOPIC_ROWS}
      />
    </Section>
  )
}
