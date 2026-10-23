import type { ScatterPoint } from '../charts/editorLayout'
import { JournalScatter } from '../charts/JournalScatter'
import { DataTable, type Column } from '../components/DataTable'
import { Figure } from '../components/Figure'
import { HowNote } from '../components/HowNote'
import { JournalLink } from '../components/JournalLink'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { ShareBar } from '../components/ShareBar'
import { TopicLink } from '../components/TopicLink'
import { groupName, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { JournalSummary, JournalsFile, SpecialIssueTopic, Topic } from '../data/types'
import { DASH, fmtInt, fmtNum, fmtPct, yearSpan } from '../lib/format'
import { useI18n, useStrings } from '../lib/i18n'
import { withPrimary } from '../lib/columns'
import { filterJournals, inhouseFlag, inhouseGap, journalName } from '../lib/journals'
import { figureCsv } from '../lib/tableCsv'
import { countLine, useRowLimit } from '../lib/tableRows'
import { statusName } from '../lib/topicText'
import { JOURNAL_SORTS, journalsCodec, TIERS, type JournalSort, type JournalsUrlState } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import { editorViz } from '../strings/editorViz'
import { journals } from '../strings/journals'

export default function JournalsPage() {
  const sj = useStrings(journals)
  return (
    <RequireRelease title={sj('jr.title')}>
      {(release) => (
        <ModuleFile<JournalsFile> release={release} module="journals" path={MODULE_FILES.journals} title={sj('jr.title')}>
          {(file) => <Journals release={release} file={file} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

/** Rows of the journals table before "แสดงทั้งหมด" (fewer on phones, see useRowLimit). */
const TABLE_ROWS = 50

const isSort = (v: string): v is JournalSort => (JOURNAL_SORTS as readonly string[]).includes(v)

function Journals({ release, file }: { release: AtlasRelease; file: JournalsFile }) {
  const { t, lang } = useI18n()
  const sj = useStrings(journals)
  const s = useStrings(editorViz)
  const [state, update] = useUrlState(journalsCodec)
  const tableRows = useRowLimit(TABLE_ROWS)
  const w = file.window
  const rows = filterJournals(file.journals, state.q, state.tier)
  const flagAt = file.inhouse_flag_share ?? null
  /** an empty rate: too few articles to compute it ("low data"), otherwise unknown — never a zero */
  const gap = (j: JournalSummary) => (j.low_data ? sj('jr.lowData') : sj('jr.unknown'))
  const columns: Column<JournalSummary>[] = withPrimary<JournalSummary>([
    { key: 'id', header: 'id', csvHeader: 'journal_id', cell: () => null, csv: (j) => j.id, csvOnly: true },
    {
      key: 'name', header: t('col.journal'), rowHeader: true, cell: (j) => <JournalLink journal={j} />, sortValue: (j) => journalName(j, lang).text,
      csvCols: [{ header: 'name_th', value: (j) => j.name_th ?? '' }, { header: 'name_en', value: (j) => j.name_en ?? '' }, { header: 'ojs_path', value: (j) => j.path }],
    },
    { key: 'tier', csvHeader: 'tci_tier', header: sj('col.tier'), numeric: true, firstDir: 'asc', cell: (j) => (j.tci_tier ? fmtInt(j.tci_tier) : DASH), sortValue: (j) => j.tci_tier ?? 9, csv: (j) => j.tci_tier ?? null },
    { key: 'articles', csvHeader: 'articles_window', header: sj('col.articlesW'), numeric: true, cell: (j) => fmtInt(j.articles_window), sortValue: (j) => j.articles_window },
    {
      key: 'completeness', csvHeader: 'completeness', header: sj('col.completeness'), unit: t('unit.of100'), numeric: true,
      cell: (j) => (j.completeness == null ? gap(j) : fmtNum(j.completeness, 1)), sortValue: (j) => j.completeness ?? null,
    },
    {
      key: 'inhouse', header: sj('col.inhouse'), numeric: true, sortValue: (j) => j.inhouse_share ?? null,
      cell: (j) => (
        j.inhouse_share == null ? (
          <span className="sbar-na">{inhouseGap(j) === 'owner_not_found' ? sj('jr.ownerNotFound') : gap(j)}</span>
        ) : (
        <>
          <ShareBar value={j.inhouse_share} />
          {j.owner_source === 'inferred' && j.inhouse_share != null ? <span className="flag">{sj('jr.inferred')}</span> : null}
          {inhouseFlag(j, flagAt) ? <span className="flag">{sj('jr.flag')}</span> : null}
        </>
        )
      ),
      csvCols: [{ header: 'inhouse_share', value: (j) => j.inhouse_share ?? null }, { header: 'owner_source', value: (j) => j.owner_source ?? '' }],
    },
    {
      key: 'orgs', header: sj('col.effOrgs'), numeric: true, cell: (j) => (j.effective_orgs == null ? gap(j) : fmtNum(j.effective_orgs, 1)), sortValue: (j) => j.effective_orgs ?? null,
      csvCols: [{ header: 'effective_orgs', value: (j) => j.effective_orgs ?? null }, { header: 'n_orgs', value: (j) => j.n_orgs ?? 0 }],
    },
    { key: 'foreign', csvHeader: 'foreign_share', header: sj('col.foreign'), numeric: true, cell: (j) => (j.foreign_share == null ? gap(j) : fmtPct(j.foreign_share, 0)), sortValue: (j) => j.foreign_share ?? null },
    { key: 'group', csvHeader: 'group', header: t('col.field'), cell: (j) => (j.group ? groupName(release, j.group, lang) : DASH), csv: (j) => j.group ?? '' },
  ], ['articles', 'completeness', 'inhouse', 'orgs'])
  const valid = columns.some((c) => c.key === state.sort && c.sortValue)
  return (
    <div className="container">
      <PageHeader title={s('q.jr')} lede={sj('jr.lede', { release: release.overview.release, n: fmtInt(file.journals.length), a: w.start, b: w.end })} />
      <div className="j-tools">
        <label>
          {sj('jr.search')}
          <input type="search" value={state.q} onChange={(e) => update({ q: e.target.value })} />
        </label>
        <label>
          {sj('jr.tier')}
          <select value={state.tier} onChange={(e) => update({ tier: (TIERS as readonly string[]).includes(e.target.value) ? (e.target.value as (typeof TIERS)[number]) : 'all' })}>
            {TIERS.map((tier) => (
              <option key={tier} value={tier}>{tier === 'all' ? sj('jr.tier.all') : tier === 'none' ? sj('jr.tier.none') : sj('jr.tier.n', { n: tier })}</option>
            ))}
          </select>
        </label>
        <p className="hint" role="status">{sj(`jr.${countLine(rows.length, file.journals.length, tableRows)}` as const, { n: fmtInt(rows.length), total: fmtInt(file.journals.length), k: fmtInt(tableRows ?? 0) })}</p>
      </div>
      <Scatter release={release} file={file} rows={rows} view={state.view} update={update} />
      <Section id="journals" title={sj('jr.table', { a: w.start, b: w.end })}>
        <DataTable
          caption={t('table.n', { n: 2, title: sj('jr.table', { a: w.start, b: w.end }) })}
          rows={rows}
          columns={columns}
          rowKey={(j) => j.id}
          limit={TABLE_ROWS}
          sort={valid ? { key: state.sort, dir: state.dir } : { key: 'articles', dir: 'desc' }}
          onSort={(s) => update({ sort: isSort(s.key) ? s.key : 'articles', dir: s.dir })}
          csvFilename={`atlas-${release.overview.release}-journals.csv`}
          empty={sj('jr.none')}
          footnote={flagAt != null ? sj('jr.foot', { p: fmtPct(flagAt, 0), n: fmtInt(file.min_articles) }) : sj('jr.footNoFlag', { n: fmtInt(file.min_articles) })}
        />
        <HowNote><p>{sj('jr.how')}</p></HowNote>
      </Section>
      <SpecialIssues release={release} file={file} />
    </div>
  )
}

/** The two figures editors can act on before an assessment: complete records (x) and authors from the owner (y). */
function Scatter({ release, file, rows, view, update }: {
  release: AtlasRelease
  file: JournalsFile
  rows: readonly JournalSummary[]
  view: JournalsUrlState['view']
  update: (patch: Partial<JournalsUrlState>) => void
}) {
  const { t, lang } = useI18n()
  const sj = useStrings(journals)
  const s = useStrings(editorViz)
  const plotted = rows.filter((j) => j.completeness != null && j.inhouse_share != null)
  if (plotted.length === 0) return null
  const flagAt = file.inhouse_flag_share ?? null
  const byId = new Map(plotted.map((j) => [j.id, j]))
  const points: ScatterPoint[] = plotted.map((j) => ({
    id: j.id, label: journalName(j, lang).text, x: j.completeness as number, y: j.inhouse_share as number, weight: j.articles_window, inferred: j.owner_source === 'inferred',
  }))
  const big = plotted.reduce((a, b) => (b.articles_window > a.articles_window ? b : a))
  const zone = flagAt != null ? s('js.zone', { p: fmtPct(flagAt, 0) }) : ''
  const columns: Column<JournalSummary>[] = [
    { key: 'name', csvHeader: 'journal_id', header: t('col.journal'), rowHeader: true, cell: (j) => <JournalLink journal={j} />, sortValue: (j) => journalName(j, lang).text, csv: (j) => j.id },
    { key: 'completeness', csvHeader: 'completeness', header: sj('col.completeness'), unit: t('unit.of100'), numeric: true, cell: (j) => fmtNum(j.completeness ?? null, 1), sortValue: (j) => j.completeness ?? null },
    { key: 'inhouse', csvHeader: 'inhouse_share', header: sj('col.inhouse'), numeric: true, cell: (j) => fmtPct(j.inhouse_share ?? null, 0), sortValue: (j) => j.inhouse_share ?? null },
    { key: 'articles', csvHeader: 'articles_window', header: sj('col.articlesW'), numeric: true, cell: (j) => fmtInt(j.articles_window), sortValue: (j) => j.articles_window },
  ]
  const rel = release.overview.release
  const title = s('js.fig')
  return (
    <Section
      id="scatter"
      title={s('js.h')}
      intro={s('js.intro', { j: journalName(big, lang).text, c: fmtNum(big.completeness ?? null, 0), p: fmtPct(big.inhouse_share ?? null, 0) })}
    >
      <Figure
        id="fig-journals"
        number={1}
        title={title}
        tableTitle={t('table.n', { n: 1, title: s('js.table') })}
        csv={figureCsv(`atlas-${rel}-journals-scatter.csv`, plotted, columns)}
        how={<p>{flagAt != null ? s('js.how', { p: fmtPct(flagAt, 0) }) : s('js.howNoBar')}</p>}
        source={t('source.line', { release: rel })}
        view={view}
        onView={(v) => update({ view: v })}
        chart={
          <JournalScatter
            points={points}
            yRef={flagAt}
            text={{ x: s('js.x'), y: s('js.y'), zone, owner: s('js.owner'), inferred: s('js.inferred') }}
            label={s('js.label', { n: fmtInt(points.length) })}
            pct={(v, d) => fmtPct(v, d)}
            describe={(p) => {
              const j = byId.get(p.id) as JournalSummary
              return s('js.tip', { j: p.label, c: fmtNum(p.x, 1), p: fmtPct(p.y, 0), n: fmtInt(j.articles_window) })
            }}
          />
        }
        table={<DataTable caption={t('table.n', { n: 1, title: s('js.table') })} rows={plotted} columns={columns} rowKey={(j) => j.id} defaultSort={{ key: 'articles', dir: 'desc' }} limit={50} />}
        note={rows.length > plotted.length ? <p className="note">{s('js.left', { n: fmtInt(rows.length - plotted.length) })}</p> : null}
      />
    </Section>
  )
}

function SpecialIssues({ release, file }: { release: AtlasRelease; file: JournalsFile }) {
  const { t, lang, name } = useI18n()
  const sj = useStrings(journals)
  const s = useStrings(editorViz)
  const rows = (file.special_issue ?? []).filter((x) => release.topicById.has(x.topic))
  if (rows.length === 0) return null
  const topicOf = (x: SpecialIssueTopic) => release.topicById.get(x.topic) as Topic
  const r = file.recent
  const span = yearSpan(r.start, r.end)
  const columns: Column<SpecialIssueTopic>[] = [
    { key: 'topic', csvHeader: 'topic_id', header: t('col.topic'), rowHeader: true, cell: (x) => <TopicLink topic={topicOf(x)} showStatus />, sortValue: (x) => name(topicOf(x)), csv: (x) => x.topic },
    { key: 'hosts', csvHeader: 'hosts', header: sj('col.hosts'), numeric: true, firstDir: 'asc', cell: (x) => fmtInt(x.hosts), sortValue: (x) => x.hosts },
    { key: 'top', csvHeader: 'top_host_share', header: sj('col.topHost'), numeric: true, cell: (x) => fmtPct(x.top_host_share, 0), sortValue: (x) => x.top_host_share },
    { key: 'articles', csvHeader: 'articles_recent', header: t('col.articlesR', { r: span }), numeric: true, cell: (x) => fmtInt(x.articles_recent), sortValue: (x) => x.articles_recent },
  ]
  // fewest journals first: the clearest openings lead
  const cards = [...rows].sort((a, b) => a.hosts - b.hosts || b.articles_recent - a.articles_recent)
  const example = cards[0]
  return (
    <Section
      id="special-issues"
      title={sj('jr.si.h')}
      intro={sj('jr.si.intro', {
        topic: name(topicOf(example)), h: fmtInt(example.hosts),
        statuses: (file.special_issue_statuses ?? []).map((st) => statusName(t, st)).join(lang === 'en' ? ' or ' : 'หรือ'),
        max: fmtInt(file.special_issue_max_hosts ?? 0), a: r.start, b: r.end,
      })}
    >
      <ul className="si-cards" aria-label={s('si.cards')}>
        {cards.map((x) => {
          const tp = topicOf(x)
          return (
            <li key={x.topic} className="si-card">
              <p className="si-name"><TopicLink topic={tp} showStatus /></p>
              <dl className="si-nums">
                <div><dt>{sj('col.hosts')}</dt><dd>{fmtInt(x.hosts)}</dd></div>
                <div><dt>{sj('col.topHost')}</dt><dd>{fmtPct(x.top_host_share, 0)}</dd></div>
                <div><dt>{t('col.articlesR', { r: span })}</dt><dd>{fmtInt(x.articles_recent)}</dd></div>
              </dl>
            </li>
          )
        })}
      </ul>
      <details className="how si-table">
        <summary>{s('si.asTable')}</summary>
        <div>
          <DataTable
            caption={t('table.n', { n: 3, title: sj('jr.si.table') })}
            rows={rows}
            columns={columns}
            rowKey={(x) => x.topic}
            limit={25}
            defaultSort={{ key: 'hosts', dir: 'asc' }}
            csvFilename={`atlas-${release.overview.release}-special-issues.csv`}
          />
        </div>
      </details>
      <HowNote><p>{sj('jr.si.how', { min: fmtInt(file.special_issue_min_host_articles ?? 0) })}</p></HowNote>
    </Section>
  )
}
