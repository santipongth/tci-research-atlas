import { lazy, Suspense, useState } from 'react'
import { DataTable, type Column } from '../components/DataTable'
import { EmptyState } from '../components/EmptyState'
import { Figure } from '../components/Figure'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { SourceLine } from '../components/SourceLine'
import { StatusGlyph } from '../components/StatusGlyph'
import { PhoneFold } from '../components/PhoneFold'
import { StatusFlowchart } from '../components/StatusFlowchart'
import { Tabs } from '../components/Tabs'
import { TopicLink } from '../components/TopicLink'
import { ForestPlot } from '../charts/ForestPlot'
import { groupName, type AtlasRelease } from '../data/release'
import type { EmergingKeyword, Topic } from '../data/types'
import { DEFINITION, fmtWindow, ruleVars, windows } from '../lib/definition'
import { ciPct, DASH, fmtInt, fmtRatio, fmtSignedPct } from '../lib/format'
import { forestSelection } from '../lib/forest'
import { useI18n, type I18n } from '../lib/i18n'
import { isSignal, isStatus, STATUSES, type StatusId } from '../lib/status'
import { withPrimary } from '../lib/columns'
import { figureCsv } from '../lib/tableCsv'
import { statusMeaning, statusName } from '../lib/topicText'
import { EMERGING_SORTS, emergingCodec, type EmergingSort } from '../lib/urlState'
import { sortBy } from '../lib/sort'
import { useUrlState } from '../lib/useUrlState'
import {
  articlesColumn, ciColumn, ciHighColumn, growthColumn, idColumn, journalsColumn, orgsColumn, ratioColumn, reasonColumn, scoreColumn, shareColumn, topicColumn,
  type ColumnContext, columnContext,
} from './topicColumns'

// The embed code for the top-10 widget loads on demand (this page is in the entry chunk).
const EmbedSnippet = lazy(() => import('../embed/EmbedTools').then((m) => ({ default: m.EmbedSnippet })))

export default function EmergingPage() {
  const { t } = useI18n()
  return <RequireRelease title={t('em.title')}>{(release) => <Emerging release={release} />}</RequireRelease>
}

function ruleText(t: I18n['t'], status: StatusId, level: number): string {
  return t(`rule.${status}` as const, ruleVars(level))
}

/** Rows drawn in the interval chart before "show all": with hundreds of topics in a status the table carries the rest. */
const FOREST_ROWS = 25

const isSort = (v: string): v is EmergingSort => (EMERGING_SORTS as readonly string[]).includes(v)

