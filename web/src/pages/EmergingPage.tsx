import { DataTable, type Column } from '../components/DataTable'
import { EmptyState } from '../components/EmptyState'
import { Figure } from '../components/Figure'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { StatusGlyph } from '../components/StatusGlyph'
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
import { statusName } from '../lib/topicText'
import { EMERGING_SORTS, emergingCodec, type EmergingSort } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import {
  articlesColumn, ciColumn, ciHighColumn, growthColumn, idColumn, journalsColumn, orgsColumn, ratioColumn, reasonColumn, scoreColumn, shareColumn, topicColumn,
  type ColumnContext,
} from './topicColumns'

export default function EmergingPage() {
  const { t } = useI18n()
  return <RequireRelease title={t('em.title')}>{(release) => <Emerging release={release} />}</RequireRelease>
}

function ruleText(t: I18n['t'], status: StatusId, level: number): string {
  return t(`rule.${status}` as const, ruleVars(level))
}

const isSort = (v: string): v is EmergingSort => (EMERGING_SORTS as readonly string[]).includes(v)

function Emerging({ release }: { release: AtlasRelease }) {
  const { t, name, lang } = useI18n()
  const [state, update] = useUrlState(emergingCodec)
  const level = ciPct(release.ciLevel)
  const ctx: ColumnContext = { t, name, groupName: (g) => groupName(release, g, lang) }
  const st = state.status
  const label = statusName(t, st)
  const counts = Object.fromEntries(STATUSES.map((s) => [s, release.topics.filter((tp) => tp.status === s).length])) as Record<StatusId, number>
  const rows = release.topics.filter((tp) => tp.status === st)
  const columns: Column<Topic>[] =
    st === 'LOW_DATA'
      ? [idColumn(), topicColumn(ctx), articlesColumn(ctx), reasonColumn(ctx), journalsColumn(ctx), orgsColumn(ctx)]
      : [idColumn(), topicColumn(ctx), shareColumn(ctx), growthColumn(ctx), ciColumn(ctx, level), ciHighColumn(), ratioColumn(ctx), journalsColumn(ctx), orgsColumn(ctx), scoreColumn(ctx)]
  const valid = columns.some((c) => c.key === state.sort && c.sortValue)
  const sort = valid ? { key: state.sort, dir: state.dir } : { key: st === 'LOW_DATA' ? 'articles' : 'growth', dir: 'desc' as const }
  const source = t('source.line', { release: release.overview.release, v: release.definitionVersion })
  const table = (
    <DataTable
      caption={t('table.n', { n: 1, title: t('em.table.title', { status: label, n: fmtInt(rows.length) }) })}
      rows={rows}
      columns={columns}
      rowKey={(r) => r.id}
      sort={sort}
      onSort={(s) => update({ sort: isSort(s.key) ? s.key : 'growth', dir: s.dir })}
      csvFilename={`atlas-${release.overview.release}-${st.toLowerCase()}.csv`}
      empty={t('em.none', { status: label })}
    />
  )
  // every topic of the status, strongest first; topics without an interval are listed as text rows, never dropped
  const forest = isSignal(st) ? forestSelection(release.topics, st) : null
  return (
    <div className="container">
      <PageHeader title={t('em.title')} lede={t('em.lede', { level })} />
      {release.topics.length === 0 ? (
        <EmptyState title={t('empty.topics')} />
      ) : (
        <Tabs
          id="em-status"
          label={t('em.tabs')}
          items={STATUSES.map((s) => ({ id: s, label: statusName(t, s), icon: <StatusGlyph status={s} size={13} />, count: counts[s] }))}
          value={st}
          onChange={(s) => update({ status: isStatus(s) ? s : 'EMERGING', sort: s === 'LOW_DATA' ? 'articles' : 'growth', dir: 'desc' })}
        >
          <p className="rule">{ruleText(t, st, level)}</p>
          {st === 'WATCH' ? (
            <div className="inset">
              <b><StatusGlyph status="WATCH" size={14} />{t('journalDriven')}</b>
              <p>{t('journalDrivenBody')}</p>
            </div>
          ) : null}
          {forest && isSignal(st) && forest.rows.length > 0 ? (
            <Figure
              id="fig-em"
              number={1}
              title={t('em.fig.title', { status: label, level })}
              source={source}
              view={state.view}
              onView={(view) => update({ view })}
              chart={
                <ForestPlot
                  groups={[{ status: st, title: label, rows: forest.rows, total: forest.total, noCi: forest.noCi }]}
                  axisLabel={t('ov.forest.axis')}
                  refLabel={t('ov.forest.bar', { v: fmtSignedPct(DEFINITION.emergingMinGrowthLo, 0) })}
                  subtitle={(tp) => groupName(release, tp.group, lang)}
                />
              }
              table={table}
            />
          ) : (
            <>
              {table}
              <p className="source">{source}</p>
            </>
          )}
          {rows.some((r) => r.metrics.orgs_unverified) ? <p className="note">{t('em.dagger')}</p> : null}
        </Tabs>
      )}
      <Keywords release={release} />
    </div>
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
  const columns: Column<EmergingKeyword>[] = [
    { key: 'term', header: t('col.term'), rowHeader: true, cell: (k) => k.term, sortValue: (k) => k.term },
    { key: 'count', header: t('col.articlesR'), numeric: true, cell: (k) => fmtInt(k.count_recent), sortValue: (k) => k.count_recent },
    { key: 'growth', header: t('col.growth'), numeric: true, cell: (k) => fmtSignedPct(k.growth), sortValue: (k) => k.growth },
    { key: 'lo', header: t('col.growthLo'), numeric: true, cell: (k) => fmtSignedPct(k.growth_lo), sortValue: (k) => k.growth_lo },
    { key: 'ratio', header: t('col.ratio'), numeric: true, cell: (k) => (k.no_baseline || k.share_ratio === null ? t('noBaseline') : fmtRatio(k.share_ratio)), sortValue: (k) => (k.no_baseline ? 1e9 : k.share_ratio), csv: (k) => k.share_ratio },
    { key: 'years', header: t('col.years'), numeric: true, cell: (k) => fmtInt(k.n_active_years), sortValue: (k) => k.n_active_years },
    { key: 'orgs', header: t('col.orgs'), numeric: true, cell: (k) => fmtInt(k.n_orgs_R), sortValue: (k) => k.n_orgs_R },
    { key: 'journals', header: t('col.journals'), numeric: true, cell: (k) => fmtInt(k.n_journals_R), sortValue: (k) => k.n_journals_R },
    {
      key: 'topic',
      header: t('col.linkedTopic'),
      cell: (k) => {
        const tp = k.topic ? release.topicById.get(k.topic) : undefined
        return tp ? <TopicLink topic={tp} showStatus /> : DASH
      },
      csv: (k) => k.topic ?? '',
    },
  ]
  return (
    <Section id="keywords" title={t('em.kw.h')} intro={t('em.kw.intro', { b: fmtWindow(w.B), o: DEFINITION.minOrgs, ky: DEFINITION.keywordMinActiveYears })}>
      <DataTable
        caption={t('table.n', { n: 2, title: t('em.kw.table', { n: fmtInt(rows.length) }) })}
        rows={rows}
        columns={columns}
        rowKey={(k) => k.term}
        defaultSort={{ key: 'growth', dir: 'desc' }}
        csvFilename={`atlas-${release.overview.release}-emerging-keywords.csv`}
      />
      {excluded > 0 ? <p className="note">{t('em.kw.excluded', { n: fmtInt(excluded) })}</p> : null}
    </Section>
  )
}
