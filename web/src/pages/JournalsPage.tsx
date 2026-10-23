import { DataTable, type Column } from '../components/DataTable'
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
import { DASH, fmtInt, fmtNum, fmtPct } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { withPrimary } from '../lib/columns'
import { filterJournals, inhouseFlag, inhouseGap, journalName } from '../lib/journals'
import { statusName } from '../lib/topicText'
import { JOURNAL_SORTS, journalsCodec, TIERS, type JournalSort } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'

export default function JournalsPage() {
  const { t } = useI18n()
  return (
    <RequireRelease title={t('jr.title')}>
      {(release) => (
        <ModuleFile<JournalsFile> release={release} module="journals" path={MODULE_FILES.journals} title={t('jr.title')}>
          {(file) => <Journals release={release} file={file} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

const isSort = (v: string): v is JournalSort => (JOURNAL_SORTS as readonly string[]).includes(v)

function Journals({ release, file }: { release: AtlasRelease; file: JournalsFile }) {
  const { t, lang } = useI18n()
  const [state, update] = useUrlState(journalsCodec)
  const w = file.window
  const rows = filterJournals(file.journals, state.q, state.tier)
  const flagAt = file.inhouse_flag_share ?? null
  /** an empty rate: too few articles to compute it ("low data"), otherwise unknown — never a zero */
  const gap = (j: JournalSummary) => (j.low_data ? t('jr.lowData') : t('jr.unknown'))
  const columns: Column<JournalSummary>[] = withPrimary<JournalSummary>([
    { key: 'id', header: 'id', csvHeader: 'journal_id', cell: () => null, csv: (j) => j.id, csvOnly: true },
    {
      key: 'name', header: t('col.journal'), rowHeader: true, cell: (j) => <JournalLink journal={j} />, sortValue: (j) => journalName(j, lang).text,
      csvCols: [{ header: 'name_th', value: (j) => j.name_th ?? '' }, { header: 'name_en', value: (j) => j.name_en ?? '' }, { header: 'ojs_path', value: (j) => j.path }],
    },
    { key: 'tier', csvHeader: 'tci_tier', header: t('col.tier'), numeric: true, firstDir: 'asc', cell: (j) => (j.tci_tier ? fmtInt(j.tci_tier) : DASH), sortValue: (j) => j.tci_tier ?? 9, csv: (j) => j.tci_tier ?? null },
    { key: 'articles', csvHeader: 'articles_window', header: t('col.articlesW'), numeric: true, cell: (j) => fmtInt(j.articles_window), sortValue: (j) => j.articles_window },
    {
      key: 'completeness', csvHeader: 'completeness', header: t('col.completeness'), unit: t('unit.of100'), numeric: true,
      cell: (j) => (j.completeness == null ? gap(j) : fmtNum(j.completeness, 1)), sortValue: (j) => j.completeness ?? null,
    },
    {
      key: 'inhouse', header: t('col.inhouse'), numeric: true, sortValue: (j) => j.inhouse_share ?? null,
      cell: (j) => (
        j.inhouse_share == null ? (
          <span className="sbar-na">{inhouseGap(j) === 'owner_not_found' ? t('jr.ownerNotFound') : gap(j)}</span>
        ) : (
        <>
          <ShareBar value={j.inhouse_share} />
          {j.owner_source === 'inferred' && j.inhouse_share != null ? <span className="flag">{t('jr.inferred')}</span> : null}
          {inhouseFlag(j, flagAt) ? <span className="flag">{t('jr.flag')}</span> : null}
        </>
        )
      ),
      csvCols: [{ header: 'inhouse_share', value: (j) => j.inhouse_share ?? null }, { header: 'owner_source', value: (j) => j.owner_source ?? '' }],
    },
    {
      key: 'orgs', header: t('col.effOrgs'), numeric: true, cell: (j) => (j.effective_orgs == null ? gap(j) : fmtNum(j.effective_orgs, 1)), sortValue: (j) => j.effective_orgs ?? null,
      csvCols: [{ header: 'effective_orgs', value: (j) => j.effective_orgs ?? null }, { header: 'n_orgs', value: (j) => j.n_orgs ?? 0 }],
    },
    { key: 'foreign', csvHeader: 'foreign_share', header: t('col.foreign'), numeric: true, cell: (j) => (j.foreign_share == null ? gap(j) : fmtPct(j.foreign_share, 0)), sortValue: (j) => j.foreign_share ?? null },
    { key: 'group', csvHeader: 'group', header: t('col.field'), cell: (j) => (j.group ? groupName(release, j.group, lang) : DASH), csv: (j) => j.group ?? '' },
  ], ['articles', 'completeness', 'inhouse', 'orgs'])
  const valid = columns.some((c) => c.key === state.sort && c.sortValue)
  return (
    <div className="container">
      <PageHeader title={t('jr.title')} lede={t('jr.lede', { a: w.start, b: w.end })} />
      <div className="j-tools">
        <label>
          {t('jr.search')}
          <input type="search" value={state.q} onChange={(e) => update({ q: e.target.value })} />
        </label>
        <label>
          {t('jr.tier')}
          <select value={state.tier} onChange={(e) => update({ tier: (TIERS as readonly string[]).includes(e.target.value) ? (e.target.value as (typeof TIERS)[number]) : 'all' })}>
            {TIERS.map((tier) => (
              <option key={tier} value={tier}>{tier === 'all' ? t('jr.tier.all') : tier === 'none' ? t('jr.tier.none') : t('jr.tier.n', { n: tier })}</option>
            ))}
          </select>
        </label>
        <p className="hint" role="status">{t('jr.count', { n: fmtInt(rows.length), total: fmtInt(file.journals.length) })}</p>
      </div>
      <Section id="journals" title={t('jr.table', { a: w.start, b: w.end })}>
        <DataTable
          caption={t('table.n', { n: 1, title: t('jr.table', { a: w.start, b: w.end }) })}
          rows={rows}
          columns={columns}
          rowKey={(j) => j.id}
          sort={valid ? { key: state.sort, dir: state.dir } : { key: 'articles', dir: 'desc' }}
          onSort={(s) => update({ sort: isSort(s.key) ? s.key : 'articles', dir: s.dir })}
          csvFilename={`atlas-${release.overview.release}-journals.csv`}
          empty={t('jr.none')}
          footnote={flagAt != null ? t('jr.foot', { p: fmtPct(flagAt, 0), n: fmtInt(file.min_articles) }) : t('jr.footNoFlag', { n: fmtInt(file.min_articles) })}
        />
        <HowNote><p>{t('jr.how')}</p></HowNote>
      </Section>
      <SpecialIssues release={release} file={file} />
    </div>
  )
}

function SpecialIssues({ release, file }: { release: AtlasRelease; file: JournalsFile }) {
  const { t, lang, name } = useI18n()
  const rows = (file.special_issue ?? []).filter((s) => release.topicById.has(s.topic))
  if (rows.length === 0) return null
  const topicOf = (s: SpecialIssueTopic) => release.topicById.get(s.topic) as Topic
  const columns: Column<SpecialIssueTopic>[] = [
    { key: 'topic', csvHeader: 'topic_id', header: t('col.topic'), rowHeader: true, cell: (s) => <TopicLink topic={topicOf(s)} showStatus />, sortValue: (s) => s.topic, csv: (s) => s.topic },
    { key: 'hosts', csvHeader: 'hosts', header: t('col.hosts'), numeric: true, firstDir: 'asc', cell: (s) => fmtInt(s.hosts), sortValue: (s) => s.hosts },
    { key: 'top', csvHeader: 'top_host_share', header: t('col.topHost'), numeric: true, cell: (s) => fmtPct(s.top_host_share, 0), sortValue: (s) => s.top_host_share },
    { key: 'articles', csvHeader: 'articles_recent', header: t('col.articlesR', { r: `${file.recent.start}–${file.recent.end}` }), numeric: true, cell: (s) => fmtInt(s.articles_recent), sortValue: (s) => s.articles_recent },
  ]
  const r = file.recent
  // the example in the intro: the topic the fewest journals publish
  const example = rows.reduce((a, b) => (b.hosts < a.hosts ? b : a))
  return (
    <Section
      id="special-issues"
      title={t('jr.si.h')}
      intro={t('jr.si.intro', {
        topic: name(topicOf(example)), h: fmtInt(example.hosts),
        statuses: (file.special_issue_statuses ?? []).map((s) => statusName(t, s)).join(lang === 'en' ? ' or ' : 'หรือ'),
        max: fmtInt(file.special_issue_max_hosts ?? 0), a: r.start, b: r.end,
      })}
    >
      <DataTable
        caption={t('table.n', { n: 2, title: t('jr.si.table') })}
        rows={rows}
        columns={columns}
        rowKey={(s) => s.topic}
        defaultSort={{ key: 'hosts', dir: 'asc' }}
        csvFilename={`atlas-${release.overview.release}-special-issues.csv`}
      />
      <HowNote><p>{t('jr.si.how', { min: fmtInt(file.special_issue_min_host_articles ?? 0) })}</p></HowNote>
    </Section>
  )
}