function Emerging({ release }: { release: AtlasRelease }) {
  const { t, name, lang } = useI18n()
  const [state, update] = useUrlState(emergingCodec)
  const level = ciPct(release.ciLevel)
  const ctx: ColumnContext = columnContext(release, { t, name, lang })
  const st = state.status
  const [expanded, setExpanded] = useState<ReadonlySet<StatusId>>(() => new Set())
  const label = statusName(t, st)
  const counts = Object.fromEntries(STATUSES.map((s) => [s, release.topics.filter((tp) => tp.status === s).length])) as Record<StatusId, number>
  const rows = release.topics.filter((tp) => tp.status === st)
  const columns: Column<Topic>[] =
    st === 'LOW_DATA'
      ? [idColumn(), topicColumn(ctx), articlesColumn(ctx), reasonColumn(ctx), journalsColumn(ctx), orgsColumn(ctx)]
      : withPrimary([idColumn(), topicColumn(ctx), shareColumn(ctx), growthColumn(ctx), ciColumn(ctx), ciHighColumn(), ratioColumn(ctx), journalsColumn(ctx), orgsColumn(ctx), scoreColumn(ctx)], ['growth', 'lo', 'journals', 'score'])
  const valid = columns.some((c) => c.key === state.sort && c.sortValue)
  const sort = valid ? { key: state.sort, dir: state.dir } : { key: st === 'LOW_DATA' ? 'articles' : 'growth', dir: 'desc' as const }
  const source = t('source.line', { release: release.overview.release })
  const tableTitle = t('table.n', { n: 1, title: t('em.table.title', { status: label, n: fmtInt(rows.length) }) })
  const csvName = `atlas-${release.overview.release}-${st.toLowerCase()}.csv`
  const sortCol = columns.find((c) => c.key === sort.key)
  const table = (
    <DataTable
      caption={tableTitle}
      rows={rows}
      columns={columns}
      rowKey={(r) => r.id}
      limit={50}
      sort={sort}
      onSort={(s) => update({ sort: isSort(s.key) ? s.key : 'growth', dir: s.dir })}
      csvFilename={csvName}
      empty={t('em.none', { status: label })}
      footnote={rows.some((r) => r.metrics.orgs_unverified) ? t('orgsFoot') : undefined}
    />
  )
  // every topic of the status, strongest first; topics without an interval are listed as text rows, never dropped
  const showAll = expanded.has(st)
  const forest = isSignal(st) ? forestSelection(release.topics, st, showAll ? Infinity : FOREST_ROWS) : null
  const flipAll = () => setExpanded((prev) => { const next = new Set(prev); if (next.has(st)) next.delete(st); else next.add(st); return next })
  const example = sortBy(release.topics.filter((tp) => tp.status === 'EMERGING'), (tp) => tp.score, 'desc')[0]
  const lede = example ? t('em.lede', { release: release.overview.release, n: fmtInt(counts.EMERGING), topic: name(example) }) : t('em.ledePlain', { release: release.overview.release })
  const bar = fmtSignedPct(DEFINITION.emergingMinGrowthLo, 0)
  return (
    <div className="container">
      <PageHeader title={t('em.q')} lede={lede} />
      {release.topics.length ? <StatusSteps topics={release.topics} status={st} level={level} /> : null}
      {release.topics.length === 0 ? (
        <EmptyState title={t('empty.topics')} />
      ) : (
        <Tabs
          id="em-status"
          label={t('em.tabs')}
          items={STATUSES.map((s) => ({ id: s, label: statusName(t, s), icon: <StatusGlyph status={s} size={13} />, count: counts[s] }))}
          value={st}
          onChange={(s) => update({ status: isStatus(s) ? s : 'EMERGING', sort: s === 'LOW_DATA' ? 'articles' : 'growth', dir: 'desc' })}
          strip
        >
          <p className="st-lead">
            <StatusGlyph status={st} size={16} />
            <b>{label}</b>
            <span>— {statusMeaning(t, st)}</span>
          </p>
          {/* with a chart the full rule sits in its "วิธีอ่าน"; a table-only status keeps it here */}
          {forest && forest.rows.length > 0 ? null : <p className="rule">{ruleText(t, st, level)}</p>}
          {st === 'WATCH' ? (
            <div className="inset">
              <b><StatusGlyph status="WATCH" size={14} />{t('journalDriven')}</b>
              <p>{t('journalDrivenBody', ruleVars(level))}</p>
            </div>
          ) : null}
          {forest && isSignal(st) && forest.rows.length > 0 ? (
            <Figure
              id="fig-em"
              number={1}
              title={t('em.fig.title', { status: label, level })}
              tableTitle={tableTitle}
              csv={figureCsv(csvName, sortCol?.sortValue ? sortBy(rows, sortCol.sortValue, sort.dir) : rows, columns)}
              toggle="buttons"
              how={
                <>
                  <p><b>{label}:</b> {ruleText(t, st, level)}</p>
                  <p>{t('em.how', { level, bar })}</p>
                  <p>{t('rule.how', { level })}</p>
                </>
              }
              source={source}
              view={state.view}
              onView={(view) => update({ view })}
              chart={
                <ForestPlot
                  groups={[{ status: st, title: label, rows: forest.rows, total: forest.total, noCi: forest.noCi, more: forest.total > FOREST_ROWS ? { onClick: flipAll, expanded: showAll, label: showAll ? t('em.forest.fewer', { n: FOREST_ROWS }) : t('seeAll', { n: fmtInt(forest.total) }) } : undefined }]}
                  level={level}
                  base={ctx.base}
                  axisLabel={t('ov.forest.axis')}
                  refLabel={t('ov.forest.bar', { v: bar })}
                  subtitle={(tp) => groupName(release, tp.group, lang)}
                  wide
                />
              }
              table={table}
            />
          ) : (
            <>
              {table}
              <SourceLine text={source} />
            </>
          )}
          {rows.some((r) => r.metrics.orgs_unverified) ? <p className="note">{t('em.dagger')}</p> : null}
        </Tabs>
      )}
      {counts.EMERGING + counts.WATCH > 0 ? (
        <Suspense fallback={null}>
          <EmbedSnippet kind="emerging" path="emerging" height={780} />
        </Suspense>
      ) : null}
      <Keywords release={release} />
    </div>
  )
}

