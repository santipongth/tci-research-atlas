import { DataTable } from '../../components/DataTable'
import { Figure } from '../../components/Figure'
import { StatusLegend } from '../../components/StatusLegend'
import { PortfolioMatrix } from '../../charts/PortfolioMatrix'
import type { AtlasRelease } from '../../data/release'
import type { Topic } from '../../data/types'
import { DEFINITION, fmtWindow, QUADRANTS, quadrantOf, windows, type Quadrant } from '../../lib/definition'
import { fmtInt, fmtPct } from '../../lib/format'
import { useI18n } from '../../lib/i18n'
import { STATUSES } from '../../lib/status'
import { overviewCodec } from '../../lib/urlState'
import { useUrlState } from '../../lib/useUrlState'
import { growthColumn, idColumn, shareColumn, statusColumn, topicColumn, type ColumnContext, columnContext } from '../topicColumns'

/** E2: size × growth with the four portfolio groups. */
export function Portfolio({ release, topics, threshold }: { release: AtlasRelease; topics: readonly Topic[]; threshold: number }) {
  const { t, name, lang } = useI18n()
  const [state, update] = useUrlState(overviewCodec)
  const w = fmtWindow(windows(release.overview.last_complete_year).R)
  const counts = Object.fromEntries(QUADRANTS.map((q) => [q, topics.filter((tp) => quadrantOf(tp, threshold) === q).length])) as Record<Quadrant, number>
  const quadName = (q: Quadrant) => t(`quad.${q}` as const)
  const ctx: ColumnContext = columnContext(release, { t, name, lang })
  const quadRows = QUADRANTS.map((q) => ({ q, count: counts[q] }))
  return (
    <Figure
      id="fig-portfolio"
      number={2}
      title={t('ov.pf.title', { w })}
      source={t('source.line', { release: release.overview.release })}
      view={state.pf}
      onView={(pf) => update({ pf })}
      legend={<StatusLegend plain statuses={STATUSES.filter((s) => s !== 'LOW_DATA')} />}
      how={<p>{t('ov.pf.how', { w, top: fmtPct(1 - DEFINITION.largeQuantile, 0) })}</p>}
      chart={
        <PortfolioMatrix
          topics={topics}
          threshold={threshold}
          ciLevel={release.ciLevel}
          counts={counts}
          labels={{ name: t('ov.pf.h'), x: t('ov.pf.x', { w }), y: t('ov.pf.y'), split: t('ov.pf.split', { v: fmtPct(threshold, 2) }), quadrants: { stars: quadName('stars'), rising: quadName('rising'), mature: quadName('mature'), declining: quadName('declining') } }}
        />
      }
      table={
        <>
          <DataTable
            caption={t('table.n', { n: 2, title: t('ov.pf.quadTable') })}
            rows={quadRows}
            rowKey={(r) => r.q}
            stack={false}
            columns={[
              { key: 'q', csvHeader: 'quadrant', header: t('col.group'), rowHeader: true, cell: (r) => quadName(r.q), csv: (r) => r.q },
              { key: 'meaning', header: t('col.meaning'), cell: (r) => t(`quad.${r.q}.hint` as const) },
              { key: 'count', csvHeader: 'n_topics', header: t('col.topics'), numeric: true, cell: (r) => fmtInt(r.count), sortValue: (r) => r.count },
            ]}
          />
          <DataTable
            caption={t('table.n', { n: 3, title: t('ov.pf.topicTable') })}
            rows={topics}
            rowKey={(r) => r.id}
            defaultSort={{ key: 'share', dir: 'desc' }}
            csvFilename={`atlas-${release.overview.release}-portfolio.csv`}
            columns={[
              idColumn(),
              topicColumn(ctx),
              statusColumn(ctx),
              { key: 'quadrant', csvHeader: 'quadrant', header: t('col.group'), cell: (r) => { const q = quadrantOf(r, threshold); return q ? quadName(q) : '' }, csv: (r) => quadrantOf(r, threshold) ?? '' },
              shareColumn(ctx),
              growthColumn(ctx),
            ]}
          />
        </>
      }
    />
  )
}
