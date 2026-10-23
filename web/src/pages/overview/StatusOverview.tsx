import { DataTable } from '../../components/DataTable'
import { Figure } from '../../components/Figure'
import { Term } from '../../components/Term'
import { StatusChip, StatusGlyph } from '../../components/StatusGlyph'
import { ForestPlot, type ForestGroup } from '../../charts/ForestPlot'
import { groupName, type AtlasRelease } from '../../data/release'
import { DEFINITION, ruleVars } from '../../lib/definition'
import { ciPct, fmtInt, fmtSignedPct } from '../../lib/format'
import { forestSelection } from '../../lib/forest'
import { useI18n } from '../../lib/i18n'
import { SIGNAL_STATUSES, STATUSES } from '../../lib/status'
import { withPrimary } from '../../lib/columns'
import { figureCsv } from '../../lib/tableCsv'
import { statusMeaning, statusName } from '../../lib/topicText'
import { overviewCodec } from '../../lib/urlState'
import { useUrlState } from '../../lib/useUrlState'
import { ciColumn, ciHighColumn, growthColumn, idColumn, journalsColumn, orgsColumn, ratioColumn, statusColumn, topicColumn, type ColumnContext } from '../topicColumns'

const PER_STATUS = 8

/** E3: six-status summary + forest plot of the strongest signals (all rows in /emerging). */
export function StatusOverview({ release }: { release: AtlasRelease }) {
  const { t, name, lang } = useI18n()
  const [state, update] = useUrlState(overviewCodec)
  const counts = release.overview.status_counts
  const level = ciPct(release.ciLevel)
  const bar = fmtSignedPct(DEFINITION.emergingMinGrowthLo, 0)
  const ctx: ColumnContext = { t, name, groupName: (g) => groupName(release, g, lang) }
  const groups: ForestGroup[] = SIGNAL_STATUSES.map((st) => {
    // every topic of the status counts; one without an interval is listed as a text row, never dropped
    const { rows, total, noCi } = forestSelection(release.topics, st, PER_STATUS)
    return {
      status: st,
      title: statusName(t, st),
      rows,
      total,
      noCi,
      note: st === 'WATCH' && rows.length ? (
        <div className="inset">
          <b><StatusGlyph status="WATCH" size={14} />{t('journalDriven')}</b>
          <p>{t('journalDrivenBody', ruleVars(level))}</p>
        </div>
      ) : undefined,
      more: total > rows.length ? { to: `/emerging?status=${st}`, label: t('seeAll', { n: fmtInt(total) }) } : undefined,
    }
  }).filter((g) => g.rows.length > 0)
  const rows = groups.flatMap((g) => g.rows)
  const columns = withPrimary([idColumn(), topicColumn(ctx), statusColumn(ctx), growthColumn(ctx), ciColumn(ctx, level), ciHighColumn(), ratioColumn(ctx), journalsColumn(ctx), orgsColumn(ctx)], ['status', 'growth', 'lo', 'journals'])
  const tableTitle = t('table.n', { n: 1, title: t('ov.forest.table', { n: 1 }) })
  const nUnverified = release.manifest.n_orgs_unverified ?? 0
  return (
    <>
      <dl className="st-sum">
        {STATUSES.map((st) => (
          <div key={st}>
            <dt>
              <StatusChip status={st} label={statusName(t, st)} />
              <span className="st-mean">{statusMeaning(t, st)}</span>
            </dt>
            <dd>
              {fmtInt(counts[st] ?? 0)}
              <small>{t('ov.status.of', { n: fmtInt(release.topics.length) })}</small>
            </dd>
          </div>
        ))}
      </dl>
      {nUnverified > 0 ? <p className="note">{t('ov.orgsNote', { n: fmtInt(nUnverified) })}</p> : null}
      {rows.length > 0 ? (
        <Figure
          id="fig-status"
          number={1}
          title={t('ov.forest.title', { level, n: PER_STATUS })}
          tableTitle={tableTitle}
          csv={figureCsv(`atlas-${release.overview.release}-status-intervals.csv`, rows, columns)}
          how={
            <>
              <p>{t('ov.howCI.body', { level, bar })}</p>
              <p className="how-terms">
                <span>{t('glossary.terms')}:</span>
                <Term term="ci" />
                <span aria-hidden="true">·</span>
                <Term term="shareGrowth" />
                <span aria-hidden="true">·</span>
                <Term term="baseline" />
              </p>
            </>
          }
          source={t('source.line', { release: release.overview.release })}
          view={state.st}
          onView={(st) => update({ st })}
          chart={<ForestPlot groups={groups} level={level} axisLabel={t('ov.forest.axis')} refLabel={t('ov.forest.bar', { v: bar })} subtitle={(tp) => groupName(release, tp.group, lang)} />}
          table={
            <DataTable
              caption={tableTitle}
              rows={rows}
              columns={columns}
              rowKey={(r) => r.id}
              footnote={rows.some((r) => r.metrics.orgs_unverified) ? t('orgsFoot') : undefined}
            />
          }
        />
      ) : null}
    </>
  )
}
