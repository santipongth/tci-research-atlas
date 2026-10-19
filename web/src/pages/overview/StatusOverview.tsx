import { DataTable } from '../../components/DataTable'
import { Figure } from '../../components/Figure'
import { StatusChip, StatusGlyph } from '../../components/StatusGlyph'
import { ForestPlot, type ForestGroup } from '../../charts/ForestPlot'
import { groupName, type AtlasRelease } from '../../data/release'
import { DEFINITION } from '../../lib/definition'
import { ciPct, fmtInt, fmtSignedPct } from '../../lib/format'
import { useI18n } from '../../lib/i18n'
import { sortBy } from '../../lib/sort'
import { SIGNAL_STATUSES, STATUSES } from '../../lib/status'
import { statusName } from '../../lib/topicText'
import { overviewCodec } from '../../lib/urlState'
import { useUrlState } from '../../lib/useUrlState'
import { ciColumn, ciHighColumn, growthColumn, idColumn, journalsColumn, orgsColumn, statusColumn, topicColumn, type ColumnContext } from '../topicColumns'

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
    const all = release.topics.filter((tp) => tp.status === st && tp.metrics.share_growth_lo != null && tp.metrics.share_growth_hi != null)
    const rows = sortBy(all, (tp) => tp.metrics.share_growth, st === 'DECLINING' ? 'asc' : 'desc').slice(0, PER_STATUS)
    const total = counts[st] ?? all.length
    return {
      status: st,
      title: statusName(t, st),
      rows,
      total,
      note: st === 'WATCH' && rows.length ? (
        <div className="inset">
          <b><StatusGlyph status="WATCH" size={14} />{t('journalDriven')}</b>
          <p>{t('journalDrivenBody')}</p>
        </div>
      ) : undefined,
      more: total > rows.length ? { to: `/emerging?status=${st}`, label: t('seeAll', { n: fmtInt(total) }) } : undefined,
    }
  }).filter((g) => g.rows.length > 0)
  const rows = groups.flatMap((g) => g.rows)
  const nUnverified = release.manifest.n_orgs_unverified ?? 0
  return (
    <>
      <dl className="st-sum">
        {STATUSES.map((st) => (
          <div key={st}>
            <dt><StatusChip status={st} label={statusName(t, st)} /></dt>
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
          source={t('source.line', { release: release.overview.release, v: release.definitionVersion })}
          view={state.st}
          onView={(st) => update({ st })}
          chart={<ForestPlot groups={groups} axisLabel={t('ov.forest.axis')} refLabel={t('ov.forest.bar', { v: bar })} subtitle={(tp) => groupName(release, tp.group, lang)} />}
          table={
            <DataTable
              caption={t('table.n', { n: 1, title: t('ov.forest.table', { n: 1 }) })}
              rows={rows}
              columns={[idColumn(), topicColumn(ctx), statusColumn(ctx), growthColumn(ctx), ciColumn(ctx, level), ciHighColumn(), journalsColumn(ctx), orgsColumn(ctx)]}
              rowKey={(r) => r.id}
              csvFilename={`atlas-${release.overview.release}-status-intervals.csv`}
            />
          }
        />
      ) : null}
      <details className="how">
        <summary>{t('ov.howCI')}</summary>
        <div>{t('ov.howCI.body', { level, bar })}</div>
      </details>
    </>
  )
}