/** The status rule as a decision diagram (the open tab's status is marked), folded on phones. */
function StatusSteps({ topics, status, level }: { topics: readonly Topic[]; status: StatusId; level: number }) {
  const { t } = useI18n()
  return (
    <PhoneFold id="em-steps-h" className="em-steps" headingClass="em-steps-h" heading={t('steps.h')}>
      <StatusFlowchart topics={topics} level={level} current={status} />
    </PhoneFold>
  )
}

/** Emerging keywords (independent of clustering); hidden when the release has none. */
function Keywords({ release }: { release: AtlasRelease }) {
  const { t } = useI18n()
  const all = release.keywords ?? []
  const rows = all.filter((k) => k.emerging)
  if (rows.length === 0) return null
  const excluded = all.filter((k) => !k.emerging && k.journal_driven).length
  const w = windows(release.overview.last_complete_year)
  const base = fmtWindow(w.B)
  const top = sortBy(rows, (k) => k.growth, 'desc')[0]
  const columns: Column<EmergingKeyword>[] = [
    { key: 'term', csvHeader: 'term', header: t('col.term'), rowHeader: true, cell: (k) => k.term, sortValue: (k) => k.term },
    { key: 'count', csvHeader: 'count_recent', header: t('col.articlesR', { r: fmtWindow(w.R) }), numeric: true, cell: (k) => fmtInt(k.count_recent), sortValue: (k) => k.count_recent },
    { key: 'growth', csvHeader: 'growth', header: t('col.growth'), numeric: true, cell: (k) => fmtSignedPct(k.growth), sortValue: (k) => k.growth },
    { key: 'lo', csvHeader: 'growth_lo', header: t('col.growthLo'), numeric: true, cell: (k) => fmtSignedPct(k.growth_lo), sortValue: (k) => k.growth_lo },
    { key: 'ratio', csvHeader: 'share_ratio', header: t('col.ratio', { base }), numeric: true, cell: (k) => (k.no_baseline || k.share_ratio === null ? t('noBaseline', { base }) : fmtRatio(k.share_ratio)), sortValue: (k) => (k.no_baseline ? 1e9 : k.share_ratio), csv: (k) => k.share_ratio },
    { key: 'years', csvHeader: 'n_active_years', header: t('col.years'), numeric: true, cell: (k) => fmtInt(k.n_active_years), sortValue: (k) => k.n_active_years },
    { key: 'orgs', csvHeader: 'n_orgs_R', header: t('col.orgs'), numeric: true, cell: (k) => fmtInt(k.n_orgs_R), sortValue: (k) => k.n_orgs_R },
    { key: 'journals', csvHeader: 'n_journals_R', header: t('col.journals'), numeric: true, cell: (k) => fmtInt(k.n_journals_R), sortValue: (k) => k.n_journals_R },
    {
      key: 'topic',
      csvHeader: 'topic_id',
      header: t('col.linkedTopic'),
      cell: (k) => {
        const tp = k.topic ? release.topicById.get(k.topic) : undefined
        return tp ? <TopicLink topic={tp} showStatus /> : DASH
      },
      csv: (k) => k.topic ?? '',
    },
  ]
  return (
    <Section id="keywords" title={t('em.kw.h')} intro={t('em.kw.intro', { k: top.term, b: base, o: DEFINITION.minOrgs, ky: DEFINITION.keywordMinActiveYears })}>
      <DataTable
        caption={t('table.n', { n: 2, title: t('em.kw.table', { n: fmtInt(rows.length) }) })}
        rows={rows}
        columns={columns}
        rowKey={(k) => k.term}
        limit={25}
        defaultSort={{ key: 'growth', dir: 'desc' }}
        csvFilename={`atlas-${release.overview.release}-emerging-keywords.csv`}
      />
      {excluded > 0 ? <p className="note">{t('em.kw.excluded', { n: fmtInt(excluded) })}</p> : null}
    </Section>
  )
}
